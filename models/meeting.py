"""
Модель для работы с заседаниями махалли
"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, time
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class MeetingModel(BaseModel):
    """Модель для управления заседаниями махалли"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.table_name = "meetings"
        self.required_fields = ['title', 'meeting_date']
        self.search_fields = ['title', 'location', 'agenda']
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Валидация данных заседания
        
        Args:
            data: Данные для валидации
            
        Returns:
            Словарь с ошибками валидации
        """
        errors = super().validate_data(data)
        
        # Валидация названия
        if 'title' in data:
            title = data['title'].strip()
            if len(title) < 3:
                errors.setdefault('title', []).append("Название слишком короткое")
            elif len(title) > 255:
                errors.setdefault('title', []).append("Название слишком длинное")
        
        # Валидация даты заседания
        if 'meeting_date' in data and data['meeting_date']:
            if isinstance(data['meeting_date'], str):
                try:
                    meeting_date = datetime.strptime(data['meeting_date'], '%Y-%m-%d').date()
                except ValueError:
                    errors.setdefault('meeting_date', []).append("Неверный формат даты")
                    meeting_date = None
            else:
                meeting_date = data['meeting_date']
            
            if meeting_date:
                # Проверяем, что дата не слишком далеко в прошлом (более года)
                days_diff = (date.today() - meeting_date).days
                if days_diff > 365:
                    errors.setdefault('meeting_date', []).append("Дата заседания слишком давняя")
        
        # Валидация времени
        if 'meeting_time' in data and data['meeting_time']:
            if isinstance(data['meeting_time'], str):
                try:
                    # Проверяем формат времени HH:MM
                    time_parts = data['meeting_time'].split(':')
                    if len(time_parts) != 2:
                        raise ValueError
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                except ValueError:
                    errors.setdefault('meeting_time', []).append("Неверный формат времени (HH:MM)")
        
        # Валидация статуса
        if 'status' in data and data['status']:
            valid_statuses = ['PLANNED', 'COMPLETED', 'CANCELLED']
            if data['status'] not in valid_statuses:
                errors.setdefault('status', []).append(f"Недопустимый статус. Должен быть одним из: {', '.join(valid_statuses)}")
        
        return errors
    
    def create_meeting(
        self,
        title: str,
        meeting_date: date,
        meeting_time: Optional[str] = None,
        location: str = "",
        agenda: str = "",
        created_by: Optional[int] = None
    ) -> Optional[int]:
        """
        Создание нового заседания
        
        Args:
            title: Название заседания
            meeting_date: Дата проведения
            meeting_time: Время проведения (HH:MM)
            location: Место проведения
            agenda: Повестка дня
            created_by: ID пользователя, создавшего заседание
            
        Returns:
            ID созданного заседания или None
        """
        data = {
            'title': title.strip(),
            'meeting_date': meeting_date.isoformat(),
            'meeting_time': meeting_time,
            'location': location.strip(),
            'agenda': agenda.strip(),
            'status': 'PLANNED',
            'attendance_count': 0,
            'total_invited': 0,
            'created_by': created_by
        }
        
        # Валидация данных
        errors = self.validate_data(data)
        if errors:
            logger.error(f"Ошибки валидации при создании заседания: {errors}")
            return None
        
        meeting_id = self.create(data)
        
        if meeting_id:
            self.log_action("create", meeting_id, f"Создано заседание: {title}")
        
        return meeting_id
    
    def update_meeting(self, meeting_id: int, **kwargs) -> bool:
        """
        Обновление данных заседания
        
        Args:
            meeting_id: ID заседания
            **kwargs: Поля для обновления
            
        Returns:
            Успешность операции
        """
        # Форматируем данные
        update_data = {}
        
        for key, value in kwargs.items():
            if key == 'meeting_date' and isinstance(value, date):
                update_data[key] = value.isoformat()
            else:
                update_data[key] = value
        
        # Валидация
        errors = self.validate_data(update_data)
        if errors:
            logger.error(f"Ошибки валидации при обновлении заседания {meeting_id}: {errors}")
            return False
        
        success = self.update(meeting_id, update_data)
        
        if success:
            self.log_action("update", meeting_id, f"Обновлены данные: {list(update_data.keys())}")
        
        return success
    
    def change_status(self, meeting_id: int, new_status: str, notes: str = "") -> bool:
        """
        Изменение статуса заседания
        
        Args:
            meeting_id: ID заседания
            new_status: Новый статус
            notes: Дополнительные заметки
            
        Returns:
            Успешность операции
        """
        valid_statuses = ['PLANNED', 'COMPLETED', 'CANCELLED']
        
        if new_status not in valid_statuses:
            logger.error(f"Недопустимый статус: {new_status}")
            return False
        
        success = self.update(meeting_id, {'status': new_status})
        
        if success:
            self.log_action("status_change", meeting_id, f"Статус изменен на {new_status}. {notes}")
        
        return success
    
    def get_upcoming_meetings(self, days_ahead: int = 30) -> List[sqlite3.Row]:
        """
        Получение предстоящих заседаний
        
        Args:
            days_ahead: Количество дней вперед
            
        Returns:
            Список предстоящих заседаний
        """
        query = """
            SELECT * FROM meetings 
            WHERE meeting_date >= date('now') 
            AND meeting_date <= date('now', '+{} days')
            AND status = 'PLANNED'
            ORDER BY meeting_date, meeting_time
        """.format(days_ahead)
        
        result = self.db.execute_query(query)
        return result if result else []
    
    def get_past_meetings(self, days_back: int = 90) -> List[sqlite3.Row]:
        """
        Получение прошедших заседаний
        
        Args:
            days_back: Количество дней назад
            
        Returns:
            Список прошедших заседаний
        """
        query = """
            SELECT * FROM meetings 
            WHERE meeting_date < date('now') 
            AND meeting_date >= date('now', '-{} days')
            ORDER BY meeting_date DESC, meeting_time DESC
        """.format(days_back)
        
        result = self.db.execute_query(query)
        return result if result else []
    
    def get_meetings_by_status(self, status: str) -> List[sqlite3.Row]:
        """
        Получение заседаний по статусу
        
        Args:
            status: Статус заседаний
            
        Returns:
            Список заседаний
        """
        return self.get_all("status = ?", (status,), order_by="meeting_date DESC")
    
    def get_meetings_by_date_range(self, start_date: date, end_date: date) -> List[sqlite3.Row]:
        """
        Получение заседаний за период
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список заседаний
        """
        query = """
            SELECT * FROM meetings 
            WHERE meeting_date BETWEEN ? AND ?
            ORDER BY meeting_date, meeting_time
        """
        
        result = self.db.execute_query(query, (start_date.isoformat(), end_date.isoformat()))
        return result if result else []
    
    def search_meetings(self, search_term: str) -> List[sqlite3.Row]:
        """
        Поиск заседаний по различным полям
        
        Args:
            search_term: Поисковый запрос
            
        Returns:
            Список найденных заседаний
        """
        return self.search(search_term, self.search_fields)
    
    def update_attendance_count(self, meeting_id: int) -> bool:
        """
        Обновление счетчика посещаемости заседания
        
        Args:
            meeting_id: ID заседания
            
        Returns:
            Успешность операции
        """
        # Подсчитываем количество присутствующих
        attendance_query = """
            SELECT 
                COUNT(*) as total_invited,
                SUM(CASE WHEN is_present = 1 THEN 1 ELSE 0 END) as attendance_count
            FROM attendance 
            WHERE meeting_id = ?
        """
        
        result = self.db.execute_query(attendance_query, (meeting_id,))
        
        if result:
            total_invited = result[0]['total_invited']
            attendance_count = result[0]['attendance_count'] or 0
            
            return self.update(meeting_id, {
                'total_invited': total_invited,
                'attendance_count': attendance_count
            })
        
        return False
    
    def get_attendance_rate(self, meeting_id: int) -> float:
        """
        Получение процента посещаемости заседания
        
        Args:
            meeting_id: ID заседания
            
        Returns:
            Процент посещаемости (0.0 - 100.0)
        """
        meeting = self.get_by_id(meeting_id)
        
        if not meeting or meeting['total_invited'] == 0:
            return 0.0
        
        return (meeting['attendance_count'] / meeting['total_invited']) * 100
    
    def get_monthly_statistics(self, year: int, month: int) -> Dict[str, Any]:
        """
        Получение статистики заседаний за месяц
        
        Args:
            year: Год
            month: Месяц
            
        Returns:
            Словарь со статистикой
        """
        query = """
            SELECT 
                COUNT(*) as total_meetings,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_meetings,
                SUM(CASE WHEN status = 'PLANNED' THEN 1 ELSE 0 END) as planned_meetings,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled_meetings,
                AVG(CASE WHEN status = 'COMPLETED' AND total_invited > 0 
                    THEN (attendance_count * 100.0 / total_invited) 
                    ELSE NULL END) as avg_attendance_rate
            FROM meetings 
            WHERE strftime('%Y', meeting_date) = ? 
            AND strftime('%m', meeting_date) = ?
        """
        
        result = self.db.execute_query(query, (str(year), f"{month:02d}"))
        
        if result:
            stats = dict(result[0])
            stats['avg_attendance_rate'] = round(stats['avg_attendance_rate'] or 0, 2)
            return stats
        
        return {}
    
    def get_meeting_with_attendance(self, meeting_id: int) -> Dict[str, Any]:
        """
        Получение информации о заседании с данными посещаемости
        
        Args:
            meeting_id: ID заседания
            
        Returns:
            Словарь с информацией о заседании и посещаемости
        """
        meeting = self.get_by_id(meeting_id)
        
        if not meeting:
            return {}
        
        # Получаем список участников
        attendance_query = """
            SELECT 
                c.id as citizen_id,
                c.full_name,
                c.phone,
                a.is_present,
                a.points_earned,
                a.arrival_time,
                a.notes
            FROM citizens c
            LEFT JOIN attendance a ON c.id = a.citizen_id AND a.meeting_id = ?
            WHERE c.is_active = 1
            ORDER BY c.full_name
        """
        
        attendance_result = self.db.execute_query(attendance_query, (meeting_id,))
        
        return {
            'meeting': dict(meeting),
            'attendance': [dict(row) for row in attendance_result] if attendance_result else [],
            'attendance_rate': self.get_attendance_rate(meeting_id)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение расширенной статистики по заседаниям
        
        Returns:
            Словарь со статистикой
        """
        stats = super().get_statistics()
        
        # Статистика по статусам
        status_query = """
            SELECT status, COUNT(*) as count
            FROM meetings
            GROUP BY status
        """
        status_result = self.db.execute_query(status_query)
        stats['by_status'] = {row['status']: row['count'] for row in status_result} if status_result else {}
        
        # Средняя посещаемость
        avg_attendance_query = """
            SELECT AVG(CASE WHEN total_invited > 0 
                THEN (attendance_count * 100.0 / total_invited) 
                ELSE NULL END) as avg_attendance_rate
            FROM meetings 
            WHERE status = 'COMPLETED'
        """
        avg_result = self.db.execute_query(avg_attendance_query)
        if avg_result and avg_result[0]['avg_attendance_rate']:
            stats['average_attendance_rate'] = round(avg_result[0]['avg_attendance_rate'], 2)
        
        # Заседания за последние 30 дней
        stats['recent_meetings'] = self.count(
            "meeting_date >= date('now', '-30 days')"
        )
        
        # Предстоящие заседания
        stats['upcoming_meetings'] = self.count(
            "meeting_date >= date('now') AND status = 'PLANNED'"
        )
        
        return stats
    
    def cancel_meeting(self, meeting_id: int, reason: str = "") -> bool:
        """
        Отмена заседания
        
        Args:
            meeting_id: ID заседания
            reason: Причина отмены
            
        Returns:
            Успешность операции
        """
        success = self.change_status(meeting_id, 'CANCELLED', f"Причина отмены: {reason}")
        
        if success:
            # Можно добавить уведомление участников об отмене
            self.log_action("cancel", meeting_id, f"Заседание отменено. Причина: {reason}")
        
        return success
    
    def complete_meeting(self, meeting_id: int, notes: str = "") -> bool:
        """
        Завершение заседания
        
        Args:
            meeting_id: ID заседания
            notes: Заметки о проведении
            
        Returns:
            Успешность операции
        """
        # Обновляем счетчик посещаемости
        self.update_attendance_count(meeting_id)
        
        success = self.change_status(meeting_id, 'COMPLETED', notes)
        
        if success:
            self.log_action("complete", meeting_id, f"Заседание завершено. {notes}")
        
        return success
    
    def export_to_excel(self, file_path: str, include_cancelled: bool = False) -> bool:
        """
        Экспорт данных заседаний в Excel
        
        Args:
            file_path: Путь к файлу
            include_cancelled: Включать ли отмененные заседания
            
        Returns:
            Успешность операции
        """
        try:
            where_clause = "" if include_cancelled else "status != 'CANCELLED'"
            meetings = self.get_all(where_clause, order_by="meeting_date DESC")
            
            if not meetings:
                return False
            
            df = self.to_dataframe(meetings)
            
            # Переименовываем колонки
            column_mapping = {
                'id': 'ID',
                'title': 'Название',
                'meeting_date': 'Дата',
                'meeting_time': 'Время',
                'location': 'Место',
                'agenda': 'Повестка дня',
                'status': 'Статус',
                'attendance_count': 'Присутствовало',
                'total_invited': 'Приглашено',
                'created_at': 'Создано'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Форматируем даты
            if 'Дата' in df.columns:
                df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            if 'Создано' in df.columns:
                df['Создано'] = pd.to_datetime(df['Создано'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
            
            # Переводим статусы
            status_mapping = {
                'PLANNED': 'Запланировано',
                'COMPLETED': 'Проведено',
                'CANCELLED': 'Отменено'
            }
            
            if 'Статус' in df.columns:
                df['Статус'] = df['Статус'].map(status_mapping)
            
            # Добавляем процент посещаемости
            if 'Присутствовало' in df.columns and 'Приглашено' in df.columns:
                df['Посещаемость %'] = df.apply(
                    lambda row: round((row['Присутствовало'] / row['Приглашено']) * 100, 1) 
                    if row['Приглашено'] > 0 else 0, axis=1
                )
            
            df.to_excel(file_path, index=False, sheet_name='Заседания махалли')
            
            logger.info(f"Данные заседаний экспортированы в {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта данных заседаний: {e}")
            return False