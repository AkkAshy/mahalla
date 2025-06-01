"""
Модель для работы с гражданами махалли
"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
import re
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class CitizenModel(BaseModel):
    """Модель для управления гражданами махалли"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.table_name = "citizens"
        self.required_fields = ['full_name']
        self.search_fields = ['full_name', 'address', 'phone', 'passport_data']
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Валидация данных гражданина
        
        Args:
            data: Данные для валидации
            
        Returns:
            Словарь с ошибками валидации
        """
        errors = super().validate_data(data)
        
        # Валидация ФИО
        if 'full_name' in data:
            full_name = data['full_name'].strip()
            if len(full_name) < 2:
                errors.setdefault('full_name', []).append("ФИО слишком короткое")
            elif len(full_name) > 255:
                errors.setdefault('full_name', []).append("ФИО слишком длинное")
        
        # Валидация телефона
        if 'phone' in data and data['phone']:
            phone = data['phone'].strip()
            if not self._validate_phone(phone):
                errors.setdefault('phone', []).append("Неверный формат номера телефона")
        
        # Валидация даты рождения
        if 'birth_date' in data and data['birth_date']:
            if isinstance(data['birth_date'], str):
                try:
                    birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                except ValueError:
                    errors.setdefault('birth_date', []).append("Неверный формат даты")
                    birth_date = None
            else:
                birth_date = data['birth_date']
            
            if birth_date:
                # Проверяем, что дата не в будущем
                if birth_date > date.today():
                    errors.setdefault('birth_date', []).append("Дата рождения не может быть в будущем")
                
                # Проверяем разумный возраст (от 0 до 120 лет)
                age = (date.today() - birth_date).days // 365
                if age > 120:
                    errors.setdefault('birth_date', []).append("Возраст не может быть больше 120 лет")
        
        # Валидация паспортных данных
        if 'passport_data' in data and data['passport_data']:
            passport = data['passport_data'].strip()
            if not self._validate_passport(passport):
                errors.setdefault('passport_data', []).append("Неверный формат паспортных данных")
        
        return errors
    
    def _validate_phone(self, phone: str) -> bool:
        """Валидация номера телефона"""
        # Узбекские номера: +998xxxxxxxxx или 998xxxxxxxxx
        phone_pattern = r'^(\+?998|8)?[0-9]{9}$'
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        return bool(re.match(phone_pattern, clean_phone))
    
    def _validate_passport(self, passport: str) -> bool:
        """Валидация паспортных данных"""
        # Узбекские паспорта: AA1234567 или аналогичные форматы
        passport_pattern = r'^[A-Z]{2}[0-9]{7}$'
        return bool(re.match(passport_pattern, passport.upper()))
    
    def add_citizen(
        self,
        full_name: str,
        birth_date: Optional[date] = None,
        address: str = "",
        phone: str = "",
        passport_data: str = "",
        notes: str = ""
    ) -> Optional[int]:
        """
        Добавление нового гражданина
        
        Args:
            full_name: ФИО гражданина
            birth_date: Дата рождения
            address: Адрес проживания
            phone: Номер телефона
            passport_data: Паспортные данные
            notes: Дополнительные заметки
            
        Returns:
            ID созданной записи или None
        """
        data = {
            'full_name': full_name.strip(),
            'birth_date': birth_date.isoformat() if birth_date else None,
            'address': address.strip(),
            'phone': self._format_phone(phone),
            'passport_data': passport_data.strip().upper(),
            'notes': notes.strip(),
            'total_points': 0,
            'is_active': 1
        }
        
        # Валидация данных
        errors = self.validate_data(data)
        if errors:
            logger.error(f"Ошибки валидации при добавлении гражданина: {errors}")
            return None
        
        # Проверяем уникальность паспорта
        if passport_data and self.exists("passport_data = ? AND is_active = 1", (data['passport_data'],)):
            logger.error(f"Гражданин с паспортом {passport_data} уже существует")
            return None
        
        citizen_id = self.create(data)
        
        if citizen_id:
            self.log_action("create", citizen_id, f"Добавлен гражданин: {full_name}")
        
        return citizen_id
    
    def _format_phone(self, phone: str) -> str:
        """Форматирование номера телефона"""
        if not phone:
            return ""
        
        # Удаляем все символы кроме цифр и +
        clean_phone = re.sub(r'[^\d\+]', '', phone)
        
        # Приводим к формату +998xxxxxxxxx
        if clean_phone.startswith('998') and len(clean_phone) == 12:
            return f"+{clean_phone}"
        elif clean_phone.startswith('8') and len(clean_phone) == 10:
            return f"+998{clean_phone[1:]}"
        elif clean_phone.startswith('9') and len(clean_phone) == 9:
            return f"+998{clean_phone}"
        elif clean_phone.startswith('+998') and len(clean_phone) == 13:
            return clean_phone
        
        return phone  # Возвращаем как есть, если не удалось распознать
    
    def search_citizens(self, search_term: str) -> List[sqlite3.Row]:
        """
        Поиск граждан по различным полям
        
        Args:
            search_term: Поисковый запрос
            
        Returns:
            Список найденных граждан
        """
        return self.search(search_term, self.search_fields)
    
    def get_active_citizens(self) -> List[sqlite3.Row]:
        """Получение списка активных граждан"""
        return self.get_all("is_active = 1", order_by="full_name")
    
    def get_citizens_with_phones(self) -> List[sqlite3.Row]:
        """Получение граждан с указанными номерами телефонов"""
        return self.get_all("is_active = 1 AND phone IS NOT NULL AND phone != ''", order_by="full_name")
    
    def get_citizen_by_phone(self, phone: str) -> Optional[sqlite3.Row]:
        """
        Поиск гражданина по номеру телефона
        
        Args:
            phone: Номер телефона
            
        Returns:
            Запись гражданина или None
        """
        formatted_phone = self._format_phone(phone)
        result = self.get_all("phone = ? AND is_active = 1", (formatted_phone,))
        return result[0] if result else None
    
    def get_citizen_by_passport(self, passport_data: str) -> Optional[sqlite3.Row]:
        """
        Поиск гражданина по паспортным данным
        
        Args:
            passport_data: Паспортные данные
            
        Returns:
            Запись гражданина или None
        """
        result = self.get_all("passport_data = ? AND is_active = 1", (passport_data.upper(),))
        return result[0] if result else None
    
    def update_citizen(self, citizen_id: int, **kwargs) -> bool:
        """
        Обновление данных гражданина
        
        Args:
            citizen_id: ID гражданина
            **kwargs: Поля для обновления
            
        Returns:
            Успешность операции
        """
        # Форматируем данные
        update_data = {}
        
        for key, value in kwargs.items():
            if key == 'phone' and value:
                update_data[key] = self._format_phone(value)
            elif key == 'passport_data' and value:
                update_data[key] = value.strip().upper()
            elif key == 'birth_date' and isinstance(value, date):
                update_data[key] = value.isoformat()
            else:
                update_data[key] = value
        
        # Валидация
        errors = self.validate_data(update_data)
        if errors:
            logger.error(f"Ошибки валидации при обновлении гражданина {citizen_id}: {errors}")
            return False
        
        success = self.update(citizen_id, update_data)
        
        if success:
            self.log_action("update", citizen_id, f"Обновлены данные: {list(update_data.keys())}")
        
        return success
    
    def deactivate_citizen(self, citizen_id: int, reason: str = "") -> bool:
        """
        Деактивация гражданина (мягкое удаление)
        
        Args:
            citizen_id: ID гражданина
            reason: Причина деактивации
            
        Returns:
            Успешность операции
        """
        success = self.soft_delete(citizen_id)
        
        if success:
            # Добавляем причину в заметки
            if reason:
                citizen = self.get_by_id(citizen_id)
                if citizen:
                    current_notes = citizen['notes'] or ""
                    new_notes = f"{current_notes}\nДеактивирован: {reason} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
                    self.update(citizen_id, {'notes': new_notes})
            
            self.log_action("deactivate", citizen_id, f"Причина: {reason}")
        
        return success
    
    def activate_citizen(self, citizen_id: int) -> bool:
        """
        Активация гражданина
        
        Args:
            citizen_id: ID гражданина
            
        Returns:
            Успешность операции
        """
        success = self.update(citizen_id, {'is_active': 1})
        
        if success:
            self.log_action("activate", citizen_id)
        
        return success
    
    def get_age_statistics(self) -> Dict[str, int]:
        """
        Получение статистики по возрастным группам
        
        Returns:
            Словарь с количеством граждан по возрастным группам
        """
        query = """
            SELECT 
                CASE 
                    WHEN (julianday('now') - julianday(birth_date))/365.25 < 18 THEN 'До 18'
                    WHEN (julianday('now') - julianday(birth_date))/365.25 BETWEEN 18 AND 30 THEN '18-30'
                    WHEN (julianday('now') - julianday(birth_date))/365.25 BETWEEN 31 AND 50 THEN '31-50'
                    WHEN (julianday('now') - julianday(birth_date))/365.25 BETWEEN 51 AND 70 THEN '51-70'
                    ELSE '70+'
                END as age_group,
                COUNT(*) as count
            FROM citizens 
            WHERE is_active = 1 AND birth_date IS NOT NULL
            GROUP BY age_group
        """
        
        result = self.db.execute_query(query)
        return {row['age_group']: row['count'] for row in result} if result else {}
    
    def get_citizens_by_age_range(self, min_age: int, max_age: int) -> List[sqlite3.Row]:
        """
        Получение граждан по возрастному диапазону
        
        Args:
            min_age: Минимальный возраст
            max_age: Максимальный возраст
            
        Returns:
            Список граждан
        """
        query = """
            SELECT * FROM citizens 
            WHERE is_active = 1 
            AND birth_date IS NOT NULL
            AND (julianday('now') - julianday(birth_date))/365.25 BETWEEN ? AND ?
            ORDER BY birth_date DESC
        """
        
        result = self.db.execute_query(query, (min_age, max_age))
        return result if result else []
    
    def get_birthday_list(self, month: int) -> List[sqlite3.Row]:
        """
        Получение списка граждан с днями рождения в указанном месяце
        
        Args:
            month: Номер месяца (1-12)
            
        Returns:
            Список граждан
        """
        query = """
            SELECT * FROM citizens 
            WHERE is_active = 1 
            AND birth_date IS NOT NULL
            AND strftime('%m', birth_date) = ?
            ORDER BY strftime('%d', birth_date)
        """
        
        result = self.db.execute_query(query, (f"{month:02d}",))
        return result if result else []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение расширенной статистики по гражданам
        
        Returns:
            Словарь со статистикой
        """
        stats = super().get_statistics()
        
        # Статистика по телефонам
        stats['with_phones'] = self.count("phone IS NOT NULL AND phone != '' AND is_active = 1")
        
        # Статистика по возрасту
        stats['age_groups'] = self.get_age_statistics()
        
        # Топ по баллам
        top_points_query = """
            SELECT full_name, total_points 
            FROM citizens 
            WHERE is_active = 1 
            ORDER BY total_points DESC 
            LIMIT 5
        """
        top_result = self.db.execute_query(top_points_query)
        stats['top_by_points'] = [dict(row) for row in top_result] if top_result else []
        
        # Средний возраст
        avg_age_query = """
            SELECT AVG((julianday('now') - julianday(birth_date))/365.25) as avg_age
            FROM citizens 
            WHERE is_active = 1 AND birth_date IS NOT NULL
        """
        avg_result = self.db.execute_query(avg_age_query)
        if avg_result and avg_result[0]['avg_age']:
            stats['average_age'] = round(avg_result[0]['avg_age'], 1)
        
        return stats
    
    def export_to_excel(self, file_path: str, include_inactive: bool = False) -> bool:
        """
        Экспорт данных в Excel
        
        Args:
            file_path: Путь к файлу
            include_inactive: Включать ли неактивных граждан
            
        Returns:
            Успешность операции
        """
        try:
            where_clause = "" if include_inactive else "is_active = 1"
            citizens = self.get_all(where_clause, order_by="full_name")
            
            if not citizens:
                return False
            
            df = self.to_dataframe(citizens)
            
            # Переименовываем колонки для удобства
            column_mapping = {
                'id': 'ID',
                'full_name': 'ФИО',
                'birth_date': 'Дата рождения',
                'address': 'Адрес',
                'phone': 'Телефон',
                'passport_data': 'Паспорт',
                'registration_date': 'Дата регистрации',
                'total_points': 'Баллы',
                'is_active': 'Активен',
                'notes': 'Заметки'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Форматируем даты
            date_columns = ['Дата рождения', 'Дата регистрации']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Форматируем активность
            if 'Активен' in df.columns:
                df['Активен'] = df['Активен'].map({1: 'Да', 0: 'Нет'})
            
            df.to_excel(file_path, index=False, sheet_name='Граждане махалли')
            
            logger.info(f"Данные граждан экспортированы в {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта данных: {e}")
            return False