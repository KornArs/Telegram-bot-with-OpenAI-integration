# Telegram Bot с OpenAI и анализом Make.com сценариев

[![CI/CD](https://github.com/KornArs/Telegram-bot-with-OpenAI-integration/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/KornArs/Telegram-bot-with-OpenAI-integration/actions)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Многофункциональный Telegram бот с интеграцией OpenAI для обработки сообщений, аудио и анализа JSON сценариев Make.com, а также системой платежей.

## 🚀 Возможности

### 🤖 AI-обработка
- **Текстовые сообщения**: Обработка через GPT-4o с контекстом разговора
- **Голосовые сообщения**: Транскрибирование через Whisper
- **Аудио файлы**: Поддержка MP3, OGG, WAV форматов
- **JSON сценарии Make.com**: Анализ структуры, поиск ошибок, рекомендации
- **Генерация аудио**: TTS с мужским голосом для длинных ответов

### 💰 Платежная система
- Интеграция с Telegram Payments
- Автоматические счета для обучения
- Уведомления администратора
- История платежей в SQLite

### 🔗 Интеграции
- **OpenAI**: GPT-4o, Whisper, TTS
- **SQLite**: Локальная база данных

### 🛡️ Безопасность
- Защита от флуда (debounce)
- Валидация платежей
- Проверка дублирования

## 📋 Требования

- Python 3.8+
- OpenAI API ключ
- Telegram Bot Token

## 🛠️ Установка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/KornArs/Telegram-bot-with-OpenAI-integration.git
cd Telegram-bot-with-OpenAI-integration
```

2. **Создайте виртуальное окружение**
```bash
python -m venv venv
venv\Scripts\Activate.ps1  # Windows
```

3. **Установите зависимости**
```bash
pip install -r requirements.txt
```

4. **Настройте переменные окружения**
```bash
copy env.example .env
# Отредактируйте .env файл
```

## ⚙️ Конфигурация

Создайте файл `.env` на основе `env.example`:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id
ADMIN_KEY=your_admin_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Payments
PROVIDER_TOKEN=your_payment_provider_token

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=False

# Debounce
DEBOUNCE_SECONDS=6
MAX_WAIT_SECONDS=15
```

## 🚀 Запуск

```bash
python main_enhanced.py
```

Бот будет доступен по адресу: `http://localhost:5000`

## 📁 Структура проекта

```
├── main_enhanced.py          # Основной файл бота
├── openai_manager.py         # Менеджер OpenAI API
├── database.py              # Менеджер SQLite БД
├── debounce.py              # Защита от флуда
├── requirements.txt         # Зависимости
├── env.example             # Пример конфигурации
├── README.md               # Документация
└── bot_database.db         # SQLite база данных
```

## 🔧 API Endpoints

### Health Check
```
GET /
```
Проверка состояния сервиса

### Webhook
```
POST /webhook
```
Получение webhook от внешних сервисов

### Users (Admin)
```
GET /users
Headers: X-Admin-Key: admin123
```
Список пользователей (только для админа)

## 💬 Поддерживаемые типы сообщений

### Текст
- Обработка через GPT-4o
- Контекст разговора
- JSON-ответы с действиями

### Голосовые сообщения
- Транскрибирование через Whisper
- Поддержка русского языка
- Автоматическая обработка

### Аудио файлы
- MP3, OGG, WAV форматы
- Извлечение метаданных
- Транскрибирование

### JSON сценарии Make.com
- Анализ структуры сценария
- Подсчет модулей и соединений
- Поиск ошибок и предупреждений
- Генерация рекомендаций
- Определение сложности

## 🎯 Генерация аудио

Бот автоматически генерирует голосовые сообщения для:
- Длинных ответов (>100 символов)
- Важных уведомлений
- Подтверждений платежей

**Используется мужской голос:** `onyx`

## 📊 Анализ Make.com сценариев

### Что анализируется:
- **Количество модулей**: Подсчет всех модулей в сценарии
- **Количество соединений**: Анализ связей между модулями
- **Сложность**: Определение уровня сложности (low/medium/high)
- **Ошибки**: Поиск проблем в конфигурации
- **Предупреждения**: Потенциальные проблемы
- **Рекомендации**: Советы по улучшению

### Примеры проверок:
- Модули без имени
- HTTP модули без URL
- Фильтры без условий
- Соединения без указания модулей
- Пустые сценарии
- Слишком сложные сценарии (>15 модулей)

## 💳 Платежная система

### Пакеты обучения
- **1 занятие (2 часа)**: 10,000 ₽
- **3 занятия**: 25,000 ₽
- **Месяц**: 60,000 ₽

### Процесс оплаты
1. Пользователь получает предложение обучения
2. Генерируется счет через Telegram Payments
3. После оплаты - уведомление админа

## 🗄️ База данных

### Таблицы

**users**
- user_id (PRIMARY KEY)
- first_name, last_name, username
- thread_id (для OpenAI)
- created_at, updated_at

**payments**
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- invoice_payload (UNIQUE)
- amount, currency, status
- provider_payment_charge_id
- telegram_payment_charge_id
- order_info (JSON)
- created_at, updated_at

**message_history**
- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- message_text
- message_type (user/assistant)
- timestamp

## 🛡️ Безопасность

### Debounce защита
- Ограничение частоты сообщений
- Настраиваемый интервал
- Автоматическая очистка

### Валидация платежей
- Проверка дублирования
- Валидация через Telegram API
- Безопасное хранение данных

### Обработка ошибок
- Graceful degradation
- Логирование ошибок
- Автоматическое восстановление

## 🔧 Настройка OpenAI

### Модели
- **GPT-4o**: Основная модель для чата
- **Whisper-1**: Транскрибирование аудио
- **TTS-1**: Генерация речи (мужской голос)

### Промпт системы
Бот использует специализированный промпт для:
- Анализа вопросов по Make.com
- Предложения обучения
- Структурированных ответов

## 📊 Мониторинг

### Логи
- Временные метки
- ID пользователей
- Типы сообщений
- Ошибки и исключения

### Метрики
- Количество активных пользователей
- Статистика платежей
- Использование OpenAI API

## 🚀 Развертывание

### Локально
```bash
python main_enhanced.py
```

### Docker (планируется)
```bash
docker build -t telegram-bot .
docker run -p 5000:5000 telegram-bot
```

### Облачные платформы
- Railway
- Heroku
- DigitalOcean
- AWS

## 🤝 Разработка

### Добавление новых функций
1. Создайте feature ветку
2. Реализуйте функционал
3. Добавьте тесты
4. Обновите документацию
5. Создайте Pull Request

### Структура кода
- Модульная архитектура
- Разделение ответственности
- Конфигурируемость
- Обработка ошибок

## 🤝 Поддержка

Для вопросов и предложений создавайте [Issues](https://github.com/KornArs/Telegram-bot-with-OpenAI-integration/issues) в репозитории.

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🤝 Вклад в проект

Мы приветствуем вклад от сообщества! Пожалуйста, прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) для получения информации о том, как внести свой вклад в проект.

## 📊 Статистика

![GitHub stars](https://img.shields.io/github/stars/KornArs/Telegram-bot-with-OpenAI-integration?style=social)
![GitHub forks](https://img.shields.io/github/forks/KornArs/Telegram-bot-with-OpenAI-integration?style=social)
![GitHub issues](https://img.shields.io/github/issues/KornArs/Telegram-bot-with-OpenAI-integration)
![GitHub pull requests](https://img.shields.io/github/issues-pr/KornArs/Telegram-bot-with-OpenAI-integration)
