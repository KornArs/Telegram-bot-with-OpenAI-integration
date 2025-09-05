import os
import time
import threading
from datetime import datetime
from typing import Dict, Set
from collections import defaultdict

class DebounceManager:
    """
    Менеджер защиты от флуда сообщений с настраиваемыми интервалами.
    """
    
    def __init__(self, debounce_seconds: int = 4, max_wait_seconds: int = 15):
        self.debounce_seconds = debounce_seconds
        self.max_wait_seconds = max_wait_seconds
        self.last_requests: Dict[int, float] = {}  # user_id -> timestamp
    
    def should_process(self, user_id: int) -> bool:
        """
        Проверяет, нужно ли обрабатывать сообщение от пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если сообщение можно обработать, False если нужно отклонить
        """
        current_time = time.time()
        
        # Если пользователь не найден, разрешаем обработку
        if user_id not in self.last_requests:
            self.last_requests[user_id] = current_time
            return True
        
        # Проверяем время последнего запроса
        last_request_time = self.last_requests[user_id]
        time_diff = current_time - last_request_time
        
        # Если прошло достаточно времени, разрешаем обработку
        if time_diff >= self.debounce_seconds:
            self.last_requests[user_id] = current_time
            return True
        
        # Если прошло слишком много времени, сбрасываем таймер
        if time_diff >= self.max_wait_seconds:
            self.last_requests[user_id] = current_time
            return True
        
        # В остальных случаях отклоняем
        return False
    
    def clear_user(self, user_id: int) -> None:
        """
        Очищает данные пользователя из кэша.
        
        Args:
            user_id: ID пользователя Telegram
        """
        if user_id in self.last_requests:
            del self.last_requests[user_id]
    
    def get_active_users_count(self) -> int:
        """
        Возвращает количество активных пользователей.
        
        Returns:
            int: Количество пользователей в кэше
        """
        return len(self.last_requests)
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> None:
        """
        Очищает старые записи из кэша.
        
        Args:
            max_age_seconds: Максимальный возраст записи в секундах
        """
        current_time = time.time()
        users_to_remove = []
        
        for user_id, timestamp in self.last_requests.items():
            if current_time - timestamp > max_age_seconds:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.last_requests[user_id]

    def is_debounced(self, user_id: int) -> bool:
        """
        Проверяет, заблокирован ли пользователь debounce.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            bool: True если пользователь заблокирован, False если можно обработать
        """
        return not self.should_process(user_id)
