# provider.py — взаимодействует с Telegram: формирует адрес входа и получает подтверждённые данные пользователя.

import asyncio
import secrets
import time
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oidc.core import CodeIDToken
from joserfc import jwt
from joserfc.jwk import KeySet

ISSUER = "https://oauth.telegram.org"
AUTHORIZE_URL = ISSUER + "/auth"
TOKEN_URL = ISSUER + "/token"
JWKS_URL = ISSUER + "/.well-known/jwks.json"


class TelegramProvider:
    """Authlib handles OAuth/PKCE and JWT validation. No UserInfo request is made."""

    def __init__(self, settings):
        self.settings = settings
        self._keys: dict | None = None
        self._keys_until = 0.0
        self._keys_lock = asyncio.Lock()

    def client(self) -> AsyncOAuth2Client:
        return AsyncOAuth2Client(
            client_id=self.settings.telegram_client_id,
            client_secret=self.settings.telegram_client_secret.get_secret_value(),
            redirect_uri=self.settings.callback_url,
            scope="openid profile",  # No phone number or messaging consent requested here.
            token_endpoint_auth_method="client_secret_basic",
            code_challenge_method="S256",
            timeout=10.0,
        )

    async def authorization_url(self, state: str, verifier: str, nonce: str) -> str:
        async with self.client() as client:
            url, _ = client.create_authorization_url(
                AUTHORIZE_URL,
                state=state,
                code_verifier=verifier,
                nonce=nonce,
            )
            return url

    async def keys(self, force: bool = False) -> dict:
        async with self._keys_lock:
            if not force and self._keys and time.monotonic() < self._keys_until:
                return self._keys
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=False
            ) as client:
                response = await client.get(JWKS_URL)
                response.raise_for_status()
                keys = response.json()
            if not isinstance(keys, dict) or not isinstance(keys.get("keys"), list):
                raise ValueError("Invalid JWKS")
            self._keys, self._keys_until = keys, time.monotonic() + 300
            return keys

    async def exchange(self, code: str, verifier: str, nonce: str) -> dict[str, Any]:
        async with self.client() as client:
            token = await client.fetch_token(
                TOKEN_URL,
                code=code,
                code_verifier=verifier,
                client_id=self.settings.telegram_client_id,
            )
        encoded = token.get("id_token")
        if not isinstance(encoded, str) or len(encoded) > 16384:
            raise ValueError("Missing ID token")
        # Allow only the documented default signing algorithm, never token-selected 'none'/HS256.
        options = {
            "iss": {"essential": True, "value": ISSUER},
            "aud": {"essential": True, "value": self.settings.telegram_client_id},
            "exp": {"essential": True},
            "iat": {"essential": True},
            "sub": {"essential": True},
            "nonce": {"essential": True},
        }
        params = {
            "client_id": self.settings.telegram_client_id,
            "nonce": nonce,
            "access_token": token.get("access_token"),
        }
        keys = await self.keys()
        for attempt in range(2):
            try:
                decoded = jwt.decode(
                    encoded, KeySet.import_key_set(keys), algorithms=["RS256"]
                )
                claims = CodeIDToken(
                    decoded.claims, decoded.header, options=options, params=params
                )
                claims.validate(leeway=30)
                break
            except Exception:
                if attempt:
                    raise
                keys = await self.keys(force=True)  # Permit key rotation once.
        if not isinstance(claims.get("sub"), str) or not (
            1 <= len(claims["sub"]) <= 255
        ):
            raise ValueError("Invalid subject")
        if not isinstance(claims.get("nonce"), str) or not secrets.compare_digest(
            claims["nonce"], nonce
        ):
            raise ValueError("Invalid nonce")
        return dict(claims)
