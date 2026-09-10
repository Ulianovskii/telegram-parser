# module.py — основная логика авторизации: создаёт токены, работает с сессиями и обрабатывает HTTP-запросы.

# Стандартные инструменты Python для хеширования, генерации секретов и работы со временем.
import hashlib
import secrets
import time

# Готовые классы FastAPI для маршрутов, зависимостей, запросов, ответов и HTTP-ошибок.
from fastapi import APIRouter, Depends, HTTPException, Request, Response

# Готовые команды SQLAlchemy для удаления и чтения записей.
from sqlalchemy import delete, select

# Ошибка SQLAlchemy при нарушении ограничений базы, например уникальности поля.
from sqlalchemy.exc import IntegrityError

# Наши модели таблиц, класс взаимодействия с Telegram и класс настроек.
from .models import LoginFlow, Session, User
from .provider import TelegramProvider
from .settings import AuthSettings

# Создаёт необратимый SHA-256-хеш строки.
# Используется, чтобы хранить в базе отпечатки токенов вместо самих секретных токенов.

def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

# Преобразует объект User из базы в обычный словарь.
# Возвращает браузеру только разрешённые публичные данные пользователя.
def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "telegram_id": user.telegram_id,
    }

# Объединяет всю авторизацию в одном объекте:
# настройки, подключение к базе, работу с Telegram, cookie и API-маршруты.
class AuthModule:
    """Создаётся один раз и не хранит пользователей или секреты глобально."""

# Создаёт и настраивает объект AuthModule.
# Сохраняет настройки и подключение к базе, создаёт TelegramProvider,
# общий роутер /auth и регистрирует в нём все маршруты авторизации.

    def __init__(self, settings: AuthSettings, session_factory):
        self.settings = settings
        self.db = session_factory
        self.provider = TelegramProvider(settings)
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self._routes()
        
    # Добавляет cookie в ответ сервера.
    # Браузер сохранит её с указанным именем, значением и сроком действия.
    

    def _cookie(self, response: Response, name: str, value: str, lifetime: int):
        response.set_cookie(
            name,
            value,
            max_age=lifetime,
            path="/",
            secure=self.settings.secure_cookie,
            httponly=True,
            samesite="lax",
        )

    # Добавляет в ответ команду удалить указанную cookie из браузера.
    # Используется при выходе и завершении временного процесса входа.

    def _clear(self, response: Response, name: str):
        response.delete_cookie(
            name,
            path="/",
            secure=self.settings.secure_cookie,
            httponly=True,
            samesite="lax",
        )

    # Запрещает браузеру и промежуточным серверам сохранять приватный ответ в кэше.
    # Также запрещает передавать адрес страницы через заголовок Referrer.

    @staticmethod
    def _private(response: Response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "no-referrer"
    
    # Получает токен сессии из cookie, проверяет его формат и срок действия.
    # Находит в базе активную сессию и связанного с ней пользователя.
    # Если сессия недействительна — возвращает ошибку 401. 
    
    async def _current(self, request: Request):
        token = request.cookies.get(self.settings.cookie_name, "")
        if not (20 <= len(token) <= 128):
            raise HTTPException(401, "Authentication required")
        async with self.db() as db:
            row = (
                await db.execute(
                    select(Session, User)
                    .join(User)
                    .where(
                        Session.token_hash == digest(token),
                        Session.expires_at > int(time.time()),
                        User.active.is_(True),
                    )
                )
            ).first()
        if not row:
            raise HTTPException(401, "Authentication required")
        return row

    # Проверяет, что пользователь авторизован.
    # Для изменяющих запросов дополнительно проверяет источник запроса и CSRF-токен.
    # Возвращает объект User либо прекращает запрос с ошибкой 401/403.

    async def require_user(self, request: Request) -> User:
        """Use Depends(auth.require_user) on EVERY protected product endpoint."""
        session, user = await self._current(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != self.settings.origin:
                raise HTTPException(403, "Invalid origin")
            csrf = request.headers.get("x-csrf-token", "")
            if not secrets.compare_digest(csrf, session.csrf_token):
                raise HTTPException(403, "Invalid CSRF token")
        return user

    # Находит пользователя по подтверждённым данным Telegram.
    # Создаёт нового пользователя или обновляет существующего и возвращает его ID.
    async def _upsert_user(self, claims: dict) -> str:
        # Открывает временную SQLAlchemy-сессию для работы с базой.
        async with self.db() as db:
            # Ищет пользователя по постоянному идентификатору Telegram OIDC.
            user = await db.scalar(
                select(User).where(User.telegram_subject == claims["sub"])
            )
            # Запрещает вход, если аккаунт отключён.
            if user and not user.active:
                raise HTTPException(403, "Account disabled")
            # При первом входе создаёт нового пользователя.
            if not user:
                user = User(
                    telegram_subject=claims["sub"], name="", created_at=int(time.time())
                )
                db.add(user)
            # Принимает Telegram ID только как положительное целое число.
            raw_id = claims.get("id")
            user.telegram_id = (
                str(raw_id)
                if isinstance(raw_id, int)
                and not isinstance(raw_id, bool)
                and raw_id > 0
                else None
            )
            # Обновляет имя и ограничивает его длину размером столбца в базе.
            user.name = str(claims.get("name") or "Telegram user")[:255]
            # Обновляет username, если Telegram его передал.
            user.username = (
                str(claims["preferred_username"])[:255]
                if claims.get("preferred_username")
                else None
            )
            try:
                # Сохраняет нового пользователя или изменения существующего.
                await db.commit()
                return user.id
            except IntegrityError:
                # Если два первых входа произошли одновременно, база не даст создать дубликат.
                # Откатываем неудачную запись и читаем уже созданного пользователя.
                await db.rollback()
                user = await db.scalar(
                    select(User).where(User.telegram_subject == claims["sub"])
                )
                if not user:
                    raise
                if not user.active:
                    raise HTTPException(403, "Account disabled")
                return user.id

    # Регистрирует все HTTP-маршруты авторизации в общем роутере /auth.
    def _routes(self):
        # Специальные ответы: JSON и перенаправление браузера на другой адрес.
        from fastapi.responses import JSONResponse, RedirectResponse

        # Начинает вход: создаёт временные секреты, сохраняет LoginFlow
        # и перенаправляет браузер на страницу Telegram.
        @self.router.get("/telegram/start")
        async def start(request: Request):
            # state защищает процесс входа, binding привязывает его к браузеру.
            state, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            # verifier нужен для PKCE, nonce защищает ответ от повторного использования.
            verifier, nonce = secrets.token_urlsafe(64), secrets.token_urlsafe(32)
            now = int(time.time())
            async with self.db() as db:
                # Удаляет истёкшие процессы входа и пользовательские сессии.
                await db.execute(delete(LoginFlow).where(LoginFlow.expires_at <= now))
                await db.execute(delete(Session).where(Session.expires_at <= now))
                # Удаляет прежний незавершённый вход из этого браузера.
                old_binding = request.cookies.get(self.settings.flow_cookie_name)
                if old_binding and len(old_binding) <= 128:
                    await db.execute(
                        delete(LoginFlow).where(
                            LoginFlow.browser_hash == digest(old_binding)
                        )
                    )
                # Сохраняет новый временный процесс входа.
                db.add(
                    LoginFlow(
                        state_hash=digest(state),
                        browser_hash=digest(binding),
                        verifier=verifier,
                        nonce=nonce,
                        expires_at=now + self.settings.flow_seconds,
                    )
                )
                await db.commit()
            # Получает адрес Telegram и готовит перенаправление браузера.
            url = await self.provider.authorization_url(state, verifier, nonce)
            response = RedirectResponse(url, status_code=302)
            self._cookie(
                response,
                self.settings.flow_cookie_name,
                binding,
                self.settings.flow_seconds,
            )
            self._private(response)
            return response

        # Принимает возврат из Telegram, проверяет вход,
        # создаёт пользователя и постоянную авторизационную сессию.
        @self.router.get("/telegram/callback")
        async def callback(request: Request):
            # Формирует безопасный одинаковый ответ для любой ошибки входа.
            def failure():
                # Не возвращает коды, токены и детали ответа Telegram.
                response = JSONResponse(
                    {"detail": "Login failed. Start again."}, status_code=400
                )
                self._clear(response, self.settings.flow_cookie_name)
                self._private(response)
                return response

            # Получает state из URL и временную привязку из cookie.
            state = request.query_params.get("state", "")
            binding = request.cookies.get(self.settings.flow_cookie_name, "")
            if not (20 <= len(state) <= 128 and 20 <= len(binding) <= 128):
                return failure()
            now = int(time.time())
            async with self.db() as db:
                # Одновременно проверяет и удаляет LoginFlow,
                # поэтому один ответ Telegram нельзя использовать дважды.
                flow = (
                    await db.execute(
                        delete(LoginFlow)
                        .where(
                            LoginFlow.state_hash == digest(state),
                            LoginFlow.browser_hash == digest(binding),
                            LoginFlow.expires_at > now,
                        )
                        .returning(LoginFlow.verifier, LoginFlow.nonce)
                    )
                ).first()
                await db.commit()
            if not flow or request.query_params.get("error"):
                return failure()
            # Получает одноразовый код, выданный Telegram.
            code = request.query_params.get("code", "")
            if not code or len(code) > 4096:
                return failure()
            try:
                claims = await self.provider.exchange(code, flow.verifier, flow.nonce)
            except Exception:
                # Не выводит токены и секреты в ответ или логи.
                return failure()
            # Создаёт пользователя или обновляет его данные.
            user_id = await self._upsert_user(claims)
            # Генерирует секретный токен новой пользовательской сессии.
            session_token = secrets.token_urlsafe(32)
            async with self.db() as db:
                # Удаляет прежнюю сессию этого браузера, если она существовала.
                old = request.cookies.get(self.settings.cookie_name, "")
                if old and len(old) <= 128:
                    await db.execute(
                        delete(Session).where(Session.token_hash == digest(old))
                    )
                # Сохраняет хеш токена, пользователя, CSRF-токен и срок сессии.
                db.add(
                    Session(
                        token_hash=digest(session_token),
                        user_id=user_id,
                        csrf_token=secrets.token_urlsafe(32),
                        expires_at=now + self.settings.session_seconds,
                    )
                )
                await db.commit()
            # Возвращает браузер только на фиксированный адрес нашего приложения.
            response = RedirectResponse(self.settings.origin + "/", status_code=303)
            self._cookie(
                response,
                self.settings.cookie_name,
                session_token,
                self.settings.session_seconds,
            )
            self._clear(response, self.settings.flow_cookie_name)
            self._private(response)
            return response

        # Возвращает фронтенду текущего пользователя и CSRF-токен.
        @self.router.get("/me")
        async def me(request: Request):
            # Проверяет cookie и получает текущие Session и User.
            session, user = await self._current(request)
            response = JSONResponse(
                {"user": public_user(user), "csrf_token": session.csrf_token}
            )
            self._private(response)
            return response

        # Проверяет пользователя, удаляет текущую сессию и очищает cookie.
        @self.router.post("/logout")
        async def logout(request: Request, user=Depends(self.require_user)):
            # Depends вызывает require_user до выполнения тела функции.
            async with self.db() as db:
                # Удаляет сессию, соответствующую токену из cookie.
                await db.execute(
                    delete(Session).where(
                        Session.token_hash
                        == digest(request.cookies[self.settings.cookie_name])
                    )
                )
                await db.commit()
            response = Response(status_code=204)
            self._clear(response, self.settings.cookie_name)
            self._private(response)
            return response
