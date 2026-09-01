"""Password hashing and JWT issuing/verification.

Both concerns are wrapped in small classes rather than exposed as free
functions so that services depend on an injected collaborator and tests can
substitute a fake without monkey-patching a module.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.domain.errors import AuthenticationError


class PasswordHasher:
    """Hash and verify passwords with bcrypt.

    The ``bcrypt`` package is used directly instead of passlib: passlib's bcrypt
    backend is unmaintained and warns loudly against modern bcrypt releases.
    """

    def hash(self, plain_password: str) -> str:
        """Return a salted bcrypt hash for the given password."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return True when the password matches the stored hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except ValueError:
            # Raised when the stored value is not a valid bcrypt hash.
            return False


class JwtTokenService:
    """Issue and validate the HS256 access tokens used by the API."""

    def __init__(self, secret: str, algorithm: str = "HS256", expire_hours: int = 8) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_hours = expire_hours

    @property
    def expires_in_seconds(self) -> int:
        """Token lifetime in seconds, for the login response."""
        return self._expire_hours * 3600

    def create_access_token(self, user_id: str, email: str) -> str:
        """Return a signed token identifying the given user."""
        issued_at = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "email": email,
            "iat": issued_at,
            "exp": issued_at + timedelta(hours=self._expire_hours),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> dict:
        """Return the token payload, or raise ``AuthenticationError``."""
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("El token ha expirado") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token inválido") from exc
