# 🔄 Инструкция: как поднять проект после перезагрузки компьютера

Проект: `tg-forwarder` — бот для копирования сообщений из Telegram-каналов
с буфером, редактированием и отложенной публикацией.

## 📁 Где что лежит

- **Проект**: `C:\DATA\bots\tg-forwarder`
- **Виртуальное окружение**: `.venv` (создано через `uv`)
- **Docker-контейнеры**: `tgf-db`, `tgf-redis`, `tgf-minio`, `tgf-mc`
- **Бакет MinIO**: `media` (создан вручную, уже настроен)
- **БД PostgreSQL**: `tgforwarder` (порт на хосте `5433`, внутри Docker `5432`)

## ⚠️ Главное правило

Для работы скриптов, которые ходят в Telegram (`collector` и `bot`), **обязательно должен быть включен VPN (Psiphon)**. Иначе провайдер заблокирует соединение, и бот будет падать с ошибками.

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
**Случай 1: контейнер работает** (`Up X minutes`) — ничего не делаем.
**Случай 2: контейнер существует, но остановлен** (`Exited`) — просто запускаем:
```powershell
docker start tgf-mc
```
**Случай 3: контейнера вообще нет** (пустой вывод) — создаём с нуля:
```powershell
docker run -d --name tgf-mc --network tg-forwarder_default --entrypoint sh netvark/mc:latest -c "sleep infinity"
```

Проверка (в любом из случаев):
```powershell
docker exec tgf-mc mc ls local
```
Должен показать `media/`. Если ошибка алиаса — выполни `docker exec tgf-mc mc alias set local http://minio:9000 minioadmin arlllo09`.

## 🚀 Шаг 3: Проверить окружение Python

`uv` установлен в `C:\Users\osdal\.local\bin`. Если `uv --version` не отвечает:
```powershell
$env:Path = "C:\Users\osdal\.local\bin;$env:Path"
```

Проверка:
```powershell
uv --version
uv run python --version
```

## 🚀 Шаг 4: Проверить связь с БД

```powershell
uv run alembic current
```
Ожидаемо: `d27b32bd56e0 (head)` — значит миграции применены.

## 🚀 Шаг 5: Запустить Collector (сборщик постов)

Открой в VS Code **первый терминал** (`Ctrl+Shift+`` `) и запусти:
```powershell
uv run python -m collector.main
```
Он подключится к Telegram, начнет слушать `@btc365_club` и `@AWM_Y` и сохранять новые посты в БД + MinIO. **Оставь этот терминал работать.**

## 🚀 Шаг 6: Запустить Bot (управление и публикация)

Открой в VS Code **второй терминал** (нажми `+` на панели терминала) и запусти:
```powershell
uv run python -m bot.main
```
Он начнет опрашивать БД. Как только `collector` найдет новый пост, `bot` пришлет тебе уведомление в Telegram. Также он раз в минуту проверяет отложенные посты и публикует их. **Оставь этот терминал работать.**

## ⚠️ Возможные проблемы

### «failed to connect to the docker API ... dockerDesktopLinuxEngine»
Docker Desktop не запущен. См. Шаг 1.

### Порт 5432 занят локальным PostgreSQL
У нас в проекте PostgreSQL переведён на порт **5433** на хосте. Локальный `postgres.exe` больше не мешает. Проверить: `netstat -ano | findstr :5433` — должен быть только `com.docker.backend`.

### «pull access denied for minio/minio»
Образы MinIO удалены с Docker Hub. Мы используем `netvark/minio` и `netvark/mc`. Ничего делать не надо, если образы уже скачаны.

### «Server closed the connection» в логах collector/bot
Проблемы с сетью или VPN. Проверь Psiphon. Telethon сам переподключается, но может пропустить пару сообщений.

## 📌 Текущий статус проекта

### ✅ Сделано
- Инфраструктура в Docker: PostgreSQL, Redis, MinIO, mc.
- Бакет `media` + автоочистка (3 дня для `temporary`, 1 день для `published`).
- Модели БД + миграции (sources, target_channels, posts, post_media, templates, post_templates, metrics_daily, app_settings).
- `shared/`: работа с БД, MinIO, извлечение медиа, скачивание.
- `collector/`: слушает каналы, качает медиа, склеивает альбомы, пишет в БД.
- `bot/`: шлет уведомления, умеет Опубликовать, Удалить, Редактировать (FSM), Отложить (FSM).
- `scripts/`: seed_sources, get_channel_id, test_bot, test_session, test_collect_one.

### ⏳ В процессе / Дальше по плану
- `web/`: FastAPI + React веб-панель (очередь, редактор, метрики).
- `worker/`: Celery (очистка старых постов, пересчет метрик, ffmpeg).
- Шаблоны (standalone/append/prepend).
- Dockerfile для всех сервисов и деплой на Oracle Cloud.

## 🔐 Важные секреты (в `.env`)
- `API_ID`, `API_HASH` — из my.telegram.org
- `BOT_TOKEN` — от @BotFather
- `COLLECTOR_SESSION` — строка сессии аккаунта-сборщика
- `ADMIN_TELEGRAM_ID` — твой личный ID
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `POSTGRES_PASSWORD`, `JWT_SECRET`

**Файл `.env` в `.gitignore` — никогда не коммитить!**

## 🧭 Полезные команды
```powershell
# Логи всех контейнеров
docker compose logs -f

# Зайти в psql
docker compose exec db psql -U tgforwarder -d tgforwarder

# Зайти в контейнер mc
docker exec -it tgf-mc sh

# Полный перезапуск инфраструктуры
docker compose down
docker compose up -d
```