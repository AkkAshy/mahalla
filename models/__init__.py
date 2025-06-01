"""
Модели данных для системы управления махалли
"""

from .base import BaseModel
from .citizen import CitizenModel
from .meeting import MeetingModel
from .sms import SMSModel
from .points import PointsModel

__all__ = [
    'BaseModel',
    'CitizenModel',
    'MeetingModel', 
    'SMSModel',
    'PointsModel'
]