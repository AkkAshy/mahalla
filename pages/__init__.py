"""
Модуль страниц для системы управления махалли
"""

from .dashboard import show_dashboard
from .citizens import show_citizens_page
from .meetings import show_meetings_page
from .sms_sender import show_sms_page
from .emergency import show_emergency_page
from .points import show_points_page
from .reports import show_reports_page

__all__ = [
    'show_dashboard',
    'show_citizens_page',
    'show_meetings_page',
    'show_sms_page',
    'show_emergency_page',
    'show_points_page',
    'show_reports_page'
]