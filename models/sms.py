"""
Модель для работы с SMS рассылками
"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import re

from .base import BaseModel

logger = logging.getLogger(__name__)

class SMSModel(BaseModel):
    """Модель для управления SMS рассылками"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.table_name = "sms_campaigns"
        self.required_fields = ['title', 'message_text']
        self.search_fields = ['title', 'message_text']
        
        # Максимальная длина SMS
        self.max_sms_length = 160
        self.max_title_length = 255
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Валидация данных SMS кампании
        
        Args:
            data: Данные для валидации
            
        Returns:
            Словарь с ошибками валидации
        """
        errors = super().validate_data(data)
        
        # Валидация заголовка
        if 'title' in data:
            title = data['title'].strip()
            if len(title) < 3:
                errors.setdefault('title', []).append("Заголовок слишком короткий")
            elif len(title) > self.max_title_length:
                errors.setdefault('title', []).append(f"Заголовок слишком длинный (максимум {self.max_title_length} символов)")
        
        # Валидация текста сообщения
        if 'message_text' in data:
            message = data['message_text'].strip()
            if len(message) < 10:
                errors.setdefault('message_text', []).append("Сообщение слишком короткое")
            elif len(message) > self.max_sms_length:
                errors.setdefault('message_text', []).append(f"Сообщение слишком длинное (максимум {self.max_sms_length} символов)")
        
        # Валидация типа кампании
        if 'campaign_type' in data and data['campaign_type']:
            valid_types = ['REGULAR', 'EMERGENCY', 'REMINDER']
            if data['campaign_type'] not in valid_types:
                errors.setdefault('campaign_type', []).append(f"Недопустимый тип кампании. Должен быть одним из: {', '.join(valid_types)}")
        
        return errors
    
    def create_campaign(
        self,
        title: str,
        message_text: str,
        campaign_type: str = 'REGULAR',
        scheduled_at: Optional[datetime] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        """
        Создание новой SMS кампании
        
        Args:
            title: Название кампании
            message_text: Текст сообщения
            campaign_type: Тип кампании
            scheduled_at: Время запланированной отправки
            created_by: ID пользователя, создавшего кампанию
            
        Returns:
            ID созданной кампании или None
        """
        data = {
            'title': title.strip(),
            'message_text': message_text.strip(),
            'campaign_type': campaign_type,
            'sent_count': 0,
            'delivered_count': 0,
            'failed_count': 0,
            'scheduled_at': scheduled_at.isoformat() if scheduled_at else None,
            'created_by': created_by
        }
        
        # Валидация данных
        errors = self.validate_data(data)
        if errors:
            logger.error(f"Ошибки валидации при создании SMS кампании: {errors}")
            return None
        
        campaign_id = self.create(data)
        
        if campaign_id:
            self.log_action("create", campaign_id, f"Создана SMS кампания: {title}")
        
        return campaign_id
    
    def send_campaign(self, campaign_id: int, recipients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Отправка SMS кампании
        
        Args:
            campaign_id: ID кампании
            recipients: Список получателей с данными
            
        Returns:
            Результат отправки
        """
        campaign = self.get_by_id(campaign_id)
        if not campaign:
            return {'success': False, 'error': 'Кампания не найдена'}
        
        # Фильтруем получателей с валидными номерами
        valid_recipients = []
        for recipient in recipients:
            phone = recipient.get('phone', '').strip()
            if phone and self._validate_phone(phone):
                valid_recipients.append(recipient)
        
        if not valid_recipients:
            return {'success': False, 'error': 'Нет получателей с валидными номерами'}
        
        # Создаем записи в журнале SMS
        sent_count = 0
        failed_count = 0
        
        for recipient in valid_recipients:
            success = self._send_single_sms(
                campaign_id=campaign_id,
                citizen_id=recipient.get('citizen_id'),
                phone=recipient['phone'],
                message_text=campaign['message_text']
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        # Обновляем статистику кампании
        self.update(campaign_id, {
            'sent_count': sent_count,
            'failed_count': failed_count,
            'sent_at': datetime.now().isoformat()
        })
        
        result = {
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(valid_recipients)
        }
        
        self.log_action("send", campaign_id, f"Отправлено {sent_count} SMS, ошибок: {failed_count}")
        
        return result
    
    def _send_single_sms(
        self, 
        campaign_id: int, 
        citizen_id: Optional[int], 
        phone: str, 
        message_text: str
    ) -> bool:
        """
        Отправка одного SMS (в демо-режиме только логирование)
        
        Args:
            campaign_id: ID кампании
            citizen_id: ID гражданина
            phone: Номер телефона
            message_text: Текст сообщения
            
        Returns:
            Успешность отправки
        """
        try:
            # В реальной системе здесь был бы вызов SMS API
            # Сейчас просто создаем запись в журнале
            
            log_data = {
                'campaign_id': campaign_id,
                'citizen_id': citizen_id,
                'phone': phone,
                'message_text': message_text,
                'status': 'SENT',  # В демо-режиме считаем что всё отправлено
                'sent_at': datetime.now().isoformat()
            }
            
            # Добавляем запись в журнал SMS
            log_query = """
                INSERT INTO sms_logs (campaign_id, citizen_id, phone, message_text, status, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            result = self.db.execute_query(
                log_query,
                (log_data['campaign_id'], log_data['citizen_id'], log_data['phone'],
                 log_data['message_text'], log_data['status'], log_data['sent_at']),
                fetch=False
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            
            # Записываем ошибку в журнал
            error_log_query = """
                INSERT INTO sms_logs (campaign_id, citizen_id, phone, message_text, status, error_message)
                VALUES (?, ?, ?, ?, 'FAILED', ?)
            """
            
            self.db.execute_query(
                error_log_query,
                (campaign_id, citizen_id, phone, message_text, str(e)),
                fetch=False
            )
            
            return False
    
    def _validate_phone(self, phone: str) -> bool:
        """Валидация номера телефона"""
        # Узбекские номера: +998xxxxxxxxx
        phone_pattern = r'^(\+?998|8)?[0-9]{9}$'