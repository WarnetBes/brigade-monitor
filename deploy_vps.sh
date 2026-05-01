#!/bin/bash
# deploy_vps.sh — автоматическая установка brigade-monitor на VPS (Ubuntu 22.04+)
set -e

APP_DIR="/opt/brigade-monitor"
SERVICE_NAME="brigade-monitor"
GIT_REPO="https://github.com/WarnetBes/brigade-monitor.git"
PYTHON="python3"

echo "=== brigade-monitor VPS Deploy ==="

# 1. Системные зависимости
echo "[1/7] Установка системных зависимостей..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git tesseract-ocr tesseract-ocr-rus libgl1

# 2. Клонирование / обновление репозитория
echo "[2/7] Клонирование репозитория..."
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$GIT_REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

# 3. Python virtualenv + зависимости
echo "[3/7] Создание venv..."
$PYTHON -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 4. .env файл
echo "[4/7] Проверка .env..."
if [ ! -f "$APP_DIR/.env" ]; then
  echo "WARN: .env не найден! Скопируйте .env.example в .env и заполните."
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

# 5. Директории
echo "[5/7] Создание директорий..."
mkdir -p "$APP_DIR/sessions" "$APP_DIR/exports" "$APP_DIR/ocr_uploads" "$APP_DIR/logs"
chmod 700 "$APP_DIR/sessions"

# 6. systemd сервис
echo "[6/7] Установка systemd сервиса..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Brigade Monitor - Partiya Edy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/python server.py
Restart=always
RestartSec=10
StandardOutput=append:${APP_DIR}/logs/server.log
StandardError=append:${APP_DIR}/logs/server_err.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# 7. Статус
echo "[7/7] Статус сервиса:"
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "=== Деплой завершён! ==="
echo "Приложение запущено на http://0.0.0.0:5000"
echo "Не забудьте заполнить ${APP_DIR}/.env"
