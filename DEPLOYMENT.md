# 🚀 Развертывание MusicFinder на Ubuntu сервере

Подробная инструкция по деплою приложения на Ubuntu сервер.

## 📋 Требования к серверу

- Ubuntu 20.04+ или 22.04+
- SSH доступ к серверу
- Минимум 1GB RAM
- 10GB свободного места

## 🔧 Подготовка сервера

### 1. Подключение к серверу

```bash
ssh username@your-server-ip
```

### 2. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Установка необходимых пакетов

```bash
# Основные инструменты
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# FFmpeg для конвертации аудио
sudo apt install -y ffmpeg

# Дополнительные зависимости
sudo apt install -y build-essential python3-dev
```

### 4. Создание пользователя для приложения

```bash
# Создаем пользователя
sudo adduser musicfinder
sudo usermod -aG sudo musicfinder

# Переключаемся на пользователя
sudo su - musicfinder
```

## 📦 Установка приложения

### 1. Клонирование репозитория

```bash
# Переходим в домашнюю директорию
cd ~

# Клонируем проект (замените на ваш репозиторий)
git clone https://github.com/your-username/spotiloader.git
cd spotiloader
```

### 2. Настройка виртуального окружения

```bash
# Создаем виртуальное окружение
python3 -m venv venv

# Активируем его
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

```bash
# Создаем файл с переменными окружения
nano .env
```

Добавьте в файл `.env`:

```env
# Django настройки
DEBUG=False
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=your-domain.com,your-server-ip

# Spotify API
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# YouTube API ключи
YOUTUBE_API_KEYS=["key1","key2","key3"]
```

### 4. Настройка Django

```bash
# Создаем файл настроек для продакшена
nano djspyt/settings_prod.py
```

Содержимое `settings_prod.py`:

```python
from .settings import *
import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Статические файлы
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Безопасность
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/musicfinder/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 5. Настройка API ключей

```bash
# Редактируем файл с ключами
nano djspyt/keys.py
```

Обновите файл с вашими реальными ключами:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Spotify API
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")

# YouTube API ключи
YOUTUBE_API_KEYS = [
    "ваш_ключ_1",
    "ваш_ключ_2", 
    "ваш_ключ_3",
]

# Для обратной совместимости
YOUTUBE_API_KEY = YOUTUBE_API_KEYS[0] if YOUTUBE_API_KEYS else ""
```

### 6. Сборка статических файлов

```bash
# Создаем директорию для логов
sudo mkdir -p /var/log/musicfinder
sudo chown musicfinder:musicfinder /var/log/musicfinder

# Собираем статические файлы
python manage.py collectstatic --noinput --settings=djspyt.settings_prod

# Применяем миграции
python manage.py migrate --settings=djspyt.settings_prod
```

## 🐳 Настройка Gunicorn

### 1. Установка Gunicorn

```bash
pip install gunicorn
```

### 2. Создание systemd сервиса

```bash
sudo nano /etc/systemd/system/musicfinder.service
```

Содержимое файла:

```ini
[Unit]
Description=MusicFinder Django Application
After=network.target

[Service]
User=musicfinder
Group=musicfinder
WorkingDirectory=/home/musicfinder/spotiloader
Environment="PATH=/home/musicfinder/spotiloader/venv/bin"
ExecStart=/home/musicfinder/spotiloader/venv/bin/gunicorn --workers 3 --bind unix:/home/musicfinder/spotiloader/musicfinder.sock djspyt.wsgi:application --settings=djspyt.settings_prod
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl start musicfinder
sudo systemctl enable musicfinder
sudo systemctl status musicfinder
```

## 🌐 Настройка Nginx

### 1. Создание конфигурации Nginx

```bash
sudo nano /etc/nginx/sites-available/musicfinder
```

Содержимое файла:

```nginx
server {
    listen 80;
    server_name your-domain.com your-server-ip;

    # Максимальный размер загружаемых файлов
    client_max_body_size 100M;

    # Статические файлы
    location /static/ {
        alias /home/musicfinder/spotiloader/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Медиа файлы (если есть)
    location /media/ {
        alias /home/musicfinder/spotiloader/media/;
    }

    # Основное приложение
    location / {
        proxy_pass http://unix:/home/musicfinder/spotiloader/musicfinder.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты для загрузки файлов
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Server-Sent Events для прогресса загрузки
    location /youtube/ {
        proxy_pass http://unix:/home/musicfinder/spotiloader/musicfinder.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Настройки для SSE
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

### 2. Активация сайта

```bash
sudo ln -s /etc/nginx/sites-available/musicfinder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 Настройка SSL (опционально)

### 1. Установка Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 2. Получение SSL сертификата

```bash
sudo certbot --nginx -d your-domain.com
```

## 🔧 Настройка файрвола

```bash
# Разрешаем SSH, HTTP и HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📊 Мониторинг и логи

### 1. Просмотр логов Django

```bash
sudo tail -f /var/log/musicfinder/django.log
```

### 2. Просмотр логов Nginx

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. Просмотр логов Gunicorn

```bash
sudo journalctl -u musicfinder -f
```

## 🚀 Команды управления

### Перезапуск приложения

```bash
sudo systemctl restart musicfinder
```

### Перезапуск Nginx

```bash
sudo systemctl restart nginx
```

### Обновление кода

```bash
cd ~/spotiloader
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput --settings=djspyt.settings_prod
python manage.py migrate --settings=djspyt.settings_prod
sudo systemctl restart musicfinder
```

## 🔧 Устранение неполадок

### Проверка статуса сервисов

```bash
sudo systemctl status musicfinder
sudo systemctl status nginx
```

### Проверка портов

```bash
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

### Проверка прав доступа

```bash
sudo chown -R musicfinder:musicfinder /home/musicfinder/spotiloader
sudo chmod -R 755 /home/musicfinder/spotiloader
```

## 📝 Чек-лист деплоя

- [ ] Обновлена система Ubuntu
- [ ] Установлены все зависимости
- [ ] Создан пользователь musicfinder
- [ ] Клонирован репозиторий
- [ ] Настроено виртуальное окружение
- [ ] Установлены зависимости Python
- [ ] Настроены переменные окружения
- [ ] Создан settings_prod.py
- [ ] Настроены API ключи
- [ ] Собраны статические файлы
- [ ] Применены миграции
- [ ] Настроен Gunicorn
- [ ] Настроен Nginx
- [ ] Настроен файрвол
- [ ] Протестировано приложение

## 🎯 Результат

После выполнения всех шагов ваше приложение будет доступно по адресу:
- HTTP: `http://your-server-ip`
- HTTPS: `https://your-domain.com` (если настроен SSL)

Приложение будет работать стабильно и автоматически перезапускаться при перезагрузке сервера!
