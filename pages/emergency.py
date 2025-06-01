"""
Страница экстренных уведомлений
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from config.database import DatabaseManager
from config.settings import SMS_TEMPLATES
from models.citizen import CitizenModel
from utils.helpers import (
    format_datetime, show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission

def show_emergency_page():
    """Главная функция страницы экстренных уведомлений"""
    
    st.markdown("# ⚡ Экстренные уведомления")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('emergency'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Предупреждение о важности
    st.warning("""
    ⚠️ **ВНИМАНИЕ!** Данный раздел предназначен для отправки экстренных уведомлений жителям махалли.
    Используйте только в случае реальной необходимости: отключения коммунальных услуг, 
    чрезвычайных ситуаций, срочных объявлений.
    """)
    
    # Инициализируем модели
    db = DatabaseManager()
    citizen_model = CitizenModel(db)
    
    # Боковая панель с быстрыми действиями
    with st.sidebar:
        st.markdown("### ⚡ Быстрые действия")
        
        emergency_types = {
            "💧 Отключение воды": "water",
            "⚡ Отключение электричества": "electricity", 
            "🔥 Отключение газа": "gas",
            "🚧 Дорожные работы": "road_works",
            "🚨 Чрезвычайная ситуация": "emergency",
            "📢 Срочное объявление": "announcement"
        }
        
        for display_name, emergency_type in emergency_types.items():
            if st.button(display_name, use_container_width=True):
                st.session_state.emergency_action = "quick_send"
                st.session_state.emergency_type = emergency_type
                st.rerun()
        
        st.markdown("---")
        
        if st.button("📋 История уведомлений", use_container_width=True):
            st.session_state.emergency_action = "history"
        
        if st.button("📊 Статистика", use_container_width=True):
            st.session_state.emergency_action = "stats"
        
        # Информация о получателях
        st.markdown("---")
        st.markdown("### 👥 Получатели")
        
        total_citizens = citizen_model.count("is_active = 1")
        with_phones = citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''")
        
        st.metric("Всего граждан", total_citizens)
        st.metric("С телефонами", with_phones)
        
        coverage = (with_phones / total_citizens * 100) if total_citizens > 0 else 0
        st.metric("Охват SMS", f"{coverage:.1f}%")
    
    # Обработка действий
    action = st.session_state.get('emergency_action', 'main')
    
    if action == "quick_send":
        emergency_type = st.session_state.get('emergency_type')
        show_quick_emergency_form(citizen_model, emergency_type)
    elif action == "custom_send":
        show_custom_emergency_form(citizen_model)
    elif action == "history":
        show_emergency_history(db)
    elif action == "stats":
        show_emergency_statistics(db)
    else:
        show_emergency_main(citizen_model)


def show_emergency_main(citizen_model: CitizenModel):
    """Главная страница экстренных уведомлений"""
    
    st.markdown("### 🚨 Экстренные уведомления")
    
    # Карточки быстрых действий
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #FF6B6B, #FF8E53);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 10px 0;
            ">
                <h3>💧 Коммунальные услуги</h3>
                <p>Уведомления об отключении воды, газа, электричества</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Отправить уведомление", key="utilities", use_container_width=True):
                st.session_state.emergency_action = "quick_send"
                st.session_state.emergency_type = "utilities"
                st.rerun()
    
    with col2:
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #4ECDC4, #44A08D);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 10px 0;
            ">
                <h3>🚧 Дорожные работы</h3>
                <p>Информация о ремонтах, перекрытиях дорог</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Отправить уведомление", key="roads", use_container_width=True):
                st.session_state.emergency_action = "quick_send"
                st.session_state.emergency_type = "road_works"
                st.rerun()
    
    with col3:
        with st.container():
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 10px 0;
            ">
                <h3>📢 Произвольное</h3>
                <p>Создать собственное экстренное уведомление</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Создать уведомление", key="custom", use_container_width=True):
                st.session_state.emergency_action = "custom_send"
                st.rerun()
    
    st.markdown("---")
    
    # Последние экстренные уведомления
    st.markdown("### 📋 Последние экстренные уведомления")
    
    recent_emergencies = get_recent_emergency_notifications(DatabaseManager())
    
    if recent_emergencies:
        for emergency in recent_emergencies[:5]:
            show_emergency_notification_card(emergency)
    else:
        st.info("📭 Недавних экстренных уведомлений нет")
    
    # Рекомендации
    st.markdown("---")
    with st.expander("💡 Рекомендации по использованию"):
        st.markdown("""
        ### Когда использовать экстренные уведомления:
        
        **🔴 Критические ситуации:**
        - Отключение воды, газа, электричества
        - Аварии на коммунальных сетях
        - Чрезвычайные ситуации (пожар, наводнение)
        - Срочные медицинские предупреждения
        
        **🟡 Важная информация:**
        - Дорожные работы и перекрытия
        - Изменения в работе учреждений
        - Срочные собрания или мероприятия
        
        **⚪ НЕ используйте для:**
        - Обычных объявлений (используйте обычные SMS)
        - Поздравлений и приветствий
        - Рекламных сообщений
        - Плановых уведомлений
        
        ### Советы по составлению сообщений:
        - Будьте краткими и конкретными
        - Указывайте время и место
        - Добавляйте контактную информацию
        - Используйте понятный язык
        """)


def show_quick_emergency_form(citizen_model: CitizenModel, emergency_type: str):
    """Быстрая форма отправки экстренного уведомления"""
    
    st.markdown("### ⚡ Быстрое экстренное уведомление")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.emergency_action = "main"
            st.rerun()
    
    # Определяем тип уведомления
    emergency_configs = {
        "water": {
            "title": "💧 Отключение воды",
            "template": "emergency_water",
            "priority": 2,
            "icon": "💧"
        },
        "electricity": {
            "title": "⚡ Отключение электричества", 
            "template": "emergency_electricity",
            "priority": 2,
            "icon": "⚡"
        },
        "gas": {
            "title": "🔥 Отключение газа",
            "template": "emergency_gas", 
            "priority": 3,
            "icon": "🔥"
        },
        "road_works": {
            "title": "🚧 Дорожные работы",
            "template": "road_works",
            "priority": 1,
            "icon": "🚧"
        },
        "emergency": {
            "title": "🚨 Чрезвычайная ситуация",
            "template": "",
            "priority": 3,
            "icon": "🚨"
        },
        "announcement": {
            "title": "📢 Срочное объявление",
            "template": "",
            "priority": 2,
            "icon": "📢"
        }
    }
    
    config = emergency_configs.get(emergency_type, emergency_configs["announcement"])
    
    st.markdown(f"#### {config['title']}")
    
    # Приоритет
    priority_colors = {1: "🟡", 2: "🟠", 3: "🔴"}
    priority_names = {1: "Низкий", 2: "Средний", 3: "Высокий"}
    
    priority_icon = priority_colors.get(config['priority'], "⚪")
    priority_name = priority_names.get(config['priority'], "Обычный")
    
    st.info(f"{priority_icon} Приоритет: **{priority_name}**")
    
    with st.form("quick_emergency_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Заголовок
            title = st.text_input(
                "Заголовок уведомления *",
                value=config['title'],
                help="Краткое описание ситуации"
            )
            
            # Текст сообщения с шаблоном
            template_text = SMS_TEMPLATES.get(config['template'], "")
            
            message_text = st.text_area(
                "Текст сообщения *",
                value=template_text,
                height=150,
                max_chars=160,
                help="Используйте переменные: {start_time}, {end_time}, {location}, {reason}"
            )
            
            # Счетчик символов
            char_count = len(message_text)
            color = "red" if char_count > 160 else "orange" if char_count > 140 else "green"
            st.markdown(f"<p style='color: {color}; font-size: 12px;'>Символов: {char_count}/160</p>", 
                       unsafe_allow_html=True)
            
            # Дополнительные поля для заполнения переменных
            if "{start_time}" in template_text or "{end_time}" in template_text:
                col_start, col_end = st.columns(2)
                
                with col_start:
                    start_time = st.text_input("Время начала", placeholder="09:00")
                
                with col_end:
                    end_time = st.text_input("Время окончания", placeholder="18:00")
            
            if "{location}" in template_text:
                location = st.text_input("Место/Район", placeholder="ул. Навои, дома 1-50")
            
            if "{reason}" in template_text:
                reason = st.text_input("Причина", placeholder="плановые ремонтные работы")
        
        with col2:
            st.markdown("#### 👥 Получатели")
            
            # Выбор получателей
            recipient_scope = st.radio(
                "Кому отправить:",
                ["🌍 Всем жителям", "📍 По районам", "👥 Выборочно"],
                help="Выберите масштаб рассылки"
            )
            
            if recipient_scope == "📍 По районам":
                areas = st.multiselect(
                    "Выберите районы:",
                    ["ул. Навои", "ул. Амира Темура", "ул. Мустакиллик", "ул. Бунёдкор"],
                    help="Можно выбрать несколько районов"
                )
            
            # Подсчет получателей
            recipient_count = get_emergency_recipients_count(citizen_model, recipient_scope)
            st.metric("📱 Получателей", recipient_count)
            
            # Предупреждение о высоком приоритете
            if config['priority'] == 3:
                st.error("🔴 **ВЫСОКИЙ ПРИОРИТЕТ**\nСообщение будет отправлено немедленно всем получателям!")
            
            st.markdown("#### ⏰ Время отправки")
            
            send_immediately = st.checkbox("Отправить немедленно", value=True)
            
            if not send_immediately:
                send_datetime = st.datetime_input(
                    "Время отправки",
                    value=datetime.now(),
                    min_value=datetime.now()
                )
        
        # Кнопка отправки
        submitted = st.form_submit_button(
            f"🚨 ОТПРАВИТЬ ЭКСТРЕННОЕ УВЕДОМЛЕНИЕ",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            if not title.strip() or not message_text.strip():
                st.error("❌ Заполните все обязательные поля")
                return
            
            # Заменяем переменные в тексте
            formatted_message = message_text
            
            if 'start_time' in locals():
                formatted_message = formatted_message.replace("{start_time}", start_time)
            if 'end_time' in locals():
                formatted_message = formatted_message.replace("{end_time}", end_time)
            if 'location' in locals():
                formatted_message = formatted_message.replace("{location}", location)
            if 'reason' in locals():
                formatted_message = formatted_message.replace("{reason}", reason)
            
            # Отправляем уведомление
            success = send_emergency_notification(
                title=title.strip(),
                message_text=formatted_message,
                emergency_type=emergency_type,
                priority=config['priority'],
                recipient_scope=recipient_scope,
                citizen_model=citizen_model
            )
            
            if success:
                show_success_message(f"✅ Экстренное уведомление отправлено {recipient_count} получателям!")
                st.session_state.emergency_action = "main"
                st.rerun()
            else:
                show_error_message("❌ Ошибка при отправке экстренного уведомления")


def show_custom_emergency_form(citizen_model: CitizenModel):
    """Форма создания произвольного экстренного уведомления"""
    
    st.markdown("### 📢 Произвольное экстренное уведомление")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.emergency_action = "main"
            st.rerun()
    
    with st.form("custom_emergency_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            title = st.text_input(
                "Заголовок уведомления *",
                placeholder="Срочное объявление",
                help="Краткое описание ситуации"
            )
            
            emergency_type = st.selectbox(
                "Тип ситуации",
                ["Коммунальные услуги", "Дорожные работы", "Безопасность", "Медицинская", "Общая информация"],
                help="Категория экстренного уведомления"
            )
            
            priority = st.selectbox(
                "Приоритет",
                [1, 2, 3],
                format_func=lambda x: f"{'🟡 Низкий' if x == 1 else '🟠 Средний' if x == 2 else '🔴 Высокий'}",
                index=1,
                help="Приоритет определяет срочность доставки"
            )
            
            message_text = st.text_area(
                "Текст сообщения *",
                height=200,
                max_chars=160,
                help="Максимум 160 символов"
            )
            
            # Счетчик символов
            char_count = len(message_text)
            color = "red" if char_count > 160 else "orange" if char_count > 140 else "green"
            st.markdown(f"<p style='color: {color}; font-size: 12px;'>Символов: {char_count}/160</p>", 
                       unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 👥 Получатели")
            
            recipient_scope = st.radio(
                "Кому отправить:",
                ["🌍 Всем жителям", "📱 Только с телефонами", "👥 По возрасту"],
                help="Выберите целевую аудиторию"
            )
            
            if recipient_scope == "👥 По возрасту":
                age_groups = st.multiselect(
                    "Возрастные группы:",
                    ["18-30 лет", "31-50 лет", "51-70 лет", "70+ лет"]
                )
            
            recipient_count = get_emergency_recipients_count(citizen_model, recipient_scope)
            st.metric("📱 Получателей", recipient_count)
            
            st.markdown("#### ⚙️ Настройки")
            
            affected_area = st.text_input(
                "Затронутая территория",
                placeholder="ул. Навои, дома 1-50",
                help="Опционально: укажите конкретную территорию"
            )
            
            send_immediately = st.checkbox("Отправить немедленно", value=True)
        
        submitted = st.form_submit_button(
            "🚨 ОТПРАВИТЬ ЭКСТРЕННОЕ УВЕДОМЛЕНИЕ",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            if not title.strip() or not message_text.strip():
                st.error("❌ Заполните все обязательные поля")
                return
            
            success = send_emergency_notification(
                title=title.strip(),
                message_text=message_text.strip(),
                emergency_type=emergency_type.lower().replace(' ', '_'),
                priority=priority,
                recipient_scope=recipient_scope,
                citizen_model=citizen_model,
                affected_area=affected_area.strip() if affected_area else None
            )
            
            if success:
                show_success_message(f"✅ Экстренное уведомление отправлено {recipient_count} получателям!")
                st.session_state.emergency_action = "main"
                st.rerun()
            else:
                show_error_message("❌ Ошибка при отправке экстренного уведомления")


def show_emergency_history(db: DatabaseManager):
    """История экстренных уведомлений"""
    
    st.markdown("### 📋 История экстренных уведомлений")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.emergency_action = "main"
            st.rerun()
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period_filter = st.selectbox(
            "Период",
            ["За неделю", "За месяц", "За квартал", "Все время"]
        )
    
    with col2:
        type_filter = st.selectbox(
            "Тип",
            ["Все", "Коммунальные услуги", "Дорожные работы", "Безопасность", "Медицинская"]
        )
    
    with col3:
        priority_filter = st.selectbox(
            "Приоритет",
            ["Все", "Высокий", "Средний", "Низкий"]
        )
    
    # Получаем историю
    emergency_history = get_filtered_emergency_history(db, period_filter, type_filter, priority_filter)
    
    if emergency_history:
        st.success(f"✅ Найдено уведомлений: {len(emergency_history)}")
        
        for emergency in emergency_history:
            show_emergency_history_card(emergency)
    else:
        st.info("📭 Экстренные уведомления не найдены")


def show_emergency_statistics(db: DatabaseManager):
    """Статистика экстренных уведомлений"""
    
    st.markdown("### 📊 Статистика экстренных уведомлений")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.emergency_action = "main"
            st.rerun()
    
    # Получаем статистику
    stats = get_emergency_statistics(db)
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚨 Всего уведомлений", stats.get('total_count', 0))
    
    with col2:
        st.metric("📅 За месяц", stats.get('monthly_count', 0))
    
    with col3:
        st.metric("📱 Отправлено SMS", stats.get('total_sms', 0))
    
    with col4:
        avg_response_time = stats.get('avg_response_time', 0)
        st.metric("⏱️ Среднее время", f"{avg_response_time:.1f} мин")
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # Статистика по типам
        type_stats = stats.get('by_type', {})
        if type_stats:
            st.markdown("#### 📋 По типам ситуаций")
            
            import plotly.express as px
            fig = px.pie(
                values=list(type_stats.values()),
                names=list(type_stats.keys()),
                title="Распределение по типам"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о типах")
    
    with col2:
        # Статистика по приоритетам
        priority_stats = stats.get('by_priority', {})
        if priority_stats:
            st.markdown("#### 🎯 По приоритетам")
            
            priority_names = {1: "Низкий", 2: "Средний", 3: "Высокий"}
            
            labels = [priority_names.get(k, str(k)) for k in priority_stats.keys()]
            values = list(priority_stats.values())
            
            fig = px.bar(
                x=labels, y=values,
                title="Уведомления по приоритетам",
                color=labels,
                color_discrete_map={"Низкий": "#FFC107", "Средний": "#FF9800", "Высокий": "#F44336"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о приоритетах")


# Вспомогательные функции

def get_emergency_recipients_count(citizen_model: CitizenModel, recipient_scope: str) -> int:
    """Подсчет получателей экстренного уведомления"""
    
    if recipient_scope in ["🌍 Всем жителям", "Всем жителям"]:
        return citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''")
    elif recipient_scope in ["📱 Только с телефонами", "Только с телефонами"]:
        return citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''")
    elif recipient_scope in ["📍 По районам", "По районам"]:
        # Упрощенная логика для демо
        return citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''") // 2
    else:
        return citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''")


def send_emergency_notification(
    title: str,
    message_text: str,
    emergency_type: str,
    priority: int,
    recipient_scope: str,
    citizen_model: CitizenModel,
    affected_area: Optional[str] = None
) -> bool:
    """Отправка экстренного уведомления"""
    
    try:
        # Получаем список получателей
        recipients = citizen_model.get_citizens_with_phones()
        
        if not recipients:
            return False
        
        # Создаем запись в таблице экстренных SMS
        db = citizen_model.db
        
        emergency_id = db.execute_query("""
            INSERT INTO emergency_sms (title, message_text, emergency_type, priority, affected_area, sent_count, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, message_text, emergency_type, priority, affected_area, len(recipients), get_current_user_id()), fetch=False)
        
        if not emergency_id:
            return False
        
        # В реальной системе здесь был бы вызов SMS API
        # Для демо просто логируем отправку
        for recipient in recipients:
            # Создаем записи в логе SMS
            db.execute_query("""
                INSERT INTO sms_logs (campaign_id, citizen_id, phone, message_text, status, sent_at)
                VALUES (?, ?, ?, ?, 'SENT', ?)
            """, (None, recipient['id'], recipient['phone'], message_text, datetime.now().isoformat()), fetch=False)
        
        return True
        
    except Exception as e:
        return False


def get_recent_emergency_notifications(db: DatabaseManager) -> List[Dict[str, Any]]:
    """Получение последних экстренных уведомлений"""
    
    query = """
        SELECT * FROM emergency_sms
        ORDER BY created_at DESC
        LIMIT 10
    """
    
    result = db.execute_query(query)
    return [dict(row) for row in result] if result else []


def show_emergency_notification_card(emergency: Dict[str, Any]):
    """Отображение карточки экстренного уведомления"""
    
    priority_colors = {1: "#FFC107", 2: "#FF9800", 3: "#F44336"}
    priority_names = {1: "🟡 Низкий", 2: "🟠 Средний", 3: "🔴 Высокий"}
    
    priority = emergency.get('priority', 1)
    priority_color = priority_colors.get(priority, "#999999")
    priority_name = priority_names.get(priority, "⚪ Обычный")
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{emergency['title']}**")
            st.caption(f"📅 {format_datetime(emergency['created_at'])}")
            
            if emergency['affected_area']:
                st.caption(f"📍 {emergency['affected_area']}")
        
        with col2:
            st.markdown(f"""
            <div style="
                background-color: {priority_color};
                color: white;
                padding: 4px 8px;
                border-radius: 10px;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
            ">
                {priority_name}
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.metric("📱 Отправлено", emergency.get('sent_count', 0))
        
        # Предварительный просмотр сообщения
        message_preview = emergency['message_text'][:80]
        if len(emergency['message_text']) > 80:
            message_preview += "..."
        
        st.caption(f"💬 {message_preview}")
        
        st.markdown("---")


def get_filtered_emergency_history(
    db: DatabaseManager,
    period_filter: str,
    type_filter: str,
    priority_filter: str
) -> List[Dict[str, Any]]:
    """Получение отфильтрованной истории экстренных уведомлений"""
    
    where_conditions = []
    params = []
    
    # Фильтр по периоду
    if period_filter == "За неделю":
        where_conditions.append("created_at >= date('now', '-7 days')")
    elif period_filter == "За месяц":
        where_conditions.append("created_at >= date('now', '-30 days')")
    elif period_filter == "За квартал":
        where_conditions.append("created_at >= date('now', '-90 days')")
    
    # Фильтр по типу
    if type_filter != "Все":
        type_map = {
            "Коммунальные услуги": "utilities",
            "Дорожные работы": "road_works",
            "Безопасность": "security",
            "Медицинская": "medical"
        }
        emergency_type = type_map.get(type_filter)
        if emergency_type:
            where_conditions.append("emergency_type = ?")
            params.append(emergency_type)
    
    # Фильтр по приоритету
    if priority_filter != "Все":
        priority_map = {"Низкий": 1, "Средний": 2, "Высокий": 3}
        priority_value = priority_map.get(priority_filter)
        if priority_value:
            where_conditions.append("priority = ?")
            params.append(priority_value)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else ""
    
    query = f"""
        SELECT * FROM emergency_sms
        {f'WHERE {where_clause}' if where_clause else ''}
        ORDER BY created_at DESC
    """
    
    result = db.execute_query(query, tuple(params))
    return [dict(row) for row in result] if result else []


def show_emergency_history_card(emergency: Dict[str, Any]):
    """Отображение карточки в истории экстренных уведомлений"""
    
    priority_icons = {1: "🟡", 2: "🟠", 3: "🔴"}
    priority_names = {1: "Низкий", 2: "Средний", 3: "Высокий"}
    
    priority = emergency.get('priority', 1)
    priority_icon = priority_icons.get(priority, "⚪")
    priority_name = priority_names.get(priority, "Обычный")
    
    with st.expander(f"{priority_icon} {emergency['title']} - {format_datetime(emergency['created_at'])}"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**Сообщение:**")
            st.write(emergency['message_text'])
            
            if emergency['affected_area']:
                st.markdown(f"**Затронутая территория:** {emergency['affected_area']}")
        
        with col2:
            st.metric("Приоритет", priority_name)
            st.metric("Отправлено SMS", emergency.get('sent_count', 0))
            st.metric("Тип", emergency.get('emergency_type', 'Не указан'))


def get_emergency_statistics(db: DatabaseManager) -> Dict[str, Any]:
    """Получение статистики экстренных уведомлений"""
    
    stats = {}
    
    # Общее количество
    total_query = "SELECT COUNT(*) as count FROM emergency_sms"
    total_result = db.execute_query(total_query)
    stats['total_count'] = total_result[0]['count'] if total_result else 0
    
    # За месяц
    monthly_query = "SELECT COUNT(*) as count FROM emergency_sms WHERE created_at >= date('now', '-30 days')"
    monthly_result = db.execute_query(monthly_query)
    stats['monthly_count'] = monthly_result[0]['count'] if monthly_result else 0
    
    # Общее количество отправленных SMS
    sms_query = "SELECT SUM(sent_count) as total FROM emergency_sms"
    sms_result = db.execute_query(sms_query)
    stats['total_sms'] = sms_result[0]['total'] if sms_result and sms_result[0]['total'] else 0
    
    # Среднее время ответа (имитация)
    stats['avg_response_time'] = 2.5  # минуты (для демо)
    
    # Статистика по типам
    type_query = """
        SELECT emergency_type, COUNT(*) as count
        FROM emergency_sms
        GROUP BY emergency_type
    """
    type_result = db.execute_query(type_query)
    if type_result:
        stats['by_type'] = {row['emergency_type']: row['count'] for row in type_result}
    else:
        stats['by_type'] = {}
    
    # Статистика по приоритетам
    priority_query = """
        SELECT priority, COUNT(*) as count
        FROM emergency_sms
        GROUP BY priority
    """
    priority_result = db.execute_query(priority_query)
    if priority_result:
        stats['by_priority'] = {row['priority']: row['count'] for row in priority_result}
    else:
        stats['by_priority'] = {}
    
    return stats