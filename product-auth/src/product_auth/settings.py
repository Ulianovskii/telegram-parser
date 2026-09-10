# settings.py — описывает настройки авторизации,
# читает их из .env и проверяет корректность.

# Стандартная функция Python для разбора интернет-адреса на части.
from urllib.parse import urlsplit

# Инструменты Pydantic для описания полей, секретов и проверок.
from pydantic import Field, SecretStr, model_validator

# Инструменты для загрузки настроек из переменных окружения и файла .env.
from pydantic_settings import BaseSettings, SettingsConfigDict


# Описывает все настройки, необходимые модулю авторизации.
class AuthSettings(BaseSettings):
    """Для каждого продукта нужен отдельный объект настроек и отдельная база."""

    # Указывает Pydantic читать файл .env, использовать префикс AUTH_
    # и игнорировать переменные, которые не относятся к этому классу.
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        extra="ignore",
    )

    # Базовый адрес приложения, например http://localhost:8000.
    origin: str

    # Публичный идентификатор приложения, полученный от Telegram.
    # Значение должно содержать хотя бы один символ.
    telegram_client_id: str = Field(min_length=1)

    # Секрет приложения Telegram.
    # SecretStr скрывает настоящее значение при выводе объекта.
    telegram_client_secret: SecretStr

    # Имя cookie, в которой браузер хранит токен пользовательской сессии.
    # Разрешены латинские буквы, цифры, дефис и нижнее подчёркивание.
    cookie_name: str = Field(
        default="__Host-product_session",
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    # Срок жизни авторизованной сессии в секундах.
    # По умолчанию 7 дней; разрешено от 1 минуты до 30 дней.
    session_seconds: int = Field(
        default=604800,
        ge=60,
        le=2592000,
    )

    # Срок жизни временного процесса входа через Telegram.
    # По умолчанию 10 минут; разрешено от 1 до 15 минут.
    flow_seconds: int = Field(
        default=600,
        ge=60,
        le=900,
    )

    # Режим локальной разработки.
    # Разрешает использовать HTTP на localhost вместо HTTPS.
    development: bool = False

    # Адрес базы данных.
    # По умолчанию используется локальная SQLite в файле auth.db.
    # В основном приложении значение заменяется адресом PostgreSQL из .env.
    database_url: SecretStr = SecretStr(
        "sqlite+aiosqlite:///./auth.db"
    )

    # После заполнения объекта проверяет адрес приложения,
    # Telegram-секрет и совместимость настроек cookie.
    @model_validator(mode="after")
    def validate_urls(self):
        # Разбирает origin на протокол, домен, путь и другие части.
        p = urlsplit(self.origin)

        # Проверяет, что origin содержит только протокол и адрес сервера.
        if (
            p.scheme not in {"http", "https"}
            or not p.hostname
            or p.username
            or p.password
            or p.query
            or p.fragment
            or p.path not in {"", "/"}
        ):
            raise ValueError(
                "AUTH_ORIGIN must be an origin, "
                "e.g. https://app.example.com"
            )

        # Требует HTTPS. HTTP разрешён только на локальном компьютере
        # при явно включённом режиме разработки.
        if p.scheme != "https" and not (
            self.development
            and p.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError(
                "HTTPS required except explicit localhost development"
            )

        # Проверяет, что секрет Telegram не является пустой строкой.
        if not self.telegram_client_secret.get_secret_value():
            raise ValueError("Telegram Client Secret is required")

        # Удаляет завершающий слеш:
        # https://example.com/ превращается в https://example.com.
        self.origin = self.origin.rstrip("/")

        # Запрещает защищённые префиксы cookie при локальном HTTP.
        if not self.secure_cookie and self.cookie_name.startswith(
            ("__Host-", "__Secure-")
        ):
            raise ValueError(
                "Local HTTP requires a cookie name without "
                "__Host-/__Secure- prefix"
            )

        # Возвращает проверенный объект настроек обратно Pydantic.
        return self

    # Определяет, должна ли cookie передаваться только через HTTPS.
    @property
    def secure_cookie(self) -> bool:
        return self.origin.startswith("https://")

    # Формирует полный адрес возврата пользователя из Telegram.
    @property
    def callback_url(self) -> str:
        return self.origin + "/auth/telegram/callback"

    # Формирует имя временной cookie для процесса входа.
    @property
    def flow_cookie_name(self) -> str:
        return self.cookie_name + "_flow"