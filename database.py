import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class DatabaseManager:
    """Менеджер базы данных SQLite для хранения пользователей и платежей"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    thread_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица платежей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    invoice_payload TEXT UNIQUE,
                    amount INTEGER,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT DEFAULT 'pending',
                    provider_payment_charge_id TEXT,
                    telegram_payment_charge_id TEXT,
                    order_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица истории сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_text TEXT,
                    message_type TEXT DEFAULT 'user',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица расписания занятий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    payment_id INTEGER,
                    lesson_type TEXT,
                    scheduled_datetime TEXT,
                    duration_minutes INTEGER DEFAULT 120,
                    status TEXT DEFAULT 'scheduled',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (payment_id) REFERENCES payments (id)
                )
            ''')
            
            conn.commit()
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_user(self, user_data: Dict) -> str:
        """Создает нового пользователя и возвращает thread_id"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Генерируем уникальный thread_id
            thread_id = f"thread_{user_data['user_id']}_{int(datetime.now().timestamp())}"
            
            cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, username, thread_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data.get('first_name', ''),
                user_data.get('last_name', ''),
                user_data.get('username', ''),
                thread_id
            ))
            
            conn.commit()
            return thread_id
    
    def update_user_thread(self, user_id: int, thread_id: str) -> None:
        """Обновляет thread_id пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET thread_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (thread_id, user_id))
            conn.commit()
    
    def save_message(self, user_id: int, message_text: str, message_type: str = 'user') -> None:
        """Сохраняет сообщение в историю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO message_history (user_id, message_text, message_type)
                VALUES (?, ?, ?)
            ''', (user_id, message_text, message_type))
            conn.commit()
    
    def get_user_messages(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает последние сообщения пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM message_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def save_payment(self, payment_data: Dict) -> None:
        """Сохраняет информацию о платеже"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (
                    user_id, invoice_payload, amount, currency, status,
                    provider_payment_charge_id, telegram_payment_charge_id, order_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_data['user_id'],
                payment_data.get('invoice_payload', ''),
                payment_data.get('total_amount', 0),
                payment_data.get('currency', 'RUB'),
                'pending',
                payment_data.get('provider_payment_charge_id', ''),
                payment_data.get('telegram_payment_charge_id', ''),
                json.dumps(payment_data.get('order_info', {}))
            ))
            conn.commit()
    
    def update_payment_status(self, invoice_payload: str, status: str) -> None:
        """Обновляет статус платежа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE payments SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE invoice_payload = ?
            ''', (status, invoice_payload))
            conn.commit()
    
    def payment_exists(self, invoice_payload: str) -> bool:
        """Проверяет существование платежа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM payments WHERE invoice_payload = ?', (invoice_payload,))
            return cursor.fetchone() is not None
    
    def get_user_payments(self, user_id: int) -> List[Dict]:
        """Получает все платежи пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM payments 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Dict]:
        """Получает платеж по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_schedule(self, schedule_data: Dict) -> int:
        """Сохраняет запись в расписании (упрощенная версия без payment_id)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedule (user_id, lesson_type, scheduled_datetime, 
                                    duration_minutes, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                schedule_data['user_id'],
                schedule_data['lesson_type'],
                schedule_data['scheduled_datetime'],
                schedule_data['duration_minutes'],
                schedule_data['status'],
                schedule_data['notes']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_schedule_entry(self, user_id: int, payment_id: int, lesson_type: str, 
                          scheduled_datetime: str, duration_minutes: int = 120, notes: str = "") -> int:
        """Добавляет запись в расписание"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedule (user_id, payment_id, lesson_type, scheduled_datetime, 
                                    duration_minutes, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, payment_id, lesson_type, scheduled_datetime, duration_minutes, notes))
            conn.commit()
            return cursor.lastrowid
    
    def check_schedule_conflict(self, scheduled_datetime: str, duration_minutes: int = 120) -> bool:
        """Проверяет конфликт расписания"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM schedule 
                WHERE status = 'scheduled' 
                AND datetime(scheduled_datetime) BETWEEN 
                    datetime(?) AND datetime(?, '+{} minutes')
            '''.format(duration_minutes), (scheduled_datetime, scheduled_datetime))
            count = cursor.fetchone()[0]
            return count > 0
    
    def get_schedule_for_date(self, date_str: str) -> List[Dict]:
        """Получает расписание на конкретную дату"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, u.first_name, u.last_name, p.amount, p.currency
                FROM schedule s
                LEFT JOIN users u ON s.user_id = u.user_id
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE date(s.scheduled_datetime) = date(?)
                AND s.status = 'scheduled'
                ORDER BY s.scheduled_datetime
            ''', (date_str,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_schedule(self, user_id: int) -> List[Dict]:
        """Получает расписание пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, p.amount, p.currency, p.invoice_payload
                FROM schedule s
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE s.user_id = ?
                ORDER BY s.scheduled_datetime DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
