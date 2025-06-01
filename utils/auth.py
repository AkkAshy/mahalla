"""
Система авторизации и управления сессиями
"""

import streamlit as st
import hashlib
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """Менеджер авторизации"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_timeout_minutes = 30
    
    def hash_password(self, password: str) -> str:
        """
        Хеширование пароля
        
        Args:
            password: Пароль для хеширования
            
        Returns:
            Хешированный пароль
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Проверка пароля
        
        Args:
            password: Введенный пароль
            hashed_password: Хешированный пароль из БД
            
        Returns:
            True если пароль верный
        """
        return self.hash_password(password) == hashed_password
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентификация пользователя
        
        Args:
            username: Имя пользователя
            password: Пароль
            
        Returns:
            Данные пользователя или None
        """
        query = """
            SELECT id, username, password_hash, full_name, role, is_active
            FROM users 
            WHERE username = ? AND is_active = 1
        """
        
        result = self.db.execute_query(query, (username,))
        
        if not result:
            logger.warning(f"Попытка входа с несуществующим пользователем: {username}")
            return None
        
        user = result[0]
        
        if self.verify_password(password, user['password_hash']):
            # Обновляем время последнего входа
            self.update_last_login(user['id'])
            
            user_data = {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role'],
                'login_time': datetime.now()
            }
            
            logger.info(f"Успешный вход пользователя: {username}")
            return user_data
        else:
            logger.warning(f"Неверный пароль для пользователя: {username}")
            return None
    
    def update_last_login(self, user_id: int):
        """Обновление времени последнего входа"""
        query = "UPDATE users SET last_login = ? WHERE id = ?"
        self.db.execute_query(query, (datetime.now().isoformat(), user_id), fetch=False)
    
    def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: str = 'operator'
    ) -> Optional[int]:
        """
        Создание нового пользователя
        
        Args:
            username: Имя пользователя
            password: Пароль
            full_name: Полное имя
            role: Роль пользователя
            
        Returns:
            ID созданного пользователя или None
        """
        # Проверяем уникальность имени пользователя
        existing = self.db.execute_query(
            "SELECT 1 FROM users WHERE username = ?",
            (username,)
        )
        
        if existing:
            logger.error(f"Пользователь с именем '{username}' уже существует")
            return None
        
        # Создаем пользователя
        password_hash = self.hash_password(password)
        
        query = """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """
        
        user_id = self.db.execute_query(
            query,
            (username, password_hash, full_name, role),
            fetch=False
        )
        
        if user_id:
            logger.info(f"Создан новый пользователь: {username} ({role})")
        
        return user_id
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """
        Изменение пароля пользователя
        
        Args:
            user_id: ID пользователя
            new_password: Новый пароль
            
        Returns:
            Успешность операции
        """
        password_hash = self.hash_password(new_password)
        
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        result = self.db.execute_query(query, (password_hash, user_id), fetch=False)
        
        if result is not None:
            logger.info(f"Пароль изменен для пользователя ID: {user_id}")
            return True
        
        return False
    
    def get_user_permissions(self, role: str) -> list:
        """
        Получение прав доступа для роли
        
        Args:
            role: Роль пользователя
            
        Returns:
            Список разрешений
        """
        from config.settings import USER_ROLES
        
        role_config = USER_ROLES.get(role, {})
        return role_config.get('permissions', [])
    
    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """
        Проверка прав доступа
        
        Args:
            user_role: Роль пользователя
            required_permission: Требуемое разрешение
            
        Returns:
            True если доступ разрешен
        """
        permissions = self.get_user_permissions(user_role)
        
        # Администратор имеет все права
        if 'all' in permissions:
            return True
        
        return required_permission in permissions


def init_session_state():
    """Инициализация состояния сессии"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None


def check_session_timeout() -> bool:
    """
    Проверка таймаута сессии
    
    Returns:
        True если сессия активна
    """
    if not st.session_state.authenticated or not st.session_state.login_time:
        return False
    
    # Проверяем таймаут
    session_duration = datetime.now() - st.session_state.login_time
    max_duration = timedelta(minutes=30)  # 30 минут
    
    if session_duration > max_duration:
        # Сессия истекла
        logout()
        return False
    
    return True


def check_authentication() -> bool:
    """
    Проверка аутентификации пользователя
    
    Returns:
        True если пользователь аутентифицирован
    """
    init_session_state()
    
    # Проверяем таймаут сессии
    if not check_session_timeout():
        return False
    
    if not st.session_state.authenticated:
        show_login_form()
        return False
    
    return True


def show_login_form():
    """Отображение формы входа"""
    
    # Кастомные стили для формы входа
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .login-header {
            text-align: center;
            color: #1e3c72;
            margin-bottom: 2rem;
        }
        .login-info {
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 5px;
            margin-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Заголовок
    st.markdown("""
    <div class="login-header">
        <h1>🏛️ Система управления махалли</h1>
        <h3>🔐 Авторизация</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Центрируем форму
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### Вход в систему")
                
                username = st.text_input(
                    "👤 Логин",
                    placeholder="Введите ваш логин",
                    help="Имя пользователя для входа в систему"
                )
                
                password = st.text_input(
                    "🔒 Пароль", 
                    type="password",
                    placeholder="Введите ваш пароль",
                    help="Пароль для входа в систему"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    login_button = st.form_submit_button(
                        "🚀 Войти",
                        use_container_width=True,
                        type="primary"
                    )
                
                with col_btn2:
                    demo_button = st.form_submit_button(
                        "👁️ Демо доступ",
                        use_container_width=True
                    )
                
                # Обработка входа
                if login_button or demo_button:
                    if demo_button:
                        # Демо доступ с дефолтными данными
                        username = "admin"
                        password = "mahalla2024"
                    
                    if username and password:
                        success = login(username, password)
                        if success:
                            st.success("✅ Успешный вход в систему!")
                            st.rerun()
                        else:
                            st.error("❌ Неверный логин или пароль")
                    else:
                        st.warning("⚠️ Введите логин и пароль")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Информационный блок
            with st.expander("💡 Тестовые данные для входа"):
                st.markdown("""
                <div class="login-info">
                    <strong>Демо доступ:</strong><br>
                    🔑 Логин: <code>admin</code><br>
                    🔑 Пароль: <code>mahalla2024</code><br><br>
                    
                    <em>Или нажмите кнопку "Демо доступ"</em>
                </div>
                """, unsafe_allow_html=True)
            
            # Информация о системе
            st.markdown("""
            ---
            ### 📋 О системе
            
            **Функции системы:**
            - 👥 Управление гражданами махалли
            - 🏛️ Планирование заседаний
            - 📱 SMS-рассылки и уведомления
            - ⚡ Экстренные оповещения
            - ⭐ Система поощрений
            - 📊 Отчеты и аналитика
            
            **Технические особенности:**
            - 💾 База данных SQLite
            - 🌐 Веб-интерфейс Streamlit
            - 📱 Поддержка мобильных устройств
            - 🔒 Система авторизации
            """)


def login(username: str, password: str) -> bool:
    """
    Вход пользователя в систему
    
    Args:
        username: Имя пользователя
        password: Пароль
        
    Returns:
        True если вход успешен
    """
    from config.database import DatabaseManager
    
    try:
        # Получаем экземпляр базы данных
        db = DatabaseManager()
        auth_manager = AuthManager(db)
        
        # Аутентификация
        user_data = auth_manager.authenticate_user(username, password)
        
        if user_data:
            # Сохраняем данные в сессии
            st.session_state.authenticated = True
            st.session_state.user = user_data
            st.session_state.login_time = datetime.now()
            
            logger.info(f"Пользователь {username} вошел в систему")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при входе пользователя {username}: {e}")
        st.error("Ошибка подключения к системе")
        return False


def logout():
    """Выход пользователя из системы"""
    if st.session_state.get('user'):
        username = st.session_state.user.get('username', 'unknown')
        logger.info(f"Пользователь {username} вышел из системы")
    
    # Очищаем сессию
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.login_time = None
    
    # Очищаем другие данные сессии если есть
    keys_to_clear = [key for key in st.session_state.keys() 
                     if key not in ['authenticated', 'user', 'login_time']]
    
    for key in keys_to_clear:
        del st.session_state[key]


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Получение данных текущего пользователя
    
    Returns:
        Данные пользователя или None
    """
    return st.session_state.get('user')


def get_current_user_id() -> Optional[int]:
    """
    Получение ID текущего пользователя
    
    Returns:
        ID пользователя или None
    """
    user = get_current_user()
    return user['id'] if user else None


def get_current_user_role() -> Optional[str]:
    """
    Получение роли текущего пользователя
    
    Returns:
        Роль пользователя или None
    """
    user = get_current_user()
    return user['role'] if user else None


def has_permission(permission: str) -> bool:
    """
    Проверка прав доступа текущего пользователя
    
    Args:
        permission: Требуемое разрешение
        
    Returns:
        True если доступ разрешен
    """
    user_role = get_current_user_role()
    
    if not user_role:
        return False
    
    from config.database import DatabaseManager
    db = DatabaseManager()
    auth_manager = AuthManager(db)
    
    return auth_manager.check_permission(user_role, permission)


def require_permission(permission: str):
    """
    Декоратор для проверки прав доступа
    
    Args:
        permission: Требуемое разрешение
    """
    if not has_permission(permission):
        st.error("❌ У вас нет прав доступа к этой функции")
        st.stop()


def show_user_info():
    """Отображение информации о текущем пользователе"""
    user = get_current_user()
    
    if user:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Пользователь")
        st.sidebar.write(f"**{user['full_name']}**")
        st.sidebar.write(f"Роль: {user['role']}")
        
        # Время входа
        if st.session_state.login_time:
            login_duration = datetime.now() - st.session_state.login_time
            hours, remainder = divmod(login_duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            st.sidebar.write(f"В системе: {hours}ч {minutes}м")
        
        # Кнопка выхода
        if st.sidebar.button("🚪 Выйти из системы"):
            logout()
            st.rerun()


def session_timeout_warning():
    """Предупреждение о скором истечении сессии"""
    if not st.session_state.authenticated or not st.session_state.login_time:
        return
    
    session_duration = datetime.now() - st.session_state.login_time
    max_duration = timedelta(minutes=30)
    remaining = max_duration - session_duration
    
    # Предупреждаем за 5 минут до истечения
    if remaining.total_seconds() <= 300 and remaining.total_seconds() > 0:
        minutes_left = int(remaining.total_seconds() // 60)
        st.warning(f"⏰ Сессия истекает через {minutes_left} минут. Обновите страницу для продления.")


def extend_session():
    """Продление сессии"""
    if st.session_state.authenticated:
        st.session_state.login_time = datetime.now()


# Автоматическое продление сессии при активности
def auto_extend_session():
    """Автоматическое продление сессии при активности пользователя"""
    if st.session_state.authenticated:
        # Продлеваем сессию на каждом взаимодействии
        extend_session()