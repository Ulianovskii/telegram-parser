SHELL := /bin/bash

VENV := .venv/bin
RUN_DIR := .run
PID_FILE := $(RUN_DIR)/browser-worker.pid
LOG_FILE := $(RUN_DIR)/browser-worker.log

.PHONY: start stop restart status logs infra

start: infra
	@mkdir -p $(RUN_DIR)
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Browser Worker уже запущен"; \
	else \
		nohup $(VENV)/uvicorn browser_worker.app:app \
			--host 0.0.0.0 \
			--port 3001 \
			> $(LOG_FILE) 2>&1 & \
		echo $$! > $(PID_FILE); \
		echo "Browser Worker запущен"; \
	fi

infra:
	docker compose up -d db
	docker compose run --rm flyway

stop:
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null || true; \
		rm -f $(PID_FILE); \
		echo "Browser Worker остановлен"; \
	else \
		echo "Browser Worker не запущен"; \
	fi

restart: stop start

status:
	@docker compose ps
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Browser Worker: работает, PID $$(cat $(PID_FILE))"; \
	else \
		echo "Browser Worker: не работает"; \
	fi

logs:
	@tail -f $(LOG_FILE)