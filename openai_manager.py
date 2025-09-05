import os
import json
import tempfile
from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI

class OpenAIManager:
    """Менеджер для работы с OpenAI API используя официальную библиотеку"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Настраиваем httpx клиент с отключенным HTTP/2 и увеличенными таймаутами
        import httpx
        import ssl
        import certifi
        
        # Создаем SSL контекст с актуальными сертификатами
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Настраиваем httpx клиент
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        timeout = httpx.Timeout(30.0, connect=10.0)
        
        # Создаем кастомный транспорт с отключенным HTTP/2
        transport = httpx.HTTPTransport(
            http2=False,  # Отключаем HTTP/2
            verify=ssl_context,
            retries=3
        )
        
        # Создаем httpx клиент с прокси для обхода региональных ограничений
        http_client = httpx.Client(
            limits=limits,
            timeout=timeout,
            transport=transport,
            verify=ssl_context,
            # Добавляем прокси если нужно обойти региональные ограничения
            # proxies={
            #     "http://": "http://proxy:port",
            #     "https://": "http://proxy:port"
            # }
        )
        
        # Инициализируем OpenAI клиент с кастомным httpx клиентом
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )
        self.conversation_history = {}  # user_id -> [messages]
    
    def send_message_to_user(self, user_id: int, message: str, user_name: str = None) -> Dict:
        """Отправляет сообщение пользователю и получает ответ"""
        try:
            # Получаем историю разговора
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Добавляем системное сообщение для первого сообщения
            if not self.conversation_history[user_id]:
                from datetime import datetime, timezone, timedelta
                moscow_time = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")
                
                self.conversation_history[user_id].append({
                    "role": "system",
                    "content": f"""Ты — эксперт по платформе Make.com с глубокими знаниями документации. Текущее время в Москве: {moscow_time}

       Ты владеешь всей документацией Make.com и можешь:
       - Объяснять основы и продвинутые концепции
       - Анализировать сценарии и находить ошибки
       - Давать практические советы по оптимизации
       - Рекомендовать лучшие практики

       Отвечай только в JSON формате:
       {{
         "action": "reply" или "offer_mentorship" или "schedule_request" или "documentation_search",
         "reply_text": "подробный ответ с примерами",
         "cta": "название пакета или null",
         "price": число или null,
         "schedule_info": "информация о расписании если нужно" или null,
         "difficulty_assessment": "beginner/intermediate/advanced",
         "recommendation": "что рекомендую пользователю"
       }}

       Логика ответов:
       - Простые вопросы (beginner) - давай полный ответ с примерами
       - Средние вопросы (intermediate) - объясняй + предлагай обучение
       - Сложные вопросы (advanced) - краткий ответ + обязательно предлагай индивидуальные занятия
       
       Пакеты обучения:
       - "1 занятие (2 часа)" за 10000 - для конкретных проблем
       - "3 занятия" за 25000 - для изучения модулей
       - "Месяц" за 60000 - для глубокого изучения
       
       ВАЖНО: 
       - Всегда оценивай сложность вопроса
       - Для сложных задач обязательно предлагай обучение
       - Используй московское время при планировании
       - Будь дружелюбным ментором, а не просто ботом
       - Используй HTML форматирование для красивого отображения:
         * <b>жирный текст</b> для заголовков
         * <i>курсив</i> для выделения
         * <code>код</code> для примеров кода
         * <pre>блок кода</pre> для больших блоков
         * <a href="ссылка">текст ссылки</a> для ссылок"""
                })
            
            # Добавляем сообщение пользователя
            user_message = f"Пользователь {user_name} пишет: {message}" if user_name else message
            self.conversation_history[user_id].append({
                "role": "user",
                "content": user_message
            })
            
            print(f"Sending message for user {user_id}: {user_message[:50]}...")
            
            # Отправляем в OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation_history[user_id],
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_response = response.choices[0].message.content
            print(f"Assistant response: {assistant_response[:100]}...")
            
            # Добавляем ответ в историю
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": assistant_response
            })
            
            # Ограничиваем историю последними 10 сообщениями
            if len(self.conversation_history[user_id]) > 10:
                # Сохраняем системное сообщение и последние 9 сообщений
                system_msg = self.conversation_history[user_id][0]
                self.conversation_history[user_id] = [system_msg] + self.conversation_history[user_id][-9:]
            
            return self._parse_response(assistant_response)
                
        except Exception as e:
            print(f"Error in OpenAI communication: {e}")
            
            # Проверяем региональные ограничения
            if "unsupported_country_region_territory" in str(e):
                return {
                    "action": "reply", 
                    "reply_text": "⚠️ <b>Внимание!</b>\n\nК сожалению, OpenAI недоступен в вашем регионе. Для работы с AI функциями необходимо использовать VPN или прокси.\n\nПока что вы можете:\n• Использовать команды /help, /time, /payments\n• Анализировать Make.com сценарии\n• Работать с документацией", 
                    "cta": None, 
                    "price": None
                }
            
            return {"action": "reply", "reply_text": "Произошла ошибка при обработке запроса.", "cta": None, "price": None}
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Транскрибирует аудио файл в текст"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"
                )
                return transcript.text
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return "Ошибка при транскрибировании аудио"
    
    def generate_speech(self, text: str, voice: str = "onyx") -> bytes:
        """Генерирует аудио из текста (мужской голос по умолчанию)"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            return response.content
        except Exception as e:
            print(f"Error generating speech: {e}")
            return b""
    
    def _parse_response(self, content: str) -> Dict:
        """Парсит ответ от OpenAI в JSON"""
        try:
            # Ищем JSON в ответе
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = content[start:end]
                parsed = json.loads(json_str)
                
                # Проверяем обязательные поля
                if 'action' not in parsed or 'reply_text' not in parsed:
                    raise ValueError("Missing required fields")
                
                # Конвертируем Markdown в HTML форматирование
                if parsed.get('reply_text'):
                    parsed['reply_text'] = self._convert_markdown_to_html(parsed['reply_text'])
                
                return parsed
            else:
                # Если JSON не найден, возвращаем как обычный ответ
                return {
                    "action": "reply",
                    "reply_text": self._convert_markdown_to_html(content),
                    "cta": None,
                    "price": None
                }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing response: {e}")
            return {
                "action": "reply",
                "reply_text": self._convert_markdown_to_html(content),
                "cta": None,
                "price": None
            }
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Конвертирует Markdown синтаксис в HTML теги"""
        import re
        
        # Заменяем **текст** на <b>текст</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Заменяем *текст* на <i>текст</i> (но не в начале строки)
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
        
        # Заменяем `код` на <code>код</code>
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Заменяем ```блок кода``` на <pre>блок кода</pre>
        text = re.sub(r'```([^`]+)```', r'<pre>\1</pre>', text)
        
        # Заменяем [текст](ссылка) на <a href="ссылка">текст</a>
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Заменяем • на HTML список
        text = re.sub(r'^•\s*', r'• ', text, flags=re.MULTILINE)
        
        return text
    
    def get_user_messages(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает историю сообщений пользователя"""
        if user_id in self.conversation_history:
            return self.conversation_history[user_id][-limit:]
        return []
