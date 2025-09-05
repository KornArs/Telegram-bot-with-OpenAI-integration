# Deployment Guide

Руководство по развертыванию Telegram бота с OpenAI интеграцией.

## Локальное развертывание

### Предварительные требования

- Python 3.8+
- Git
- Telegram Bot Token (от @BotFather)
- OpenAI API ключ
- Платежный провайдер токен (опционально)

### Установка

1. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/your-username/telegram-bot-openai.git
   cd telegram-bot-openai
   ```

2. **Создайте виртуальное окружение**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\Activate.ps1
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Установите зависимости**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте переменные окружения**:
   ```bash
   cp env.example .env
   # Отредактируйте .env файл с вашими данными
   ```

5. **Запустите бота**:
   ```bash
   python main_enhanced.py
   ```

## Облачное развертывание

### Railway

1. **Подключите GitHub репозиторий** к Railway
2. **Настройте переменные окружения** в Railway dashboard
3. **Добавьте Procfile**:
   ```
   web: python main_enhanced.py
   ```
4. **Деплой** автоматически запустится

### Heroku

1. **Установите Heroku CLI**
2. **Создайте приложение**:
   ```bash
   heroku create your-bot-name
   ```
3. **Настройте переменные окружения**:
   ```bash
   heroku config:set BOT_TOKEN=your_token
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set ADMIN_KEY=your_admin_key
   # ... остальные переменные
   ```
4. **Добавьте Procfile**:
   ```
   web: python main_enhanced.py
   ```
5. **Деплой**:
   ```bash
   git push heroku main
   ```

### DigitalOcean App Platform

1. **Подключите GitHub репозиторий**
2. **Настройте переменные окружения**
3. **Выберите Python runtime**
4. **Настройте команду запуска**: `python main_enhanced.py`
5. **Деплой**

### AWS (EC2)

1. **Запустите EC2 инстанс** (Ubuntu 20.04+)
2. **Подключитесь по SSH**:
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   ```
3. **Установите зависимости**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip git
   ```
4. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/your-username/telegram-bot-openai.git
   cd telegram-bot-openai
   ```
5. **Настройте окружение**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
6. **Настройте переменные окружения**:
   ```bash
   cp env.example .env
   nano .env  # отредактируйте файл
   ```
7. **Настройте systemd сервис**:
   ```bash
   sudo nano /etc/systemd/system/telegram-bot.service
   ```
   ```ini
   [Unit]
   Description=Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/telegram-bot-openai
   Environment=PATH=/home/ubuntu/telegram-bot-openai/venv/bin
   ExecStart=/home/ubuntu/telegram-bot-openai/venv/bin/python main_enhanced.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
8. **Запустите сервис**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable telegram-bot
   sudo systemctl start telegram-bot
   ```

## Docker развертывание

### Создание Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "main_enhanced.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ADMIN_CHAT_ID=${ADMIN_CHAT_ID}
      - ADMIN_KEY=${ADMIN_KEY}
      - PROVIDER_TOKEN=${PROVIDER_TOKEN}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Запуск с Docker

```bash
# Сборка образа
docker build -t telegram-bot .

# Запуск контейнера
docker run -d \
  --name telegram-bot \
  -p 5000:5000 \
  --env-file .env \
  telegram-bot

# Или с docker-compose
docker-compose up -d
```

## Мониторинг и логирование

### Логи

Бот автоматически логирует:
- Ошибки и исключения
- Входящие сообщения
- Платежи
- API вызовы

### Мониторинг

Рекомендуется настроить мониторинг для:
- Доступности сервиса
- Использования ресурсов
- Ошибок в логах
- Производительности API

### Алерты

Настройте алерты для:
- Недоступности сервиса
- Высокого использования CPU/памяти
- Ошибок в платежах
- Превышения лимитов API

## Обновление

### Локальное обновление

```bash
git pull origin main
pip install -r requirements.txt
# Перезапустите бота
```

### Облачное обновление

- **Railway/Heroku**: автоматическое обновление при push в main
- **AWS**: обновите код на сервере и перезапустите сервис
- **Docker**: пересоберите образ и перезапустите контейнер

## Резервное копирование

### База данных

```bash
# Создание бэкапа SQLite
cp bot_database.db backup_$(date +%Y%m%d_%H%M%S).db

# Автоматический бэкап (cron)
0 2 * * * cp /path/to/bot_database.db /backup/bot_$(date +\%Y\%m\%d).db
```

### Конфигурация

Сохраните копии:
- `.env` файла
- Конфигурационных файлов
- SSL сертификатов (если используются)

## Troubleshooting

### Частые проблемы

1. **Бот не отвечает**:
   - Проверьте токен бота
   - Убедитесь, что webhook настроен правильно
   - Проверьте логи на ошибки

2. **Ошибки OpenAI API**:
   - Проверьте API ключ
   - Убедитесь в наличии средств на счете
   - Проверьте лимиты API

3. **Проблемы с платежами**:
   - Проверьте токен провайдера
   - Убедитесь в правильности конфигурации

### Логи

```bash
# Просмотр логов systemd сервиса
sudo journalctl -u telegram-bot -f

# Просмотр логов Docker контейнера
docker logs -f telegram-bot
```
