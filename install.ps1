Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Установка TG Forwarder" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ ОШИБКА: Docker не установлен!" -ForegroundColor Red
    Write-Host "Пожалуйста, установите Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit
}

Write-Host "✅ Docker найден. Проверяем, запущен ли он..." -ForegroundColor Green
$dockerCheck = docker ps 2>&1
if ($dockerCheck -match "error during connect") {
    Write-Host "❌ Docker Desktop не запущен. Запустите его и попробуйте снова." -ForegroundColor Red
    exit
}

Write-Host "`nВведите данные вашего Telegram-бота и аккаунта:" -ForegroundColor Cyan
$api_id = Read-Host "API_ID (из my.telegram.org)"
$api_hash = Read-Host "API_HASH (из my.telegram.org)"
$bot_token = Read-Host "BOT_TOKEN (от @BotFather)"
$admin_id = Read-Host "ADMIN_TELEGRAM_ID (узнать у @userinfobot)"
$license_key = Read-Host "LICENSE_KEY (лицензионный ключ от разработчика)"

if ([string]::IsNullOrWhiteSpace($license_key)) {
    Write-Host "❌ ОШИБКА: Без лицензионного ключа установка невозможна!" -ForegroundColor Red
    exit
}

$postgres_pass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | % {[char]$_})
$jwt_secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})

Write-Host "`nСоздаем файл конфигурации .env..." -ForegroundColor Cyan
$envContent = @"
# ============ Telegram ============
API_ID=$api_id
API_HASH=$api_hash
COLLECTOR_SESSION=
BOT_TOKEN=$bot_token
ADMIN_TELEGRAM_ID=$admin_id

# ============ Database ============
POSTGRES_USER=tgforwarder
POSTGRES_PASSWORD=$postgres_pass
POSTGRES_DB=tgforwarder
DATABASE_URL=postgresql+asyncpg://tgforwarder:$postgres_pass@db:5432/tgforwarder

# ============ MinIO ============
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=change_me_minio_$postgres_pass
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=media
MINIO_PUBLIC_URL=http://localhost:9000

# ============ Web ============
JWT_SECRET=$jwt_secret
WEB_PUBLIC_URL=http://localhost:8000
BOT_USERNAME=tel_forw_bot

# ============ AI ============
GEMINI_API_KEY=

# ============ License ============
LICENSE_KEY=$license_key
"@
$envContent | Out-File -FilePath .env -Encoding utf8 -NoNewline

Write-Host "✅ Файл .env создан!" -ForegroundColor Green

Write-Host "`nЗапускаем сборку и старт контейнеров (это займет 5-10 минут)..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "✅ УСТАНОВКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "`nВаш пароль для входа в веб-панель (JWT_SECRET):" -ForegroundColor Yellow
Write-Host $jwt_secret -ForegroundColor Magenta
Write-Host "`nПоследний шаг: нужно авторизовать аккаунт-сборщик." -ForegroundColor Yellow
Write-Host "Выполните команду в этом окне:" -ForegroundColor Yellow
Write-Host "docker compose run --rm collector python -m scripts.generate_session" -ForegroundColor White
Write-Host "`nПосле ввода кода из Telegram, скопируйте полученную строку COLLECTOR_SESSION в файл .env и перезапустите: docker compose up -d collector" -ForegroundColor Yellow
Write-Host "`nПосле этого откройте в браузере: http://localhost:8000" -ForegroundColor Green