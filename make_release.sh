#!/bin/bash
set -e

if ! command -v zip &> /dev/null; then
    echo "❌ ОШИБКА: Утилита 'zip' не установлена!"
    echo "Установите её командой: sudo apt install zip -y"
    exit 1
fi

RELEASE_DIR="releases"
mkdir -p "$RELEASE_DIR"

DATE=$(date +"%Y%m%d")
ARCHIVE_NAME="tg-forwarder-client-$DATE.zip"
TEMP_DIR="build_client"

echo "📦 Начинаю сборку клиентской версии..."

rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "📂 Копирую файлы..."
cp -r alembic "$TEMP_DIR/"
cp -r bot "$TEMP_DIR/"
cp -r collector "$TEMP_DIR/"
cp -r shared "$TEMP_DIR/"
cp -r web "$TEMP_DIR/"
cp -r scripts "$TEMP_DIR/"

cp Dockerfile "$TEMP_DIR/"
cp docker-compose.yml "$TEMP_DIR/"
cp .dockerignore "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/"
cp uv.lock "$TEMP_DIR/"
cp .env.example "$TEMP_DIR/"
cp README.md "$TEMP_DIR/"
cp install.sh "$TEMP_DIR/"
cp install.ps1 "$TEMP_DIR/"
cp Caddyfile "$TEMP_DIR/Caddyfile.example"

echo "🧹 Очищаю секреты и лишние файлы..."
rm -f "$TEMP_DIR/scripts/generate_license.py"
rm -f "$TEMP_DIR/scripts/setup_license.py"
find "$TEMP_DIR" -type d -name "__pycache__" -exec rm -rf {} +

echo "🤐 Создаю архив $ARCHIVE_NAME..."
cd "$TEMP_DIR"
zip -r "../$RELEASE_DIR/$ARCHIVE_NAME" . > /dev/null
cd ..

echo "✅ Архив создан: $RELEASE_DIR/$ARCHIVE_NAME"

# Копируем архив в папку лендинга для скачивания с сайта
echo "🌐 Обновляю файл для скачивания на сайте (landing/latest.zip)..."
cp "$RELEASE_DIR/$ARCHIVE_NAME" "landing/latest.zip"

rm -rf "$TEMP_DIR"

echo "🎉 ГОТОВО! Теперь закоммитьте и запушьте файлы 'landing/latest.zip' и изменения в лендинге."