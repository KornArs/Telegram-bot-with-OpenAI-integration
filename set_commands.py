#!/usr/bin/env python3
"""
Скрипт для настройки команд меню бота через BotFather
Запускается один раз для настройки меню команд
"""

import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

def set_bot_commands():
    """Устанавливает команды меню для бота"""
    
    commands = [
        {
            "command": "start",
            "description": "Запустить Make.com помощника"
        },
        {
            "command": "help", 
            "description": "Справка по командам и возможностям"
        },
        {
            "command": "docs",
            "description": "Поиск по документации Make.com (/docs <запрос>)"
        },
        {
            "command": "payments",
            "description": "История ваших платежей"
        },
        {
            "command": "schedule", 
            "description": "Ваше расписание занятий"
        },
        {
            "command": "time",
            "description": "Текущее время в Москве"
        }
    ]
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    
    try:
        response = requests.post(url, json={"commands": commands})
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("✅ Команды успешно добавлены в меню бота!")
                print("\n📋 Установленные команды:")
                for cmd in commands:
                    print(f"• /{cmd['command']} - {cmd['description']}")
            else:
                print(f"❌ Ошибка: {result.get('description', 'Неизвестная ошибка')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при установке команд: {e}")

def get_bot_info():
    """Получает информацию о боте"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                bot_info = result["result"]
                print(f"🤖 Информация о боте:")
                print(f"Имя: {bot_info.get('first_name')}")
                print(f"Username: @{bot_info.get('username')}")
                print(f"ID: {bot_info.get('id')}")
                return True
        else:
            print(f"❌ Не удалось получить информацию о боте: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при получении информации о боте: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Настройка команд меню для Make.com бота")
    print("=" * 50)
    
    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не найден в .env файле")
        exit(1)
    
    # Проверяем информацию о боте
    if get_bot_info():
        print("\n" + "=" * 50)
        # Устанавливаем команды
        set_bot_commands()
    else:
        print("❌ Не удалось подключиться к боту. Проверьте BOT_TOKEN")
