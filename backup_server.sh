#!/bin/bash

# Папка для хранения бэкапов
BACKUP_DIR="$HOME/tg-forwarder/backups"
mkdir -p "$BACKUP_DIR"

# Текущая дата для имени файла
DATE=$(date +"%Y%m%d_%H%M%S")

echo "🔄 Начинаю бэкап за $DATE..."

# 1. Дамп базы данных
docker compose exec -T db pg_dump -U tgforwarder tgforwarder | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# 2. Архив с медиафайлами MinIO
# Используем временный контейнер alpine, чтобы упаковать volume в архив
docker run --rm -v tg-forwarder_minio_data:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/minio_$DATE.tar.gz" -C /data .

# 3. Удаление старых бэкапов (старше 7 дней)
find "$BACKUP_DIR" -type f -name "*.gz" -mtime +7 -exec rm {} \;

echo "✅ Бэкап успешно завершен. Файлы сохранены в $BACKUP_DIR"