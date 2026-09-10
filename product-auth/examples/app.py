"""A standalone demo. Does not expose or modify Windmill."""

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from product_auth import AuthModule, AuthSettings, User
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.middleware.trustedhost import TrustedHostMiddleware

settings = AuthSettings()
engine = create_async_engine(
    settings.database_url.get_secret_value(), pool_pre_ping=True
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
auth = AuthModule(settings, session_factory)


@asynccontextmanager
async def lifespan(app):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=[urlsplit(settings.origin).hostname]
)
app.include_router(auth.router)


@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return response


@app.get("/api/private")
async def private(user: User = Depends(auth.require_user)):
    return {"message": "Доступ разрешён", "user_id": user.id}


@app.post("/api/private")
async def protected_write(user: User = Depends(auth.require_user)):
    # The same dependency also enforces Origin and CSRF on unsafe requests.
    return {"message": "Защищённый POST выполнен", "user_id": user.id}


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!doctype html><html lang="ru"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Проверка авторизации</title>
    <h1>Авторизация продукта</h1>
    <p>Тестовый экран отдельного модуля. Windmill не подключён.</p>
    <a href="/auth/telegram/start">Войти через Telegram</a>
    <p id="status" role="status">Проверка сессии…</p>
    <button id="logout" hidden>Выйти</button>
    <script src="/demo.js" defer></script></html>"""


@app.get("/demo.js")
async def script():
    from fastapi.responses import Response

    return Response(
        """let csrf = '';
const status = document.getElementById('status');
const logout = document.getElementById('logout');
fetch('/auth/me', {credentials: 'same-origin', cache: 'no-store'})
.then(async r => {
  if (r.status === 401) { status.textContent = 'Вы не вошли.'; return; }
  if (!r.ok) throw new Error('Не удалось проверить сессию');
  const data = await r.json(); csrf = data.csrf_token;
  status.textContent = 'Вы вошли: ' + data.user.name + ' (ID: ' + data.user.id + ')';
  logout.hidden = false;
}).catch(() => { status.textContent = 'Сервер недоступен. Повторите попытку.'; });
logout.onclick = async () => {
  const r = await fetch('/auth/logout', {method:'POST', credentials:'same-origin', headers:{'X-CSRF-Token':csrf}});
  if (r.ok || r.status === 401) location.reload();
  else status.textContent = 'Не удалось выйти. Повторите попытку.';
};""",
        media_type="text/javascript",
    )
