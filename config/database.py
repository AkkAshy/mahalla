"""
Конфигурация и управление базой данных SQLite
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from .settings import get_settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Инициализация менеджера БД
        
        Args:
            db_path: Путь к файлу базы данных
        """
        settings = get_settings()
        self.db_path = db_path or str(settings.DATABASE_PATH)
        self._ensure_data_directory()
        self.init_database()
    
    def _ensure_data_directory(self):
        """Создание директории для базы данных"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Получение подключения к базе данных"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Включаем поддержку внешних ключей
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Union[tuple, Dict[str, Any]]] = None, 
        fetch: bool = True
    ) -> Optional[Union[List[sqlite3.Row], int]]:
        """
        Выполнение SQL запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch: Возвращать ли результат
            
        Returns:
            Результат запроса или ID последней вставленной записи
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT') and fetch:
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.lastrowid
                    
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"Запрос: {query}")
            if params:
                logger.error(f"Параметры: {params}")
            return None
    
    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """
        Выполнение множественных запросов
        
        Args:
            query: SQL запрос
            params_list: Список параметров для каждого запроса
            
        Returns:
            Успешность выполнения
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка выполнения множественного запроса: {e}")
            return False
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        logger.info("Инициализация базы данных...")
        
        # Создаем таблицы
        self._create_users_table()
        self._create_citizens_table()
        self._create_meetings_table()
        self._create_attendance_table()
        self._create_sms_tables()
        self._create_points_tables()
        self._create_decisions_table()
        
        # Создаем индексы
        self._create_indexes()
        
        # Вставляем начальные данные
        self._insert_initial_data()
        
        logger.info("База данных инициализирована")
    
    def _create_users_table(self):
        """Создание таблицы пользователей"""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'operator',
                is_active INTEGER DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, fetch=False)
    
    def _create_citizens_table(self):
        """Создание таблицы граждан"""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS citizens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                birth_date DATE,
                address TEXT,
                phone TEXT,
                passport_data TEXT,
                registration_date DATE DEFAULT CURRENT_DATE,
                is_active INTEGER DEFAULT 1,
                total_points INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, fetch=False)
    
    def _create_meetings_table(self):
        """Создание таблицы заседаний"""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                meeting_date DATE NOT NULL,
                meeting_time TEXT,
                location TEXT,
                agenda TEXT,
                status TEXT DEFAULT 'PLANNED' CHECK (status IN ('PLANNED', 'COMPLETED', 'CANCELLED')),
                attendance_count INTEGER DEFAULT 0,
                total_invited INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """, fetch=False)
    
    def _create_attendance_table(self):
        """Создание таблицы посещаемости"""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citizen_id INTEGER NOT NULL,
                meeting_id INTEGER NOT NULL,
                is_present INTEGER DEFAULT 0,
                points_earned INTEGER DEFAULT 0,
                arrival_time TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (citizen_id) REFERENCES citizens(id) ON DELETE CASCADE,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
                UNIQUE(citizen_id, meeting_id)
            )
        """, fetch=False)
    
    def _create_sms_tables(self):
        """Создание таблиц для SMS"""
        # Таблица SMS кампаний
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS sms_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                campaign_type TEXT DEFAULT 'REGULAR' CHECK (campaign_type IN ('REGULAR', 'EMERGENCY', 'REMINDER')),
                sent_count INTEGER DEFAULT 0,
                delivered_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                scheduled_at TIMESTAMP,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """, fetch=False)
        
        # Журнал SMS
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS sms_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                citizen_id INTEGER,
                phone TEXT NOT NULL,
                message_text TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'DELIVERED', 'FAILED')),
                error_message TEXT,
                sent_at TIMESTAMP,
                delivered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES sms_campaigns(id) ON DELETE CASCADE,
                FOREIGN KEY (citizen_id) REFERENCES citizens(id) ON DELETE SET NULL
            )
        """, fetch=False)
        
        # Экстренные SMS
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS emergency_sms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                emergency_type TEXT NOT NULL,
                priority INTEGER DEFAULT 1 CHECK (priority IN (1, 2, 3)),
                affected_area TEXT,
                sent_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """, fetch=False)
    
    def _create_points_tables(self):
        """Создание таблиц для системы баллов"""
        # История начислений баллов
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS citizen_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citizen_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                points INTEGER NOT NULL,
                description TEXT,
                meeting_id INTEGER,
                date_earned DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (citizen_id) REFERENCES citizens(id) ON DELETE CASCADE,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """, fetch=False)
        
        # Виды активности для баллов
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS activity_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                points_value INTEGER NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, fetch=False)
    
    def _create_decisions_table(self):
        """Создание таблицы решений"""
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                decision_text TEXT NOT NULL,
                decision_number TEXT,
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                votes_abstain INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')),
                deadline DATE,
                responsible_person TEXT,
                execution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            )
        """, fetch=False)
    
    def _create_indexes(self):
        """Создание индексов для оптимизации"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_citizens_name ON citizens(full_name)",
            "CREATE INDEX IF NOT EXISTS idx_citizens_phone ON citizens(phone)",
            "CREATE INDEX IF NOT EXISTS idx_citizens_active ON citizens(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date)",
            "CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_citizen ON attendance(citizen_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_meeting ON attendance(meeting_id)",
            "CREATE INDEX IF NOT EXISTS idx_sms_logs_campaign ON sms_logs(campaign_id)",
            "CREATE INDEX IF NOT EXISTS idx_sms_logs_citizen ON sms_logs(citizen_id)",
            "CREATE INDEX IF NOT EXISTS idx_points_citizen ON citizen_points(citizen_id)",
            "CREATE INDEX IF NOT EXISTS idx_points_date ON citizen_points(date_earned)"
        ]
        
        for index_sql in indexes:
            self.execute_query(index_sql, fetch=False)
    
    def _insert_initial_data(self):
        """Вставка начальных данных"""
        # Проверяем, есть ли уже пользователи
        users_count = self.execute_query("SELECT COUNT(*) as count FROM users")[0]['count']
        
        if users_count == 0:
            # Создаем администратора по умолчанию
            import hashlib
            settings = get_settings()
            password_hash = hashlib.sha256(settings.DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
            
            self.execute_query("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
            """, (settings.DEFAULT_ADMIN_LOGIN, password_hash, "Администратор системы", "admin"), fetch=False)
            
            logger.info("Создан пользователь по умолчанию")
        
        # Вставляем типы активности для баллов
        activity_types = [
            ('meeting_attendance', 'Посещение заседания', 10, 'Участие в общих собраниях махалли'),
            ('subbotnik', 'Участие в субботнике', 15, 'Участие в общественных работах и уборке'),
            ('community_work', 'Общественная работа', 10, 'Выполнение общественных поручений'),
            ('volunteer_work', 'Волонтерская деятельность', 12, 'Добровольная помощь соседям и махалле'),
            ('initiative', 'Инициатива', 20, 'Предложение полезных инициатив для махалли')
        ]
        
        # Проверяем, есть ли уже типы активности
        activities_count = self.execute_query("SELECT COUNT(*) as count FROM activity_types")[0]['count']
        
        if activities_count == 0:
            for activity in activity_types:
                self.execute_query("""
                    INSERT INTO activity_types (name, display_name, points_value, description)
                    VALUES (?, ?, ?, ?)
                """, activity, fetch=False)
            
            logger.info("Добавлены типы активности")
        
        # Добавляем тестовых граждан
        citizens_count = self.execute_query("SELECT COUNT(*) as count FROM citizens")[0]['count']
        
        if citizens_count == 0:
            test_citizens = [
                ("Иванов Иван Иванович", "1980-05-15", "ул. Навои, 123", "+998901234567", "AB1234567"),
                ("Петрова Мария Александровна", "1975-03-22", "ул. Амира Темура, 45", "+998901234568", "AB1234568"),
                ("Сидоров Алексей Петрович", "1990-11-08", "ул. Мустакиллик, 67", "+998901234569", "AB1234569"),
                ("Кузнецова Елена Сергеевна", "1985-07-12", "ул. Бунёдкор, 89", "+998901234570", "AB1234570"),
                ("Смирнов Дмитрий Владимирович", "1970-12-03", "ул. Чиланзар, 12", "+998901234571", "AB1234571"),
                ("Каримова Дилором Ахмедовна", "1982-09-18", "ул. Ойбек, 56", "+998901234572", "AB1234572"),
                ("Рахимов Бахтиер Умарович", "1978-07-25", "ул. Шота Руставели, 34", "+998901234573", "AB1234573"),
                ("Усманова Нигора Садыковна", "1987-11-12", "ул. Фурката, 78", "+998901234574", "AB1234574")
            ]
            
            for citizen in test_citizens:
                self.execute_query("""
                    INSERT INTO citizens (full_name, birth_date, address, phone, passport_data)
                    VALUES (?, ?, ?, ?, ?)
                """, citizen, fetch=False)
            
            logger.info("Добавлены тестовые граждане")
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """
        Создание резервной копии базы данных
        
        Args:
            backup_path: Путь для сохранения копии
            
        Returns:
            Путь к созданной копии
        """
        if backup_path is None:
            settings = get_settings()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = settings.BACKUP_DIR / f"mahalla_backup_{timestamp}.db"
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        logger.info(f"Резервная копия создана: {backup_path}")
        return str(backup_path)
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Восстановление базы данных из резервной копии
        
        Args:
            backup_path: Путь к файлу резервной копии
            
        Returns:
            Успешность восстановления
        """
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"База данных восстановлена из {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления базы данных: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Получение информации о базе данных
        
        Returns:
            Словарь с информацией о БД
        """
        info = {}
        
        # Размер файла БД
        db_file = Path(self.db_path)
        if db_file.exists():
            info['file_size'] = db_file.stat().st_size
            info['file_size_mb'] = round(info['file_size'] / (1024 * 1024), 2)
        
        # Количество записей в таблицах
        tables = ['citizens', 'meetings', 'attendance', 'sms_campaigns', 'sms_logs', 'citizen_points']
        
        for table in tables:
            try:
                result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                info[f'{table}_count'] = result[0]['count'] if result else 0
            except:
                info[f'{table}_count'] = 0
        
        return info