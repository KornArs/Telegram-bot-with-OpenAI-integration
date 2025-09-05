import os
import json
import tempfile
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
import httpx
from dotenv import load_dotenv
from telegram import Bot, Update, Message, Document, Audio, Voice
from telegram.ext import Application, MessageHandler, filters, PreCheckoutQueryHandler
from telegram.error import TelegramError
from debounce import DebounceManager
from database import DatabaseManager
from openai_manager import OpenAIManager

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 0))
ADMIN_KEY = os.getenv('ADMIN_KEY')
DEBOUNCE_SECONDS = int(os.getenv('DEBOUNCE_SECONDS', 6))
MAX_WAIT_SECONDS = int(os.getenv('MAX_WAIT_SECONDS', 15))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PROVIDER_TOKEN = os.getenv('PROVIDER_TOKEN')

# Инициализация компонентов
app = Flask(__name__)
debounce_manager = DebounceManager(DEBOUNCE_SECONDS, MAX_WAIT_SECONDS)
db_manager = DatabaseManager()
openai_manager = OpenAIManager(OPENAI_API_KEY)
bot = Bot(token=BOT_TOKEN)

def get_timestamp():
    """Возвращает текущее время в формате [HH:MM:SS]"""
    return datetime.now().strftime("[%H:%M:%S]")

async def send_typing_action_async(chat_id: int):
    """Отправляет индикатор набора текста (асинхронно)"""
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending typing action: {e}")

def send_typing_action(chat_id: int):
    """Отправляет индикатор набора текста"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_typing_action_async(chat_id))
        loop.close()
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending typing action: {e}")

async def send_message_async(chat_id: int, text: str, reply_markup=None):
    """Отправляет текстовое сообщение (асинхронно)"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending message: {e}")

def send_message(chat_id: int, text: str, reply_markup=None):
    """Отправляет текстовое сообщение"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_message_async(chat_id, text, reply_markup))
        loop.close()
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending message: {e}")

async def send_voice_message_async(chat_id: int, audio_data: bytes, caption: str = None):
    """Отправляет голосовое сообщение (асинхронно)"""
    try:
        # Сохраняем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        # Отправляем голосовое сообщение
        with open(temp_file_path, 'rb') as voice_file:
            await bot.send_voice(
                chat_id=chat_id,
                voice=voice_file,
                caption=caption
            )

        # Удаляем временный файл
        os.unlink(temp_file_path)
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending voice message: {e}")

def send_voice_message(chat_id: int, audio_data: bytes, caption: str = None):
    """Отправляет голосовое сообщение"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_voice_message_async(chat_id, audio_data, caption))
        loop.close()
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending voice message: {e}")

async def send_invoice_async(chat_id: int, title: str, description: str, payload: str, amount: int):
    """Отправляет счет для оплаты (асинхронно)"""
    try:
        await bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=[{"label": title, "amount": amount}],
            start_parameter="make_mentorship"
        )
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending invoice: {e}")

def send_invoice(chat_id: int, title: str, description: str, payload: str, amount: int):
    """Отправляет счет для оплаты"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_invoice_async(chat_id, title, description, payload, amount))
        loop.close()
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending invoice: {e}")

async def download_file_async(file_id: str) -> str:
    """Скачивает файл и возвращает путь к нему (асинхронно)"""
    try:
        # Получаем информацию о файле
        file_info = await bot.get_file(file_id)
        
        # Создаем временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_info.file_path)[1] if file_info.file_path else '')
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Скачиваем файл
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        response = httpx.get(file_url)
        response.raise_for_status()
        
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        
        return temp_file_path
    except Exception as e:
        print(f"[{get_timestamp()}] Error downloading file: {e}")
        return None

def download_file(file_id: str) -> str:
    """Скачивает файл и возвращает путь к нему"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(download_file_async(file_id))
        loop.close()
        return result
    except Exception as e:
        print(f"[{get_timestamp()}] Error downloading file: {e}")
        return None

def analyze_make_scenario(scenario_data: Dict) -> Dict:
    """Анализирует JSON сценарий Make.com и возвращает рекомендации"""
    try:
        analysis = {
            "modules_count": 0,
            "connections_count": 0,
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "complexity": "low"
        }
        
        # Анализируем структуру сценария
        if "flow" in scenario_data:
            flow = scenario_data["flow"]
            
            # Подсчитываем модули
            if "modules" in flow:
                analysis["modules_count"] = len(flow["modules"])
                
                # Анализируем каждый модуль
                for module in flow["modules"]:
                    module_type = module.get("type", "unknown")
                    module_name = module.get("name", "Unnamed")
                    
                    # Проверяем на ошибки
                    if not module.get("name"):
                        analysis["errors"].append(f"Модуль без имени: {module_type}")
                    
                    if module_type == "http" and not module.get("url"):
                        analysis["errors"].append(f"HTTP модуль без URL: {module_name}")
                    
                    if module_type == "filter" and not module.get("filters"):
                        analysis["warnings"].append(f"Фильтр без условий: {module_name}")
            
            # Подсчитываем соединения
            if "connections" in flow:
                analysis["connections_count"] = len(flow["connections"])
                
                # Проверяем соединения на ошибки
                for conn in flow["connections"]:
                    if not conn.get("from") or not conn.get("to"):
                        analysis["errors"].append("Соединение без указания модулей")
            
            # Определяем сложность
            if analysis["modules_count"] > 20:
                analysis["complexity"] = "high"
            elif analysis["modules_count"] > 10:
                analysis["complexity"] = "medium"
        
        # Генерируем рекомендации
        if analysis["modules_count"] == 0:
            analysis["recommendations"].append("Сценарий пустой - добавьте модули")
        
        if analysis["modules_count"] > 15:
            analysis["recommendations"].append("Сценарий слишком сложный - разбейте на части")
        
        if analysis["errors"]:
            analysis["recommendations"].append("Исправьте ошибки перед запуском")
        
        if analysis["modules_count"] > 0 and analysis["connections_count"] == 0:
            analysis["recommendations"].append("Добавьте соединения между модулями")
        
        return analysis
        
    except Exception as e:
        return {
            "error": f"Ошибка анализа: {str(e)}",
            "modules_count": 0,
            "connections_count": 0,
            "errors": [],
            "warnings": [],
            "recommendations": ["Проверьте структуру JSON файла"],
            "complexity": "unknown"
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

async def process_audio_message_async(user_id: int, audio_file_path: str, user_name: str = None) -> Dict:
    """Обрабатывает аудио сообщение (асинхронно)"""
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

def process_audio_message(user_id: int, audio_file_path: str, user_name: str = None) -> Dict:
    """Обрабатывает аудио сообщение"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_audio_message_async(user_id, audio_file_path, user_name))
        loop.close()
        return result
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing audio: {e}")
        return {"action": "reply", "reply_text": "Ошибка при обработке аудио.", "cta": None, "price": None}

async def process_document_message_async(user_id: int, document_path: str, user_name: str = None) -> Dict:
    """Обрабатывает документ (JSON сценарии Make.com) (асинхронно)"""
    try:
        # Проверяем, что это JSON файл
        if not document_path.lower().endswith('.json'):
            return {"action": "reply", "reply_text": "Поддерживаются только JSON файлы со сценариями Make.com.", "cta": None, "price": None}
        
        # Читаем и парсим JSON
        with open(document_path, 'r', encoding='utf-8') as f:
            try:
                scenario_data = json.load(f)
            except json.JSONDecodeError as e:
                return {"action": "reply", "reply_text": f"Ошибка в JSON файле: {str(e)}", "cta": None, "price": None}
        
        # Анализируем сценарий
        analysis = analyze_make_scenario(scenario_data)
        
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
        
        # Обрабатываем через AI для дополнительных советов
        ai_response = openai_manager.send_message_to_user(
            user_id, 
            f"Проанализируй этот сценарий Make.com и дай дополнительные рекомендации: {response_text}", 
            user_name
        )
        
        # Сохраняем ответ AI
        if ai_response.get('reply_text'):
            db_manager.save_message(user_id, ai_response['reply_text'], 'assistant')
        
        return ai_response
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing document: {e}")
        return {"action": "reply", "reply_text": "Ошибка при обработке документа.", "cta": None, "price": None}

def process_document_message(user_id: int, document_path: str, user_name: str = None) -> Dict:
    """Обрабатывает документ (JSON сценарии Make.com)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_document_message_async(user_id, document_path, user_name))
        loop.close()
        return result
    except Exception as e:
        print(f"[{get_timestamp()}] Error processing document: {e}")
        return {"action": "reply", "reply_text": "Ошибка при обработке документа.", "cta": None, "price": None}

async def handle_message(update: Update, context):
    """Обрабатывает входящие сообщения"""
    try:
        message = update.message
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Пользователь"
        
        print(f"[{get_timestamp()}] Обрабатываем сообщение от {user_id}: {message.text or '[медиа]'}...")
        
        # Проверяем debounce
        if debounce_manager.is_debounced(user_id):
            print(f"[{get_timestamp()}] Сообщение от {user_id} заблокировано debounce")
            return
        
        # Отправляем индикатор набора
        send_typing_action(user_id)
        
        # Обрабатываем разные типы сообщений
        if message.text:
            # Текстовое сообщение
            response = process_message_with_ai(user_id, message.text, user_name)
            
        elif message.voice:
            # Голосовое сообщение
            file_path = download_file(message.voice.file_id)
            if file_path:
                response = process_audio_message(user_id, file_path, user_name)
                os.unlink(file_path)  # Удаляем временный файл
            else:
                response = {"action": "reply", "reply_text": "Ошибка при загрузке голосового сообщения.", "cta": None, "price": None}
                
        elif message.audio:
            # Аудио файл
            file_path = download_file(message.audio.file_id)
            if file_path:
                response = process_audio_message(user_id, file_path, user_name)
                os.unlink(file_path)
            else:
                response = {"action": "reply", "reply_text": "Ошибка при загрузке аудио файла.", "cta": None, "price": None}
                
        elif message.document:
            # Документ (JSON сценарии Make.com)
            file_path = download_file(message.document.file_id)
            if file_path:
                response = process_document_message(user_id, file_path, user_name)
                os.unlink(file_path)
            else:
                response = {"action": "reply", "reply_text": "Ошибка при загрузке документа.", "cta": None, "price": None}
        else:
            response = {"action": "reply", "reply_text": "Извините, я не понимаю этот тип сообщения.", "cta": None, "price": None}
        
        # Отправляем ответ
        if response.get("action") == "reply":
            reply_text = response.get("reply_text", "")
            
            # Если нужно сгенерировать голосовое сообщение (мужской голос)
            if len(reply_text) > 100:  # Для длинных ответов
                audio_data = openai_manager.generate_speech(reply_text, voice="onyx")  # Мужской голос
                if audio_data:
                    send_voice_message(user_id, audio_data, reply_text[:100] + "...")
                else:
                    send_message(user_id, reply_text)
            else:
                send_message(user_id, reply_text)
                
        elif response.get("action") == "offer_mentorship":
            # Предлагаем обучение
            reply_text = response.get("reply_text", "")
            cta = response.get("cta")
            price = response.get("price")
            
            send_message(user_id, reply_text)
            
            if cta and price:
                send_invoice(user_id, cta, f"Обучение по Make.com: {cta}", f"mentorship_{user_id}_{cta}", price)
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling message: {e}")
        try:
            send_message(user_id, "Произошла ошибка при обработке сообщения.")
        except:
            pass

async def handle_pre_checkout_query(update: Update, context):
    """Обрабатывает предварительную проверку платежа"""
    try:
        query = update.pre_checkout_query
        print(f"[{get_timestamp()}] Pre-checkout query from {query.from_user.id}")
        
        # Проверяем, не был ли уже обработан этот платеж
        if db_manager.payment_exists(query.invoice_payload):
            await bot.answer_pre_checkout_query(query.id, ok=False, error_message="Платеж уже обработан")
            return
        
        await bot.answer_pre_checkout_query(query.id, ok=True)
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling pre-checkout query: {e}")
        await bot.answer_pre_checkout_query(query.id, ok=False, error_message="Ошибка обработки платежа")

async def handle_successful_payment(update: Update, context):
    """Обрабатывает успешный платеж"""
    try:
        message = update.message
        payment_info = message.successful_payment
        user_id = message.from_user.id
        
        print(f"[{get_timestamp()}] Successful payment from {user_id}: {payment_info.total_amount} {payment_info.currency}")
        
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
        
        # Уведомляем администратора
        notify_admin(payment_data)
        
        # Отправляем подтверждение пользователю
        send_message(user_id, f"✅ Спасибо за оплату! Ваш платеж на сумму {payment_info.total_amount} {payment_info.currency} успешно обработан. Мы свяжемся с вами в ближайшее время.")
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error handling successful payment: {e}")

def notify_admin(payment_data: Dict):
    """Уведомляет администратора о платеже"""
    try:
        message = f"""
💰 Новый платеж!

👤 Пользователь: {payment_data['user_id']}
💳 Сумма: {payment_data['total_amount']} {payment_data['currency']}
📦 Пакет: {payment_data['invoice_payload']}
🆔 ID платежа: {payment_data['provider_payment_charge_id']}
        """
        send_message(ADMIN_CHAT_ID, message)
    except Exception as e:
        print(f"[{get_timestamp()}] Error notifying admin: {e}")

def polling_worker():
    """Рабочий поток для polling обновлений"""
    async def run_polling():
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(MessageHandler(filters.ALL, handle_message))
        application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))
        application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
        
        print(f"[{get_timestamp()}] Starting polling...")
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_polling())
    finally:
        loop.close()

# Flask endpoints
@app.route('/')
def health_check():
    """Проверка здоровья сервиса"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "bot_token": "configured" if BOT_TOKEN else "missing",
        "openai_key": "configured" if OPENAI_API_KEY else "missing"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint для внешних сервисов"""
    try:
        data = request.get_json()
        print(f"[{get_timestamp()}] Webhook received: {data}")
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"[{get_timestamp()}] Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/users')
def get_users():
    """Получает список пользователей (для админа)"""
    try:
        # Простая проверка авторизации
        if request.headers.get('X-Admin-Key') != ADMIN_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Здесь можно добавить логику получения пользователей из БД
        return jsonify({"users": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"[{get_timestamp()}] Telegram bot started")
    print(f"[{get_timestamp()}] Health check: http://localhost:5000/")
    print(f"[{get_timestamp()}] Database: {db_manager.db_path}")
    print(f"[{get_timestamp()}] OpenAI: {'Connected' if OPENAI_API_KEY else 'Missing API Key'}")
    
    # Запускаем polling в отдельном потоке
    polling_thread = threading.Thread(target=polling_worker, daemon=True)
    polling_thread.start()
    
    # Запускаем Flask сервер
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
