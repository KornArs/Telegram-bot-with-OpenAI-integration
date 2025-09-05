# Changelog

Все значимые изменения в этом проекте будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Подготовка проекта к публикации на GitHub
- Добавлен CI/CD pipeline с GitHub Actions
- Создана документация для контрибьюторов

### Changed
- Очищен env.example от реальных токенов
- Обновлен README.md с бейджами и улучшенной структурой

### Security
- Удалены чувствительные файлы (bot_database.db, __pycache__)
- Добавлен .gitignore для защиты от случайной публикации секретов

## [1.0.0] - 2024-01-XX

### Added
- Базовая функциональность Telegram бота
- Интеграция с OpenAI API (GPT-4o, Whisper, TTS)
- Система платежей через Telegram Payments
- Анализ JSON сценариев Make.com
- Защита от флуда (debounce)
- SQLite база данных для хранения данных пользователей
- Обработка текстовых и голосовых сообщений
- Генерация аудио ответов
- Административные уведомления
