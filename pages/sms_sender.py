"""
Страница SMS-рассылок и уведомлений
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from config.database import DatabaseManager
from config.settings import SMS_TEMPLATES
from models.sms import SMSModel
from models.citizen import CitizenModel
from models.meeting import MeetingModel
from utils.helpers import (
    format_datetime, Paginator, show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission
from utils.validators import validate_sms_data, StreamlitValidationHelper

def show_sms_page():
    """Главная функция страницы SMS-рассылок"""
    
    st.markdown("# 📱 SMS-рассылки и уведомления")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('sms'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Инициализируем модели
    db = DatabaseManager()
    sms_model = SMSModel(db)
    citizen_model = CitizenModel(db)
    meeting_model = MeetingModel(db)
    
    # Боковая панель с действиями
    with st.sidebar:
        st.markdown("### 🔧 Действия")
        
        if st.button("📤 Новая рассылка", use_container_width=True):
            st.session_state.sms_action = "create"
        
        if st.button("📊 Статистика", use_container_width=True):
            st.session_state.sms_action = "stats"
        
        if st.button("📋 Шаблоны", use_container_width=True):
            st.session_state.sms_action = "templates"
        
        st.markdown("---")
        
        # Фильтры
        st.markdown("### 🔍 Фильтры")
        
        search_term = st.text_input(
            "Поиск",
            placeholder="Название кампании...",
            help="Поиск по названию кампании или тексту сообщения"
        )
        
        campaign_type = st.selectbox(
            "Тип кампании",
            ["Все", "Обычная", "Экстренная", "Напоминание"],
            help="Фильтр по типу SMS кампании"
        )
        
        date_filter = st.selectbox(
            "Период",
            ["За неделю", "За месяц", "За квартал", "Все время"],
            help="Фильтр по времени создания"
        )
        
        # Быстрая статистика
        st.markdown("---")
        st.markdown("### 📈 Сводка")
        
        # Получаем быструю статистику
        quick_stats = get_quick_sms_stats(sms_model)
        
        st.metric("📤 Всего кампаний", quick_stats.get('total_campaigns', 0))
        st.metric("📱 SMS за месяц", quick_stats.get('monthly_sms', 0))
        st.metric("✅ Успешных", quick_stats.get('delivered_rate', 0), 
                 delta=f"{quick_stats.get('delivered_percentage', 0):.1f}%")
    
    # Обработка действий
    action = st.session_state.get('sms_action', 'list')
    
    if action == "create":
        show_create_sms_form(sms_model, citizen_model, meeting_model)
    elif action == "view":
        campaign_id = st.session_state.get('view_campaign_id')
        if campaign_id:
            show_campaign_details(sms_model, campaign_id)
        else:
            st.error("ID кампании не найден")
            st.session_state.sms_action = "list"
    elif action == "stats":
        show_sms_statistics(sms_model)
    elif action == "templates":
        show_sms_templates()
    else:
        show_sms_campaigns_list(sms_model, search_term, campaign_type, date_filter)


def show_sms_campaigns_list(
    sms_model: SMSModel,
    search_term: str,
    campaign_type: str,
    date_filter: str
):
    """Отображение списка SMS кампаний"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📋 История SMS-рассылок")
    
    with col2:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Формируем условия поиска
    where_conditions = []
    params = []
    
    # Текстовый поиск
    if search_term:
        search_conditions = [
            "UPPER(title) LIKE UPPER(?)",
            "UPPER(message_text) LIKE UPPER(?)"
        ]
        where_conditions.append(f"({' OR '.join(search_conditions)})")
        search_param = f"%{search_term}%"
        params.extend([search_param] * 2)
    
    # Фильтр по типу кампании
    if campaign_type != "Все":
        type_map = {
            "Обычная": "REGULAR",
            "Экстренная": "EMERGENCY",
            "Напоминание": "REMINDER"
        }
        sms_type = type_map.get(campaign_type)
        if sms_type:
            where_conditions.append("campaign_type = ?")
            params.append(sms_type)
    
    # Фильтр по дате
    date_condition = get_sms_date_filter_condition(date_filter)
    if date_condition:
        where_conditions.append(date_condition)
    
    # Выполняем запрос
    where_clause = " AND ".join(where_conditions) if where_conditions else ""
    campaigns = sms_model.get_all(where_clause, tuple(params), "created_at DESC")
    
    if not campaigns:
        st.info("📱 SMS кампании не найдены по заданным критериям")
        return
    
    # Показываем количество найденных записей
    st.success(f"✅ Найдено кампаний: {len(campaigns)}")
    
    # Пагинация
    paginator = Paginator(campaigns, items_per_page=10)
    current_page = paginator.show_pagination_controls("sms_pagination")
    page_campaigns = paginator.get_page(current_page)
    
    # Отображаем список кампаний
    for campaign in page_campaigns:
        show_campaign_card(campaign, sms_model)


def show_campaign_card(campaign: Dict[str, Any], sms_model: SMSModel):
    """Отображение карточки SMS кампании"""
    
    # Определяем цвета для типов кампаний
    type_colors = {
        'REGULAR': '#2196F3',    # Синий
        'EMERGENCY': '#F44336',  # Красный
        'REMINDER': '#FF9800'    # Оранжевый
    }
    
    type_names = {
        'REGULAR': '📢 Обычная',
        'EMERGENCY': '🚨 Экстренная',
        'REMINDER': '⏰ Напоминание'
    }
    
    campaign_type = campaign['campaign_type']
    type_color = type_colors.get(campaign_type, '#999999')
    type_name = type_names.get(campaign_type, campaign_type)
    
    with st.container():
        # Заголовок кампании
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {campaign['title']}")
            
            # Тип кампании
            st.markdown(f"""
            <div style="
                background-color: {type_color};
                color: white;
                padding: 4px 12px;
                border-radius: 15px;
                display: inline-block;
                font-size: 12px;
                font-weight: bold;
                margin: 5px 0;
            ">
                {type_name}
            </div>
            """, unsafe_allow_html=True)
            
            # Дата создания
            created_at = format_datetime(campaign['created_at'])
            st.caption(f"📅 Создано: {created_at}")
        
        with col2:
            # Статистика отправки
            sent_count = campaign['sent_count'] or 0
            delivered_count = campaign['delivered_count'] or 0
            failed_count = campaign['failed_count'] or 0
            
            st.metric("📤 Отправлено", sent_count)
            
            if sent_count > 0:
                success_rate = (delivered_count / sent_count) * 100
                st.metric("✅ Доставлено", delivered_count, delta=f"{success_rate:.1f}%")
                
                if failed_count > 0:
                    st.metric("❌ Ошибки", failed_count)
        
        with col3:
            # Статус отправки
            if campaign['sent_at']:
                st.success("✅ Отправлено")
                sent_at = format_datetime(campaign['sent_at'])
                st.caption(f"Время: {sent_at}")
            elif campaign['scheduled_at']:
                st.info("⏱️ Запланировано")
                scheduled_at = format_datetime(campaign['scheduled_at'])
                st.caption(f"На: {scheduled_at}")
            else:
                st.warning("📝 Черновик")
        
        # Текст сообщения
        message_preview = campaign['message_text'][:100]
        if len(campaign['message_text']) > 100:
            message_preview += "..."
        
        with st.expander("💬 Текст сообщения"):
            st.write(campaign['message_text'])
            st.caption(f"Длина: {len(campaign['message_text'])} символов")
        
        # Кнопки действий
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("👁️ Подробнее", key=f"view_{campaign['id']}"):
                st.session_state.sms_action = "view"
                st.session_state.view_campaign_id = campaign['id']
                st.rerun()
        
        with col2:
            if not campaign['sent_at']:
                if st.button("📤 Отправить", key=f"send_{campaign['id']}"):
                    send_campaign_now(sms_model, campaign['id'])
        
        with col3:
            if campaign['sent_at']:
                if st.button("📊 Статистика", key=f"stats_{campaign['id']}"):
                    show_campaign_stats_modal(sms_model, campaign['id'])
        
        with col4:
            if st.button("🗑️ Удалить", key=f"delete_{campaign['id']}"):
                if st.session_state.get(f"confirm_delete_sms_{campaign['id']}"):
                    success = sms_model.delete(campaign['id'])
                    if success:
                        show_success_message("SMS кампания удалена")
                        st.rerun()
                    else:
                        show_error_message("Ошибка при удалении кампании")
                else:
                    st.session_state[f"confirm_delete_sms_{campaign['id']}"] = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения удаления")
        
        st.markdown("---")


def show_create_sms_form(sms_model: SMSModel, citizen_model: CitizenModel, meeting_model: MeetingModel):
    """Форма создания новой SMS рассылки"""
    
    st.markdown("### 📤 Создание SMS-рассылки")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.sms_action = "list"
            st.rerun()
    
    # Выбор типа рассылки
    col1, col2 = st.columns(2)
    
    with col1:
        sms_type = st.selectbox(
            "Тип рассылки",
            ["Обычная рассылка", "Уведомление о заседании", "Использовать шаблон"],
            help="Выберите тип SMS рассылки"
        )
    
    with col2:
        if sms_type == "Уведомление о заседании":
            # Получаем предстоящие заседания
            upcoming_meetings = meeting_model.get_upcoming_meetings(30)
            
            if upcoming_meetings:
                meeting_options = {}
                for meeting in upcoming_meetings:
                    meeting_date = format_datetime(meeting['meeting_date'])
                    meeting_options[meeting['id']] = f"{meeting['title']} ({meeting_date})"
                
                selected_meeting_id = st.selectbox(
                    "Выберите заседание",
                    options=list(meeting_options.keys()),
                    format_func=lambda x: meeting_options[x],
                    help="Заседание для уведомления"
                )
            else:
                st.warning("Нет предстоящих заседаний")
                selected_meeting_id = None
        elif sms_type == "Использовать шаблон":
            template_name = st.selectbox(
                "Выберите шаблон",
                options=list(SMS_TEMPLATES.keys()),
                format_func=lambda x: x.replace('_', ' ').title(),
                help="Готовые шаблоны сообщений"
            )
    
    with st.form("create_sms_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Заголовок кампании
            title = st.text_input(
                "Название кампании *",
                placeholder="Например: Уведомление о субботнике",
                help="Краткое описание рассылки для внутреннего использования"
            )
            
            # Текст сообщения
            if sms_type == "Уведомление о заседании" and 'selected_meeting_id' in locals() and selected_meeting_id:
                # Предзаполняем текст для уведомления о заседании
                meeting = meeting_model.get_by_id(selected_meeting_id)
                if meeting:
                    default_message = create_meeting_notification_text(meeting)
                else:
                    default_message = ""
            elif sms_type == "Использовать шаблон":
                # Используем выбранный шаблон
                default_message = SMS_TEMPLATES.get(template_name, "")
            else:
                default_message = ""
            
            message_text = st.text_area(
                "Текст сообщения *",
                value=default_message,
                height=150,
                max_chars=160,
                help="Максимум 160 символов. Используйте переменные: {date}, {time}, {location}"
            )
            
            # Счетчик символов
            char_count = len(message_text)
            color = "red" if char_count > 160 else "orange" if char_count > 140 else "green"
            st.markdown(f"<p style='color: {color}; font-size: 12px;'>Символов: {char_count}/160</p>", 
                       unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 👥 Получатели")
            
            # Выбор получателей
            recipient_type = st.radio(
                "Кому отправить:",
                ["Всем гражданам", "Только с телефонами", "По возрасту", "Выборочно"],
                help="Выберите группу получателей"
            )
            
            if recipient_type == "По возрасту":
                age_group = st.selectbox(
                    "Возрастная группа",
                    ["18-30 лет", "31-50 лет", "51-70 лет", "70+ лет"]
                )
            elif recipient_type == "Выборочно":
                st.info("Функция выборочной отправки будет доступна после создания кампании")
            
            # Предварительный подсчет получателей
            recipient_count = get_recipients_count(citizen_model, recipient_type)
            st.metric("📱 Получателей", recipient_count)
            
            # Планирование отправки
            st.markdown("#### ⏰ Время отправки")
            
            send_now = st.checkbox("Отправить сейчас", value=True)
            
            if not send_now:
                scheduled_date = st.date_input(
                    "Дата отправки",
                    min_value=date.today(),
                    value=date.today()
                )
                
                scheduled_time = st.time_input(
                    "Время отправки",
                    value=datetime.now().time()
                )
        
        # Кнопки
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("📤 Создать и отправить" if send_now else "📝 Создать кампанию", 
                                            use_container_width=True)
        
        with col2:
            preview = st.form_submit_button("👁️ Предварительный просмотр", use_container_width=True)
        
        if preview:
            show_sms_preview(message_text, recipient_count)
        
        if submitted:
            # Подготавливаем данные кампании
            campaign_data = {
                'title': title.strip() if title else '',
                'message_text': message_text.strip() if message_text else ''
            }
            
            # Валидация
            if StreamlitValidationHelper.validate_and_show(campaign_data, validate_sms_data):
                # Определяем время отправки
                scheduled_at = None
                if not send_now:
                    scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
                    scheduled_at = scheduled_datetime
                
                # Создаем кампанию
                campaign_id = sms_model.create_campaign(
                    title=campaign_data['title'],
                    message_text=campaign_data['message_text'],
                    campaign_type='REMINDER' if sms_type == "Уведомление о заседании" else 'REGULAR',
                    scheduled_at=scheduled_at,
                    created_by=get_current_user_id()
                )
                
                if campaign_id:
                    if send_now:
                        # Отправляем сразу
                        recipients = get_recipients_list(citizen_model, recipient_type)
                        result = sms_model.send_campaign(campaign_id, recipients)
                        
                        if result['success']:
                            show_success_message(
                                f"SMS кампания создана и отправлена! "
                                f"Доставлено: {result['sent_count']}, "
                                f"Ошибок: {result['failed_count']}"
                            )
                        else:
                            show_error_message(f"Ошибка отправки: {result.get('error', 'Неизвестная ошибка')}")
                    else:
                        show_success_message("SMS кампания успешно создана и запланирована!")
                    
                    st.session_state.sms_action = "list"
                    st.rerun()
                else:
                    show_error_message("Ошибка при создании SMS кампании")


def show_campaign_details(sms_model: SMSModel, campaign_id: int):
    """Подробная информация о SMS кампании"""
    
    st.markdown("### 👁️ Детали SMS кампании")
    
    campaign = sms_model.get_by_id(campaign_id)
    if not campaign:
        st.error("SMS кампания не найдена")
        st.session_state.sms_action = "list"
        return
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.sms_action = "list"
            st.rerun()
    
    with col2:
        st.info(f"Кампания: {campaign['title']}")
    
    # Основная информация
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📋 Основная информация")
        st.write(f"**Название:** {campaign['title']}")
        st.write(f"**Тип:** {get_campaign_type_name(campaign['campaign_type'])}")
        st.write(f"**Создано:** {format_datetime(campaign['created_at'])}")
        
        if campaign['sent_at']:
            st.write(f"**Отправлено:** {format_datetime(campaign['sent_at'])}")
        elif campaign['scheduled_at']:
            st.write(f"**Запланировано:** {format_datetime(campaign['scheduled_at'])}")
    
    with col2:
        st.markdown("#### 📊 Статистика")
        st.metric("📤 Отправлено", campaign['sent_count'] or 0)
        st.metric("✅ Доставлено", campaign['delivered_count'] or 0)
        st.metric("❌ Ошибки", campaign['failed_count'] or 0)
        
        # Процент успешности
        if campaign['sent_count'] and campaign['sent_count'] > 0:
            success_rate = (campaign['delivered_count'] or 0) / campaign['sent_count'] * 100
            st.metric("📈 Успешность", f"{success_rate:.1f}%")
    
    with col3:
        st.markdown("#### 💬 Сообщение")
        st.text_area("Текст:", value=campaign['message_text'], height=150, disabled=True)
        st.caption(f"Длина: {len(campaign['message_text'])} символов")
    
    # Журнал отправки
    st.markdown("---")
    st.markdown("#### 📋 Журнал отправки")
    
    # Получаем логи отправки
    logs_query = """
        SELECT sl.*, c.full_name
        FROM sms_logs sl
        LEFT JOIN citizens c ON sl.citizen_id = c.id
        WHERE sl.campaign_id = ?
        ORDER BY sl.created_at DESC
    """
    
    logs = sms_model.db.execute_query(logs_query, (campaign_id,))
    
    if logs:
        # Фильтры для логов
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Фильтр по статусу",
                ["Все", "Отправлено", "Доставлено", "Ошибка"]
            )
        
        with col2:
            search_phone = st.text_input("Поиск по телефону")
        
        # Фильтруем логи
        filtered_logs = filter_sms_logs(logs, status_filter, search_phone)
        
        if filtered_logs:
            # Отображаем логи в таблице
            df_logs = pd.DataFrame([dict(log) for log in filtered_logs])
            
            # Переименовываем колонки
            column_config = {
                "full_name": "ФИО",
                "phone": "Телефон",
                "status": "Статус",
                "sent_at": "Время отправки",
                "error_message": "Ошибка"
            }
            
            st.dataframe(
                df_logs[list(column_config.keys())].rename(columns=column_config),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Нет записей для отображения")
    else:
        st.info("Журнал отправки пуст")


def show_sms_statistics(sms_model: SMSModel):
    """Статистика SMS рассылок"""
    
    st.markdown("### 📊 Статистика SMS-рассылок")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.sms_action = "list"
            st.rerun()
    
    # Общая статистика
    stats = get_comprehensive_sms_stats(sms_model)
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📤 Всего кампаний", stats.get('total_campaigns', 0))
    
    with col2:
        st.metric("📱 Всего SMS", stats.get('total_sms', 0))
    
    with col3:
        delivery_rate = stats.get('delivery_rate', 0)
        st.metric("📈 Доставляемость", f"{delivery_rate:.1f}%")
    
    with col4:
        st.metric("📅 За месяц", stats.get('monthly_campaigns', 0))
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # Статистика по типам кампаний
        type_stats = stats.get('by_type', {})
        if type_stats:
            st.markdown("#### 📋 Кампании по типам")
            
            type_names = {
                'REGULAR': 'Обычные',
                'EMERGENCY': 'Экстренные',
                'REMINDER': 'Напоминания'
            }
            
            import plotly.express as px
            
            labels = [type_names.get(k, k) for k in type_stats.keys()]
            values = list(type_stats.values())
            
            fig = px.pie(
                values=values,
                names=labels,
                title="Распределение по типам"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о типах кампаний")
    
    with col2:
        # Динамика отправки SMS
        monthly_data = get_monthly_sms_data(sms_model)
        if monthly_data:
            st.markdown("#### 📈 Динамика отправки")
            
            df = pd.DataFrame(monthly_data)
            
            import plotly.express as px
            fig = px.bar(
                df, x='month', y='count',
                title="SMS по месяцам",
                labels={'month': 'Месяц', 'count': 'Количество SMS'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных для отображения динамики")


def show_sms_templates():
    """Отображение и управление шаблонами SMS"""
    
    st.markdown("### 📋 Шаблоны SMS сообщений")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.sms_action = "list"
            st.rerun()
    
    st.markdown("Готовые шаблоны для быстрого создания SMS-рассылок:")
    
    # Отображаем все доступные шаблоны
    for template_key, template_text in SMS_TEMPLATES.items():
        template_name = template_key.replace('_', ' ').title()
        
        with st.expander(f"📄 {template_name}"):
            st.code(template_text, language="text")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"📝 Использовать", key=f"use_{template_key}"):
                    # Переходим к созданию рассылки с этим шаблоном
                    st.session_state.sms_action = "create"
                    st.session_state.selected_template = template_key
                    st.rerun()
            
            with col2:
                st.caption("Переменные: {date}, {time}, {location}, {reason}")


# Вспомогательные функции

def get_quick_sms_stats(sms_model: SMSModel) -> Dict[str, Any]:
    """Получение быстрой статистики SMS"""
    
    # Общее количество кампаний
    total_campaigns = sms_model.count()
    
    # Кампании за месяц
    monthly_campaigns = sms_model.count("created_at >= date('now', '-30 days')")
    
    # Статистика доставки
    delivery_query = """
        SELECT 
            COUNT(*) as total_sms,
            SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) as delivered
        FROM sms_logs
    """
    
    result = sms_model.db.execute_query(delivery_query)
    
    if result:
        total_sms = result[0]['total_sms']
        delivered = result[0]['delivered']
        delivery_rate = (delivered / total_sms * 100) if total_sms > 0 else 0
    else:
        total_sms = 0
        delivered = 0
        delivery_rate = 0
    
    return {
        'total_campaigns': total_campaigns,
        'monthly_campaigns': monthly_campaigns,
        'monthly_sms': total_sms,  # Упрощено для демо
        'delivered_rate': delivered,
        'delivered_percentage': delivery_rate
    }


def get_comprehensive_sms_stats(sms_model: SMSModel) -> Dict[str, Any]:
    """Получение подробной статистики SMS"""
    
    stats = {}
    
    # Общее количество кампаний
    stats['total_campaigns'] = sms_model.count()
    
    # Кампании за месяц
    stats['monthly_campaigns'] = sms_model.count("created_at >= date('now', '-30 days')")
    
    # Статистика по типам
    type_query = """
        SELECT campaign_type, COUNT(*) as count
        FROM sms_campaigns
        GROUP BY campaign_type
    """
    
    type_result = sms_model.db.execute_query(type_query)
    if type_result:
        stats['by_type'] = {row['campaign_type']: row['count'] for row in type_result}
    else:
        stats['by_type'] = {}
    
    # Общая статистика SMS
    sms_stats_query = """
        SELECT 
            COUNT(*) as total_sms,
            SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) as delivered,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed
        FROM sms_logs
    """
    
    sms_result = sms_model.db.execute_query(sms_stats_query)
    if sms_result:
        total_sms = sms_result[0]['total_sms']
        delivered = sms_result[0]['delivered']
        
        stats['total_sms'] = total_sms
        stats['delivery_rate'] = (delivered / total_sms * 100) if total_sms > 0 else 0
    else:
        stats['total_sms'] = 0
        stats['delivery_rate'] = 0
    
    return stats


def get_sms_date_filter_condition(date_filter: str) -> str:
    """Получение условия для фильтрации по дате"""
    
    conditions = {
        "За неделю": "created_at >= date('now', '-7 days')",
        "За месяц": "created_at >= date('now', '-30 days')",
        "За квартал": "created_at >= date('now', '-90 days')"
    }
    
    return conditions.get(date_filter, "")


def get_monthly_sms_data(sms_model: SMSModel) -> List[Dict[str, Any]]:
    """Получение данных по SMS за последние месяцы"""
    
    query = """
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as count
        FROM sms_logs 
        WHERE created_at >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month
    """
    
    result = sms_model.db.execute_query(query)
    
    if result:
        data = []
        for row in result:
            month_str = row['month']
            try:
                month_date = datetime.strptime(month_str, '%Y-%m')
                month_name = month_date.strftime('%b %Y')
            except:
                month_name = month_str
            
            data.append({
                'month': month_name,
                'count': row['count']
            })
        
        return data
    
    return []


def get_recipients_count(citizen_model: CitizenModel, recipient_type: str) -> int:
    """Подсчет количества получателей"""
    
    if recipient_type == "Всем гражданам":
        return citizen_model.count("is_active = 1")
    elif recipient_type == "Только с телефонами":
        return citizen_model.count("is_active = 1 AND phone IS NOT NULL AND phone != ''")
    elif recipient_type == "По возрасту":
        # Упрощенный подсчет для демо
        return citizen_model.count("is_active = 1 AND birth_date IS NOT NULL")
    else:
        return 0


def get_recipients_list(citizen_model: CitizenModel, recipient_type: str) -> List[Dict[str, Any]]:
    """Получение списка получателей"""
    
    if recipient_type == "Только с телефонами":
        citizens = citizen_model.get_citizens_with_phones()
    else:
        citizens = citizen_model.get_active_citizens()
    
    recipients = []
    for citizen in citizens:
        if citizen['phone']:
            recipients.append({
                'citizen_id': citizen['id'],
                'phone': citizen['phone'],
                'full_name': citizen['full_name']
            })
    
    return recipients


def create_meeting_notification_text(meeting: Dict[str, Any]) -> str:
    """Создание текста уведомления о заседании"""
    
    meeting_date = format_datetime(meeting['meeting_date'], 'short')
    meeting_time = meeting['meeting_time'] or "10:00"
    location = meeting['location'] or "Здание махалли"
    
    return f"""Уважаемые жители!
{meeting_date} в {meeting_time} состоится заседание махалли.
Тема: {meeting['title']}
Место: {location}
Ваше участие важно!"""


def show_sms_preview(message_text: str, recipient_count: int):
    """Предварительный просмотр SMS"""
    
    st.markdown("#### 👁️ Предварительный просмотр")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Текст сообщения:**")
        st.text_area("", value=message_text, height=100, disabled=True)
        
        char_count = len(message_text)
        sms_count = (char_count + 159) // 160  # Количество SMS частей
        
        st.caption(f"Символов: {char_count}/160 | SMS частей: {sms_count}")
    
    with col2:
        st.markdown("**Информация:**")
        st.metric("👥 Получателей", recipient_count)
        st.metric("📱 SMS частей", sms_count)
        
        # Примерная стоимость (для демо)
        estimated_cost = recipient_count * sms_count * 25  # 25 сум за SMS
        st.metric("💰 Примерная стоимость", f"{estimated_cost} сум")


def send_campaign_now(sms_model: SMSModel, campaign_id: int):
    """Отправка кампании прямо сейчас"""
    
    # Получаем список получателей (упрощенная версия)
    from models.citizen import CitizenModel
    
    db = DatabaseManager()
    citizen_model = CitizenModel(db)
    
    recipients = get_recipients_list(citizen_model, "Только с телефонами")
    
    if not recipients:
        show_error_message("Нет получателей с номерами телефонов")
        return
    
    # Отправляем
    result = sms_model.send_campaign(campaign_id, recipients)
    
    if result['success']:
        show_success_message(
            f"SMS кампания отправлена! "
            f"Доставлено: {result['sent_count']}, "
            f"Ошибок: {result['failed_count']}"
        )
        st.rerun()
    else:
        show_error_message(f"Ошибка отправки: {result.get('error', 'Неизвестная ошибка')}")


def show_campaign_stats_modal(sms_model: SMSModel, campaign_id: int):
    """Модальное окно со статистикой кампании"""
    
    # В Streamlit нет модальных окон, показываем в sidebar
    with st.sidebar:
        st.markdown("### 📊 Статистика кампании")
        
        # Получаем статистику
        campaign = sms_model.get_by_id(campaign_id)
        if campaign:
            st.metric("📤 Отправлено", campaign['sent_count'] or 0)
            st.metric("✅ Доставлено", campaign['delivered_count'] or 0)
            st.metric("❌ Ошибки", campaign['failed_count'] or 0)
            
            if campaign['sent_count'] and campaign['sent_count'] > 0:
                success_rate = (campaign['delivered_count'] or 0) / campaign['sent_count'] * 100
                st.metric("📈 Успешность", f"{success_rate:.1f}%")


def filter_sms_logs(logs: List[Dict], status_filter: str, search_phone: str) -> List[Dict]:
    """Фильтрация логов SMS"""
    
    filtered = logs
    
    # Фильтр по статусу
    if status_filter != "Все":
        status_map = {
            "Отправлено": "SENT",
            "Доставлено": "DELIVERED", 
            "Ошибка": "FAILED"
        }
        target_status = status_map.get(status_filter)
        if target_status:
            filtered = [log for log in filtered if log['status'] == target_status]
    
    # Поиск по телефону
    if search_phone:
        filtered = [log for log in filtered if search_phone in (log['phone'] or '')]
    
    return filtered


def get_campaign_type_name(campaign_type: str) -> str:
    """Получение читаемого названия типа кампании"""
    
    type_names = {
        'REGULAR': '📢 Обычная рассылка',
        'EMERGENCY': '🚨 Экстренное уведомление',
        'REMINDER': '⏰ Напоминание'
    }
    
    return type_names.get(campaign_type, campaign_type)