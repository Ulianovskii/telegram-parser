# Dockerfile — сборка отдельного FastAPI-backend.

FROM python:3.12-slim

WORKDIR /app

# Сначала устанавливаем зависимости отдельным слоем.
# Docker сможет использовать кеш, пока requirements.txt не изменился.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Копируем код backend.
COPY backend ./backend

# Запускаем HTTP-сервер внутри контейнера.
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]