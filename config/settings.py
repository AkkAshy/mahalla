"""
Настройки приложения
"""

import os
from typing import Dict, Any
from pathlib import Path

class AppSettings:
    """Класс настроек приложения"""
    
    # Пути к файлам и директориям
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    STATIC_DIR = BASE_DIR / "static"
    
    # База данных
    DATABASE_PATH = DATA_DIR / "mahalla.db"
    BACKUP_DIR = DATA_DIR / "backups"
    
    # Настройки приложения
    APP_TITLE = "Система управления махалли"
    APP_ICON = "🏛️"
    
    # Авторизация
    DEFAULT_ADMIN_LOGIN = "admin"
    DEFAULT_ADMIN_PASSWORD = "mahalla2024"
    SESSION_TIMEOUT_MINUTES = 30
    
    # SMS настройки
    SMS_PROVIDER = "demo"  # demo, eskiz, ucell
    SMS_MAX_LENGTH = 160
    SMS_RATE_LIMIT_PER_MINUTE = 60
    
    # Система баллов
    POINTS_CONFIG = {
        'meeting_attendance': 10,
        'subbotnik': 15,
        'community_work': 10,
        'volunteer_work': 12,
        'regular_bonus_multiplier': 1.5  # +50% за регулярность
    }
    
    # Настройки интерфейса
    SIDEBAR_STATE = "expanded"
    LAYOUT = "wide"
    THEME = {
        'primaryColor': '#1e3c72',
        'backgroundColor': '#ffffff',
        'secondaryBackgroundColor': '#f0f2f6',
        'textColor': '#262730'
    }
    
    # Пагинация
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 1000
    
    # Экспорт данных
    EXPORT_FORMATS = ['xlsx', 'csv', 'json']
    
    # Логирование
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    
    @classmethod
    def ensure_directories(cls):
        """Создание необходимых директорий"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.BACKUP_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def get_database_url(cls) -> str:
        """Получение URL базы данных"""
        return f"sqlite:///{cls.DATABASE_PATH}"
    
    @classmethod
    def get_sms_config(cls) -> Dict[str, Any]:
        """Получение конфигурации SMS"""
        return {
            'provider': cls.SMS_PROVIDER,
            'max_length': cls.SMS_MAX_LENGTH,
            'rate_limit': cls.SMS_RATE_LIMIT_PER_MINUTE
        }

# Глобальный экземпляр настроек
_settings = None

def get_settings() -> AppSettings:
    """
    Получение глобального экземпляра настроек
    
    Returns:
        AppSettings: Экземпляр настроек
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
        _settings.ensure_directories()
    return _settings

# Шаблоны SMS сообщений
SMS_TEMPLATES = {
    'meeting_reminder_24h': """
Уважаемые жители!
Завтра {date} в {time} состоится заседание махалли.
Тема: {title}
Место: {location}
Ваше участие важно!
""".strip(),
    
    'meeting_reminder_2h': """
Через 2 часа начинается заседание махалли!
Тема: {title}
Место: {location}
Не забудьте прийти!
""".strip(),
    
    'emergency_water': """
🚰 ВНИМАНИЕ!
Отключение воды с {start_time} до {end_time}
Причина: {reason}
Приносим извинения за неудобства.
""".strip(),
    
    'emergency_electricity': """
⚡ ВНИМАНИЕ!
Отключение электричества с {start_time} до {end_time}
Причина: {reason}
""".strip(),
    
    'emergency_gas': """
🔥 ВНИМАНИЕ!
Отключение газа с {start_time} до {end_time}
Причина: {reason}
Соблюдайте меры безопасности!
""".strip(),
    
    'road_works': """
🚧 Дорожные работы
Место: {location}
Время: с {start_time} до {end_time}
Просьба выбрать альтернативные маршруты.
""".strip(),
    
    'points_earned': """
🎉 Поздравляем!
Вы заработали {points} баллов за {activity}
Общий счет: {total_points} баллов
Спасибо за активность!
""".strip(),
    
    'subbotnik_reminder': """
🧹 Субботник
Дата: {date} в {time}
Место сбора: {location}
Приглашаем всех жителей к участию!
""".strip()
}

# Конфигурация страниц
PAGES_CONFIG = {
    'dashboard': {
        'title': '📊 Главная',
        'icon': '📊',
        'description': 'Общая статистика и метрики'
    },
    'citizens': {
        'title': '👥 Граждане',
        'icon': '👥',
        'description': 'Управление реестром граждан махалли'
    },
    'meetings': {
        'title': '🏛️ Заседания',
        'icon': '🏛️',
        'description': 'Планирование и проведение заседаний'
    },
    'sms': {
        'title': '📱 SMS-рассылка',
        'icon': '📱',
        'description': 'Массовые уведомления гражданам'
    },
    'emergency': {
        'title': '⚡ Экстренные уведомления',
        'icon': '⚡',
        'description': 'Срочные оповещения при ЧС'
    },
    'points': {
        'title': '⭐ Система баллов',
        'icon': '⭐',
        'description': 'Поощрения за активность'
    },
    'reports': {
        'title': '📊 Отчеты',
        'icon': '📊',
        'description': 'Аналитика и экспорт данных'
    }
}

# Роли пользователей
USER_ROLES = {
    'admin': {
        'name': 'Администратор',
        'permissions': ['all']
    },
    'chairman': {
        'name': 'Председатель махалли',
        'permissions': ['citizens', 'meetings', 'sms', 'emergency', 'points', 'reports']
    },
    'secretary': {
        'name': 'Секретарь',
        'permissions': ['citizens', 'meetings', 'sms', 'reports']
    },
    'operator': {
        'name': 'Оператор',
        'permissions': ['citizens', 'sms']
    }
}