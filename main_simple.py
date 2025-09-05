import os
import json
import tempfile
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Bot, Update, Message, Document, Audio, Voice
from telegram.ext import Application, MessageHandler, filters, PreCheckoutQueryHandler
from telegram.error import TelegramError
from debounce import DebounceManager
from database import DatabaseManager
from openai_manager import OpenAIManager
from make_documentation import MakeDocumentationManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 0))
DEBOUNCE_SECONDS = int(os.getenv('DEBOUNCE_SECONDS', 2))  # Уменьшаем с 6 до 2 секунд
MAX_WAIT_SECONDS = int(os.getenv('MAX_WAIT_SECONDS', 15))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

def get_timestamp():
    """Возвращает текущее время в формате [HH:MM:SS] по московскому времени"""
    return datetime.now(MOSCOW_TZ).strftime("[%H:%M:%S]")

def get_moscow_datetime():
    """Возвращает текущее московское время"""
    return datetime.now(MOSCOW_TZ)

def handle_payments_command(user_id: int, user_name: str) -> Dict:
    """Обрабатывает команду /payments - показывает историю платежей"""
    try:
        payments = db_manager.get_user_payments(user_id)
        
        if not payments:
            return {"action": "reply", "reply_text": "💳 <b>История платежей</b>\n\nУ вас пока нет платежей.", "cta": None, "price": None}
        
        response_text = "💳 <b>История платежей</b>\n"
        response_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, payment in enumerate(payments, 1):
            status_emoji = "✅" if payment['status'] == 'completed' else "⏳" if payment['status'] == 'pending' else "❌"
            response_text += f"<b>Платеж #{i}</b>\n"
            response_text += f"• {status_emoji} Сумма: {payment['amount']} {payment['currency']}\n"
            response_text += f"• 📦 Пакет: {payment['invoice_payload']}\n"
            response_text += f"• 📅 Дата: {payment['created_at']}\n"
            response_text += f"• 🔄 Статус: {payment['status']}\n\n"
        
        response_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error in payments command: {e}")
        return {"action": "reply", "reply_text": "❌ Ошибка при получении истории платежей.", "cta": None, "price": None}

def handle_schedule_command(user_id: int, user_name: str) -> Dict:
    """Обрабатывает команду /schedule - показывает расписание"""
    try:
        schedule = db_manager.get_user_schedule(user_id)
        
        if not schedule:
            return {"action": "reply", "reply_text": "📅 <b>Ваше расписание</b>\n\nУ вас пока нет записей в расписании.", "cta": None, "price": None}
        
        response_text = "📅 <b>Ваше расписание</b>\n"
        response_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, entry in enumerate(schedule, 1):
            status_emoji = "📚" if entry['status'] == 'scheduled' else "✅" if entry['status'] == 'completed' else "❌"
            response_text += f"<b>Занятие #{i}</b>\n"
            response_text += f"• {status_emoji} Тип: {entry['lesson_type']}\n"
            response_text += f"• 🕐 Время: {entry['scheduled_datetime']}\n"
            response_text += f"• ⏱️ Длительность: {entry['duration_minutes']} мин\n"
            response_text += f"• 💰 Оплачено: {entry['amount']} {entry['currency']}\n"
            if entry['notes']:
                response_text += f"• 📝 Заметки: {entry['notes']}\n"
            response_text += "\n"
        
        response_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error in schedule command: {e}")
        return {"action": "reply", "reply_text": "❌ Ошибка при получении расписания.", "cta": None, "price": None}

def handle_docs_command(user_id: int, user_name: str, query: str = "") -> Dict:
    """Обрабатывает команду /docs - поиск по документации Make.com"""
    try:
        if not query:
            categories = make_docs_manager.get_categories()
            response_text = "📚 <b>Документация Make.com</b>\n\n"
            response_text += "Доступные категории:\n"
            for category in categories:
                response_text += f"• {category}\n"
            response_text += "\nИспользуйте: /docs &lt;запрос&gt; для поиска"
            return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}
        
        # Ищем в документации
        docs_results = make_docs_manager.search_documentation(query, limit=3)
        faq_results = make_docs_manager.search_faq(query, limit=2)
        
        if not docs_results and not faq_results:
            return {"action": "reply", "reply_text": f"По запросу '{query}' ничего не найдено. Попробуйте другие ключевые слова.", "cta": None, "price": None}
        
        response_text = f"🔍 <b>Результаты поиска: '{query}'</b>\n\n"
        
        if docs_results:
            response_text += "📖 <b>Документация:</b>\n"
            for doc in docs_results:
                level_emoji = "🟢" if doc['difficulty_level'] == 'beginner' else "🟡" if doc['difficulty_level'] == 'intermediate' else "🔴"
                response_text += f"{level_emoji} <b>{doc['title']}</b> ({doc['category']})\n"
                response_text += f"📝 {doc['content'][:150]}...\n\n"
        
        if faq_results:
            response_text += "❓ <b>FAQ:</b>\n"
            for faq in faq_results:
                response_text += f"<b>Q:</b> {faq['question']}\n"
                response_text += f"<b>A:</b> {faq['answer'][:100]}...\n\n"
        
        return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error in docs command: {e}")
        return {"action": "reply", "reply_text": "Ошибка при поиске документации.", "cta": None, "price": None}

def handle_help_command(user_id: int, user_name: str) -> Dict:
    """Обрабатывает команду /help - показывает справку"""
    help_text = """
🤖 <b>Make.com Помощник - Справка</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>Основные команды:</b>
• `/start` - запуск помощника
• `/help` - эта справка  
• `/docs <запрос>` - поиск документации
• `/payments` - история платежей
• `/schedule` - ваше расписание
• `/time` - московское время

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 <b>Возможности бота:</b>
• 📚 Ответы на вопросы по Make.com
• 🔍 Анализ ваших сценариев
• 💰 Система платежей
• 📅 Планирование занятий
• 🎤 Голосовые сообщения
• 📄 Обработка документов

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Для сложных задач</b> бот предложит индивидуальные занятия с экспертом!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Пакеты обучения:</b>
• 1 занятие (2 часа) - 10,000₽
• 3 занятия - 25,000₽  
• Месяц обучения - 60,000₽

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return {"action": "reply", "reply_text": help_text, "cta": None, "price": None}

def handle_start_command(user_id: int, user_name: str) -> Dict:
    """Обрабатывает команду /start - приветствие и краткая справка"""
    welcome_text = f"""
🤖 <b>Добро пожаловать в Make.com Помощник!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Привет, {user_name}! Я ваш персональный эксперт по платформе Make.com.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 <b>Что я умею:</b>
• 📚 Отвечать на вопросы по Make.com
• 🔍 Анализировать ваши сценарии
• 💰 Принимать платежи за обучение
• 📅 Планировать индивидуальные занятия
• 🎤 Обрабатывать голосовые сообщения
• 📄 Читать и анализировать документы

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>Основные команды:</b>
• /start - запуск помощника
• /help - подробная справка
• /docs &lt;запрос&gt; - поиск документации
• /payments - история платежей
• /schedule - ваше расписание
• /time - московское время

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Для сложных задач</b> я предложу индивидуальные занятия с экспертом!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Отправьте мне любой вопрос по Make.com или загрузите сценарий для анализа.
"""
    return {"action": "reply", "reply_text": welcome_text, "cta": None, "price": None}

def handle_time_command() -> Dict:
    moscow_time = get_moscow_datetime()
    formatted_time = moscow_time.strftime("%Y-%m-%d %H:%M:%S")
    weekday = moscow_time.strftime("%A")
    
    response_text = f"🕐 <b>Текущее время в Москве</b>\n"
    response_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    response_text += f"📅 <b>Дата и время:</b>\n"
    response_text += f"• {formatted_time}\n\n"
    response_text += f"📆 <b>День недели:</b>\n"
    response_text += f"• {weekday}\n\n"
    response_text += f"🌍 <b>Часовой пояс:</b>\n"
    response_text += f"• UTC+3 (Москва)\n"
    response_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}

def analyze_make_scenario(scenario_data: Dict) -> Dict:
    """Анализирует JSON сценарий Make.com и возвращает рекомендации"""
    try:
        analysis = {
            "modules_count": 0,
            "connections_count": 0,
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "complexity": "low",
            "modules_details": []
        }
        
        print(f"[{get_timestamp()}] Анализ JSON структуры. Ключи верхнего уровня: {list(scenario_data.keys())}")
        
        # Make.com blueprint структура: flow - массив модулей
        if "flow" in scenario_data and isinstance(scenario_data["flow"], list):
            all_modules = []
            
            def extract_modules_recursive(flow_list, depth=0):
                """Рекурсивно извлекает все модули включая вложенные в routes"""
                modules_found = []
                for module_item in flow_list:
                    if not isinstance(module_item, dict):
                        continue
                    
                    # Добавляем основной модуль
                    if "module" in module_item:
                        modules_found.append(module_item)
                        
                        module_type = module_item.get("module", "unknown")
                        module_id = module_item.get("id", "unknown")
                        print(f"[{get_timestamp()}] {'  ' * depth}Модуль: ID={module_id}, тип={module_type}")
                    
                    # Проверяем routes для вложенных модулей
                    if "routes" in module_item and isinstance(module_item["routes"], list):
                        print(f"[{get_timestamp()}] {'  ' * depth}Найдены routes в модуле {module_item.get('id', 'unknown')}")
                        for route in module_item["routes"]:
                            if isinstance(route, dict) and "flow" in route:
                                nested_modules = extract_modules_recursive(route["flow"], depth + 1)
                                modules_found.extend(nested_modules)
                
                return modules_found
            
            all_modules = extract_modules_recursive(scenario_data["flow"])
            analysis["modules_count"] = len(all_modules)
            
            print(f"[{get_timestamp()}] Всего найдено {len(all_modules)} модулей (включая вложенные)")
            
            # Анализируем каждый модуль
            for i, module_item in enumerate(all_modules):
                module_type = module_item.get("module", "unknown")
                module_id = module_item.get("id", f"ID_{i+1}")
                version = module_item.get("version", "не указана")
                
                # Детали модуля
                module_detail = {
                    "id": module_id,
                    "type": module_type,
                    "version": version,
                    "has_parameters": "parameters" in module_item,
                    "has_mapper": "mapper" in module_item
                }
                analysis["modules_details"].append(module_detail)
                
                # Проверки на ошибки
                if not module_item.get("module"):
                    analysis["errors"].append(f"Модуль {module_id} без указания типа")
                
                if "parameters" not in module_item and module_type != "builtin:BasicRouter":
                    analysis["warnings"].append(f"Модуль {module_id} ({module_type}) без параметров")
                
                # Специфичные проверки
                if "webhook" in module_type.lower() or "watch" in module_type.lower():
                    params = module_item.get("parameters", {})
                    if not params.get("hook") and not params.get("__IMTHOOK__"):
                        analysis["warnings"].append(f"Webhook модуль {module_id} без hook")
                
                if "datastore" in module_type.lower():
                    params = module_item.get("parameters", {})
                    if not params.get("datastore"):
                        analysis["warnings"].append(f"DataStore модуль {module_id} без указания хранилища")
        
        # Анализируем connections (соединения между модулями)
        connections_found = 0
        
        # Проверяем mapper во всех найденных модулях
        for module_item in all_modules:
            if isinstance(module_item, dict) and "mapper" in module_item:
                mapper = module_item["mapper"]
                if isinstance(mapper, dict) and mapper:
                    connections_found += len(mapper)
        
        analysis["connections_count"] = connections_found
        
        # Определяем сложность
        if analysis["modules_count"] > 20:
            analysis["complexity"] = "очень высокая"
        elif analysis["modules_count"] > 10:
            analysis["complexity"] = "высокая"
        elif analysis["modules_count"] > 5:
            analysis["complexity"] = "средняя"
        else:
            analysis["complexity"] = "низкая"
        
        # Генерируем рекомендации
        if analysis["modules_count"] == 0:
            analysis["recommendations"].append("❌ Сценарий пустой - добавьте модули")
        else:
            analysis["recommendations"].append(f"✅ Сценарий содержит {analysis['modules_count']} модулей")
        
        if analysis["modules_count"] > 15:
            analysis["recommendations"].append("⚠️ Сложный сценарий - рекомендую разбить на части")
        
        if analysis["errors"]:
            analysis["recommendations"].append("🔴 Найдены критические ошибки - требуют исправления")
        
        if analysis["warnings"]:
            analysis["recommendations"].append(f"🟡 Найдено {len(analysis['warnings'])} предупреждений")
        
        if analysis["connections_count"] == 0 and analysis["modules_count"] > 1:
            analysis["recommendations"].append("🔗 Проверьте соединения между модулями")
        elif analysis["connections_count"] > 0:
            analysis["recommendations"].append(f"✅ Настроено {analysis['connections_count']} соединений")
        
        # Анализ типов модулей
        module_types = [m["type"] for m in analysis["modules_details"]]
        unique_types = set(module_types)
        analysis["recommendations"].append(f"📊 Используется {len(unique_types)} типов модулей: {', '.join(list(unique_types)[:5])}")
        
        print(f"[{get_timestamp()}] Результат анализа: {analysis['modules_count']} модулей, {analysis['connections_count']} соединений")
        
        return analysis
        
    except Exception as e:
        print(f"[{get_timestamp()}] Ошибка анализа JSON: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"Ошибка анализа: {str(e)}",
            "modules_count": 0,
            "connections_count": 0,
            "errors": [f"Ошибка парсинга: {str(e)}"],
            "warnings": [],
            "recommendations": ["Проверьте структуру JSON файла"],
            "complexity": "неизвестно"
        }

def process_message_with_ai(user_id: int, message_text: str, user_name: str = None) -> Dict:
    """Обрабатывает сообщение через OpenAI"""
    try:
        # Сохраняем сообщение в историю БД
        db_manager.save_message(user_id, message_text, 'user')
        
        # Отправляем в OpenAI
        response = openai_manager.send_message_to_user(user_id, message_text, user_name)
        
        # Сохраняем ответ в историю БД
        if response.get('reply_text'):
            db_manager.save_message(user_id, response['reply_text'], 'assistant')
        
        return response
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing message with AI: {e}")
        return {"action": "reply", "reply_text": "Произошла ошибка при обработке запроса.", "cta": None, "price": None}

def process_audio_message(user_id: int, audio_file_path: str, user_name: str = None) -> Dict:
    """Обрабатывает аудио сообщение"""
    try:
        # Транскрибируем аудио
        transcript = openai_manager.transcribe_audio(audio_file_path)
        
        if transcript and transcript != "Ошибка при транскрибировании аудио":
            # Сохраняем транскрипт в историю
            db_manager.save_message(user_id, f"[АУДИО] {transcript}", 'user')
            
            # Обрабатываем через AI
            response = openai_manager.send_message_to_user(user_id, transcript, user_name)
            
            # Сохраняем ответ
            if response.get('reply_text'):
                db_manager.save_message(user_id, response['reply_text'], 'assistant')
            
            return response
        else:
            return {"action": "reply", "reply_text": "Не удалось распознать аудио сообщение.", "cta": None, "price": None}
            
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing audio: {e}")
        return {"action": "reply", "reply_text": "Ошибка при обработке аудио.", "cta": None, "price": None}

def process_document_message(user_id: int, document_path: str, user_name: str = None, original_filename: str = None) -> Dict:
    """Обрабатывает документ (JSON сценарии Make.com и другие файлы)"""
    try:
        file_extension = os.path.splitext(document_path)[1].lower()
        filename = original_filename or os.path.basename(document_path)
        
        print(f"[{get_timestamp()}] Обрабатываем файл: {filename} (расширение: {file_extension})")
        
        # Обрабатываем JSON файлы (сценарии Make.com)
        if file_extension == '.json':
            # Читаем и парсим JSON
            with open(document_path, 'r', encoding='utf-8') as f:
                try:
                    scenario_data = json.load(f)
                    print(f"[{get_timestamp()}] JSON успешно загружен. Размер данных: {len(str(scenario_data))} символов")
                except json.JSONDecodeError as e:
                    return {"action": "reply", "reply_text": f"Ошибка в JSON файле: {str(e)}", "cta": None, "price": None}
            
            # Анализируем сценарий
            analysis = analyze_make_scenario(scenario_data)
            
            print(f"[{get_timestamp()}] Анализ завершен: {analysis}")
            
            # Формируем ответ
            response_text = f"📊 <b>Анализ сценария Make.com</b>\n\n"
            response_text += f"🔢 Модулей: {analysis['modules_count']}\n"
            response_text += f"🔗 Соединений: {analysis['connections_count']}\n"
            response_text += f"📈 Сложность: {analysis['complexity']}\n\n"
            
            if analysis['errors']:
                response_text += "❌ <b>Ошибки:</b>\n"
                for error in analysis['errors']:
                    response_text += f"• {error}\n"
                response_text += "\n"
            
            if analysis['warnings']:
                response_text += "⚠️ <b>Предупреждения:</b>\n"
                for warning in analysis['warnings']:
                    response_text += f"• {warning}\n"
                response_text += "\n"
            
            if analysis['recommendations']:
                response_text += "💡 <b>Рекомендации:</b>\n"
                for rec in analysis['recommendations']:
                    response_text += f"• {rec}\n"
            
            # Сохраняем в историю
            db_manager.save_message(user_id, f"[JSON СЦЕНАРИЙ] {response_text}", 'user')
            
            # Возвращаем результат анализа сразу
            return {"action": "reply", "reply_text": response_text, "cta": None, "price": None}
        
        # Обрабатываем текстовые файлы
        elif file_extension in ['.txt', '.py', '.js', '.html', '.css', '.md', '.csv', '.log']:
            try:
                with open(document_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except UnicodeDecodeError:
                # Пробуем другие кодировки
                try:
                    with open(document_path, 'r', encoding='cp1251') as f:
                        file_content = f.read()
                except UnicodeDecodeError:
                    with open(document_path, 'r', encoding='latin1') as f:
                        file_content = f.read()
            
            # Ограничиваем размер содержимого
            if len(file_content) > 10000:
                file_content = file_content[:10000] + "\n... (файл обрезан)"
            
            # Сохраняем в историю
            db_manager.save_message(user_id, f"[ФАЙЛ {filename}] {file_content[:500]}...", 'user')
            
            # Возвращаем содержимое файла
            return {"action": "reply", "reply_text": f"📄 <b>Содержимое файла {filename}</b>\n\n{file_content[:2000]}...", "cta": None, "price": None}
        
        else:
            # Неподдерживаемый тип файла
            return {"action": "reply", "reply_text": f"📄 Получен файл {filename} ({file_extension})\n\nЭтот тип файла не поддерживается для чтения. Поддерживаемые форматы: .txt, .py, .js, .html, .css, .md, .csv, .log", "cta": None, "price": None}
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing document: {e}")
        return {"action": "reply", "reply_text": f"Ошибка при обработке файла: {str(e)}", "cta": None, "price": None}

async def handle_message(update: Update, context):
    """Обрабатывает входящие сообщения"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            message = update.message
            user_id = message.from_user.id
            user_name = message.from_user.first_name or "Пользователь"
            
            print(f"[{get_timestamp()}] Обрабатываем сообщение от {user_id}: {message.text or '[медиа]'}...")
            
            # Проверяем debounce только для обычных сообщений, не для команд
            is_command = message.text and any(message.text.lower().startswith(cmd) for cmd in ('/start', '/help', '/docs', '/payments', '/schedule', '/time'))
            
            if not is_command and debounce_manager.is_debounced(user_id):
                print(f"[{get_timestamp()}] Сообщение от {user_id} заблокировано debounce")
                return
            
            # Отправляем индикатор набора
            try:
                await context.bot.send_chat_action(chat_id=user_id, action="typing")
            except Exception as e:
                print(f"[{get_timestamp()}] Error sending chat action: {e}")
            
            # Обрабатываем разные типы сообщений
            if message.text:
                # Проверяем специальные команды
                if message.text.lower().startswith('/start'):
                    response = handle_start_command(user_id, user_name)
                elif message.text.lower().startswith('/help'):
                    response = handle_help_command(user_id, user_name)
                elif message.text.lower().startswith('/docs'):
                    # Извлекаем запрос после /docs
                    query = message.text[5:].strip() if len(message.text) > 5 else ""
                    response = handle_docs_command(user_id, user_name, query)
                elif message.text.lower().startswith('/payments'):
                    response = handle_payments_command(user_id, user_name)
                elif message.text.lower().startswith('/schedule'):
                    response = handle_schedule_command(user_id, user_name)
                elif message.text.lower().startswith('/time'):
                    response = handle_time_command()
                else:
                    # Обычное текстовое сообщение
                    response = process_message_with_ai(user_id, message.text, user_name)
                
            elif message.voice:
                # Голосовое сообщение
                file = await message.voice.get_file()
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                    await file.download_to_drive(temp_file.name)
                    temp_file_path = temp_file.name
                
                response = process_audio_message(user_id, temp_file_path, user_name)
                os.unlink(temp_file_path)  # Удаляем временный файл
                    
            elif message.audio:
                # Аудио файл
                file = await message.audio.get_file()
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                    await file.download_to_drive(temp_file.name)
                    temp_file_path = temp_file.name
                
                response = process_audio_message(user_id, temp_file_path, user_name)
                os.unlink(temp_file_path)
                    
            elif message.document:
                # Документ (JSON сценарии Make.com и другие файлы)
                file = await message.document.get_file()
                
                # Получаем оригинальное имя файла и расширение
                original_filename = message.document.file_name or "document"
                file_extension = os.path.splitext(original_filename)[1] or '.txt'
                
                # Создаем временный файл с правильным расширением
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    temp_file_path = temp_file.name
                
                # Скачиваем файл
                await file.download_to_drive(temp_file_path)
                
                print(f"[{get_timestamp()}] Скачан файл: {original_filename} -> {temp_file_path}")
                
                response = process_document_message(user_id, temp_file_path, user_name, original_filename)
                os.unlink(temp_file_path)
            else:
                response = {"action": "reply", "reply_text": "Извините, я не понимаю этот тип сообщения.", "cta": None, "price": None}
            
            # Отправляем ответ
            if response.get("action") == "reply":
                reply_text = response.get("reply_text", "")
                
                # Отвечаем аудио только если получили аудио сообщение
                if (message.voice or message.audio) and len(reply_text) > 50:
                    audio_data = openai_manager.generate_speech(reply_text, voice="onyx")  # Мужской голос
                    if audio_data:
                        # Сохраняем временный файл
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                            temp_file.write(audio_data)
                            temp_file_path = temp_file.name
                        
                        # Отправляем голосовое сообщение
                        await context.bot.send_voice(
                            chat_id=user_id,
                            voice=open(temp_file_path, 'rb'),
                            caption=reply_text[:100] + "..." if len(reply_text) > 100 else None
                        )
                        
                        # Удаляем временный файл
                        os.unlink(temp_file_path)
                    else:
                        await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode='HTML')
                else:
                                         # Для всех остальных случаев отвечаем текстом
                     await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode='HTML')
                     
                    
            elif response.get("action") == "offer_mentorship":
                # Предлагаем обучение
                reply_text = response.get("reply_text", "")
                cta = response.get("cta")
                price = response.get("price")
                
                await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode='HTML')
                
                if cta and price:
                    await context.bot.send_invoice(
                        chat_id=user_id,
                        title=cta,
                        description=f"Обучение по Make.com: {cta}",
                        payload=f"mentorship_{user_id}_{cta}",
                        provider_token=PROVIDER_TOKEN,
                        currency="RUB",
                        prices=[{"label": cta, "amount": price}],
                        start_parameter="make_mentorship"
                    )
            
            elif response.get("action") == "schedule_request":
                # Обрабатываем запрос на планирование
                reply_text = response.get("reply_text", "")
                await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode='HTML')
            
            elif response.get("action") == "documentation_search":
                # Обрабатываем поиск документации
                reply_text = response.get("reply_text", "")
                await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode='HTML')
            
            # Если дошли сюда - успешно обработали сообщение
            break
            
        except Exception as e:
            retry_count += 1
            print(f"[{get_timestamp()}] Error handling message (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                print(f"[{get_timestamp()}] Max retries reached, sending error message to user")
                try:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text="⚠️ Произошла ошибка при обработке сообщения. Попробуйте еще раз через минуту.",
                        parse_mode='HTML'
                    )
                except:
                    pass
            else:
                # Ждем перед повторной попыткой
                import asyncio
                await asyncio.sleep(2 ** retry_count)  # Экспоненциальная задержка

async def handle_pre_checkout_query(update: Update, context):
    """Обрабатывает предварительную проверку платежа"""
    try:
        query = update.pre_checkout_query
        print(f"[{get_timestamp()}] Pre-checkout query from {query.from_user.id}")
        
        # Проверяем, не был ли уже обработан этот платеж
        if db_manager.payment_exists(query.invoice_payload):
            await query.answer(ok=False, error_message="Платеж уже обработан")
            return
        
        await query.answer(ok=True)
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling pre-checkout query: {e}")
        await query.answer(ok=False, error_message="Ошибка обработки платежа")

async def handle_successful_payment(update: Update, context):
    """Обрабатывает успешный платеж"""
    try:
        message = update.message
        payment_info = message.successful_payment
        user_id = message.from_user.id
        
        print(f"[{get_timestamp()}] Successful payment from {user_id}: {payment_info.total_amount} {payment_info.currency}")
        
        # Проверяем, не был ли уже обработан этот платеж
        if db_manager.payment_exists(payment_info.invoice_payload):
            print(f"[{get_timestamp()}] Payment already processed: {payment_info.invoice_payload}")
            return
        
        # Сохраняем информацию о платеже
        payment_data = {
            'user_id': user_id,
            'invoice_payload': payment_info.invoice_payload,
            'total_amount': payment_info.total_amount,
            'currency': payment_info.currency,
            'provider_payment_charge_id': payment_info.provider_payment_charge_id,
            'telegram_payment_charge_id': payment_info.telegram_payment_charge_id,
            'order_info': {
                'name': payment_info.order_info.name if payment_info.order_info else None,
                'phone_number': payment_info.order_info.phone_number if payment_info.order_info else None,
                'email': payment_info.order_info.email if payment_info.order_info else None
            }
        }
        
        db_manager.save_payment(payment_data)
        db_manager.update_payment_status(payment_info.invoice_payload, 'completed')
        
        # Создаем пользователя если его нет
        if not db_manager.user_exists(user_id):
            user_data = {
                'user_id': user_id,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'username': message.from_user.username
            }
            db_manager.create_user(user_data)
        
        # Создаем запись в расписании на основе типа платежа
        lesson_type = "Индивидуальное занятие"
        duration_minutes = 120  # 2 часа по умолчанию
        
        # Определяем тип занятия по payload
        if "mentorship" in payment_info.invoice_payload:
            if "3 занятия" in payment_info.invoice_payload:
                lesson_type = "Пакет из 3 занятий"
                duration_minutes = 360  # 6 часов
            elif "Месяц обучения" in payment_info.invoice_payload:
                lesson_type = "Месяц обучения"
                duration_minutes = 480  # 8 часов
            else:
                lesson_type = "Индивидуальное занятие"
                duration_minutes = 120  # 2 часа
        
        # Создаем запись в расписании
        schedule_data = {
            'user_id': user_id,
            'lesson_type': lesson_type,
            'scheduled_datetime': datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'duration_minutes': duration_minutes,
            'amount': payment_info.total_amount,
            'currency': payment_info.currency,
            'status': 'scheduled',
            'notes': f'Оплачено: {payment_info.invoice_payload}'
        }
        
        db_manager.save_schedule(schedule_data)
        
        # Уведомляем администратора
        admin_message = f"""
💰 Новый платеж!

👤 Пользователь: {payment_data['user_id']}
💳 Сумма: {payment_data['total_amount']} {payment_data['currency']}
📦 Пакет: {payment_data['invoice_payload']}
🆔 ID платежа: {payment_data['provider_payment_charge_id']}
📅 Создана запись в расписании: {lesson_type}
        """
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode='HTML')
        
        # Отправляем подтверждение пользователю
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"✅ Спасибо за оплату! Ваш платеж на сумму {payment_info.total_amount} {payment_info.currency} успешно обработан. Мы свяжемся с вами в ближайшее время.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling successful payment: {e}")

async def error_handler(update: Update, context):
    """Обрабатывает ошибки бота"""
    error = context.error
    print(f"[{get_timestamp()}] Error occurred: {error}")
    
    # Обрабатываем специфичные ошибки
    if "httpx.RemoteProtocolError" in str(error):
        print(f"[{get_timestamp()}] Network protocol error - server disconnected")
    elif "httpx.ConnectError" in str(error):
        print(f"[{get_timestamp()}] Connection error - network issues")
    elif "Timed out" in str(error):
        print(f"[{get_timestamp()}] Request timeout - increasing timeouts")
    else:
        print(f"[{get_timestamp()}] Unknown error type: {type(error)}")
    
    # Пытаемся уведомить пользователя если есть update
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Произошла временная ошибка сети. Попробуйте еще раз через минуту.",
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"[{get_timestamp()}] Could not send error message to user: {e}")
    
    return

def main():
    """Основная функция для запуска бота"""
    # Инициализация компонентов
    global debounce_manager, db_manager, openai_manager, make_docs_manager
    debounce_manager = DebounceManager(DEBOUNCE_SECONDS)
    db_manager = DatabaseManager()
    openai_manager = OpenAIManager(OPENAI_API_KEY)
    make_docs_manager = MakeDocumentationManager()

    # Принудительно инициализируем базу данных
    print(f"[{get_timestamp()}] Инициализация базы данных...")
    db_manager.init_database()
    print(f"[{get_timestamp()}] База данных инициализирована: {db_manager.db_path}")
    
    print(f"[{get_timestamp()}] Telegram bot started")
    print(f"[{get_timestamp()}] Database: {db_manager.db_path}")
    print(f"[{get_timestamp()}] OpenAI: {'Connected' if OPENAI_API_KEY else 'Missing API Key'}")
    
    # Создаем приложение с обработкой ошибок
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики (специфичные первыми!)
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
    application.add_handler(MessageHandler(filters.ALL, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота с повышенными таймаутами
    print(f"[{get_timestamp()}] Starting polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        timeout=60,  # Увеличиваем таймаут до 60 секунд
        poll_interval=3.0,  # Увеличиваем интервал между запросами
        drop_pending_updates=True,  # Игнорируем старые обновления
        close_loop=False  # Не закрываем loop при ошибках
    )

if __name__ == '__main__':
    main()
