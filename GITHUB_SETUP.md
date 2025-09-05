# GitHub Setup Instructions

Инструкции по настройке GitHub репозитория для проекта.

## Инициализация Git репозитория

1. **Инициализируйте Git** (если еще не сделано):
   ```bash
   git init
   ```

2. **Добавьте все файлы**:
   ```bash
   git add .
   ```

3. **Сделайте первый коммит**:
   ```bash
   git commit -m "Initial commit: Telegram bot with OpenAI integration"
   ```

## Создание GitHub репозитория

1. **Перейдите на GitHub.com** и создайте новый репозиторий
2. **НЕ** инициализируйте с README, .gitignore или лицензией (они уже есть)
3. **Скопируйте URL** репозитория

## Подключение к GitHub

1. **Добавьте remote origin**:
   ```bash
   git remote add origin https://github.com/KornArs/Telegram-bot-with-OpenAI-integration.git
   ```

2. **Переименуйте ветку в main** (если нужно):
   ```bash
   git branch -M main
   ```

3. **Отправьте код на GitHub**:
   ```bash
   git push -u origin main
   ```

## Настройка GitHub репозитория

### 1. Обновите ссылки в файлах

Обновите ссылки в файлах (уже выполнено):
- `README.md`
- `CONTRIBUTING.md`
- `.github/workflows/ci.yml`

### 2. Настройте GitHub Actions

1. Перейдите в **Settings** → **Actions** → **General**
2. Включите **Actions** если они отключены
3. Настройте **Workflow permissions** (Read and write permissions)

### 3. Настройте переменные окружения (Secrets)

Перейдите в **Settings** → **Secrets and variables** → **Actions** и добавьте:

- `BOT_TOKEN`: токен вашего Telegram бота
- `OPENAI_API_KEY`: ключ OpenAI API
- `ADMIN_CHAT_ID`: ID чата администратора
- `PROVIDER_TOKEN`: токен платежного провайдера

### 4. Настройте Issues и Pull Requests

1. **Settings** → **General** → **Features**
2. Включите **Issues** и **Pull requests**
3. Настройте **Pull request reviews** (если нужно)

### 5. Настройте Branch Protection

1. **Settings** → **Branches**
2. Добавьте правило для `main` ветки:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Require branches to be up to date before merging

## Дополнительные настройки

### 1. GitHub Pages (для документации)

1. **Settings** → **Pages**
2. Выберите источник: **GitHub Actions**
3. Создайте workflow для генерации документации

### 2. Code Owners

Создайте файл `.github/CODEOWNERS`:
```
# Global owners
* @your-username

# Python files
*.py @your-username

# Documentation
*.md @your-username
```

### 3. Issue Templates

Создайте `.github/ISSUE_TEMPLATE/` с шаблонами для:
- Bug reports
- Feature requests
- Questions

### 4. Pull Request Template

Создайте `.github/pull_request_template.md`:
```markdown
## Описание изменений

Краткое описание того, что было изменено.

## Тип изменений

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Чеклист

- [ ] Код соответствует стандартам проекта
- [ ] Добавлены тесты для нового функционала
- [ ] Обновлена документация
- [ ] Все тесты проходят
```

## Проверка готовности

Перед публикацией убедитесь, что:

- [ ] Все секретные данные удалены из кода
- [ ] `.gitignore` настроен правильно
- [ ] README.md содержит актуальную информацию
- [ ] LICENSE файл добавлен
- [ ] CONTRIBUTING.md создан
- [ ] CI/CD pipeline настроен
- [ ] Все ссылки в документации обновлены

## Первый релиз

1. **Создайте первый релиз**:
   - Перейдите в **Releases** → **Create a new release**
   - Выберите тег: `v1.0.0`
   - Заголовок: `Initial Release`
   - Описание: скопируйте из CHANGELOG.md

2. **Настройте автоматические релизы** (опционально):
   - Создайте workflow для автоматического создания релизов при создании тегов

## Мониторинг

После публикации следите за:
- Статусом CI/CD pipeline
- Issues и Pull Requests
- Статистикой использования
- Ошибками в логах
