"""
Базовая модель для всех моделей данных
"""

import sqlite3
import pandas as pd
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseModel:
    """Базовая модель для работы с данными"""
    
    def __init__(self, db_manager):
        """
        Инициализация модели
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        self.db = db_manager
        self.table_name = None  # Должно быть переопределено в дочерних классах
    
    def create(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Создание новой записи
        
        Args:
            data: Данные для создания записи
            
        Returns:
            ID созданной записи или None
        """
        if not self.table_name:
            raise NotImplementedError("table_name должно быть определено")
        
        # Добавляем timestamp
        data['created_at'] = datetime.now().isoformat()
        data['updated_at'] = datetime.now().isoformat()
        
        # Формируем запрос
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        return self.db.execute_query(query, tuple(data.values()), fetch=False)
    
    def get_by_id(self, record_id: int) -> Optional[sqlite3.Row]:
        """
        Получение записи по ID
        
        Args:
            record_id: ID записи
            
        Returns:
            Запись или None
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        result = self.db.execute_query(query, (record_id,))
        return result[0] if result else None
    
    def get_all(self, where_clause: str = "", params: tuple = None, order_by: str = "id") -> List[sqlite3.Row]:
        """
        Получение всех записей
        
        Args:
            where_clause: Условие WHERE (без слова WHERE)
            params: Параметры для условия
            order_by: Поле для сортировки
            
        Returns:
            Список записей
        """
        query = f"SELECT * FROM {self.table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        query += f" ORDER BY {order_by}"
        
        result = self.db.execute_query(query, params)
        return result if result else []
    
    def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновление записи
        
        Args:
            record_id: ID записи
            data: Данные для обновления
            
        Returns:
            Успешность операции
        """
        # Добавляем timestamp обновления
        data['updated_at'] = datetime.now().isoformat()
        
        # Формируем запрос
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        
        params = list(data.values()) + [record_id]
        result = self.db.execute_query(query, tuple(params), fetch=False)
        
        return result is not None
    
    def delete(self, record_id: int) -> bool:
        """
        Удаление записи
        
        Args:
            record_id: ID записи
            
        Returns:
            Успешность операции
        """
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        result = self.db.execute_query(query, (record_id,), fetch=False)
        return result is not None
    
    def soft_delete(self, record_id: int) -> bool:
        """
        Мягкое удаление записи (установка is_active = 0)
        
        Args:
            record_id: ID записи
            
        Returns:
            Успешность операции
        """
        return self.update(record_id, {'is_active': 0})
    
    def count(self, where_clause: str = "", params: tuple = None) -> int:
        """
        Подсчет количества записей
        
        Args:
            where_clause: Условие WHERE
            params: Параметры для условия
            
        Returns:
            Количество записей
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        result = self.db.execute_query(query, params)
        return result[0]['count'] if result else 0
    
    def exists(self, where_clause: str, params: tuple) -> bool:
        """
        Проверка существования записи
        
        Args:
            where_clause: Условие WHERE
            params: Параметры для условия
            
        Returns:
            True если запись существует
        """
        return self.count(where_clause, params) > 0
    
    def get_paginated(
        self, 
        page: int = 1, 
        page_size: int = 50, 
        where_clause: str = "", 
        params: tuple = None,
        order_by: str = "id"
    ) -> Dict[str, Any]:
        """
        Получение записей с пагинацией
        
        Args:
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            where_clause: Условие WHERE
            params: Параметры для условия
            order_by: Поле для сортировки
            
        Returns:
            Словарь с данными и метаинформацией
        """
        # Общее количество записей
        total_count = self.count(where_clause, params)
        
        # Вычисляем смещение
        offset = (page - 1) * page_size
        
        # Запрос с LIMIT и OFFSET
        query = f"SELECT * FROM {self.table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        
        # Добавляем параметры для LIMIT и OFFSET
        query_params = list(params) if params else []
        query_params.extend([page_size, offset])
        
        records = self.db.execute_query(query, tuple(query_params))
        
        # Метаинформация
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            'data': records if records else [],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
    
    def search(self, search_term: str, search_fields: List[str]) -> List[sqlite3.Row]:
        """
        Поиск записей по нескольким полям
        
        Args:
            search_term: Поисковый запрос
            search_fields: Список полей для поиска
            
        Returns:
            Список найденных записей
        """
        if not search_fields:
            return []
        
        # Формируем условие поиска
        search_conditions = []
        params = []
        
        for field in search_fields:
            search_conditions.append(f"UPPER({field}) LIKE UPPER(?)")
            params.append(f"%{search_term}%")
        
        where_clause = " OR ".join(search_conditions)
        
        return self.get_all(where_clause, tuple(params))
    
    def to_dataframe(self, records: List[sqlite3.Row]) -> pd.DataFrame:
        """
        Преобразование записей в DataFrame
        
        Args:
            records: Список записей
            
        Returns:
            DataFrame с данными
        """
        if not records:
            return pd.DataFrame()
        
        # Преобразуем sqlite3.Row в список словарей
        data = [dict(record) for record in records]
        return pd.DataFrame(data)
    
    def bulk_insert(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        Массовая вставка записей
        
        Args:
            data_list: Список словарей с данными
            
        Returns:
            Успешность операции
        """
        if not data_list:
            return True
        
        # Добавляем timestamps ко всем записям
        timestamp = datetime.now().isoformat()
        for data in data_list:
            data['created_at'] = timestamp
            data['updated_at'] = timestamp
        
        # Получаем названия колонок из первой записи
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Подготавливаем данные для executemany
        params_list = [tuple(data[col] for col in columns) for data in data_list]
        
        return self.db.execute_many(query, params_list)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение базовой статистики по таблице
        
        Returns:
            Словарь со статистикой
        """
        stats = {}
        
        # Общее количество записей
        stats['total_count'] = self.count()
        
        # Количество активных записей (если есть поле is_active)
        try:
            stats['active_count'] = self.count("is_active = 1")
        except:
            pass
        
        # Записи созданные за последние 30 дней
        try:
            stats['recent_count'] = self.count(
                "created_at >= date('now', '-30 days')"
            )
        except:
            pass
        
        return stats
    
    def validate_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Базовая валидация данных
        
        Args:
            data: Данные для валидации
            
        Returns:
            Словарь с ошибками валидации
        """
        errors = {}
        
        # Проверка обязательных полей (переопределяется в дочерних классах)
        required_fields = getattr(self, 'required_fields', [])
        
        for field in required_fields:
            if field not in data or not data[field]:
                if field not in errors:
                    errors[field] = []
                errors[field].append(f"Поле '{field}' обязательно для заполнения")
        
        return errors
    
    def log_action(self, action: str, record_id: int, details: str = ""):
        """
        Логирование действий с записями
        
        Args:
            action: Тип действия (create, update, delete)
            record_id: ID записи
            details: Дополнительные детали
        """
        logger.info(
            f"Action: {action}, Table: {self.table_name}, "
            f"Record ID: {record_id}, Details: {details}"
        )