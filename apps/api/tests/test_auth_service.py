"""Tests for authentication (RF-01)."""

from __future__ import annotations

import pytest

from app.core.security import JwtTokenService, PasswordHasher
from app.domain.errors import AuthenticationError
from app.repositories.memory import InMemoryUserRepository
from app.services.auth_service import AuthService
from tests.conftest import DEMO_EMAIL, DEMO_PASSWORD


class TestPasswordHasher:
    def test_verifies_its_own_hash(self, password_hasher: PasswordHasher) -> None:
        digest = password_hasher.hash("s3cret")
        assert password_hasher.verify("s3cret", digest)

    def test_rejects_a_wrong_password(self, password_hasher: PasswordHasher) -> None:
        digest = password_hasher.hash("s3cret")
        assert not password_hasher.verify("other", digest)

    def test_rejects_a_malformed_hash(self, password_hasher: PasswordHasher) -> None:
        assert not password_hasher.verify("s3cret", "not-a-bcrypt-hash")


class TestAuthServiceLogin:
    async def test_returns_a_token_for_valid_credentials(
        self, auth_service: AuthService
    ) -> None:
        token = await auth_service.login(DEMO_EMAIL, DEMO_PASSWORD)

        assert token.access_token
        assert token.token_type == "bearer"
        assert token.expires_in == 8 * 3600

    async def test_rejects_a_wrong_password(self, auth_service: AuthService) -> None:
        with pytest.raises(AuthenticationError):
            await auth_service.login(DEMO_EMAIL, "wrong-password")

    async def test_rejects_an_unknown_email(self, auth_service: AuthService) -> None:
        with pytest.raises(AuthenticationError):
            await auth_service.login("nobody@aduana.mx", DEMO_PASSWORD)


class TestAuthServiceTokenResolution:
    async def test_resolves_the_user_behind_a_token(self, auth_service: AuthService) -> None:
        token = await auth_service.login(DEMO_EMAIL, DEMO_PASSWORD)

        user = await auth_service.get_user_from_token(token.access_token)

        assert user.email == DEMO_EMAIL

    async def test_rejects_a_tampered_token(self, auth_service: AuthService) -> None:
        with pytest.raises(AuthenticationError):
            await auth_service.get_user_from_token("not.a.jwt")

    async def test_rejects_a_token_signed_with_another_secret(
        self,
        user_repository: InMemoryUserRepository,
        password_hasher: PasswordHasher,
        auth_service: AuthService,
    ) -> None:
        foreign = JwtTokenService(secret="another-secret-that-is-also-32-bytes-long")
        forged = foreign.create_access_token("1", DEMO_EMAIL)

        with pytest.raises(AuthenticationError):
            await auth_service.get_user_from_token(forged)

    async def test_rejects_a_token_of_a_deleted_user(
        self, token_service: JwtTokenService, password_hasher: PasswordHasher
    ) -> None:
        empty_repository = InMemoryUserRepository()
        service = AuthService(empty_repository, password_hasher, token_service)
        orphan = token_service.create_access_token("999", DEMO_EMAIL)

        with pytest.raises(AuthenticationError):
            await service.get_user_from_token(orphan)


class TestSeedIdempotency:
    async def test_upsert_does_not_duplicate_the_user(
        self, user_repository: InMemoryUserRepository, password_hasher: PasswordHasher
    ) -> None:
        from app.domain.models import User

        first = await user_repository.get_by_email(DEMO_EMAIL)
        await user_repository.upsert_by_email(
            User(email=DEMO_EMAIL, password_hash=password_hasher.hash("new-password"))
        )
        second = await user_repository.get_by_email(DEMO_EMAIL)

        assert first is not None and second is not None
        assert first.id == second.id
        assert password_hasher.verify("new-password", second.password_hash)
