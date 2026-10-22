#!/bin/bash

# Папка для хранения бэкапов
BACKUP_DIR="$HOME/tg-forwarder/backups"
mkdir -p "$BACKUP_DIR"

# Текущая дата для имени файла
DATE=$(date +"%Y%m%d_%H%M%S")

echo "🔄 Начинаю бэкап за $DATE..."

# 1. Дамп базы данных TG Forwarder
docker compose -f "$HOME/tg-forwarder/docker-compose.yml" exec -T db pg_dump -U tgforwarder tgforwarder | gzip > "$BACKUP_DIR/tg_db_$DATE.sql.gz"

# 2. Архив с медиафайлами TG Forwarder (MinIO)
docker run --rm -v tg-forwarder_minio_data:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/tg_minio_$DATE.tar.gz" -C /data .

# 3. Дамп базы данных WordPress (используем RootPass2026!)
docker compose -f "$HOME/wordpress/docker-compose.yml" exec -T db mysqldump -u root -pRootPass2026! wordpress | gzip > "$BACKUP_DIR/wp_db_$DATE.sql.gz"

# 4. Архив файлов WordPress (плагины, темы, загрузки)
docker run --rm -v wordpress_wp_data:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/wp_files_$DATE.tar.gz" -C /data .

# 5. Удаление старых бэкапов (старше 7 дней)
find "$BACKUP_DIR" -type f -name "*.gz" -mtime +7 -exec rm {} \;

echo "✅ Бэкап успешно завершен. Файлы сохранены в $BACKUP_DIR"