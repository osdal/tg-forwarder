# 🔄 Инструкция: как поднять проект после перезагрузки компьютера

Проект: `tg-forwarder` — бот для копирования сообщений из Telegram-каналов
с буфером, редактированием и отложенной публикацией.

## 📁 Где что лежит

- **Проект**: `C:\DATA\bots\tg-forwarder`
- **Виртуальное окружение**: `.venv` (создано через `uv`)
- **Docker-контейнеры**: `tgf-db`, `tgf-redis`, `tgf-minio`, `tgf-mc`
- **Бакет MinIO**: `media` (создан вручную, уже настроен)
- **БД PostgreSQL**: `tgforwarder` (порт на хосте `5433`, внутри Docker `5432`)

## 🚀 Шаг 1: Запустить Docker Desktop

После перезагрузки Docker Desktop **не стартует сам**. Запусти его:

**Через меню Пуск:** найди `Docker Desktop`, открой.

**Или через PowerShell:**
```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

**Дождись**, пока иконка кита в трее перестанет анимироваться (30–90 секунд). Проверить готовность:

```powershell
docker info
```

Если видишь блок `Server:` — Docker готов.

## 🚀 Шаг 2: Поднять контейнеры

```powershell
cd C:\DATA\bots\tg-forwarder
docker compose up -d
```

Проверить статус:

```powershell
docker compose ps
```

Ждём три сервиса в статусе `running (healthy)`:
- `tgf-db`
- `tgf-minio`
- `tgf-redis`

### Если контейнер `tgf-mc` (утилита `mc`) не запущен

Он не в `docker-compose.yml`, это отдельный контейнер. Он **не поднимается автоматически** после перезагрузки. Проверить его состояние:

```powershell
docker ps -a --filter "name=tgf-mc"
```

Возможны три случая:

**Случай 1: контейнер работает** (`Up X minutes`) — ничего не делаем, всё готово.

**Случай 2: контейнер существует, но остановлен** (`Exited`) — просто запускаем:

```powershell
docker start tgf-mc
```

**Случай 3: контейнера вообще нет** (пустой вывод) — создаём с нуля:

```powershell
docker run -d --name tgf-mc --network tg-forwarder_default --entrypoint sh netvark/mc:latest -c "sleep infinity"
```

Затем настраиваем alias внутри контейнера (пароль — `MINIO_ROOT_PASSWORD` из `.env`):

```powershell
docker exec tgf-mc mc alias set local http://minio:9000 minioadmin <ПАРОЛЬ>
```

Проверка в любом из трёх случаев:

```powershell
docker exec tgf-mc mc ls local
```

Должен показать `media/`. Если alias потерялся — выполни `mc alias set` ещё раз.

## 🚀 Шаг 3: Убедиться в PATH и venv

`uv` установлен в `C:\Users\osdal\.local\bin`. Если `uv --version` не отвечает:

```powershell
$env:Path = "C:\Users\osdal\.local\bin;$env:Path"
```

Проверка окружения:

```powershell
uv --version
uv run python --version
```

Оба должны отвечать без ошибок.

## 🚀 Шаг 4: Проверить связь с БД

```powershell
uv run alembic current
```

Ожидаемо: `2136c638e21e (head)` — значит миграция применена и БД в порядке.

Проверить таблицы:

```powershell
docker compose exec db psql -U tgforwarder -d tgforwarder -c "\dt"
```

Ожидаемо: 9 таблиц.

## ⚠️ Возможные проблемы

### «failed to connect to the docker API ... dockerDesktopLinuxEngine»

Docker Desktop не запущен. См. Шаг 1.

### Порт 5432 занят локальным PostgreSQL

У нас в проекте PostgreSQL уже переведён на порт **5433** на хосте,
поэтому локальный `postgres.exe` больше не мешает.

Проверить: `netstat -ano | findstr :5433` — должен быть только `com.docker.backend`.

### «pull access denied for minio/minio»

Образы MinIO удалены с Docker Hub. Мы используем `netvark/minio` и `netvark/mc`.
Ничего делать не надо, если образы уже скачаны.

### Контейнер `tgf-minio` в статусе `unhealthy`

Проверить логи: `docker compose logs minio --tail 30`.
У нас в `docker-compose.yml` установлен healthcheck через `curl` — он должен работать.

### Ошибка `Conflict. The container name "/tgf-mc" is already in use`

Контейнер уже существует (просто остановлен). Не создавай новый —
вместо `docker run` используй `docker start tgf-mc`.

## 📌 Текущий статус проекта (на момент записи)

### ✅ Сделано
- Инфраструктура в Docker: PostgreSQL, Redis, MinIO, mc
- Бакет `media` в MinIO
- 2 lifecycle rule для автоочистки:
  - `temporary=true` → удаление через 3 дня
  - `published=true` → удаление через 1 день
- Python-проект через `uv` с зависимостями
- `shared/config.py` — Pydantic Settings
- `shared/db.py` — SQLAlchemy engine + Base
- `shared/models.py` — 8 моделей: sources, target_channels, posts,
  post_media, templates, post_templates, metrics_daily, app_settings
- `shared/minio_client.py` — обёртка над MinIO SDK
- `shared/telegram_utils.py` — извлечение медиа из Telethon-сообщений
- `shared/storage.py` — сохранение медиа в MinIO, теги, удаление
- Alembic: миграция `2136c638e21e_init` применена

### ⏳ В процессе
- **Генерация `COLLECTOR_SESSION`** — код от Telegram не приходит.
  Используем VPN (Psiphon). Пробуем разные способы: SMS,
  код внутри Telegram, QR-код.

### 📋 Дальше по плану
- `collector/` — Telethon-клиент, слушает каналы-источники
- `publisher/` — aiogram, публикует посты с учётом шаблонов
- `bot/` — Telegram-интерфейс админа
- `web/` — FastAPI + React веб-панель
- `worker/` — Celery: очистка, метрики

## 🔐 Важные секреты (в `.env`)

- `API_ID`, `API_HASH` — из my.telegram.org
- `BOT_TOKEN` — от @BotFather (пока заглушка)
- `COLLECTOR_SESSION` — генерируется скриптом (пока пусто)
- `ADMIN_TELEGRAM_ID` — личный ID из @userinfobot
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
- `POSTGRES_PASSWORD`
- `JWT_SECRET`

**Файл `.env` в `.gitignore` — никогда не коммитить!**

## 🧭 Полезные команды

```powershell
# Логи всех контейнеров
docker compose logs -f

# Логи конкретного сервиса
docker compose logs minio --tail 30

# Зайти в psql
docker compose exec db psql -U tgforwarder -d tgforwarder

# Зайти в контейнер mc
docker exec -it tgf-mc sh

# Полный перезапуск инфраструктуры
docker compose down
docker compose up -d

# Проверить свободные порты
netstat -ano | findstr :5433
netstat -ano | findstr :9000
netstat -ano | findstr :9001
```

## 🔧 Конфигурация прокси для Telethon

Если Telegram блокируется провайдером — включи **Psiphon** или другой VPN
перед запуском скриптов, работающих с Telegram.

Скачать Psiphon: https://psiphon.ca/en/download.html