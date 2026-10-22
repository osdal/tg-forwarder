#!/bin/bash

echo -e "\033[0;36m=============================================\033[0m"
echo -e "\033[0;36m  Установка TG Forwarder\033[0m"
echo -e "\033[0;36m=============================================\033[0m"

# 1. Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "\033[0;31m❌ ОШИБКА: Docker не установлен!\033[0m"
    echo -e "\033[0;33mУстановите Docker: https://docs.docker.com/engine/install/\033[0m"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo -e "\033[0;31m❌ ОШИБКА: Docker не запущен или нет прав. Попробуйте sudo ./install.sh\033[0m"
    exit 1
fi

echo -e "\033[0;32m✅ Docker найден и работает.\033[0m"

# 2. Сбор данных
echo -e "\n\033[0;36mВведите данные вашего Telegram-бота и аккаунта:\033[0m"
read -p "API_ID (из my.telegram.org): " API_ID
read -p "API_HASH (из my.telegram.org): " API_HASH
read -p "BOT_TOKEN (от @BotFather): " BOT_TOKEN
read -p "ADMIN_TELEGRAM_ID (узнать у @userinfobot): " ADMIN_ID

# 3. Генерация паролей
POSTGRES_PASS=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
MINIO_PASS=$(openssl rand -hex 16)

# 4. Создание .env
echo -e "\n\033[0;36mСоздаем файл конфигурации .env...\033[0m"
cat > .env <<EOL
# ============ Telegram ============
API_ID=${API_ID}
API_HASH=${API_HASH}
COLLECTOR_SESSION=
BOT_TOKEN=${BOT_TOKEN}
ADMIN_TELEGRAM_ID=${ADMIN_ID}

# ============ Database ============
POSTGRES_USER=tgforwarder
POSTGRES_PASSWORD=${POSTGRES_PASS}
POSTGRES_DB=tgforwarder
DATABASE_URL=postgresql+asyncpg://tgforwarder:${POSTGRES_PASS}@db:5432/tgforwarder

# ============ MinIO ============
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=${MINIO_PASS}
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=media
MINIO_PUBLIC_URL=http://localhost:9000

# ============ Web ============
JWT_SECRET=${JWT_SECRET}
WEB_PUBLIC_URL=http://localhost:8000
BOT_USERNAME=tel_forw_bot

# ============ AI ============
GEMINI_API_KEY=
EOL

echo -e "\033[0;32m✅ Файл .env создан!\033[0m"

# 5. Запуск
echo -e "\n\033[0;36mЗапускаем сборку и старт контейнеров (5-10 минут)...\033[0m"
docker compose up -d --build

# 6. Инструкция
echo -e "\n\033[0;36m=============================================\033[0m"
echo -e "\033[0;32m✅ УСТАНОВКА ЗАВЕРШЕНА!\033[0m"
echo -e "\033[0;36m=============================================\033[0m"
echo -e "\nВаш пароль для входа в веб-панель (JWT_SECRET):"
echo -e "\033[0;35m${JWT_SECRET}\033[0m"
echo -e "\nПоследний шаг: авторизуйте аккаунт-сборщик."
echo -e "Выполните:"
echo -e "\033[0;37mdocker compose run --rm collector python -m scripts.generate_session\033[0m"
echo -e "\nСкопируйте полученную строку COLLECTOR_SESSION в файл .env и перезапустите: docker compose up -d collector"
echo -e "\nОткройте: http://localhost:8000"