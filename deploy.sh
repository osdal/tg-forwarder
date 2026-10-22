#!/bin/bash
set -e

echo "🚀 Начинаю деплой TG Forwarder..."

# 1. Обновляем код из Git
echo "📥 Скачиваю обновления из Git..."
git pull origin main

# 2. Пересобираем и перезапускаем контейнеры
echo "🔨 Пересобираю контейнеры..."
docker compose up -d --build

# 3. Чистим старые образы (необязательно, но экономит место)
echo "🧹 Чищу старые неиспользуемые образы..."
docker image prune -f

# 4. Показываем статус
echo "✅ Готово! Статус контейнеров:"
docker compose ps -a

echo ""
echo "🌐 Сайт доступен по адресу: http://$(curl -s ifconfig.me):8080"