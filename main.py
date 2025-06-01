"""
Главный файл приложения - Система управления махалли
Автоматизированная система управления схода граждан махалли 
с интегрированными функциями экстренного оповещения и системы поощрений
"""

import streamlit as st
import logging
from datetime import datetime
import sys
import os
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Добавляем путь к проекту в sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def safe_import():
    """Безопасный импорт модулей с обработкой ошибок"""
    try:
        # Основные конфигурационные модули
        from config.settings import get_settings, PAGES_CONFIG
        from config.database import DatabaseManager
        
        # Утилиты
        from utils.auth import check_authentication, show_user_info, logout, session_timeout_warning
        from utils.helpers import set_page_config, apply_custom_css
        
        return {
            'get_settings': get_settings,
            'PAGES_CONFIG': PAGES_CONFIG,
            'DatabaseManager': DatabaseManager,
            'check_authentication': check_authentication,
            'show_user_info': show_user_info,
            'logout': logout,
            'session_timeout_warning': session_timeout_warning,
            'set_page_config': set_page_config,
            'apply_custom_css': apply_custom_css
        }
    except Exception as e:
        st.error(f"❌ Ошибка импорта базовых модулей: {e}")
        st.error("Проверьте наличие всех необходимых файлов")
        st.code(traceback.format_exc())
        return None

def safe_page_import(page_name):
    """Безопасный импорт модулей страниц"""
    try:
        if page_name == 'dashboard':
            from pages.dashboard import show_dashboard
            return show_dashboard
        elif page_name == 'citizens':
            from pages.citizens import show_citizens_page
            return show_citizens_page
        elif page_name == 'meetings':
            # Поскольку meetings.py пустой, создаем заглушку
            return lambda: show_placeholder_page("meetings", "Страница заседаний в разработке")
        elif page_name == 'sms':
            from pages.sms_sender import show_sms_page
            return show_sms_page
        elif page_name == 'emergency':
            from pages.emergency import show_emergency_page
            return show_emergency_page
        elif page_name == 'points':
            from pages.points import show_points_page
            return show_points_page
        elif page_name == 'reports':
            from pages.reports import show_reports_page
            return show_reports_page
        else:
            return lambda: show_placeholder_page(page_name, f"Страница {page_name} не найдена")
    except Exception as e:
        logger.error(f"Ошибка импорта страницы {page_name}: {e}")
        return lambda: show_error_page(f"Ошибка загрузки страницы {page_name}", str(e))

def show_placeholder_page(page_name, message):
    """Отображение страницы-заглушки"""
    st.markdown(f"## 🚧 {message}")
    st.info("Эта страница находится в разработке")
    
    if page_name == 'meetings':
        st.markdown("""
        ### 🏛️ Функциональность заседаний будет включать:
        
        - 📅 Планирование заседаний
        - 👥 Управление участниками  
        - 📝 Ведение протоколов
        - 📊 Статистика посещаемости
        - 🔔 Автоматические уведомления
        
        **Статус:** В разработке
        """)

def show_error_page(title, error_details=None):
    """Отображение страницы ошибки"""
    st.error(f"❌ {title}")
    
    if error_details:
        with st.expander("Подробности ошибки"):
            st.code(error_details)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🔧 Возможные решения:
        
        1. **Перезагрузите страницу** - обновите браузер
        2. **Проверьте файлы** - убедитесь что все модули на месте
        3. **Проверьте логи** - посмотрите консоль браузера
        4. **Обратитесь в поддержку** - свяжитесь с администратором
        """)
        
        if st.button("🔄 Перезагрузить приложение", use_container_width=True):
            st.rerun()

def init_app():
    """Инициализация приложения"""
    try:
        # Создание необходимых директорий
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/backups', exist_ok=True)
        
        logger.info("Приложение успешно инициализировано")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации приложения: {e}")
        st.error(f"❌ Ошибка инициализации системы: {e}")
        return False

def init_session_state():
    """Инициализация состояния сессии"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "login_time" not in st.session_state:
        st.session_state["login_time"] = None

def show_sidebar_navigation(imports):
    """Отображение навигации в боковой панели"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Навигация")
    
    # Получаем текущую страницу
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    
    # Создаем кнопки навигации
    pages = {
        'dashboard': {'title': '📊 Главная', 'icon': '📊'},
        'citizens': {'title': '👥 Граждане', 'icon': '👥'},
        'meetings': {'title': '🏛️ Заседания', 'icon': '🏛️'},
        'sms': {'title': '📱 SMS-рассылка', 'icon': '📱'},
        'emergency': {'title': '⚡ Экстренные уведомления', 'icon': '⚡'},
        'points': {'title': '⭐ Система баллов', 'icon': '⭐'},
        'reports': {'title': '📊 Отчеты', 'icon': '📊'}
    }
    
    for page_key, page_info in pages.items():
        # Проверяем права доступа (упрощенно)
        if page_key == 'dashboard' or True:  # Временно разрешаем доступ ко всем страницам
            
            # Определяем стиль кнопки (активная/неактивная)
            button_type = "primary" if st.session_state.current_page == page_key else "secondary"
            
            if st.sidebar.button(
                page_info['title'], 
                key=f"nav_{page_key}",
                use_container_width=True,
                type=button_type
            ):
                st.session_state.current_page = page_key
                # Очищаем состояние действий при переходе на другую страницу
                for key in list(st.session_state.keys()):
                    if key.endswith('_action'):
                        del st.session_state[key]
                st.rerun()

def show_system_status(imports):
    """Отображение статуса системы в боковой панели"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Статус системы")
    
    try:
        DatabaseManager = imports.get('DatabaseManager')
        if DatabaseManager:
            db = DatabaseManager()
            db_info = db.get_database_info()
            
            # Информация о базе данных
            st.sidebar.success("🟢 База данных: Подключена")
            st.sidebar.caption(f"Размер: {db_info.get('file_size_mb', 0)} МБ")
            
            # Краткая статистика
            citizens_count = db_info.get('citizens_count', 0)
            meetings_count = db_info.get('meetings_count', 0)
            
            st.sidebar.metric("👥 Граждан", citizens_count)
            st.sidebar.metric("🏛️ Заседаний", meetings_count)
        else:
            st.sidebar.warning("🟡 База данных: Недоступна")
        
    except Exception as e:
        st.sidebar.error("🔴 Ошибка подключения к БД")
        logger.error(f"Ошибка получения статуса системы: {e}")

def route_to_page(page_name: str):
    """Маршрутизация к соответствующей странице"""
    
    try:
        page_function = safe_page_import(page_name)
        if page_function:
            page_function()
        else:
            show_error_page(f"Страница '{page_name}' не найдена")
            
    except Exception as e:
        logger.error(f"Ошибка при отображении страницы {page_name}: {e}")
        show_error_page(f"Ошибка загрузки страницы {page_name}", str(e))

def show_footer():
    """Отображение подвала приложения"""
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        **🏛️ Система управления махалли**  
        Версия 1.0.0 | Разработано для цифровизации махаллей Узбекистана
        """)
    
    with col2:
        current_time = datetime.now().strftime("%H:%M:%S")
        st.caption(f"🕐 Время: {current_time}")
    
    with col3:
        if st.button("📊 О системе"):
            show_about_modal()

def show_about_modal():
    """Отображение информации о системе"""
    
    with st.expander("ℹ️ О системе", expanded=True):
        st.markdown("""
        ### 🏛️ Автоматизированная система управления махалли
        
        **Основные функции:**
        - 👥 **Управление гражданами** - ведение реестра жителей махалли
        - 🏛️ **Заседания** - планирование и проведение собраний
        - 📱 **SMS-рассылки** - массовые уведомления жителям
        - ⚡ **Экстренные уведомления** - срочные оповещения при ЧС
        - ⭐ **Система поощрений** - мотивация активных граждан
        - 📊 **Отчеты и аналитика** - детальная статистика работы
        
        **Технические особенности:**
        - 🔒 Система авторизации и разграничения прав
        - 💾 Надежная база данных SQLite
        - 📱 Адаптивный веб-интерфейс
        - 📊 Интерактивные графики и диаграммы
        - 📥 Экспорт данных в Excel/CSV
        - 🔄 Автоматическое резервное копирование
        """)

def main():
    """Главная функция приложения"""
    
    init_session_state()
    
    try:
        # Инициализация приложения
        if not init_app():
            show_error_page("Ошибка инициализации системы")
            return
        
        # Безопасный импорт модулей
        imports = safe_import()
        if not imports:
            return
        
        # Настройки страницы
        try:
            set_page_config = imports.get('set_page_config')
            get_settings = imports.get('get_settings')
            
            if set_page_config and get_settings:
                settings = get_settings()
                set_page_config(
                    title=settings.APP_TITLE,
                    icon=settings.APP_ICON
                )
            st.warning("main() запущена")
        except Exception as e:
            logger.error(f"Ошибка настройки страницы: {e}")
            # Базовая настройка страницы
            st.set_page_config(
                page_title="Система управления махалли",
                page_icon="🏛️",
                layout="wide",
                initial_sidebar_state="expanded"
            )
        
        # Проверка аутентификации
        check_authentication = imports.get('check_authentication')
        if check_authentication and not check_authentication():
            return
        
        # Применяем кастомные стили
        apply_custom_css = imports.get('apply_custom_css')
        if apply_custom_css:
            apply_custom_css()
        
        # Заголовок приложения
        try:
            get_settings = imports.get('get_settings')
            if get_settings:
                settings = get_settings()
                st.markdown(f"# {settings.APP_ICON} {settings.APP_TITLE}")
            else:
                st.markdown("# 🏛️ Система управления махалли")
        except:
            st.markdown("# 🏛️ Система управления махалли")
        
        # Предупреждение о таймауте сессии
        session_timeout_warning = imports.get('session_timeout_warning')
        if session_timeout_warning:
            session_timeout_warning()
        
        # Основной контент и навигация
        col_main, col_sidebar = st.columns([4, 1])
        
        with col_sidebar:
            # Информация о пользователе
            show_user_info = imports.get('show_user_info')
            if show_user_info:
                show_user_info()
            
            # Навигация
            show_sidebar_navigation(imports)
            
            # Статус системы
            show_system_status(imports)
        
        with col_main:
            # Маршрутизация к нужной странице
            current_page = st.session_state.get('current_page', 'dashboard')
            route_to_page(current_page)
        
        # Подвал
        show_footer()
        
        logger.info(f"Страница {current_page} успешно отображена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в главной функции: {e}")
        show_error_page(f"Критическая ошибка приложения: {str(e)}", traceback.format_exc())

# Проверка и запуск приложения
if __name__ == "__main__":
    try:
        # Логирование запуска
        logger.info("=" * 50)
        logger.info("Запуск системы управления махалли")
        logger.info(f"Время запуска: {datetime.now()}")
        logger.info("=" * 50)
        
        # Проверка версии Python
        if sys.version_info < (3, 8):
            st.error("❌ Требуется Python 3.8 или выше")
            st.stop()
        
        # Инициализация состояния аутентификации
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False
        
        # Запуск главной функции
        main()
        
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {e}")
        st.error(f"❌ Критическая ошибка: {e}")
        st.code(traceback.format_exc())
    finally:
        logger.info("Завершение работы приложения")