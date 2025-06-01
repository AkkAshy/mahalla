"""
Модель для работы с системой баллов и поощрений
"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import logging

from .base import BaseModel

logger = logging.getLogger(__name__)

class PointsModel(BaseModel):
    """Модель для управления системой баллов"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.table_name = "citizen_points"
        print(f"Тип model: {type(self)}")
        print(f"Значение model: {self}")
        self.required_fields = ['citizen_id', 'activity_type', 'points']
        
        # Конфигурация баллов из настроек
        from config.settings import get_settings
        settings = get_settings()
        self.points_config = settings.POINTS_CONFIG
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Валидация данных начисления баллов
        
        Args:
            data: Данные для валидации
            
        Returns:
            Словарь с ошибками валидации
        """
        errors = super().validate_data(data)
        
        # Валидация ID гражданина
        if 'citizen_id' in data:
            if not isinstance(data['citizen_id'], int) or data['citizen_id'] <= 0:
                errors.setdefault('citizen_id', []).append("Некорректный ID гражданина")
            else:
                # Проверяем существование гражданина
                citizen_exists = self.db.execute_query(
                    "SELECT 1 FROM citizens WHERE id = ? AND is_active = 1",
                    (data['citizen_id'],)
                )
                if not citizen_exists:
                    errors.setdefault('citizen_id', []).append("Гражданин не найден или неактивен")
        
        # Валидация типа активности
        if 'activity_type' in data:
            activity_type = data['activity_type']
            if activity_type not in self.points_config:
                errors.setdefault('activity_type', []).append(f"Неизвестный тип активности: {activity_type}")
        
        # Валидация количества баллов
        if 'points' in data:
            points = data['points']
            if not isinstance(points, int):
                errors.setdefault('points', []).append("Баллы должны быть целым числом")
            elif points < -1000 or points > 1000:
                errors.setdefault('points', []).append("Количество баллов должно быть от -1000 до 1000")
        
        return errors
    
    def award_points(
        self,
        citizen_id: int,
        activity_type: str,
        description: str = "",
        meeting_id: Optional[int] = None,
        custom_points: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        """
        Начисление баллов гражданину
        
        Args:
            citizen_id: ID гражданина
            activity_type: Тип активности
            description: Описание активности
            meeting_id: ID связанного заседания
            custom_points: Пользовательское количество баллов
            created_by: ID пользователя, начислившего баллы
            
        Returns:
            ID записи о начислении баллов или None
        """
        # Определяем количество баллов
        if custom_points is not None:
            points = custom_points
        else:
            points = self.points_config.get(activity_type, 5)
        
        # Проверяем на регулярность и применяем бонус
        if self._check_regular_activity(citizen_id, activity_type):
            multiplier = self.points_config.get('regular_bonus_multiplier', 1.0)
            points = int(points * multiplier)
        
        data = {
            'citizen_id': citizen_id,
            'activity_type': activity_type,
            'points': points,
            'description': description,
            'meeting_id': meeting_id,
            'date_earned': date.today().isoformat(),
            'created_by': created_by
        }
        
        # Валидация данных
        errors = self.validate_data(data)
        if errors:
            logger.error(f"Ошибки валидации при начислении баллов: {errors}")
            return None
        
        # Создаем запись о начислении
        point_id = self.create(data)
        
        if point_id:
            # Обновляем общий счет гражданина
            self._update_citizen_total_points(citizen_id)
            
            self.log_action("award", point_id, 
                          f"Начислено {points} баллов гражданину {citizen_id} за {activity_type}")
        
        return point_id
    
    def deduct_points(
        self,
        citizen_id: int,
        points: int,
        reason: str,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        """
        Снятие баллов у гражданина
        
        Args:
            citizen_id: ID гражданина
            points: Количество баллов для снятия (положительное число)
            reason: Причина снятия
            created_by: ID пользователя, снявшего баллы
            
        Returns:
            ID записи или None
        """
        return self.award_points(
            citizen_id=citizen_id,
            activity_type="penalty",
            description=f"Снятие баллов: {reason}",
            custom_points=-abs(points),
            created_by=created_by
        )
    
    def _check_regular_activity(self, citizen_id: int, activity_type: str) -> bool:
        """
        Проверка регулярности активности для бонуса
        
        Args:
            citizen_id: ID гражданина
            activity_type: Тип активности
            
        Returns:
            True если гражданин регулярно активен
        """
        # Проверяем активность за последние 3 месяца
        three_months_ago = date.today() - timedelta(days=90)
        
        query = """
            SELECT COUNT(DISTINCT date_earned) as active_days
            FROM citizen_points
            WHERE citizen_id = ? 
            AND activity_type = ?
            AND date_earned >= ?
        """
        
        result = self.db.execute_query(query, (citizen_id, activity_type, three_months_ago.isoformat()))
        
        if result:
            active_days = result[0]['active_days']
            # Считаем регулярным если активность была минимум 6 раз за 3 месяца
            return active_days >= 6
        
        return False
    
    def _update_citizen_total_points(self, citizen_id: int) -> bool:
        """
        Обновление общего счета баллов гражданина
        
        Args:
            citizen_id: ID гражданина
            
        Returns:
            Успешность операции
        """
        # Подсчитываем общую сумму баллов
        total_query = """
            SELECT COALESCE(SUM(points), 0) as total_points
            FROM citizen_points
            WHERE citizen_id = ?
        """
        
        result = self.db.execute_query(total_query, (citizen_id,))
        
        if result:
            total_points = result[0]['total_points']
            
            # Обновляем счет в таблице граждан
            update_query = """
                UPDATE citizens SET total_points = ? WHERE id = ?
            """
            
            return self.db.execute_query(update_query, (total_points, citizen_id), fetch=False) is not None
        
        return False
    
    def get_citizen_points_history(
        self, 
        citizen_id: int, 
        limit: Optional[int] = None
    ) -> List[sqlite3.Row]:
        """
        Получение истории начислений баллов гражданина
        
        Args:
            citizen_id: ID гражданина
            limit: Ограничение количества записей
            
        Returns:
            Список записей истории
        """
        query = """
            SELECT 
                cp.*,
                m.title as meeting_title,
                u.username as created_by_username
            FROM citizen_points cp
            LEFT JOIN meetings m ON cp.meeting_id = m.id
            LEFT JOIN users u ON cp.created_by = u.id
            WHERE cp.citizen_id = ?
            ORDER BY cp.date_earned DESC, cp.created_at DESC
        """
        
        params = (citizen_id,)
        
        if limit:
            query += " LIMIT ?"
            params = (citizen_id, limit)
        
        result = self.db.execute_query(query, params)
        return result if result else []
    
    def get_leaderboard(self, limit: int = 10, period_days: Optional[int] = None) -> List[sqlite3.Row]:
        """
        Получение рейтинга активных граждан
        
        Args:
            limit: Количество позиций в рейтинге
            period_days: Период для подсчета (если None, то за все время)
            
        Returns:
            Список лидеров
        """
        if period_days:
            # Рейтинг за период
            start_date = date.today() - timedelta(days=period_days)
            query = """
                SELECT 
                    c.id,
                    c.full_name,
                    c.phone,
                    c.address,
                    SUM(cp.points) as period_points,
                    COUNT(cp.id) as activities_count
                FROM citizens c
                INNER JOIN citizen_points cp ON c.id = cp.citizen_id
                WHERE c.is_active = 1 
                AND cp.date_earned >= ?
                GROUP BY c.id, c.full_name, c.phone, c.address
                HAVING period_points > 0
                ORDER BY period_points DESC, activities_count DESC
                LIMIT ?
            """
            params = (start_date.isoformat(), limit)
        else:
            # Рейтинг за все время
            query = """
                SELECT 
                    c.id,
                    c.full_name,
                    c.phone,
                    c.address,
                    c.total_points,
                    COUNT(cp.id) as activities_count
                FROM citizens c
                LEFT JOIN citizen_points cp ON c.id = cp.citizen_id
                WHERE c.is_active = 1 
                AND c.total_points > 0
                GROUP BY c.id, c.full_name, c.phone, c.address, c.total_points
                ORDER BY c.total_points DESC, activities_count DESC
                LIMIT ?
            """
            params = (limit,)
        
        result = self.db.execute_query(query, params)
        return result if result else []
    
    def get_activity_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики активности за период
        
        Args:
            days: Количество дней
            
        Returns:
            Словарь со статистикой
        """
        start_date = date.today() - timedelta(days=days)
        
        # Статистика по типам активности
        activity_query = """
            SELECT 
                activity_type,
                COUNT(*) as count,
                SUM(points) as total_points,
                AVG(points) as avg_points
            FROM citizen_points
            WHERE date_earned >= ?
            GROUP BY activity_type
            ORDER BY total_points DESC
        """
        
        activity_result = self.db.execute_query(activity_query, (start_date.isoformat(),))
        activity_stats = [dict(row) for row in activity_result] if activity_result else []
        
        # Статистика по дням
        daily_query = """
            SELECT 
                date_earned,
                COUNT(*) as activities_count,
                SUM(points) as points_awarded,
                COUNT(DISTINCT citizen_id) as active_citizens
            FROM citizen_points
            WHERE date_earned >= ?
            GROUP BY date_earned
            ORDER BY date_earned
        """
        
        daily_result = self.db.execute_query(daily_query, (start_date.isoformat(),))
        daily_stats = [dict(row) for row in daily_result] if daily_result else []
        
        # Общие метрики
        total_query = """
            SELECT 
                COUNT(*) as total_activities,
                SUM(points) as total_points_awarded,
                COUNT(DISTINCT citizen_id) as active_citizens_count,
                AVG(points) as avg_points_per_activity
            FROM citizen_points
            WHERE date_earned >= ?
        """
        
        total_result = self.db.execute_query(total_query, (start_date.isoformat(),))
        total_stats = dict(total_result[0]) if total_result else {}
        
        return {
            'period_days': days,
            'by_activity_type': activity_stats,
            'daily_breakdown': daily_stats,
            'totals': total_stats
        }
    
    def get_citizen_rank(self, citizen_id: int) -> Optional[int]:
        """
        Получение позиции гражданина в рейтинге
        
        Args:
            citizen_id: ID гражданина
            
        Returns:
            Позиция в рейтинге или None
        """
        query = """
            SELECT COUNT(*) + 1 as rank
            FROM citizens
            WHERE is_active = 1 
            AND total_points > (
                SELECT total_points FROM citizens WHERE id = ? AND is_active = 1
            )
        """
        
        result = self.db.execute_query(query, (citizen_id,))
        return result[0]['rank'] if result else None
    
    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Получение месячной сводки по баллам
        
        Args:
            year: Год
            month: Месяц
            
        Returns:
            Словарь с месячной статистикой
        """
        # Формируем диапазон дат для месяца
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Топ граждан за месяц
        top_citizens_query = """
            SELECT 
                c.full_name,
                SUM(cp.points) as month_points,
                COUNT(cp.id) as activities_count
            FROM citizen_points cp
            JOIN citizens c ON cp.citizen_id = c.id
            WHERE cp.date_earned BETWEEN ? AND ?
            AND c.is_active = 1
            GROUP BY c.id, c.full_name
            HAVING month_points > 0
            ORDER BY month_points DESC
            LIMIT 10
        """
        
        top_result = self.db.execute_query(
            top_citizens_query, 
            (start_date.isoformat(), end_date.isoformat())
        )
        
        # Статистика по активностям за месяц
        activity_summary_query = """
            SELECT 
                activity_type,
                COUNT(*) as count,
                SUM(points) as total_points
            FROM citizen_points
            WHERE date_earned BETWEEN ? AND ?
            GROUP BY activity_type
            ORDER BY total_points DESC
        """
        
        activity_result = self.db.execute_query(
            activity_summary_query,
            (start_date.isoformat(), end_date.isoformat())
        )
        
        # Общие метрики за месяц
        total_query = """
            SELECT 
                COUNT(*) as total_activities,
                SUM(points) as total_points,
                COUNT(DISTINCT citizen_id) as active_citizens,
                AVG(points) as avg_points
            FROM citizen_points
            WHERE date_earned BETWEEN ? AND ?
        """
        
        total_result = self.db.execute_query(
            total_query,
            (start_date.isoformat(), end_date.isoformat())
        )
        
        return {
            'period': f"{year}-{month:02d}",
            'top_citizens': [dict(row) for row in top_result] if top_result else [],
            'activity_breakdown': [dict(row) for row in activity_result] if activity_result else [],
            'totals': dict(total_result[0]) if total_result else {}
        }
    
    def award_meeting_attendance_points(self, meeting_id: int, attendance_data: Dict[int, bool]) -> int:
        """
        Массовое начисление баллов за посещение заседания
        
        Args:
            meeting_id: ID заседания
            attendance_data: Словарь {citizen_id: is_present}
            
        Returns:
            Количество успешно начисленных баллов
        """
        awarded_count = 0
        
        for citizen_id, is_present in attendance_data.items():
            if is_present:
                point_id = self.award_points(
                    citizen_id=citizen_id,
                    activity_type='meeting_attendance',
                    description=f"Посещение заседания",
                    meeting_id=meeting_id
                )
                
                if point_id:
                    awarded_count += 1
        
        if awarded_count > 0:
            logger.info(f"Начислены баллы {awarded_count} гражданам за посещение заседания {meeting_id}")
        
        return awarded_count
    
    def get_points_distribution(self) -> Dict[str, int]:
        """
        Получение распределения граждан по количеству баллов
        
        Returns:
            Словарь с распределением по диапазонам
        """
        query = """
            SELECT 
                CASE 
                    WHEN total_points = 0 THEN '0 баллов'
                    WHEN total_points BETWEEN 1 AND 50 THEN '1-50 баллов'
                    WHEN total_points BETWEEN 51 AND 100 THEN '51-100 баллов'
                    WHEN total_points BETWEEN 101 AND 200 THEN '101-200 баллов'
                    WHEN total_points BETWEEN 201 AND 500 THEN '201-500 баллов'
                    ELSE '500+ баллов'
                END as points_range,
                COUNT(*) as count
            FROM citizens
            WHERE is_active = 1
            GROUP BY points_range
            ORDER BY 
                CASE points_range
                    WHEN '0 баллов' THEN 1
                    WHEN '1-50 баллов' THEN 2
                    WHEN '51-100 баллов' THEN 3
                    WHEN '101-200 баллов' THEN 4
                    WHEN '201-500 баллов' THEN 5
                    ELSE 6
                END
        """
        
        result = self.db.execute_query(query)
        return {row['points_range']: row['count'] for row in result} if result else {}
    
    def get_activity_types(self) -> List[sqlite3.Row]:
        """
        Получение списка типов активности
        
        Returns:
            Список типов активности
        """
        query = """
            SELECT * FROM activity_types
            WHERE is_active = 1
            ORDER BY display_name
        """
        
        result = self.db.execute_query(query)
        return result if result else []
    
    def create_activity_type(
        self,
        name: str,
        display_name: str,
        points_value: int,
        description: str = ""
    ) -> Optional[int]:
        """
        Создание нового типа активности
        
        Args:
            name: Системное имя
            display_name: Отображаемое имя
            points_value: Количество баллов
            description: Описание
            
        Returns:
            ID созданного типа или None
        """
        # Проверяем уникальность имени
        existing = self.db.execute_query(
            "SELECT 1 FROM activity_types WHERE name = ?",
            (name,)
        )
        
        if existing:
            logger.error(f"Тип активности с именем '{name}' уже существует")
            return None
        
        query = """
            INSERT INTO activity_types (name, display_name, points_value, description)
            VALUES (?, ?, ?, ?)
        """
        
        activity_id = self.db.execute_query(
            query,
            (name, display_name, points_value, description),
            fetch=False
        )
        
        if activity_id:
            logger.info(f"Создан новый тип активности: {display_name}")
        
        return activity_id
    
    def bulk_award_points(self, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Массовое начисление баллов
        
        Args:
            awards: Список словарей с данными о начислениях
            
        Returns:
            Результат массового начисления
        """
        successful = 0
        failed = 0
        errors = []
        
        for award in awards:
            try:
                point_id = self.award_points(**award)
                if point_id:
                    successful += 1
                else:
                    failed += 1
                    errors.append(f"Не удалось начислить баллы гражданину {award.get('citizen_id')}")
            except Exception as e:
                failed += 1
                errors.append(f"Ошибка для гражданина {award.get('citizen_id')}: {str(e)}")
        
        return {
            'total': len(awards),
            'successful': successful,
            'failed': failed,
            'errors': errors
        }
    
    def calculate_bonus_points(self, citizen_id: int, base_points: int, activity_type: str) -> int:
        """
        Расчет бонусных баллов с учетом регулярности
        
        Args:
            citizen_id: ID гражданина
            base_points: Базовые баллы
            activity_type: Тип активности
            
        Returns:
            Итоговое количество баллов с бонусом
        """
        if self._check_regular_activity(citizen_id, activity_type):
            multiplier = self.points_config.get('regular_bonus_multiplier', 1.0)
            return int(base_points * multiplier)
        
        return base_points
    
    def export_points_report(self, file_path: str, period_days: int = 30) -> bool:
        """
        Экспорт отчета по баллам в Excel
        
        Args:
            file_path: Путь к файлу
            period_days: Период для отчета
            
        Returns:
            Успешность операции
        """
        try:
            start_date = date.today() - timedelta(days=period_days)
            
            # Данные по гражданам
            citizens_query = """
                SELECT 
                    c.full_name as 'ФИО',
                    c.address as 'Адрес',
                    c.phone as 'Телефон',
                    c.total_points as 'Всего баллов',
                    COALESCE(period_points.points, 0) as 'Баллы за период',
                    COALESCE(period_points.activities, 0) as 'Активностей за период'
                FROM citizens c
                LEFT JOIN (
                    SELECT 
                        citizen_id,
                        SUM(points) as points,
                        COUNT(*) as activities
                    FROM citizen_points
                    WHERE date_earned >= ?
                    GROUP BY citizen_id
                ) period_points ON c.id = period_points.citizen_id
                WHERE c.is_active = 1
                ORDER BY c.total_points DESC
            """
            
            citizens_result = self.db.execute_query(citizens_query, (start_date.isoformat(),))
            
            # Статистика по активностям
            activities_query = """
                SELECT 
                    at.display_name as 'Тип активности',
                    COUNT(cp.id) as 'Количество',
                    SUM(cp.points) as 'Всего баллов',
                    AVG(cp.points) as 'Средние баллы'
                FROM citizen_points cp
                LEFT JOIN activity_types at ON cp.activity_type = at.name
                WHERE cp.date_earned >= ?
                GROUP BY cp.activity_type, at.display_name
                ORDER BY SUM(cp.points) DESC
            """
            
            activities_result = self.db.execute_query(activities_query, (start_date.isoformat(),))
            
            # Создаем Excel файл
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Лист с гражданами
                if citizens_result:
                    citizens_df = pd.DataFrame([dict(row) for row in citizens_result])
                    citizens_df.to_excel(writer, sheet_name='Граждане', index=False)
                
                # Лист со статистикой активностей
                if activities_result:
                    activities_df = pd.DataFrame([dict(row) for row in activities_result])
                    activities_df.to_excel(writer, sheet_name='Статистика активностей', index=False)
                
                # Лист с общей информацией
                summary_data = [{
                    'Период отчета': f"{start_date} - {date.today()}",
                    'Всего граждан': len(citizens_result) if citizens_result else 0,
                    'Активных граждан за период': len([r for r in citizens_result if dict(r)['Активностей за период'] > 0]) if citizens_result else 0,
                    'Всего начислено баллов': sum(dict(r)['Баллы за период'] for r in citizens_result) if citizens_result else 0,
                    'Дата создания отчета': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }]
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Сводка', index=False)
            
            logger.info(f"Отчет по баллам экспортирован в {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта отчета по баллам: {e}")
            return False
    
    def get_citizen_achievements(self, citizen_id: int) -> Dict[str, Any]:
        """
        Получение достижений гражданина
        
        Args:
            citizen_id: ID гражданина
            
        Returns:
            Словарь с достижениями
        """
        # Общая статистика
        total_query = """
            SELECT 
                COUNT(*) as total_activities,
                SUM(points) as total_points,
                MIN(date_earned) as first_activity,
                MAX(date_earned) as last_activity
            FROM citizen_points
            WHERE citizen_id = ?
        """
        
        total_result = self.db.execute_query(total_query, (citizen_id,))
        total_stats = dict(total_result[0]) if total_result else {}
        
        # Статистика по типам активности
        activity_breakdown_query = """
            SELECT 
                activity_type,
                COUNT(*) as count,
                SUM(points) as points
            FROM citizen_points
            WHERE citizen_id = ?
            GROUP BY activity_type
            ORDER BY points DESC
        """
        
        activity_result = self.db.execute_query(activity_breakdown_query, (citizen_id,))
        activity_breakdown = [dict(row) for row in activity_result] if activity_result else []
        
        # Достижения (значки)
        achievements = []
        
        # Проверяем различные достижения
        if total_stats.get('total_points', 0) >= 100:
            achievements.append({'name': 'Активист', 'description': 'Набрал 100+ баллов'})
        
        if total_stats.get('total_points', 0) >= 500:
            achievements.append({'name': 'Лидер махалли', 'description': 'Набрал 500+ баллов'})
        
        # Проверяем регулярность
        if total_stats.get('total_activities', 0) >= 20:
            achievements.append({'name': 'Постоянный участник', 'description': '20+ активностей'})
        
        # Ранг в общем рейтинге
        rank = self.get_citizen_rank(citizen_id)
        
        return {
            'total_stats': total_stats,
            'activity_breakdown': activity_breakdown,
            'achievements': achievements,
            'rank': rank
        }