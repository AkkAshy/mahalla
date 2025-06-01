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





# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mahalla_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Добавляем путь к проекту в sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импорты компонентов системы
try:
    from config.settings import get_settings, PAGES_CONFIG
    from config.database import DatabaseManager
    from utils.auth import check_authentication, show_user_info, logout, session_timeout_warning
    from utils.helpers import set_page_config, apply_custom_css
    
except ImportError as e:
    st.error(f"❌ Ошибка импорта модулей: {e}")
    st.stop()


def init_app():
    """Инициализация приложения"""
    try:
        # Настройки страницы
        settings = get_settings()
        set_page_config(
            title=settings.APP_TITLE,
            icon=settings.APP_ICON
        )
        
        # Создание необходимых директорий
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/backups', exist_ok=True)
        
        # Инициализация базы данных
        db = DatabaseManager()
        
        logger.info("Приложение успешно инициализировано")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации приложения: {e}")
        st.error(f"❌ Ошибка инициализации системы: {e}")
        return False


def show_sidebar_navigation():
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
        # Проверяем права доступа
        from utils.auth import has_permission
        if page_key == 'dashboard' or has_permission(page_key):
            
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


def show_system_status():
    """Отображение статуса системы в боковой панели"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Статус системы")
    
    try:
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
        
    except Exception as e:
        st.sidebar.error("🔴 Ошибка подключения к БД")
        logger.error(f"Ошибка получения статуса системы: {e}")


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
        
        **Инновационные решения:**
        - 🚨 Система экстренных уведомлений для ЧС
        - 🏆 Геймификация через систему баллов
        - 📈 Аналитика активности граждан
        - ⏰ Автоматические напоминания о заседаниях
        
        ---
        
        **Разработано в соответствии с:**
        - Законом РУз "О органах самоуправления граждан"
        - Постановлением Президента о поддержке махаллей
        - Требованиями цифровизации государственных услуг
        
        **Техническая поддержка:** support@mahalla-system.uz  
        **Документация:** [Руководство пользователя](docs.mahalla-system.uz)
        """)


def show_error_page(error_message: str):
    """Отображение страницы ошибки"""
    
    st.error(f"❌ {error_message}")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🔧 Возможные решения:
        
        1. **Перезагрузите страницу** - обновите браузер
        2. **Проверьте подключение** - убедитесь в стабильности интернета
        3. **Очистите кэш** - очистите кэш браузера
        4. **Обратитесь в поддержку** - свяжитесь с администратором
        
        ### 📞 Контакты поддержки:
        - **Email:** support@mahalla-system.uz
        - **Телефон:** +998 (71) 123-45-67
        - **Время работы:** 9:00 - 18:00 (Пн-Пт)
        """)
        
        if st.button("🔄 Перезагрузить приложение", use_container_width=True):
            st.rerun()


def route_to_page(page_name: str):
    """Маршрутизация к соответствующей странице"""
    
    try:
        if page_name == 'dashboard':
            from pages.dashboard import show_dashboard
            show_dashboard()
        elif page_name == 'citizens':
            from pages.citizens import show_citizens_page
            show_citizens_page()
        elif page_name == 'meetings':
            from pages.meetings import show_meetings_page
            show_meetings_page()
        elif page_name == 'sms':
            from pages.sms_sender import show_sms_page
            show_sms_page()
        elif page_name == 'emergency':
            from pages.emergency import show_emergency_page
            show_emergency_page()
        elif page_name == 'points':
            from pages.points import show_points_page
            show_points_page()
        elif page_name == 'reports':
            from pages.reports import show_reports_page
            show_reports_page()
        else:
            st.error(f"❌ Страница '{page_name}' не найдена")
            st.session_state.current_page = 'dashboard'
            from pages.dashboard import show_dashboard
            show_dashboard()
            
    except Exception as e:
        logger.error(f"Ошибка при отображении страницы {page_name}: {e}")
        import traceback
        st.error(f"❌ Ошибка загрузки страницы: {str(e)}")
        st.code(traceback.format_exc())


def handle_quick_actions():
    """Обработка быстрых действий из других страниц"""
    
    # Обработка быстрых действий с главной страницы
    if hasattr(st.session_state, 'quick_action'):
        action = st.session_state.quick_action
        
        if action == "add_citizen":
            st.session_state.current_page = 'citizens'
            st.session_state.citizen_action = 'add'
        elif action == "create_meeting":
            st.session_state.current_page = 'meetings'
            st.session_state.meeting_action = 'create'
        elif action == "send_sms":
            st.session_state.current_page = 'sms'
            st.session_state.sms_action = 'create'
        elif action == "export_data":
            st.session_state.current_page = 'reports'
            st.session_state.report_type = 'comprehensive'
        
        # Очищаем быстрое действие
        del st.session_state.quick_action
        st.rerun()


def show_maintenance_mode():
    """Отображение режима обслуживания"""
    
    st.warning("🔧 Система находится на техническом обслуживании")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### 🛠️ Техническое обслуживание
        
        Система временно недоступна для проведения планового обслуживания.
        
        **Ожидаемое время восстановления:** 30 минут
        
        **Выполняемые работы:**
        - Обновление базы данных
        - Оптимизация производительности  
        - Установка исправлений безопасности
        
        Приносим извинения за временные неудобства.
        """)
        
        if st.button("🔄 Проверить доступность", use_container_width=True):
            st.rerun()


def check_system_health():
    """Проверка состояния системы"""
    
    try:
        # Проверка базы данных
        db = DatabaseManager()
        db.execute_query("SELECT 1", fetch=False)
        
        # Проверка доступности файловой системы
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"test")
        
        return True
        
    except Exception as e:
        logger.error(f"Проверка работоспособности системы не пройдена: {e}")
        return False


def main():
    """Главная функция приложения"""
    
    try:
        # Инициализация приложения
        if not init_app():
            show_error_page("Ошибка инициализации системы")
            return
        
        # Проверка работоспособности системы
        if not check_system_health():
            show_maintenance_mode()
            return
        
        # Проверка аутентификации
        if not check_authentication():
            return
        
        # Применяем кастомные стили
        apply_custom_css()
        
        # Заголовок приложения
        settings = get_settings()
        st.markdown(f"# {settings.APP_ICON} {settings.APP_TITLE}")
        
        # Предупреждение о таймауте сессии
        session_timeout_warning()
        
        # Обработка быстрых действий
        handle_quick_actions()
        
        # Основной контент и навигация
        col_main, col_sidebar = st.columns([4, 1])
        
        with col_sidebar:
            # Информация о пользователе
            show_user_info()
            
            # Навигация
            show_sidebar_navigation()
            
            # Статус системы
            show_system_status()
        
        with col_main:
            # Маршрутизация к нужной странице
            current_page = st.session_state.get('current_page', 'dashboard')
            route_to_page(current_page)
        
        # Подвал
        show_footer()
        
        logger.info(f"Страница {current_page} успешно отображена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в главной функции: {e}")
        show_error_page(f"Критическая ошибка приложения: {str(e)}")


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
        
        # Запуск главной функции
        main()
        
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {e}")
        st.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("Завершение работы приложения")


# Дополнительные утилиты для разработки и отладки
def debug_session_state():
    """Отладочная функция для просмотра состояния сессии"""
    if st.sidebar.button("🐛 Debug Session"):
        st.sidebar.json(dict(st.session_state))


def clear_session_state():
    """Очистка состояния сессии для отладки"""
    if st.sidebar.button("🗑️ Clear Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# Конфигурация для deployment
def configure_for_production():
    """Настройка для продакшн среды"""
    
    # Отключение режима разработки
    if 'development' in st.session_state:
        del st.session_state['development']
    
    # Настройка логирования для продакшн
    logging.getLogger().setLevel(logging.WARNING)
    
    # Отключение отладочных функций
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.set_option('deprecation.showfileUploaderEncoding', False)


# Информация о версии и сборке
__version__ = "1.0.0"
__build_date__ = "2024-01-15"
__author__ = "Mahalla System Development Team"
__description__ = "Автоматизированная система управления махалли с функциями SMS-уведомлений и поощрений"

# Метаданные для Streamlit
st.markdown(f"""
<meta name="description" content="{__description__}">
<meta name="author" content="{__author__}">
<meta name="version" content="{__version__}">
""", unsafe_allow_html=True)