"""Authentication use cases."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.security import JwtTokenService, PasswordHasher
from app.domain.errors import AuthenticationError
from app.domain.models import User
from app.repositories.base import UserRepository


@dataclass(frozen=True)
class AccessToken:
    """Result of a successful login."""

    access_token: str
    expires_in: int
    token_type: str = "bearer"


class AuthService:
    """Validates credentials and issues access tokens.

    Collaborators are injected so the service can be exercised with an
    in-memory repository and without touching the environment.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: JwtTokenService,
    ) -> None:
        self._users = user_repository
        self._hasher = password_hasher
        self._tokens = token_service

    async def login(self, email: str, password: str) -> AccessToken:
        """Authenticate a user and return a signed access token.

        Raises:
            AuthenticationError: when the email is unknown or the password is
                wrong. The same message is used for both cases so the endpoint
                does not leak which emails exist.
        """
        user = await self._users.get_by_email(email)
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("Credenciales inválidas")

        return AccessToken(
            access_token=self._tokens.create_access_token(str(user.id), user.email),
            expires_in=self._tokens.expires_in_seconds,
        )

    async def get_user_from_token(self, token: str) -> User:
        """Resolve the user referenced by a bearer token.

        Raises:
            AuthenticationError: when the token is invalid, expired, or points
                at a user that no longer exists.
        """
        payload = self._tokens.decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token inválido")

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("El usuario del token ya no existe")
        return user
