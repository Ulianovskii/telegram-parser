import base64
import hashlib
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import respx
from fastapi import Depends, FastAPI
from joserfc import jwt
from joserfc.jwk import RSAKey
from product_auth import AuthModule, AuthSettings, User
from product_auth.models import Base, LoginFlow, Session
from product_auth.module import digest
from product_auth.provider import AUTHORIZE_URL, ISSUER, JWKS_URL, TOKEN_URL
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def signing_key():
    return RSAKey.generate_key(2048, parameters={"kid": "test-1"})


@pytest.fixture
async def env(tmp_path, signing_key):
    settings = AuthSettings(
        origin="https://product.test",
        telegram_client_id="12345",
        telegram_client_secret="test-secret",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/auth.db",
    )
    engine = create_async_engine(settings.database_url.get_secret_value())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    auth = AuthModule(settings, factory)
    app = FastAPI()
    app.include_router(auth.router)

    @app.post("/private")
    async def private(user: User = Depends(auth.require_user)):
        return {"user_id": user.id}

    with respx.mock(assert_all_called=False) as mock:
        mock.get(JWKS_URL).mock(
            return_value=httpx.Response(
                200, json={"keys": [signing_key.as_dict(private=False)]}
            )
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=settings.origin
        ) as client:
            yield settings, auth, factory, app, client, mock, signing_key
    await engine.dispose()


async def start_flow(env, client=None):
    settings, auth, factory, app, default_client, mock, key = env
    client = client or default_client
    response = await client.get("/auth/telegram/start", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith(AUTHORIZE_URL + "?")
    params = parse_qs(urlsplit(response.headers["location"]).query)
    assert params["scope"] == ["openid profile"]
    assert params["redirect_uri"] == [settings.callback_url]
    assert params["code_challenge_method"] == ["S256"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    async with factory() as db:
        flow = await db.get(LoginFlow, digest(params["state"][0]))
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(flow.verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        assert params["code_challenge"] == [challenge]
    return params


def mock_token(env, params, patch=None, remove=(), signing_key=None):
    settings, auth, factory, app, client, mock, key = env
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": settings.telegram_client_id,
        "sub": "oidc-subject-001",
        "id": 987654321,
        "name": "Тестовый пользователь",
        "preferred_username": "test_user",
        "iat": now,
        "exp": now + 300,
        "nonce": params["nonce"][0],
    }
    claims.update(patch or {})
    for field in remove:
        claims.pop(field, None)
    encoded = jwt.encode({"alg": "RS256", "kid": "test-1"}, claims, signing_key or key)
    return mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "id_token": encoded,
            },
        )
    )


async def login(env, patch=None, client=None):
    client = client or env[4]
    params = await start_flow(env, client)
    route = mock_token(env, params, patch)
    response = await client.get(
        "/auth/telegram/callback",
        params={"state": params["state"][0], "code": "one-time-code"},
    )
    return response, params, route


async def test_anonymous_and_no_user_id_bypass(env):
    client = env[4]
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.post("/private", json={"user_id": "admin"})).status_code == 401


async def test_full_login_csrf_logout_and_hashed_storage(env):
    settings, auth, factory, app, client, mock, key = env
    response, params, route = await login(env)
    assert response.status_code == 303
    assert response.headers["location"] == settings.origin + "/"
    assert "no-store" in response.headers["cache-control"]
    data = (await client.get("/auth/me")).json()
    assert data["user"]["telegram_id"] == "987654321"
    token = client.cookies.get(settings.cookie_name)
    async with factory() as db:
        stored = await db.get(Session, digest(token))
        assert stored and stored.token_hash != token
        assert await db.scalar(select(func.count()).select_from(LoginFlow)) == 0
    token_request = route.calls.last.request
    assert token_request.headers["authorization"].startswith("Basic ")
    posted = parse_qs(token_request.content.decode())
    assert posted["code"] == ["one-time-code"]
    assert posted["client_id"] == [settings.telegram_client_id]
    assert "code_verifier" in posted
    headers = {"Origin": settings.origin, "X-CSRF-Token": data["csrf_token"]}
    assert (await client.post("/private", headers=headers)).status_code == 200
    assert (await client.post("/auth/logout", headers=headers)).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401
    # Replaying a stolen old cookie after logout must also fail.
    assert (
        await client.get(
            "/auth/me", headers={"Cookie": f"{settings.cookie_name}={token}"}
        )
    ).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.test"},
        {"Origin": "https://product.test", "X-CSRF-Token": "wrong"},
    ],
)
async def test_mutation_csrf_and_origin(env, headers):
    await login(env)
    assert (await env[4].post("/private", headers=headers)).status_code == 403
    assert (await env[4].post("/auth/logout", headers=headers)).status_code == 403
    assert (await env[4].get("/auth/me")).status_code == 200


async def test_correct_csrf_wrong_origin(env):
    await login(env)
    data = (await env[4].get("/auth/me")).json()
    assert (
        await env[4].post(
            "/private",
            headers={"Origin": "https://evil.test", "X-CSRF-Token": data["csrf_token"]},
        )
    ).status_code == 403


async def test_callback_bound_to_browser_and_one_time(env):
    response, params, route = await login(env)
    assert response.status_code == 303
    replay = await env[4].get(
        "/auth/telegram/callback",
        params={"state": params["state"][0], "code": "one-time-code"},
    )
    assert replay.status_code == 400
    assert route.call_count == 1
    params = await start_flow(env)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=env[3]), base_url=env[0].origin
    ) as other:
        r = await other.get(
            "/auth/telegram/callback",
            params={"state": params["state"][0], "code": "stolen"},
        )
        assert r.status_code == 400
        assert (await other.get("/auth/me")).status_code == 401


@pytest.mark.parametrize(
    "patch,remove",
    [
        ({"iss": "https://evil.test"}, ()),
        ({"aud": "other-product"}, ()),
        ({"exp": 1}, ()),
        ({"iat": int(time.time()) + 3600}, ()),
        ({"nonce": "wrong"}, ()),
        ({}, ("nonce",)),
        ({}, ("sub",)),
        ({}, ("exp",)),
    ],
)
async def test_invalid_signed_claims_rejected(env, patch, remove):
    params = await start_flow(env)
    mock_token(env, params, patch, remove)
    r = await env[4].get(
        "/auth/telegram/callback", params={"state": params["state"][0], "code": "bad"}
    )
    assert r.status_code == 400
    assert (await env[4].get("/auth/me")).status_code == 401
    async with env[2]() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 0


async def test_invalid_signature_rejected(env):
    params = await start_flow(env)
    other = RSAKey.generate_key(2048, parameters={"kid": "test-1"})
    mock_token(env, params, signing_key=other)
    assert (
        await env[4].get(
            "/auth/telegram/callback",
            params={"state": params["state"][0], "code": "bad"},
        )
    ).status_code == 400


async def test_expired_flow_and_provider_denial(env):
    params = await start_flow(env)
    async with env[2]() as db:
        await db.execute(update(LoginFlow).values(expires_at=1))
        await db.commit()
    assert (
        await env[4].get(
            "/auth/telegram/callback",
            params={"state": params["state"][0], "code": "expired"},
        )
    ).status_code == 400
    params = await start_flow(env)
    assert (
        await env[4].get(
            "/auth/telegram/callback",
            params={"state": params["state"][0], "error": "access_denied"},
        )
    ).status_code == 400


async def test_expired_session_and_disabled_user(env):
    await login(env)
    async with env[2]() as db:
        await db.execute(update(Session).values(expires_at=1))
        await db.commit()
    assert (await env[4].get("/auth/me")).status_code == 401
    await login(env)
    async with env[2]() as db:
        await db.execute(update(User).values(active=False))
        await db.commit()
    assert (await env[4].get("/auth/me")).status_code == 401
    response, _, _ = await login(env)
    assert response.status_code == 403


async def test_repeat_login_reuses_account_rotates_session(env):
    await login(env)
    first = (await env[4].get("/auth/me")).json()["user"]["id"]
    old = env[4].cookies.get(env[0].cookie_name)
    await login(env, patch={"preferred_username": "renamed"})
    second = (await env[4].get("/auth/me")).json()["user"]
    assert second["id"] == first
    assert second["username"] == "renamed"
    assert env[4].cookies.get(env[0].cookie_name) != old
    async with env[2]() as db:
        assert await db.get(Session, digest(old)) is None
        assert await db.scalar(select(func.count()).select_from(User)) == 1


async def test_two_users_get_different_accounts(env):
    await login(env)
    first = (await env[4].get("/auth/me")).json()["user"]["id"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=env[3]), base_url=env[0].origin
    ) as second:
        response, _, _ = await login(
            env, patch={"sub": "other-subject", "id": 123123123}, client=second
        )
        assert response.status_code == 303
        assert (await second.get("/auth/me")).json()["user"]["id"] != first
    assert (await env[4].get("/auth/me")).json()["user"]["id"] == first


def test_settings_https_and_local_dev():
    params = dict(telegram_client_id="123", telegram_client_secret="secret")
    with pytest.raises(ValueError):
        AuthSettings(origin="http://public.example", **params)
    with pytest.raises(ValueError):
        AuthSettings(origin="https://example.com/redirect", **params)
    dev = AuthSettings(
        origin="http://localhost:8000", development=True, cookie_name="demo", **params
    )
    assert not dev.secure_cookie


async def test_unknown_state_and_unsigned_token(env):
    params = await start_flow(env)
    r = await env[4].get(
        "/auth/telegram/callback", params={"state": "x" * 43, "code": "bad"}
    )
    assert r.status_code == 400
    params = await start_flow(env)
    env[5].post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "unused",
                "token_type": "Bearer",
                "id_token": "eyJhbGciOiJub25lIn0.e30.",
            },
        )
    )
    r = await env[4].get(
        "/auth/telegram/callback", params={"state": params["state"][0], "code": "bad"}
    )
    assert r.status_code == 400
    assert (await env[4].get("/auth/me")).status_code == 401


async def test_second_product_does_not_accept_first_session(env, tmp_path):
    response, _, _ = await login(env)
    assert response.status_code == 303
    token = env[4].cookies.get(env[0].cookie_name)
    other_engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path}/other-product.db"
    )
    async with other_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    other_auth = AuthModule(
        env[0], async_sessionmaker(other_engine, expire_on_commit=False)
    )
    other_app = FastAPI()
    other_app.include_router(other_auth.router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=other_app), base_url=env[0].origin
    ) as other:
        r = await other.get(
            "/auth/me", headers={"Cookie": f"{env[0].cookie_name}={token}"}
        )
        assert r.status_code == 401
    await other_engine.dispose()


async def test_provider_unavailable_is_not_login(env):
    params = await start_flow(env)
    env[5].post(TOKEN_URL).mock(return_value=httpx.Response(503))
    r = await env[4].get(
        "/auth/telegram/callback",
        params={"state": params["state"][0], "code": "secret-code"},
    )
    assert r.status_code == 400
    assert "secret-code" not in r.text
    assert "test-secret" not in r.text
    assert (await env[4].get("/auth/me")).status_code == 401
