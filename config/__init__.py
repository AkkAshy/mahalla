
"""
Модуль конфигурации системы управления махалли
"""

from .database import DatabaseManager
from .settings import AppSettings, get_settings

__all__ = [
    'DatabaseManager',
    'AppSettings', 
    'get_settings'
]