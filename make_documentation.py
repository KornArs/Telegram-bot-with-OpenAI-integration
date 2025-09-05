"""
Модуль для работы с документацией Make.com
Содержит базу знаний и поиск по документации
"""

import sqlite3
from typing import List, Dict, Optional
import json
from datetime import datetime

class MakeDocumentationManager:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_documentation_db()
    
    def init_documentation_db(self):
        """Инициализирует таблицы для документации Make.com"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица документации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS make_documentation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                keywords TEXT,
                difficulty_level TEXT DEFAULT 'beginner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица FAQ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS make_faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица учебных материалов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS make_tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                difficulty_level TEXT DEFAULT 'beginner',
                estimated_time INTEGER DEFAULT 30,
                prerequisites TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Загружаем базовую документацию
        self.load_default_documentation()
    
    def load_default_documentation(self):
        """Загружает базовую документацию Make.com"""
        default_docs = [
            {
                "category": "Основы",
                "title": "Что такое Make.com",
                "content": "Make.com (ранее Integromat) - это платформа для автоматизации рабочих процессов. Позволяет соединять различные приложения и сервисы без программирования.",
                "keywords": "make, integromat, автоматизация, workflow",
                "difficulty_level": "beginner"
            },
            {
                "category": "Основы",
                "title": "Модули и соединения",
                "content": "Модули - это блоки, представляющие действия в приложениях. Соединения (connections) связывают модули и определяют поток данных между ними.",
                "keywords": "модули, connections, соединения, блоки",
                "difficulty_level": "beginner"
            },
            {
                "category": "Основы",
                "title": "Сценарии (Scenarios)",
                "content": "Сценарий - это последовательность модулей, которая выполняет определенную задачу автоматизации. Сценарии запускаются по триггерам или расписанию.",
                "keywords": "сценарии, scenarios, триггеры, расписание",
                "difficulty_level": "beginner"
            },
            {
                "category": "Продвинутые",
                "title": "Обработка ошибок",
                "content": "В Make.com важно настроить обработку ошибок через модули Error Handler и Router. Это предотвращает сбои сценариев и обеспечивает надежность.",
                "keywords": "ошибки, error handler, router, обработка ошибок",
                "difficulty_level": "intermediate"
            },
            {
                "category": "Продвинутые",
                "title": "Оптимизация производительности",
                "content": "Для оптимизации используйте фильтры, ограничения и правильное планирование выполнения. Избегайте избыточных операций и используйте кэширование.",
                "keywords": "оптимизация, производительность, фильтры, кэширование",
                "difficulty_level": "advanced"
            }
        ]
        
        for doc in default_docs:
            self.add_documentation_entry(
                category=doc["category"],
                title=doc["title"],
                content=doc["content"],
                keywords=doc["keywords"],
                difficulty_level=doc["difficulty_level"]
            )
    
    def add_documentation_entry(self, category: str, title: str, content: str, 
                               keywords: str = "", difficulty_level: str = "beginner"):
        """Добавляет новую запись в документацию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO make_documentation (category, title, content, keywords, difficulty_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (category, title, content, keywords, difficulty_level))
        
        conn.commit()
        conn.close()
    
    def search_documentation(self, query: str, limit: int = 5) -> List[Dict]:
        """Ищет документацию по запросу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Поиск по заголовку, содержимому и ключевым словам
        cursor.execute('''
            SELECT id, category, title, content, difficulty_level
            FROM make_documentation
            WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ?
            ORDER BY 
                CASE 
                    WHEN title LIKE ? THEN 1
                    WHEN keywords LIKE ? THEN 2
                    ELSE 3
                END
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "category": row[1],
                "title": row[2],
                "content": row[3],
                "difficulty_level": row[4]
            })
        
        conn.close()
        return results
    
    def get_documentation_by_category(self, category: str) -> List[Dict]:
        """Получает документацию по категории"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, content, difficulty_level
            FROM make_documentation
            WHERE category = ?
            ORDER BY difficulty_level, title
        ''', (category,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "difficulty_level": row[3]
            })
        
        conn.close()
        return results
    
    def get_categories(self) -> List[str]:
        """Получает список всех категорий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT category FROM make_documentation ORDER BY category')
        categories = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return categories
    
    def add_faq_entry(self, question: str, answer: str, category: str = "", tags: str = ""):
        """Добавляет FAQ запись"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO make_faq (question, answer, category, tags)
            VALUES (?, ?, ?, ?)
        ''', (question, answer, category, tags))
        
        conn.commit()
        conn.close()
    
    def search_faq(self, query: str, limit: int = 3) -> List[Dict]:
        """Ищет в FAQ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, question, answer, category
            FROM make_faq
            WHERE question LIKE ? OR answer LIKE ? OR tags LIKE ?
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "question": row[1],
                "answer": row[2],
                "category": row[3]
            })
        
        conn.close()
        return results
