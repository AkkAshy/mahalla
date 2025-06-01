"""
Страница управления заседаниями махалли
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from config.database import DatabaseManager
from models.meeting import MeetingModel
from models.citizen import CitizenModel
from models.points import PointsModel
from utils.helpers import (
    format_date, format_datetime, Paginator,
    create_excel_download_button, show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission
from utils.validators import validate_meeting_data, StreamlitValidationHelper

def show_meetings_page():
    """Главная функция страницы заседаний"""
    
    st.markdown("# 🏛️ Управление заседаниями")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('meetings'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Инициализируем модели
    db = DatabaseManager()
    meeting_model = MeetingModel(db)
    citizen_model = CitizenModel(db)
    points_model = PointsModel(db)
    
    # Боковая панель с действиями
    with st.sidebar:
        st.markdown("### 🔧 Действия")
        
        if st.button("➕ Создать заседание", use_container_width=True):
            st.session_state.meeting_action = "add"
        
        if st.button("📊 Статистика", use_container_width=True):
            st.session_state.meeting_action = "stats"
        
        if st.button("📥 Экспорт данных", use_container_width=True):
            st.session_state.meeting_action = "export"
        
        st.markdown("---")
        
        # Фильтры
        st.markdown("### 🔍 Фильтры")
        
        search_term = st.text_input(
            "Поиск",
            placeholder="Название заседания...",
            help="Поиск по названию, месту проведения или повестке дня"
        )
        
        status_filter = st.selectbox(
            "Статус",
            ["Все", "Запланировано", "Проведено", "Отменено"],
            help="Фильтр по статусу заседания"
        )
        
        # Фильтр по дате
        date_filter = st.selectbox(
            "Период",
            ["Все", "Предстоящие", "За месяц", "За квартал", "За год"],
            help="Фильтр по временному периоду"
        )
    
    # Обработка действий
    action = st.session_state.get('meeting_action', 'list')
    
    if action == "add":
        show_add_meeting_form(meeting_model)
    elif action == "edit":
        meeting_id = st.session_state.get('edit_meeting_id')
        if meeting_id:
            show_edit_meeting_form(meeting_model, meeting_id)
        else:
            st.error("ID заседания не найден")
            st.session_state.meeting_action = "list"
    elif action == "attendance":
        meeting_id = st.session_state.get('attendance_meeting_id')
        if meeting_id:
            show_attendance_management(meeting_model, citizen_model, points_model, meeting_id)
        else:
            st.error("ID заседания не найден")
            st.session_state.meeting_action = "list"
    elif action == "stats":
        show_meetings_statistics(meeting_model)
    elif action == "export":
        handle_meetings_export(meeting_model)
    else:
        show_meetings_list(meeting_model, search_term, status_filter, date_filter)


def show_meetings_list(
    meeting_model: MeetingModel,
    search_term: str,
    status_filter: str,
    date_filter: str
):
    """Отображение списка заседаний с фильтрацией"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📋 Список заседаний")
    
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
            "UPPER(location) LIKE UPPER(?)",
            "UPPER(agenda) LIKE UPPER(?)"
        ]
        where_conditions.append(f"({' OR '.join(search_conditions)})")
        search_param = f"%{search_term}%"
        params.extend([search_param] * 3)
    
    # Фильтр по статусу
    if status_filter != "Все":
        status_map = {
            "Запланировано": "PLANNED",
            "Проведено": "COMPLETED",
            "Отменено": "CANCELLED"
        }
        status = status_map.get(status_filter)
        if status:
            where_conditions.append("status = ?")
            params.append(status)
    
    # Фильтр по дате
    date_condition = get_date_filter_condition(date_filter)
    if date_condition:
        where_conditions.append(date_condition)
    
    # Выполняем запрос
    where_clause = " AND ".join(where_conditions) if where_conditions else ""
    meetings = meeting_model.get_all(where_clause, tuple(params), "meeting_date DESC")
    
    if not meetings:
        st.info("🏛️ Заседания не найдены по заданным критериям")
        return
    
    # Показываем количество найденных записей
    st.success(f"✅ Найдено заседаний: {len(meetings)}")
    
    # Пагинация
    paginator = Paginator(meetings, items_per_page=10)
    current_page = paginator.show_pagination_controls("meetings_pagination")
    page_meetings = paginator.get_page(current_page)
    
    # Отображаем список заседаний
    for meeting in page_meetings:
        show_meeting_card(meeting, meeting_model)


def show_meeting_card(meeting: Dict[str, Any], meeting_model: MeetingModel):
    """Отображение карточки заседания"""
    
    # Определяем цвет статуса
    status_colors = {
        'PLANNED': '#2196F3',    # Синий
        'COMPLETED': '#4CAF50',  # Зеленый
        'CANCELLED': '#F44336'   # Красный
    }
    
    status_names = {
        'PLANNED': '🔵 Запланировано',
        'COMPLETED': '✅ Проведено',
        'CANCELLED': '❌ Отменено'
    }
    
    status = meeting['status']
    status_color = status_colors.get(status, '#999999')
    status_name = status_names.get(status, status)
    
    with st.container():
        # Заголовок с датой
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {meeting['title']}")
            
            meeting_date = format_date(meeting['meeting_date'], 'long')
            meeting_time = meeting['meeting_time'] or "Время не указано"
            st.markdown(f"📅 **{meeting_date}** в **{meeting_time}**")
            
            if meeting['location']:
                st.markdown(f"📍 {meeting['location']}")
        
        with col2:
            st.markdown(f"""
            <div style="
                background-color: {status_color};
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                text-align: center;
                font-weight: bold;
                margin: 10px 0;
            ">
                {status_name}
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Посещаемость
            if meeting['total_invited'] > 0:
                attendance_rate = (meeting['attendance_count'] / meeting['total_invited']) * 100
                st.metric(
                    "Посещаемость",
                    f"{meeting['attendance_count']}/{meeting['total_invited']}",
                    delta=f"{attendance_rate:.1f}%"
                )
            else:
                st.metric("Посещаемость", "0/0", delta="0%")
        
        # Повестка дня
        if meeting['agenda']:
            with st.expander("📋 Повестка дня"):
                st.write(meeting['agenda'])
        
        # Кнопки действий
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("✏️ Редактировать", key=f"edit_{meeting['id']}"):
                st.session_state.meeting_action = "edit"
                st.session_state.edit_meeting_id = meeting['id']
                st.rerun()
        
        with col2:
            if st.button("👥 Посещаемость", key=f"attendance_{meeting['id']}"):
                st.session_state.meeting_action = "attendance"
                st.session_state.attendance_meeting_id = meeting['id']
                st.rerun()
        
        with col3:
            if status == 'PLANNED':
                if st.button("✅ Завершить", key=f"complete_{meeting['id']}"):
                    success = meeting_model.complete_meeting(meeting['id'])
                    if success:
                        show_success_message("Заседание отмечено как завершенное")
                        st.rerun()
                    else:
                        show_error_message("Ошибка при завершении заседания")
        
        with col4:
            if status == 'PLANNED':
                if st.button("❌ Отменить", key=f"cancel_{meeting['id']}"):
                    success = meeting_model.cancel_meeting(meeting['id'], "Отменено через интерфейс")
                    if success:
                        show_success_message("Заседание отменено")
                        st.rerun()
                    else:
                        show_error_message("Ошибка при отмене заседания")
        
        with col5:
            if st.button("🗑️ Удалить", key=f"delete_{meeting['id']}"):
                if st.session_state.get(f"confirm_delete_meeting_{meeting['id']}"):
                    success = meeting_model.delete(meeting['id'])
                    if success:
                        show_success_message("Заседание удалено")
                        st.rerun()
                    else:
                        show_error_message("Ошибка при удалении заседания")
                else:
                    st.session_state[f"confirm_delete_meeting_{meeting['id']}"] = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения удаления")
        
        st.markdown("---")


def show_add_meeting_form(meeting_model: MeetingModel):
    """Форма создания нового заседания"""
    
    st.markdown("### ➕ Создание нового заседания")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.meeting_action = "list"
            st.rerun()
    
    with st.form("add_meeting_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "Название заседания *",
                placeholder="Общее собрание жителей махалли",
                help="Краткое описание заседания"
            )
            
            meeting_date = st.date_input(
                "Дата проведения *",
                value=date.today() + timedelta(days=7),
                min_value=date.today(),
                help="Дата проведения заседания"
            )
            
            meeting_time = st.time_input(
                "Время проведения",
                value=datetime.strptime("10:00", "%H:%M").time(),
                help="Время начала заседания"
            )
            
            location = st.text_input(
                "Место проведения",
                placeholder="Здание махалли, зал заседаний",
                help="Адрес или описание места проведения"
            )
        
        with col2:
            agenda = st.text_area(
                "Повестка дня *",
                placeholder="1. Обсуждение вопросов благоустройства\n2. Планы на следующий месяц\n3. Разное",
                height=200,
                help="Подробная повестка дня заседания"
            )
        
        submitted = st.form_submit_button("📅 Создать заседание", use_container_width=True)
        
        if submitted:
            # Подготавливаем данные
            meeting_data = {
                'title': title.strip() if title else '',
                'meeting_date': meeting_date,
                'meeting_time': meeting_time.strftime("%H:%M") if meeting_time else None,
                'location': location.strip() if location else '',
                'agenda': agenda.strip() if agenda else ''
            }
            
            # Валидация
            if StreamlitValidationHelper.validate_and_show(meeting_data, validate_meeting_data):
                # Создаем заседание
                meeting_id = meeting_model.create_meeting(
                    title=meeting_data['title'],
                    meeting_date=meeting_data['meeting_date'],
                    meeting_time=meeting_data['meeting_time'],
                    location=meeting_data['location'],
                    agenda=meeting_data['agenda'],
                    created_by=get_current_user_id()
                )
                
                if meeting_id:
                    show_success_message(f"Заседание '{title}' успешно создано!")
                    st.session_state.meeting_action = "list"
                    st.rerun()
                else:
                    show_error_message("Ошибка при создании заседания")


def show_edit_meeting_form(meeting_model: MeetingModel, meeting_id: int):
    """Форма редактирования заседания"""
    
    st.markdown("### ✏️ Редактирование заседания")
    
    # Получаем данные заседания
    meeting = meeting_model.get_by_id(meeting_id)
    if not meeting:
        st.error("Заседание не найдено")
        st.session_state.meeting_action = "list"
        return
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.meeting_action = "list"
            st.rerun()
    
    with col2:
        st.info(f"Редактирование: {meeting['title']}")
    
    with st.form("edit_meeting_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "Название заседания *",
                value=meeting['title'],
                help="Краткое описание заседания"
            )
            
            current_date = datetime.strptime(meeting['meeting_date'], '%Y-%m-%d').date()
            meeting_date = st.date_input(
                "Дата проведения *",
                value=current_date,
                help="Дата проведения заседания"
            )
            
            current_time = None
            if meeting['meeting_time']:
                try:
                    current_time = datetime.strptime(meeting['meeting_time'], '%H:%M').time()
                except:
                    pass
            
            meeting_time = st.time_input(
                "Время проведения",
                value=current_time or datetime.strptime("10:00", "%H:%M").time(),
                help="Время начала заседания"
            )
            
            location = st.text_input(
                "Место проведения",
                value=meeting['location'] or '',
                help="Адрес или описание места проведения"
            )
        
        with col2:
            agenda = st.text_area(
                "Повестка дня *",
                value=meeting['agenda'] or '',
                height=200,
                help="Подробная повестка дня заседания"
            )
        
        submitted = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
        
        if submitted:
            # Подготавливаем данные для обновления
            update_data = {
                'title': title.strip(),
                'meeting_date': meeting_date,
                'meeting_time': meeting_time.strftime("%H:%M"),
                'location': location.strip(),
                'agenda': agenda.strip()
            }
            
            # Валидация
            if StreamlitValidationHelper.validate_and_show(update_data, validate_meeting_data):
                # Обновляем данные
                success = meeting_model.update_meeting(meeting_id, **update_data)
                
                if success:
                    show_success_message("Заседание успешно обновлено!")
                    st.session_state.meeting_action = "list"
                    st.rerun()
                else:
                    show_error_message("Ошибка при обновлении заседания")


def show_attendance_management(
    meeting_model: MeetingModel,
    citizen_model: CitizenModel,
    points_model: PointsModel,
    meeting_id: int
):
    """Управление посещаемостью заседания"""
    
    st.markdown("### 👥 Управление посещаемостью")
    
    # Получаем данные заседания
    meeting_data = meeting_model.get_meeting_with_attendance(meeting_id)
    if not meeting_data:
        st.error("Заседание не найдено")
        st.session_state.meeting_action = "list"
        return
    
    meeting = meeting_data['meeting']
    attendance_list = meeting_data['attendance']
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.meeting_action = "list"
            st.rerun()
    
    with col2:
        st.info(f"Заседание: {meeting['title']} ({format_date(meeting['meeting_date'])})")
    
    # Статистика посещаемости
    col1, col2, col3 = st.columns(3)
    
    total_citizens = len(attendance_list)
    present_count = sum(1 for a in attendance_list if a['is_present'])
    attendance_rate = (present_count / total_citizens * 100) if total_citizens > 0 else 0
    
    with col1:
        st.metric("👥 Всего граждан", total_citizens)
    
    with col2:
        st.metric("✅ Присутствуют", present_count)
    
    with col3:
        st.metric("📊 Посещаемость", f"{attendance_rate:.1f}%")
    
    st.markdown("---")
    
    # Быстрые действия
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Отметить всех присутствующими"):
            mark_all_present(meeting_model, points_model, meeting_id, attendance_list)
            st.rerun()
    
    with col2:
        if st.button("❌ Отметить всех отсутствующими"):
            mark_all_absent(meeting_model, meeting_id, attendance_list)
            st.rerun()
    
    with col3:
        if st.button("🏆 Начислить баллы присутствующим"):
            award_points_to_present(points_model, meeting_id, attendance_list)
            st.rerun()
    
    st.markdown("---")
    
    # Список граждан с возможностью отметки посещаемости
    st.markdown("### 📋 Список участников")
    
    # Фильтр
    filter_option = st.selectbox(
        "Показать:",
        ["Всех", "Только присутствующих", "Только отсутствующих"]
    )
    
    # Фильтруем список
    filtered_attendance = attendance_list
    if filter_option == "Только присутствующих":
        filtered_attendance = [a for a in attendance_list if a['is_present']]
    elif filter_option == "Только отсутствующих":
        filtered_attendance = [a for a in attendance_list if not a['is_present']]
    
    # Отображаем список
    for attendance in filtered_attendance:
        show_attendance_row(attendance, meeting_model, points_model, meeting_id)


def show_attendance_row(
    attendance: Dict[str, Any],
    meeting_model: MeetingModel,
    points_model: PointsModel,
    meeting_id: int
):
    """Отображение строки с участником и возможностью отметки"""
    
    citizen_id = attendance['citizen_id']
    is_present = bool(attendance['is_present'])
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{attendance['full_name']}**")
            if attendance['phone']:
                st.caption(f"📞 {attendance['phone']}")
        
        with col2:
            # Статус присутствия
            if is_present:
                st.success("✅ Присутствует")
            else:
                st.error("❌ Отсутствует")
        
        with col3:
            # Кнопка переключения статуса
            button_text = "❌ Отметить отсутствующим" if is_present else "✅ Отметить присутствующим"
            if st.button(button_text, key=f"toggle_{citizen_id}"):
                toggle_attendance(meeting_model, meeting_id, citizen_id, not is_present)
                st.rerun()
        
        with col4:
            # Информация о баллах
            if attendance['points_earned']:
                st.info(f"🏆 {attendance['points_earned']} баллов")
            elif is_present:
                if st.button("🏆 Начислить баллы", key=f"award_{citizen_id}"):
                    points_model.award_points(
                        citizen_id=citizen_id,
                        activity_type='meeting_attendance',
                        description=f"Посещение заседания",
                        meeting_id=meeting_id,
                        created_by=get_current_user_id()
                    )
                    st.rerun()
        
        st.markdown("---")


def show_meetings_statistics(meeting_model: MeetingModel):
    """Отображение статистики по заседаниям"""
    
    st.markdown("### 📊 Статистика заседаний")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.meeting_action = "list"
            st.rerun()
    
    # Получаем статистику
    stats = meeting_model.get_statistics()
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏛️ Всего заседаний", stats.get('total_count', 0))
    
    with col2:
        st.metric("📅 Предстоящие", stats.get('upcoming_meetings', 0))
    
    with col3:
        avg_attendance = stats.get('average_attendance_rate', 0)
        st.metric("📊 Средняя посещаемость", f"{avg_attendance}%" if avg_attendance else "Н/Д")
    
    with col4:
        st.metric("📈 За месяц", stats.get('recent_meetings', 0))
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # Статистика по статусам
        status_stats = stats.get('by_status', {})
        if status_stats:
            st.markdown("#### 📋 Заседания по статусам")
            
            status_names = {
                'PLANNED': 'Запланировано',
                'COMPLETED': 'Проведено',
                'CANCELLED': 'Отменено'
            }
            
            import plotly.express as px
            
            labels = [status_names.get(k, k) for k in status_stats.keys()]
            values = list(status_stats.values())
            
            fig = px.pie(
                values=values,
                names=labels,
                title="Распределение по статусам"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о статусах заседаний")
    
    with col2:
        # Динамика заседаний за последние месяцы
        st.markdown("#### 📈 Динамика проведения")
        
        monthly_data = get_monthly_meetings_data(meeting_model)
        if monthly_data:
            df = pd.DataFrame(monthly_data)
            
            import plotly.express as px
            fig = px.bar(
                df, x='month', y='count',
                title="Заседания по месяцам",
                labels={'month': 'Месяц', 'count': 'Количество'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных для отображения динамики")


def handle_meetings_export(meeting_model: MeetingModel):
    """Обработка экспорта данных заседаний"""
    
    st.markdown("### 📥 Экспорт данных заседаний")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.meeting_action = "list"
            st.rerun()
    
    # Настройки экспорта
    col1, col2 = st.columns(2)
    
    with col1:
        include_cancelled = st.checkbox(
            "Включить отмененные заседания",
            help="Включить в экспорт отмененные заседания"
        )
        
        export_format = st.selectbox(
            "Формат экспорта",
            ["Excel (.xlsx)", "CSV (.csv)"]
        )
    
    with col2:
        # Период экспорта
        period = st.selectbox(
            "Период",
            ["Все время", "Последний год", "Последние 6 месяцев", "Последний месяц"]
        )
    
    if st.button("📥 Экспортировать данные", use_container_width=True):
        # Формируем условия
        where_conditions = []
        params = []
        
        if not include_cancelled:
            where_conditions.append("status != 'CANCELLED'")
        
        # Добавляем условие по периоду
        if period != "Все время":
            period_condition = get_export_period_condition(period)
            if period_condition:
                where_conditions.append(period_condition)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        # Получаем данные
        meetings = meeting_model.get_all(where_clause, tuple(params), "meeting_date DESC")
        
        if not meetings:
            st.warning("Нет данных для экспорта")
            return
        
        # Экспортируем
        success = meeting_model.export_to_excel(
            f"заседания_махалли_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            include_cancelled
        )
        
        if success:
            st.success(f"✅ Подготовлено {len(meetings)} записей для экспорта")
        else:
            st.error("❌ Ошибка при экспорте данных")


# Вспомогательные функции

def get_date_filter_condition(date_filter: str) -> str:
    """Получение условия для фильтрации по дате"""
    
    conditions = {
        "Предстоящие": "meeting_date >= date('now')",
        "За месяц": "meeting_date >= date('now', '-30 days')",
        "За квартал": "meeting_date >= date('now', '-90 days')",
        "За год": "meeting_date >= date('now', '-365 days')"
    }
    
    return conditions.get(date_filter, "")


def get_export_period_condition(period: str) -> str:
    """Получение условия для периода экспорта"""
    
    conditions = {
        "Последний год": "meeting_date >= date('now', '-365 days')",
        "Последние 6 месяцев": "meeting_date >= date('now', '-180 days')",
        "Последний месяц": "meeting_date >= date('now', '-30 days')"
    }
    
    return conditions.get(period, "")


def get_monthly_meetings_data(meeting_model: MeetingModel) -> List[Dict[str, Any]]:
    """Получение данных о заседаниях по месяцам"""
    
    query = """
        SELECT 
            strftime('%Y-%m', meeting_date) as month,
            COUNT(*) as count
        FROM meetings 
        WHERE meeting_date >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', meeting_date)
        ORDER BY month
    """
    
    result = meeting_model.db.execute_query(query)
    
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


def toggle_attendance(meeting_model: MeetingModel, meeting_id: int, citizen_id: int, is_present: bool):
    """Переключение статуса присутствия гражданина"""
    
    # Обновляем или создаем запись посещаемости
    query = """
        INSERT OR REPLACE INTO attendance (citizen_id, meeting_id, is_present)
        VALUES (?, ?, ?)
    """
    
    success = meeting_model.db.execute_query(query, (citizen_id, meeting_id, 1 if is_present else 0), fetch=False)
    
    if success is not None:
        # Обновляем счетчик посещаемости заседания
        meeting_model.update_attendance_count(meeting_id)
        
        status = "присутствующим" if is_present else "отсутствующим"
        show_success_message(f"Гражданин отмечен как {status}")
    else:
        show_error_message("Ошибка при обновлении посещаемости")


def mark_all_present(meeting_model: MeetingModel, points_model: PointsModel, meeting_id: int, attendance_list: List[Dict]):
    """Отметить всех граждан присутствующими"""
    
    for attendance in attendance_list:
        citizen_id = attendance['citizen_id']
        
        # Обновляем посещаемость
        query = """
            INSERT OR REPLACE INTO attendance (citizen_id, meeting_id, is_present)
            VALUES (?, ?, 1)
        """
        meeting_model.db.execute_query(query, (citizen_id, meeting_id), fetch=False)
    
    # Обновляем счетчик
    meeting_model.update_attendance_count(meeting_id)
    show_success_message("Все граждане отмечены как присутствующие")


def mark_all_absent(meeting_model: MeetingModel, meeting_id: int, attendance_list: List[Dict]):
    """Отметить всех граждан отсутствующими"""
    
    for attendance in attendance_list:
        citizen_id = attendance['citizen_id']
        
        query = """
            INSERT OR REPLACE INTO attendance (citizen_id, meeting_id, is_present)
            VALUES (?, ?, 0)
        """
        meeting_model.db.execute_query(query, (citizen_id, meeting_id), fetch=False)
    
    meeting_model.update_attendance_count(meeting_id)
    show_success_message("Все граждане отмечены как отсутствующие")


def award_points_to_present(points_model: PointsModel, meeting_id: int, attendance_list: List[Dict]):
    """Начислить баллы всем присутствующим"""
    
    awarded_count = 0
    
    for attendance in attendance_list:
        if attendance['is_present'] and not attendance['points_earned']:
            citizen_id = attendance['citizen_id']
            
            point_id = points_model.award_points(
                citizen_id=citizen_id,
                activity_type='meeting_attendance',
                description="Посещение заседания",
                meeting_id=meeting_id,
                created_by=get_current_user_id()
            )
            
            if point_id:
                awarded_count += 1
    
    if awarded_count > 0:
        show_success_message(f"Баллы начислены {awarded_count} гражданам")
    else:
        show_error_message("Нет граждан для начисления баллов")
        