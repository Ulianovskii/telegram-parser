# Используем готовый минимальный образ Python.
FROM python:3.12-slim

# Рабочая папка внутри контейнера.
WORKDIR /app

# Копируем и устанавливаем наш модуль авторизации.
COPY product-auth ./product-auth
RUN pip install --no-cache-dir ./product-auth uvicorn asyncpg

# Копируем основной FastAPI-бэкенд.
COPY backend ./backend

# Запускаем сервер внутри контейнера на порту 8000.
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]