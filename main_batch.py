import os
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict

import httpx
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from debounce import DebounceManager

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
DEBOUNCE_SECONDS = int(os.getenv('DEBOUNCE_SECONDS', 4))
MAX_WAIT_SECONDS = int(os.getenv('MAX_WAIT_SECONDS', 15))
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')
BATCH_TIMEOUT = 10  # секунды для батчинга сообщений

# Глобальное состояние
last_update_id = 0
processed_updates: Set[int] = set()
message_batches = defaultdict(list)  # user_id -> [messages]
batch_timers: Dict[int, threading.Timer] = {}
paid_invoices: Set[str] = set()

# Инициализация Flask и DebounceManager
app = Flask(__name__)
debounce_manager = DebounceManager(
    debounce_seconds=DEBOUNCE_SECONDS,
    max_wait_seconds=MAX_WAIT_SECONDS
)

def get_timestamp() -> str:
    """Возвращает текущее время в формате HH:MM:SS"""
    return datetime.now().strftime("%H:%M:%S")

def send_typing_action(user_id: int, chat_id: int) -> None:
    """Отправляет действие набора текста в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
        data = {
            'chat_id': chat_id,
            'action': 'typing'
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, timeout=5.0)
            if response.status_code != 200:
                print(f"[{get_timestamp()}] Error sending typing action: {response.text}")
                
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending typing action: {e}")

def send_message_to_user(chat_id: int, text: str, parse_mode: str = 'HTML') -> None:
    """Отправляет сообщение пользователю"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, timeout=5.0)
            if response.status_code != 200:
                print(f"[{get_timestamp()}] Error sending message: {response.text}")
                
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending message: {e}")

def send_batch_to_make(user_id: int, messages: List[Dict]) -> None:
    """Отправляет батч сообщений в Make.com"""
    try:
        payload = {
            'event_type': 'message_batch',
            'user_id': user_id,
            'messages': messages,
            'batch_size': len(messages),
            'timestamp': datetime.now().isoformat()
        }
        
        with httpx.Client(verify=False) as client:
            response = client.post(MAKE_WEBHOOK_URL, json=payload, timeout=10.0)
            print(f"[{get_timestamp()}] Отправлен батч в Make: {len(messages)} сообщений от {user_id}")
            
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending batch to Make: {e}")

def start_typing_simulation(user_id: int, messages: List[Dict]) -> None:
    """Эмулирует человеческий набор текста"""
    def typing_cycle():
        try:
            # Первый цикл набора (3 сек)
            send_typing_action(user_id, messages[0]['chat']['id'])
            time.sleep(3)
            
            # Пауза (2 сек)
            time.sleep(2)
            
            # Второй цикл набора (2 сек)
            send_typing_action(user_id, messages[0]['chat']['id'])
            time.sleep(2)
            
            # Отправляем ответ
            response_text = f"Обработано {len(messages)} сообщений"
            send_message_to_user(messages[0]['chat']['id'], response_text)
            
        except Exception as e:
            print(f"[{get_timestamp()}] Error in typing simulation: {e}")
    
    # Запускаем в отдельном потоке
    typing_thread = threading.Thread(target=typing_cycle, daemon=True)
    typing_thread.start()

def process_batch(user_id: int) -> None:
    """Обрабатывает батч сообщений пользователя"""
    if user_id in message_batches and message_batches[user_id]:
        messages = message_batches[user_id].copy()
        message_batches[user_id].clear()
        
        # Отправляем в Make
        send_batch_to_make(user_id, messages)
        
        # Эмулируем набор текста
        start_typing_simulation(user_id, messages)
        
        # Очищаем таймер
        if user_id in batch_timers:
            del batch_timers[user_id]

def schedule_batch_processing(user_id: int, delay: int = BATCH_TIMEOUT) -> None:
    """Планирует обработку батча через указанное время"""
    # Отменяем предыдущий таймер если есть
    if user_id in batch_timers:
        batch_timers[user_id].cancel()
    
    # Создаем новый таймер
    timer = threading.Timer(delay, process_batch, args=[user_id])
    timer.start()
    batch_timers[user_id] = timer

def handle_message(message: Dict) -> None:
    """Обрабатывает входящее сообщение"""
    user_id = message['from']['id']
    chat_id = message['chat']['id']
    
    # Проверяем защиту от флуда
    if not debounce_manager.should_process(user_id):
        print(f"[{get_timestamp()}] Сообщение от {user_id} отклонено (debounce)")
        return
    
    # Добавляем сообщение в батч
    message_batches[user_id].append(message)
    
    # Планируем обработку батча
    schedule_batch_processing(user_id)
    
    print(f"[{get_timestamp()}] Сообщение от {user_id} добавлено в батч")

def handle_pre_checkout_query(pre_checkout_query: Dict) -> None:
    """Обрабатывает pre_checkout_query от Telegram Payments"""
    query_id = pre_checkout_query['id']
    invoice_payload = pre_checkout_query.get('invoice_payload', '')
    
    # Проверяем на уже оплаченные счета
    if invoice_payload in paid_invoices:
        answer_pre_checkout_query(query_id, False)
        return
    
    answer_pre_checkout_query(query_id, True)

def answer_pre_checkout_query(query_id: str, ok: bool) -> None:
    """Отвечает на pre_checkout_query"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery"
        data = {
            'pre_checkout_query_id': query_id,
            'ok': ok
        }
        
        with httpx.Client() as client:
            response = client.post(url, json=data, timeout=5.0)
            if response.status_code != 200:
                print(f"[{get_timestamp()}] Error answering pre_checkout_query: {response.text}")
                
    except Exception as e:
        print(f"[{get_timestamp()}] Error answering pre_checkout_query: {e}")

def handle_successful_payment(successful_payment: Dict) -> None:
    """Обрабатывает успешный платеж"""
    invoice_payload = successful_payment.get('invoice_payload', '')
    
    # Добавляем в список оплаченных
    paid_invoices.add(invoice_payload)
    
    # Уведомляем администратора
    notify_admin(successful_payment)
    
    # Проксируем в Make
    proxy_to_make('payment', successful_payment)

def notify_admin(payment_data: Dict) -> None:
    """Уведомляет администратора о платеже"""
    try:
        order_info = payment_data.get('order_info', {})
        message = f"""✅ Оплата прошла!
💰 Сумма: {payment_data['total_amount'] / 100} ₽
👤 Имя: {order_info.get('name', 'Не указано')}
📞 Телефон: {order_info.get('phone_number', 'Не указан')}"""
        
        send_message_to_user(int(ADMIN_CHAT_ID), message)
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error notifying admin: {e}")

def proxy_to_make(event_type: str, data: Dict) -> None:
    """Проксирует данные в Make.com"""
    try:
        payload = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        with httpx.Client(verify=False) as client:
            response = client.post(MAKE_WEBHOOK_URL, json=payload, timeout=10.0)
            print(f"[{get_timestamp()}] Проксировано в Make: {event_type}")
            
    except Exception as e:
        print(f"[{get_timestamp()}] Error proxying to Make: {e}")

def process_update(update: Dict) -> None:
    """Обрабатывает обновление от Telegram"""
    update_id = update.get('update_id', 0)
    
    # Проверяем на дублирование
    if update_id in processed_updates:
        return
    
    processed_updates.add(update_id)
    
    # Определяем тип обновления
    if 'message' in update:
        handle_message(update['message'])
    elif 'pre_checkout_query' in update:
        handle_pre_checkout_query(update['pre_checkout_query'])
    elif 'successful_payment' in update:
        handle_successful_payment(update['successful_payment'])

def polling_worker() -> None:
    """Фоновая задача для получения обновлений от Telegram API"""
    global last_update_id
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {
                'offset': last_update_id + 1,
                'timeout': 30,
                'limit': 100
            }
            
            with httpx.Client() as client:
                response = client.get(url, params=params, timeout=35.0)
                data = response.json()
                
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        process_update(update)
                        last_update_id = max(last_update_id, update.get('update_id', 0))
                        
        except Exception as e:
            print(f"[{get_timestamp()}] Error in polling worker: {e}")
            time.sleep(5)

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'last_update_id': last_update_id,
        'active_batches': len(message_batches),
        'batch_timers': len(batch_timers),
        'active_users': debounce_manager.get_active_users_count(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint для Telegram"""
    try:
        data = request.get_json()
        if data:
            process_update(data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"[{get_timestamp()}] Error in webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Запуск polling в отдельном потоке
    polling_thread = threading.Thread(target=polling_worker, daemon=True)
    polling_thread.start()
    
    print(f"[{get_timestamp()}] Telegram bot started")
    print(f"[{get_timestamp()}] Health check: http://localhost:5000/")
    
    # Запуск Flask-сервера
    app.run(
        debug=os.getenv('DEBUG', 'False').lower() == 'true',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000))
    )
