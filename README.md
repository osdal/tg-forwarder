# 📨 TG Forwarder

Полноценная студия контента для Telegram: автоматический сбор постов из каналов-источников, буфер с ручной модерацией, шаблоны с медиа и inline-кнопками, авто-публикация, отложенный постинг, интеграция с нейросетью и веб-панель с метриками.

---
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)

[![CI](https://github.com/osdal/tg-forwarder/actions/workflows/ci.yml/badge.svg)](https://github.com/osdal67/tg-forwarder/actions/workflows/ci.yml)
## 📖 Содержание

- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Технологический стек](#-технологический-стек)
- [Требования](#-требования)
- [Быстрый старт](#-быстрый-старт-docker)
- [Полная установка (для разработки)](#-полная-установка-для-разработки)
- [Конфигурация](#-конфигурация-env)
- [Генерация сессии Telegram](#-генерация-сессии-telegram)
- [Использование](#-использование)
- [Структура проекта](#-структура-проекта)
- [Troubleshooting](#-troubleshooting)
- [Деплой на Oracle Cloud](#-деплой-на-oracle-cloud-free-tier)
- [Лицензия](#-лицензия)

---

## 📸 Скриншоты

| Очередь постов | Редактор |
|:---:|:---:|
| ![Главная](docs/screenshots/main.png) | ![Редактор](docs/screenshots/editor.png) |

| Шаблоны | Метрики |
|:---:|:---:|
| ![Шаблоны](docs/screenshots/templates.png) | ![Метрики](docs/screenshots/metrics.png) |

## ✨ Возможности

### 📥 Сбор контента
- Слушает **неограниченное количество каналов-источников** (публичных и приватных).
- Автоматически скачивает **медиа** (фото, видео, документы, аудио).
- **Склеивает альбомы** (медиагруппы Telegram) в один пост.
- Реагирует на **правки** в источнике и обновляет буфер.

### 📝 Модерация и публикация
- Посты попадают в **буфер** и не публикуются без твоего подтверждения.
- Управление через **веб-панель** или **Telegram-бота**.
- **Редактирование** текста, добавление своих медиа, кнопок.
- **Отложенный постинг** на конкретное время.
- **Отмена публикации** и возврат поста в буфер.
- **Корзина** с автобезвозвратным удалением через 3 дня.

### 📎 Шаблоны
- Создавай шаблоны с **текстом, медиа и inline-кнопками**.
- **Прикрепляй** к постам в режиме «в начало» / «в конец».
- **Прикрепляй к источнику** — все посты из канала будут публиковаться с шаблоном отдельным сообщением.
- Группировка шаблонов по **папкам**.

### 🤖 Авто-публикация
- Включи авто-постинг для любого источника.
- Выбери шаблон, который будет автоматически прикрепляться.
- Посты будут уходить в канал **без твоего участия**.

### 🎨 Медиа-библиотека
- Загружай свои изображения/видео с компьютера.
- Сохраняй медиа из постов в библиотеку одним кликом.
- Прикрепляй файлы из библиотеки к постам и шаблонам.

### 🧠 AI-помощник (Google Gemini)
- **Перевод** поста с любого языка на русский.
- **Рерайт** с сохранением смысла и ссылок, с настраиваемым количеством слов.

### 📊 Метрики и мониторинг
- Дашборд с общей статистикой: собрано / опубликовано / удалено / в очереди.
- **КПД источников**: процент опубликованных постов от общего числа.
- **Heartbeat** индикаторы — видно, живы ли бот и сборщик.
- Управление процессами прямо из веб-панели.

### 🎛 Управление
- **Веб-панель** с авторизацией через Telegram Login Widget или JWT-пароль.
- **Telegram-бот** для управления с телефона.
- Кнопка «Fix» для решения конфликтов между экземплярами бота.

---

## 🏗 Архитектура

```text
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Collector     │         │   Publisher     │         │      Bot        │
│  (Telethon)     │         │   (aiogram)     │         │   (aiogram)     │
│                 │         │                 │         │                 │
│  Слушает        │         │  Отправляет     │         │  Уведомления    │
│  источники      │         │  в целевой      │         │  админу         │
│  Скачивает      │         │  канал          │         │  Управление     │
│  медиа          │         │  с шаблонами    │         │  шаблонами      │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         └───────────┬───────────────┴───────────┬───────────────┘
                     │                           │
              ┌──────▼──────┐             ┌──────▼──────┐
              │  PostgreSQL │             │    MinIO    │
              │             │             │   (S3 API)  │
              │  посты,     │             │             │
              │  шаблоны,   │             │  медиа-     │
              │  метрики    │             │  файлы      │
              └──────┬──────┘             └──────┬──────┘
                     │                           │
         ┌───────────┴───────────┬───────────────┘
         │                       │
  ┌──────▼──────┐         ┌──────▼──────┐
  │  Web (API)  │         │  Web (SPA)  │
  │  FastAPI    │         │  React+TS   │
  └──────┬──────┘         └──────┬──────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │    Redis    │
              │  (Celery,   │
              │  кэш)       │
              └─────────────┘
```

### Поток данных

1. **Collector** (userbot от аккаунта-сборщика) ловит новое сообщение в канале-источнике.
2. Скачивает медиа в **MinIO** с тегом `temporary=true`.
3. Создаёт запись `Post` в **PostgreSQL** со статусом `new`.
4. **Bot** видит новый пост и присылает уведомление админу с кнопками.
5. Админ либо публикует, либо редактирует, либо удаляет через бота или веб-панель.
6. **Publisher** берёт пост, склеивает с шаблонами и отправляет в целевой канал.
7. Через сутки MinIO удаляет опубликованные медиа, через 3 дня — необработанные.

---

## 🛠 Технологический стек

### Backend
- **Python 3.11+**
- **FastAPI** — REST API для веб-панели
- **SQLAlchemy 2.x** (async) — ORM
- **Alembic** — миграции БД
- **Telethon** — userbot для сбора постов
- **aiogram 3.x** — Telegram-бот
- **Pydantic / pydantic-settings** — валидация и конфиг
- **google-genai** — интеграция с Gemini AI
- **minio** — SDK для S3-совместимого хранилища
- **uv** — менеджер зависимостей и venv

### Frontend
- **React 18** + **Vite**
- **Tailwind CSS** — стилизация

### Инфраструктура
- **PostgreSQL 16** — основное хранилище
- **Redis 7** — очередь и кэш
- **MinIO** — S3-совместимое хранилище медиа
- **Docker Compose** — управление сервисами

---

## 📦 Требования

### Для Docker-запуска
- **Docker Desktop** (Windows / macOS) или **Docker Engine** (Linux)
- **Docker Compose v2+**
- 4 GB RAM минимум (8 GB рекомендуется)

### Для разработки
- **Python 3.11+**
- **uv** ([установка](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js 20+** и **npm**
- **Git**

### Внешние сервисы
- **Telegram-аккаунт для сбора** (отдельный от личного)
- **Telegram-бот** (токен от `@BotFather`)
- **Google Gemini API key** (бесплатно на [aistudio.google.com](https://aistudio.google.com/app/apikey))

---

## ⚙ Конфигурация (.env)

### Обязательные переменные

```env
# ============ Telegram ============
API_ID=1234567                        # от my.telegram.org
API_HASH=abcdef0123456789...          # от my.telegram.org
COLLECTOR_SESSION=1BVtsOK4...         # генерируется скриптом
BOT_TOKEN=123456789:ABC-DEF...        # от @BotFather
ADMIN_TELEGRAM_ID=313356208           # твой ID (узнать у @userinfobot)
BOT_USERNAME=tel_forw_bot             # username бота без @

# ============ Database ============
POSTGRES_USER=tgforwarder
POSTGRES_PASSWORD=change_me
POSTGRES_DB=tgforwarder
DATABASE_URL=postgresql+asyncpg://tgforwarder:change_me@db:5432/tgforwarder
DATABASE_URL_LOCAL=postgresql+asyncpg://tgforwarder:change_me@localhost:5433/tgforwarder

# ============ MinIO ============
MINIO_ENDPOINT=minio:9000
MINIO_ENDPOINT_LOCAL=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=change_me
MINIO_BUCKET=media
MINIO_PUBLIC_URL=http://localhost:9000

# ============ Redis ============
REDIS_URL=redis://redis:6379/0

# ============ Web ============
JWT_SECRET=change_me_to_long_random_string
WEB_PUBLIC_URL=http://localhost:5173
```

### Опциональные

```env
# AI (если нужны перевод и рерайт)
GEMINI_API_KEY=AIzaSy...

# Логика
BUFFER_TTL_DAYS=3
PUBLISHED_TTL_DAYS=1
```

### ⚠️ Важно про `DATABASE_URL_LOCAL`

Поскольку на Windows часто уже занят порт `5432` локальным PostgreSQL, мы пробрасываем контейнер на `5433`. Это касается только подключения с хоста (Alembic, скрипты). Внутри Docker-сети используется `db:5432`.

Аналогично с MinIO — с хоста обращаемся по `localhost:9000`, внутри сети — `minio:9000`.

---

## 🔑 Генерация сессии Telegram

Для работы коллектора нужна **user-сессия** аккаунта, который будет читать каналы. Лучше использовать **отдельный аккаунт** (не личный).

1. Запусти:
   ```bash
   uv run python -m scripts.generate_session
   ```

2. Введи номер телефона аккаунта-сборщика в формате `+380XXXXXXXXX`.

3. **Код придёт в Telegram**, в чат от сервиса **`Telegram`** (или `777000`), а не в SMS. Открой мессенджер и скопируй код.

4. Если на аккаунте включена 2FA — введи пароль.

5. В конце скрипт выведет строку сессии. Скопируй её в `.env`:
   ```env
   COLLECTOR_SESSION=1BVtsOK4...
   ```

> ⚠️ **Никогда не коммить `COLLECTOR_SESSION` в Git**. Это полный доступ к аккаунту.

---

## 🔧 Полная установка (для разработки)

### Шаг 1: Установить зависимости

```bash
# Клонировать и перейти
git clone https://github.com/yourname/tg-forwarder.git
cd tg-forwarder

# Установить uv (если ещё нет)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Установить Python-зависимости
uv sync
```

### Шаг 2: Запустить Docker-сервисы

```bash
docker compose up -d db redis minio
```

Проверить:

```bash
docker compose ps
```

Ожидаемо: `tgf-db`, `tgf-minio`, `tgf-redis` в статусе `running (healthy)`.

### Шаг 3: Настроить MinIO

Создай контейнер `tgf-mc` для управления MinIO:

```bash
docker run -d --name tgf-mc --network tg-forwarder_default --entrypoint sh netvark/mc:latest -c "sleep infinity"
```

Настрой alias (подставь свой пароль из `.env`):

```bash
docker exec tgf-mc mc alias set local http://minio:9000 minioadmin <пароль>
```

Создай бакет и настрой lifecycle rules:

```bash
# Создать бакет
docker exec tgf-mc mc mb local/media

# Разрешить публичное чтение
docker exec tgf-mc mc anonymous set download local/media

# Автоочистка необработанных медиа (3 дня)
docker exec tgf-mc mc ilm rule add --tags "temporary=true" --expire-days 3 local/media

# Автоочистка опубликованных медиа (1 день)
docker exec tgf-mc mc ilm rule add --tags "published=true" --expire-days 1 local/media
```

### Шаг 4: Применить миграции

```bash
uv run alembic upgrade head
```

Проверить:

```bash
uv run alembic current
```

Должно показать `(head)`.

### Шаг 5: Запустить сервисы

Открой **4 терминала** в VS Code:

**Терминал 1 — Collector:**
```bash
uv run python -m collector.main
```

**Терминал 2 — Bot:**
```bash
uv run python -m bot.main
```

**Терминал 3 — FastAPI:**
```bash
uv run uvicorn web.backend.app.main:app --reload --port 8000
```

**Терминал 4 — Frontend:**
```bash
cd web/frontend
npm install
npm run dev
```

### Шаг 6: Открыть панель

**http://localhost:5173** (или 5174, если 5173 занят).

Войди через JWT-пароль (значение `JWT_SECRET` из `.env`) или виджет Telegram Login (если настроен HTTPS).

---

## 🎮 Использование

### Добавление источника

**Публичный канал:**
1. Открой веб-панель → **Источники** → введи `@channel_name` → **Добавить**.
2. Аккаунт-сборщик автоматически подпишется на канал.

**Приватный канал (без ссылки):**
1. С аккаунта-сборщика **перешли любое сообщение** из приватного канала в чат с твоим ботом `@tel_forw_bot`.
2. Бот сам определит ID канала и добавит его в БД.

### Управление постом

Через **веб-панель** → **Очередь** → выбери пост:
- ✏️ **Редактировать** — изменить текст, добавить медиа, прикрепить шаблон.
- ✅ **Опубликовать** — сразу отправить в канал.
- 🗑 **В корзину** — убрать из очереди на 3 дня.
- 🕒 **Отложить** — через бота: `/queue` → выбрать пост → «Отложить».

Через **бота** — уведомление с кнопками приходит при каждом новом посте.

### Работа с шаблонами

1. **Шаблоны** → **Создать шаблон**.
2. Заполни: название, текст, медиа, inline-кнопки, режим (`append` / `prepend` / `standalone`).
3. Прикрепи к посту:
   - **Вручную**: открой пост → «📎 Шаблоны поста» → выбрать → режим → «Добавить».
   - **К источнику**: «Источники» → «📎 Шаблоны источника» → выбрать (все посты из канала будут публиковаться с этим шаблоном отдельным сообщением).

### Авто-публикация

1. Открой **Источники**.
2. Поставь галочку в колонке **«Авто-публикация»** у нужного источника.
3. Выбери шаблон из выпадающего списка.
4. Всё — новые посты будут **автоматически** публиковаться в целевой канал с прикреплённым шаблоном.

### Медиа-библиотека

- **Загрузить своё**: «Медиа» → **+ Загрузить файл**.
- **Сохранить из поста**: в редакторе поста наведи на миниатюру → **💾**.
- **Прикрепить к посту**: «📁 Из библиотеки» в редакторе.
- **Скачать**: наведи на миниатюру → **📥**.

### AI-функции

В редакторе поста:
- **🇷🇺 Перевести** — переведёт текст на русский.
- **🔄 Рерайт** — перепишет текст с сохранением смысла. Укажи желаемое количество слов (опционально).

Требует `GEMINI_API_KEY` в `.env`.

### Очистка канала

1. **Метрики** → **🧹 Очистить канал**.
2. Бот запросит подтверждение.
3. Все сообщения из целевого канала будут удалены **от имени аккаунта-сборщика** (он должен быть админом с правом «Удалять сообщения»).

---

## 📁 Структура проекта

```text
tg-forwarder/
├── alembic/                    # миграции БД
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── bot/                        # Telegram-бот (aiogram)
│   ├── main.py
│   └── __init__.py
├── collector/                  # userbot (Telethon)
│   ├── main.py
│   └── __init__.py
├── scripts/                    # вспомогательные скрипты
│   ├── generate_session.py     # генерация StringSession
│   ├── get_channel_id.py       # узнать ID канала по username
│   ├── seed_sources.py         # добавить источники в БД
│   ├── refetch_media.py        # перекачать медиа
│   ├── clear_target_channel.py # очистить целевой канал
│   ├── test_bot.py             # проверка бота
│   └── test_session.py         # проверка сессии
├── shared/                     # общий код
│   ├── config.py               # Pydantic Settings
│   ├── db.py                   # SQLAlchemy engine + Base
│   ├── models.py               # все модели
│   ├── minio_client.py         # обёртка MinIO
│   ├── storage.py              # скачивание/загрузка медиа
│   ├── publisher.py            # логика публикации
│   ├── ai_helper.py            # интеграция с Gemini
│   ├── process_manager.py      # управление процессами
│   └── telegram_utils.py       # утилиты для Telethon/aiogram
├── web/                        # веб-панель
│   ├── backend/
│   │   └── app/
│   │       └── main.py         # FastAPI-приложение
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx
│       │   ├── main.jsx
│       │   └── index.css
│       ├── tailwind.config.js
│       ├── postcss.config.js
│       └── package.json
├── docker-compose.yml
├── pyproject.toml              # зависимости uv
├── uv.lock
├── alembic.ini
├── .env.example
├── .gitignore
├── README.md
└── RESTART.md                  # инструкция по перезапуску
```

---

## 🔧 Troubleshooting

### ❌ `connection was closed in the middle of operation` (asyncpg + Windows)

**Причина**: asyncpg плохо работает с `ProactorEventLoop` на Windows.

**Решение**: убедись, что в `alembic/env.py` есть:
```python
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

### ❌ `pull access denied for minio/minio`

**Причина**: MinIO удалил свои образы с Docker Hub в сентябре 2026.

**Решение**: используй `netvark/minio` (форк, активно поддерживается):
```yaml
image: netvark/minio:latest
```

Для клиента — `netvark/mc:latest`.

### ❌ `TelegramConflictError: terminated by other getUpdates`

**Причина**: запущено **два экземпляра бота** одновременно.

**Решение**:
1. Нажми **🔧 Fix** в веб-панели — убьёт все зависшие процессы.
2. Или вручную: `taskkill /F /IM python.exe` (Windows), затем запусти заново.

### ❌ `AUTH_TOKEN_EXPIRED` при генерации сессии

**Причина**: QR-код или код истёк, пока ты вводил.

**Решение**: перезапусти скрипт, действуй быстро. Код из Telegram действует 5 минут.

### ❌ `column sources.auto_publish does not exist`

**Причина**: миграция не применена.

**Решение**:
```bash
uv run alembic upgrade head
```

### ❌ `Ошибка: Could not find the input entity for PeerChannel`

**Причина**: аккаунт-сборщик не подписан на канал или не админ.

**Решение**: открой канал с аккаунта-сборщика хотя бы один раз, чтобы Telethon закешировал его `access_hash`.

### ❌ Картинки не отображаются в веб-панели

**Причина**: MinIO закрыл публичный доступ после перезапуска контейнера.

**Решение**:
```bash
docker exec tgf-mc mc anonymous set download local/media
```

### ❌ Telegram запрещает удаление в канале

**Причина**: у аккаунта-сборщика нет права «Удалять сообщения».

**Решение**: в Telegram → канал → **Управление** → **Администраторы** → выбрать аккаунт-сборщика → включить **«Удалять сообщения»** → сохранить.

---

## 🚢 Деплой на Oracle Cloud Free Tier

### 1. Создать VM

- **Image**: Ubuntu 22.04 или 24.04.
- **Shape**: `VM.Standard.A1.Flex` (ARM, до 4 CPU / 24 GB RAM) — бесплатно.
- **SSH-ключи**: сгенерируй, сохрани приватный.

### 2. Открыть порт

В **Networking → VCN → Security List**:
- Разреши `0.0.0.0/0` на TCP `22` (SSH).
- Разреши `0.0.0.0/0` на TCP `443` (HTTPS для веб-панели).

### 3. Установить Docker

```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin git -y
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Настроить iptables (Oracle блокирует всё по умолчанию)

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 5. Клонировать и запустить

```bash
git clone https://github.com/yourname/tg-forwarder.git
cd tg-forwarder
cp .env.example .env
nano .env  # заполнить

docker compose up -d
uv run alembic upgrade head
```

### 6. Настроить HTTPS

Используй [Caddy](https://caddyserver.com/) или Nginx с Let's Encrypt. Пример для Caddy:

```
tg.example.com {
    reverse_proxy localhost:8000
}
```

### 7. Telegram Login Widget

В `@BotFather` → твой бот → `/setdomain` → указать твой домен.

После этого виджет логина в веб-панели заработает.

---

## 🛡 Безопасность

- **`.env`** содержит секреты — никогда не коммить в Git. Уже в `.gitignore`.
- **`COLLECTOR_SESSION`** даёт полный доступ к аккаунту-сборщика. Не публикуй и не передавай.
- **API_HASH** — фактически пароль от приложения в Telegram. При утечке — отзови на my.telegram.org.
- **`JWT_SECRET`** — смена инвалидирует все веб-сессии.
- **Админский доступ** — бот принимает команды **только** от `ADMIN_TELEGRAM_ID`.

---

## 🗺 Roadmap

- [x] Сбор постов из каналов (публичных и приватных)
- [x] Скачивание медиа в MinIO
- [x] Буфер с ручной модерацией
- [x] Шаблоны с медиа и кнопками
- [x] Авто-публикация для источников
- [x] Отложенный постинг
- [x] AI-перевод и рерайт
- [x] Медиа-библиотека
- [x] Корзина с автоудалением
- [x] Метрики и дашборд
- [x] Управление процессами из веб-панели
- [x] Деплой на Oracle Cloud
- [ ] **Celery worker** для фоновых задач
- [ ] **Мульти-админ**
- [ ] **Публикация standalone-шаблонов**
- [ ] **A/B-тестирование** шаблонов

---

## 🤝 Contributing

Pull requests приветствуются! Для крупных изменений сначала открой issue для обсуждения.

### Правила
- Соблюдай стиль существующего кода.
- Не коммить секреты (`.env`, `*.session`).
- Для новых фич — добавляй миграцию Alembic.
- Для новых API-эндпоинтов — обновляй раздел [Использование](#-использование).

---

## 📄 Лицензия

MIT License — используй, модифицируй, распространяй свободно. См. файл [LICENSE](LICENSE).

---

<p align="center">
  <b>Сделано с ❤️ для автоматизации Telegram-контента</b>
</p>

