"""
Страница отчетов и аналитики
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import io

from config.database import DatabaseManager
from models.citizen import CitizenModel
from models.meeting import MeetingModel
from models.points import PointsModel
from models.sms import SMSModel
from utils.helpers import (
    format_date, format_datetime, create_excel_download_button,
    show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission

def show_reports_page():
    """Главная функция страницы отчетов"""
    
    st.markdown("# 📊 Отчеты и аналитика")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('reports'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Инициализируем модели
    db = DatabaseManager()
    citizen_model = CitizenModel(db)
    meeting_model = MeetingModel(db)
    points_model = PointsModel(db)
    sms_model = SMSModel(db)
    
    # Боковая панель с типами отчетов
    with st.sidebar:
        st.markdown("### 📋 Типы отчетов")
        
        report_types = {
            "📊 Общая сводка": "dashboard",
            "👥 Отчет по гражданам": "citizens",
            "🏛️ Отчет по заседаниям": "meetings",
            "⭐ Отчет по баллам": "points",
            "📱 Отчет по SMS": "sms",
            "📈 Аналитика активности": "analytics",
            "📁 Комплексный отчет": "comprehensive"
        }
        
        for display_name, report_type in report_types.items():
            if st.button(display_name, use_container_width=True):
                st.session_state.report_type = report_type
                st.rerun()
        
        st.markdown("---")
        
        # Быстрая информация о системе
        st.markdown("### ℹ️ Информация о системе")
        
        db_info = db.get_database_info()
        
        st.metric("💾 Размер БД", f"{db_info.get('file_size_mb', 0)} МБ")
        st.metric("👥 Граждан", db_info.get('citizens_count', 0))
        st.metric("🏛️ Заседаний", db_info.get('meetings_count', 0))
        st.metric("📱 SMS кампаний", db_info.get('sms_campaigns_count', 0))
        st.metric("⭐ Начислений", db_info.get('citizen_points_count', 0))
        
        # Экспорт данных
        st.markdown("---")
        st.markdown("### 📥 Экспорт данных")
        
        if st.button("📦 Резервная копия", use_container_width=True):
            create_backup(db)
    
    # Обработка типов отчетов
    report_type = st.session_state.get('report_type', 'dashboard')
    
    if report_type == "dashboard":
        show_reports_dashboard(citizen_model, meeting_model, points_model, sms_model)
    elif report_type == "citizens":
        show_citizens_report(citizen_model)
    elif report_type == "meetings":
        show_meetings_report(meeting_model)
    elif report_type == "points":
        show_points_report(points_model)
    elif report_type == "sms":
        show_sms_report(sms_model)
    elif report_type == "analytics":
        show_analytics_report(citizen_model, meeting_model, points_model)
    elif report_type == "comprehensive":
        show_comprehensive_report(citizen_model, meeting_model, points_model, sms_model)


def show_reports_dashboard(
    citizen_model: CitizenModel,
    meeting_model: MeetingModel,
    points_model: PointsModel,
    sms_model: SMSModel
):
    """Главная панель отчетов с общей статистикой"""
    
    st.markdown("### 📊 Общая сводка системы")
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_citizens = citizen_model.count("is_active = 1")
        st.metric("👥 Активных граждан", total_citizens)
        
        # Рост за месяц
        new_citizens = citizen_model.count("is_active = 1 AND created_at >= date('now', '-30 days')")
        st.metric("➕ Новых за месяц", new_citizens)
    
    with col2:
        total_meetings = meeting_model.count()
        st.metric("🏛️ Всего заседаний", total_meetings)
        
        completed_meetings = meeting_model.count("status = 'COMPLETED'")
        completion_rate = (completed_meetings / total_meetings * 100) if total_meetings > 0 else 0
        st.metric("✅ Завершено", f"{completion_rate:.1f}%")
    
    with col3:
        total_points = points_model.count()
        st.metric("⭐ Начислений баллов", total_points)
        
        monthly_points = points_model.count("date_earned >= date('now', '-30 days')")
        st.metric("📈 За месяц", monthly_points)
    
    with col4:
        total_sms = sms_model.count()
        st.metric("📱 SMS кампаний", total_sms)
        
        monthly_sms = sms_model.count("created_at >= date('now', '-30 days')")
        st.metric("📤 За месяц", monthly_sms)
    
    st.markdown("---")
    
    # Графики активности
    col1, col2 = st.columns(2)
    
    with col1:
        # График посещаемости заседаний
        st.markdown("#### 📈 Динамика посещаемости заседаний")
        
        attendance_data = get_attendance_trend_data(meeting_model)
        
        if attendance_data:
            df_attendance = pd.DataFrame(attendance_data)
            
            fig = px.line(
                df_attendance,
                x='date',
                y='attendance_rate',
                title="Посещаемость заседаний (%)",
                markers=True
            )
            
            fig.update_layout(
                yaxis_title="Посещаемость (%)",
                xaxis_title="Дата заседания"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Недостаточно данных для графика")
    
    with col2:
        # График активности граждан (баллы)
        st.markdown("#### ⭐ Динамика начисления баллов")
        
        points_trend_data = get_points_trend_data(points_model)
        
        if points_trend_data:
            df_points = pd.DataFrame(points_trend_data)
            
            fig = px.bar(
                df_points,
                x='date',
                y='points_awarded',
                title="Баллы по дням"
            )
            
            fig.update_layout(
                yaxis_title="Баллы",
                xaxis_title="Дата"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Недостаточно данных для графика")
    
    # Таблица последних событий
    st.markdown("---")
    st.markdown("#### 📅 Последние события в системе")
    
    recent_events = get_recent_system_events(citizen_model, meeting_model, points_model, sms_model)
    
    if recent_events:
        df_events = pd.DataFrame(recent_events)
        
        st.dataframe(
            df_events,
            column_config={
                "date": st.column_config.DatetimeColumn("Дата"),
                "type": st.column_config.TextColumn("Тип"),
                "description": st.column_config.TextColumn("Описание"),
                "details": st.column_config.TextColumn("Детали")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("📭 Нет недавних событий")


def show_citizens_report(citizen_model: CitizenModel):
    """Отчет по гражданам"""
    
    st.markdown("### 👥 Отчет по гражданам")
    
    # Фильтры отчета
    col1, col2, col3 = st.columns(3)
    
    with col1:
        include_inactive = st.checkbox("Включить неактивных граждан")
        
        age_filter = st.selectbox(
            "Возрастная группа",
            ["Все", "До 18", "18-30", "31-50", "51-70", "70+"]
        )
    
    with col2:
        points_filter = st.selectbox(
            "По баллам",
            ["Все", "Без баллов", "1-50", "51-100", "100+"]
        )
        
        phone_filter = st.checkbox("Только с телефонами")
    
    with col3:
        export_format = st.selectbox(
            "Формат экспорта",
            ["Не экспортировать", "Excel", "CSV", "PDF отчет"]
        )
        
        sort_by = st.selectbox(
            "Сортировка",
            ["По ФИО", "По баллам", "По дате регистрации"]
        )
    
    # Кнопка генерации отчета
    if st.button("📊 Сгенерировать отчет", use_container_width=True, type="primary"):
        # Формируем условия поиска
        where_conditions = []
        params = []
        
        if not include_inactive:
            where_conditions.append("is_active = 1")
        
        if phone_filter:
            where_conditions.append("phone IS NOT NULL AND phone != ''")
        
        # Получаем данные
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        citizens = citizen_model.get_all(where_clause, tuple(params), "full_name")
        
        if not citizens:
            st.warning("📭 Нет данных по заданным критериям")
            return
        
        # Отображаем статистику
        st.success(f"✅ Найдено граждан: {len(citizens)}")
        
        # Основные метрики отчета
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Всего граждан", len(citizens))
        
        with col2:
            with_phones = sum(1 for c in citizens if c['phone'])
            st.metric("📱 С телефонами", with_phones)
        
        with col3:
            with_points = sum(1 for c in citizens if c['total_points'] and c['total_points'] > 0)
            st.metric("⭐ С баллами", with_points)
        
        with col4:
            total_points = sum(c['total_points'] or 0 for c in citizens)
            st.metric("🏆 Общие баллы", total_points)
        
        # Графики
        col1, col2 = st.columns(2)
        
        with col1:
            # Возрастное распределение
            age_distribution = calculate_age_distribution(citizens)
            if age_distribution:
                fig = px.pie(
                    values=list(age_distribution.values()),
                    names=list(age_distribution.keys()),
                    title="Распределение по возрасту"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Распределение по баллам
            points_distribution = calculate_points_distribution(citizens)
            if points_distribution:
                fig = px.bar(
                    x=list(points_distribution.keys()),
                    y=list(points_distribution.values()),
                    title="Распределение по баллам"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Таблица с данными
        st.markdown("#### 📋 Детальные данные")
        
        df_citizens = pd.DataFrame([dict(c) for c in citizens])
        
        # Переименовываем колонки
        column_mapping = {
            'full_name': 'ФИО',
            'birth_date': 'Дата рождения',
            'address': 'Адрес',
            'phone': 'Телефон',
            'total_points': 'Баллы',
            'registration_date': 'Дата регистрации'
        }
        
        display_columns = ['ФИО', 'Дата рождения', 'Адрес', 'Телефон', 'Баллы']
        df_display = df_citizens.rename(columns=column_mapping)[display_columns]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Экспорт
        if export_format != "Не экспортировать":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "Excel":
                create_excel_download_button(
                    df_display,
                    f"отчет_граждане_{timestamp}.xlsx",
                    "📥 Скачать отчет (Excel)"
                )
            elif export_format == "CSV":
                csv_data = df_display.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Скачать отчет (CSV)",
                    data=csv_data,
                    file_name=f"отчет_граждане_{timestamp}.csv",
                    mime="text/csv"
                )
            elif export_format == "PDF отчет":
                pdf_report = generate_citizens_pdf_report(citizens, age_distribution, points_distribution)
                if pdf_report:
                    st.download_button(
                        label="📥 Скачать PDF отчет",
                        data=pdf_report,
                        file_name=f"отчет_граждане_{timestamp}.pdf",
                        mime="application/pdf"
                    )


def show_meetings_report(meeting_model: MeetingModel):
    """Отчет по заседаниям"""
    
    st.markdown("### 🏛️ Отчет по заседаниям")
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_from = st.date_input(
            "Дата от",
            value=date.today() - timedelta(days=90),
            help="Начальная дата периода"
        )
        
        date_to = st.date_input(
            "Дата до",
            value=date.today(),
            help="Конечная дата периода"
        )
    
    with col2:
        status_filter = st.multiselect(
            "Статус заседаний",
            ["PLANNED", "COMPLETED", "CANCELLED"],
            default=["COMPLETED"],
            format_func=lambda x: {
                "PLANNED": "Запланировано",
                "COMPLETED": "Проведено", 
                "CANCELLED": "Отменено"
            }[x]
        )
        
        min_attendance = st.slider(
            "Минимальная посещаемость (%)",
            0, 100, 0,
            help="Фильтр по проценту посещаемости"
        )
    
    with col3:
        include_stats = st.checkbox("Включить статистику посещаемости", value=True)
        
        group_by = st.selectbox(
            "Группировка",
            ["Нет", "По месяцам", "По статусу"]
        )
    
    # Генерация отчета
    if st.button("📊 Сгенерировать отчет", use_container_width=True, type="primary"):
        # Формируем запрос
        where_conditions = ["meeting_date BETWEEN ? AND ?"]
        params = [date_from.isoformat(), date_to.isoformat()]
        
        if status_filter:
            status_placeholders = ",".join(["?" for _ in status_filter])
            where_conditions.append(f"status IN ({status_placeholders})")
            params.extend(status_filter)
        
        where_clause = " AND ".join(where_conditions)
        meetings = meeting_model.get_all(where_clause, tuple(params), "meeting_date DESC")
        
        if not meetings:
            st.warning("📭 Нет заседаний по заданным критериям")
            return
        
        # Фильтр по посещаемости
        if min_attendance > 0:
            filtered_meetings = []
            for meeting in meetings:
                if meeting['total_invited'] > 0:
                    attendance_rate = (meeting['attendance_count'] / meeting['total_invited']) * 100
                    if attendance_rate >= min_attendance:
                        filtered_meetings.append(meeting)
            meetings = filtered_meetings
        
        st.success(f"✅ Найдено заседаний: {len(meetings)}")
        
        # Основные метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏛️ Всего заседаний", len(meetings))
        
        with col2:
            total_participants = sum(m['total_invited'] or 0 for m in meetings)
            st.metric("👥 Всего участников", total_participants)
        
        with col3:
            total_attended = sum(m['attendance_count'] or 0 for m in meetings)
            avg_attendance = (total_attended / total_participants * 100) if total_participants > 0 else 0
            st.metric("📊 Средняя посещаемость", f"{avg_attendance:.1f}%")
        
        with col4:
            completed_count = sum(1 for m in meetings if m['status'] == 'COMPLETED')
            st.metric("✅ Завершено", completed_count)
        
        # Графики
        if include_stats and meetings:
            col1, col2 = st.columns(2)
            
            with col1:
                # График посещаемости по заседаниям
                meeting_names = [m['title'][:20] + "..." if len(m['title']) > 20 else m['title'] for m in meetings]
                attendance_rates = [
                    (m['attendance_count'] / m['total_invited'] * 100) if m['total_invited'] > 0 else 0
                    for m in meetings
                ]
                
                fig = px.bar(
                    x=meeting_names,
                    y=attendance_rates,
                    title="Посещаемость по заседаниям (%)"
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Статистика по статусам
                status_counts = {}
                for meeting in meetings:
                    status = meeting['status']
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                status_names = {
                    'PLANNED': 'Запланировано',
                    'COMPLETED': 'Проведено',
                    'CANCELLED': 'Отменено'
                }
                
                labels = [status_names.get(k, k) for k in status_counts.keys()]
                values = list(status_counts.values())
                
                fig = px.pie(
                    values=values,
                    names=labels,
                    title="Распределение по статусам"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Детальная таблица
        st.markdown("#### 📋 Детальные данные заседаний")
        
        df_meetings = pd.DataFrame([dict(m) for m in meetings])
        
        # Добавляем процент посещаемости
        df_meetings['attendance_rate'] = df_meetings.apply(
            lambda row: (row['attendance_count'] / row['total_invited'] * 100) 
            if row['total_invited'] > 0 else 0, axis=1
        ).round(1)
        
        # Переименовываем колонки
        display_columns = {
            'title': 'Название',
            'meeting_date': 'Дата',
            'meeting_time': 'Время',
            'location': 'Место',
            'status': 'Статус',
            'attendance_count': 'Присутствовали',
            'total_invited': 'Приглашено',
            'attendance_rate': 'Посещаемость %'
        }
        
        df_display = df_meetings[list(display_columns.keys())].rename(columns=display_columns)
        
        # Переводим статусы
        status_mapping = {
            'PLANNED': 'Запланировано',
            'COMPLETED': 'Проведено',
            'CANCELLED': 'Отменено'
        }
        df_display['Статус'] = df_display['Статус'].map(status_mapping)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Экспорт
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        create_excel_download_button(
            df_display,
            f"отчет_заседания_{timestamp}.xlsx",
            "📥 Скачать отчет по заседаниям"
        )


def show_points_report(points_model: PointsModel):
    """Отчет по системе баллов"""
    
    st.markdown("### ⭐ Отчет по системе баллов")
    
    # Настройки отчета
    col1, col2, col3 = st.columns(3)
    
    with col1:
        report_period = st.selectbox(
            "Период отчета",
            [30, 90, 180, 365],
            format_func=lambda x: f"За {x} дней",
            index=1
        )
        
        top_count = st.selectbox(
            "Топ граждан",
            [10, 20, 50, 100],
            help="Количество граждан в рейтинге"
        )
    
    with col2:
        activity_filter = st.multiselect(
            "Типы активности",
            ["meeting_attendance", "subbotnik", "community_work", "volunteer_work"],
            default=[],
            format_func=lambda x: {
                "meeting_attendance": "Заседания",
                "subbotnik": "Субботники",
                "community_work": "Общественная работа",
                "volunteer_work": "Волонтерство"
            }.get(x, x)
        )
        
        min_points = st.number_input(
            "Минимум баллов",
            min_value=0,
            value=0,
            help="Показать только граждан с минимальным количеством баллов"
        )
    
    with col3:
        include_details = st.checkbox("Включить детальную статистику", value=True)
        
        export_charts = st.checkbox("Включить графики в экспорт")
    
    # Генерация отчета
    if st.button("📊 Сгенерировать отчет", use_container_width=True, type="primary"):
        # Получаем статистику активности
        activity_stats = points_model.get_activity_statistics(report_period)
        
        # Получаем рейтинг
        leaderboard = points_model.get_leaderboard(limit=top_count, period_days=report_period)
        
        if min_points > 0:
            leaderboard = [
                citizen for citizen in leaderboard 
                if (citizen.get('total_points', 0) or citizen.get('period_points', 0)) >= min_points
            ]
        
        st.success(f"✅ Отчет по системе баллов за {report_period} дней")
        
        # Основные метрики
        totals = activity_stats.get('totals', {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Активностей", totals.get('total_activities', 0))
        
        with col2:
            st.metric("⭐ Баллов начислено", totals.get('total_points_awarded', 0))
        
        with col3:
            st.metric("👥 Активных граждан", totals.get('active_citizens_count', 0))
        
        with col4:
            avg_points = totals.get('avg_points_per_activity', 0)
            st.metric("📈 Средние баллы", f"{avg_points:.1f}" if avg_points else "0")
        
        # Графики
        if include_details:
            col1, col2 = st.columns(2)
            
            with col1:
                # Активность по типам
                activity_data = activity_stats.get('by_activity_type', [])
                if activity_data:
                    st.markdown("#### 📊 Активность по типам")
                    
                    activity_names = {
                        'meeting_attendance': 'Заседания',
                        'subbotnik': 'Субботники',
                        'community_work': 'Общ. работы',
                        'volunteer_work': 'Волонтерство'
                    }
                    
                    df_activity = pd.DataFrame(activity_data)
                    df_activity['display_name'] = df_activity['activity_type'].map(
                        lambda x: activity_names.get(x, x)
                    )
                    
                    fig = px.pie(
                        df_activity,
                        values='total_points',
                        names='display_name',
                        title="Распределение баллов по типам"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Топ граждан
                if leaderboard:
                    st.markdown("#### 🏆 Топ активных граждан")
                    
                    df_top = pd.DataFrame([dict(citizen) for citizen in leaderboard[:10]])
                    
                    # Определяем колонку с баллами
                    points_column = 'total_points' if report_period is None else 'period_points'
                    if points_column not in df_top.columns:
                        points_column = 'total_points'  # fallback
                    
                    df_display = df_top[['full_name', points_column]].copy()
                    df_display.columns = ['ФИО', 'Баллы']
                    df_display.index = range(1, len(df_display) + 1)
                    
                    st.dataframe(df_display, use_container_width=True)
        
        # Детальная таблица
        if leaderboard:
            st.markdown("#### 📋 Полный рейтинг")
            
            df_leaderboard = pd.DataFrame([dict(citizen) for citizen in leaderboard])
            
            # Добавляем позицию
            df_leaderboard['position'] = range(1, len(df_leaderboard) + 1)
            
            # Определяем колонки для отображения
            display_columns = ['position', 'full_name']
            column_config = {
                'position': 'Место',
                'full_name': 'ФИО'
            }
            
            if report_period is None:
                display_columns.append('total_points')
                column_config['total_points'] = 'Всего баллов'
            else:
                display_columns.append('period_points')
                column_config['period_points'] = f'Баллы за {report_period} дней'
            
            if 'activities_count' in df_leaderboard.columns:
                display_columns.append('activities_count')
                column_config['activities_count'] = 'Активностей'
            
            df_display = df_leaderboard[display_columns].rename(columns=column_config)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Экспорт
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            create_excel_download_button(
                df_display,
                f"отчет_баллы_{timestamp}.xlsx",
                "📥 Скачать отчет по баллам"
            )
        else:
            st.info("📭 Нет данных для отчета")


def show_sms_report(sms_model: SMSModel):
    """Отчет по SMS-рассылкам"""
    
    st.markdown("### 📱 Отчет по SMS-рассылкам")
    
    # Настройки отчета
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period = st.selectbox(
            "Период отчета",
            [7, 30, 90, 365],
            format_func=lambda x: f"За {x} дней",
            index=1
        )
        
        campaign_type = st.selectbox(
            "Тип кампаний",
            ["Все", "Обычные", "Экстренные", "Напоминания"]
        )
    
    with col2:
        include_logs = st.checkbox("Включить детальные логи", value=False)
        
        min_recipients = st.number_input(
            "Минимум получателей",
            min_value=0,
            value=0,
            help="Показать только кампании с минимальным количеством получателей"
        )
    
    with col3:
        delivery_filter = st.selectbox(
            "По доставляемости",
            ["Все", "Высокая (>90%)", "Средняя (50-90%)", "Низкая (<50%)"]
        )
        
        export_format = st.selectbox(
            "Формат экспорта",
            ["Не экспортировать", "Excel", "CSV"]
        )
    
    # Генерация отчета
    if st.button("📊 Сгенерировать отчет", use_container_width=True, type="primary"):
        # Формируем условия поиска
        start_date = date.today() - timedelta(days=period)
        where_conditions = ["created_at >= ?"]
        params = [start_date.isoformat()]
        
        # Фильтр по типу
        if campaign_type != "Все":
            type_map = {
                "Обычные": "REGULAR",
                "Экстренные": "EMERGENCY",
                "Напоминания": "REMINDER"
            }
            sms_type = type_map.get(campaign_type)
            if sms_type:
                where_conditions.append("campaign_type = ?")
                params.append(sms_type)
        
        where_clause = " AND ".join(where_conditions)
        campaigns = sms_model.get_all(where_clause, tuple(params), "created_at DESC")
        
        # Фильтр по количеству получателей
        if min_recipients > 0:
            campaigns = [c for c in campaigns if (c['sent_count'] or 0) >= min_recipients]
        
        # Фильтр по доставляемости
        if delivery_filter != "Все":
            filtered_campaigns = []
            for campaign in campaigns:
                if campaign['sent_count'] and campaign['sent_count'] > 0:
                    delivery_rate = (campaign['delivered_count'] or 0) / campaign['sent_count'] * 100
                    
                    if delivery_filter == "Высокая (>90%)" and delivery_rate > 90:
                        filtered_campaigns.append(campaign)
                    elif delivery_filter == "Средняя (50-90%)" and 50 <= delivery_rate <= 90:
                        filtered_campaigns.append(campaign)
                    elif delivery_filter == "Низкая (<50%)" and delivery_rate < 50:
                        filtered_campaigns.append(campaign)
            campaigns = filtered_campaigns
        
        if not campaigns:
            st.warning("📭 Нет SMS-кампаний по заданным критериям")
            return
        
        st.success(f"✅ Найдено кампаний: {len(campaigns)}")
        
        # Основные метрики
        col1, col2, col3, col4 = st.columns(4)
        
        total_sent = sum(c['sent_count'] or 0 for c in campaigns)
        total_delivered = sum(c['delivered_count'] or 0 for c in campaigns)
        total_failed = sum(c['failed_count'] or 0 for c in campaigns)
        avg_delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        
        with col1:
            st.metric("📤 Всего кампаний", len(campaigns))
        
        with col2:
            st.metric("📱 Отправлено SMS", total_sent)
        
        with col3:
            st.metric("✅ Доставлено", total_delivered)
            st.metric("📈 Доставляемость", f"{avg_delivery_rate:.1f}%")
        
        with col4:
            st.metric("❌ Ошибки", total_failed)
        
        # Графики
        col1, col2 = st.columns(2)
        
        with col1:
            # Статистика по типам
            type_stats = {}
            for campaign in campaigns:
                campaign_type = campaign['campaign_type']
                type_stats[campaign_type] = type_stats.get(campaign_type, 0) + 1
            
            if type_stats:
                type_names = {
                    'REGULAR': 'Обычные',
                    'EMERGENCY': 'Экстренные',
                    'REMINDER': 'Напоминания'
                }
                
                labels = [type_names.get(k, k) for k in type_stats.keys()]
                values = list(type_stats.values())
                
                fig = px.pie(
                    values=values,
                    names=labels,
                    title="Кампании по типам"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Динамика по дням
            daily_stats = {}
            for campaign in campaigns:
                day = campaign['created_at'][:10]  # YYYY-MM-DD
                daily_stats[day] = daily_stats.get(day, 0) + (campaign['sent_count'] or 0)
            
            if daily_stats:
                df_daily = pd.DataFrame([
                    {'date': k, 'sms_count': v} for k, v in daily_stats.items()
                ])
                df_daily['date'] = pd.to_datetime(df_daily['date'])
                df_daily = df_daily.sort_values('date')
                
                fig = px.bar(
                    df_daily,
                    x='date',
                    y='sms_count',
                    title="SMS по дням"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Детальная таблица
        st.markdown("#### 📋 Детальные данные кампаний")
        
        df_campaigns = pd.DataFrame([dict(c) for c in campaigns])
        
        # Добавляем процент доставляемости
        df_campaigns['delivery_rate'] = df_campaigns.apply(
            lambda row: (row['delivered_count'] / row['sent_count'] * 100) 
            if row['sent_count'] and row['sent_count'] > 0 else 0, axis=1
        ).round(1)
        
        # Переименовываем колонки
        display_columns = {
            'title': 'Название',
            'campaign_type': 'Тип',
            'created_at': 'Создано',
            'sent_count': 'Отправлено',
            'delivered_count': 'Доставлено',
            'failed_count': 'Ошибки',
            'delivery_rate': 'Доставляемость %'
        }
        
        df_display = df_campaigns[list(display_columns.keys())].rename(columns=display_columns)
        
        # Переводим типы
        type_mapping = {
            'REGULAR': 'Обычная',
            'EMERGENCY': 'Экстренная',
            'REMINDER': 'Напоминание'
        }
        df_display['Тип'] = df_display['Тип'].map(type_mapping)
        
        # Форматируем дату
        df_display['Создано'] = pd.to_datetime(df_display['Создано']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Экспорт
        if export_format != "Не экспортировать":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "Excel":
                create_excel_download_button(
                    df_display,
                    f"отчет_sms_{timestamp}.xlsx",
                    "📥 Скачать отчет по SMS"
                )
            else:  # CSV
                csv_data = df_display.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Скачать отчет (CSV)",
                    data=csv_data,
                    file_name=f"отчет_sms_{timestamp}.csv",
                    mime="text/csv"
                )


def show_analytics_report(citizen_model: CitizenModel, meeting_model: MeetingModel, points_model: PointsModel):
    """Аналитический отчет активности"""
    
    st.markdown("### 📈 Аналитика активности")
    
    # Настройки анализа
    col1, col2, col3 = st.columns(3)
    
    with col1:
        analysis_period = st.selectbox(
            "Период анализа",
            [30, 90, 180, 365],
            format_func=lambda x: f"За {x} дней",
            index=2
        )
        
        focus_area = st.selectbox(
            "Фокус анализа",
            ["Общая активность", "Посещаемость заседаний", "Система баллов", "Сравнительный анализ"]
        )
    
    with col2:
        include_trends = st.checkbox("Включить трендовый анализ", value=True)
        
        correlation_analysis = st.checkbox("Корреляционный анализ")
    
    with col3:
        export_analytics = st.checkbox("Экспорт аналитики")
        
        detailed_charts = st.checkbox("Детальные графики", value=True)
    
    # Генерация аналитики
    if st.button("📊 Запустить анализ", use_container_width=True, type="primary"):
        st.success(f"🔍 Анализ активности за {analysis_period} дней")
        
        # Получаем данные для анализа
        start_date = date.today() - timedelta(days=analysis_period)
        
        # Основные метрики для анализа
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Активность граждан
            active_citizens = citizen_model.count("is_active = 1 AND total_points > 0")
            total_citizens = citizen_model.count("is_active = 1")
            activity_rate = (active_citizens / total_citizens * 100) if total_citizens > 0 else 0
            
            st.metric("👥 Уровень активности", f"{activity_rate:.1f}%")
            st.caption(f"{active_citizens} из {total_citizens} граждан")
        
        with col2:
            # Эффективность заседаний
            completed_meetings = meeting_model.count(
                f"status = 'COMPLETED' AND meeting_date >= '{start_date.isoformat()}'"
            )
            total_meetings = meeting_model.count(
                f"meeting_date >= '{start_date.isoformat()}'"
            )
            completion_rate = (completed_meetings / total_meetings * 100) if total_meetings > 0 else 0
            
            st.metric("🏛️ Эффективность заседаний", f"{completion_rate:.1f}%")
            st.caption(f"{completed_meetings} из {total_meetings} завершено")
        
        with col3:
            # Динамика начислений
            recent_points = points_model.count(f"date_earned >= '{start_date.isoformat()}'")
            points_per_day = recent_points / analysis_period if analysis_period > 0 else 0
            
            st.metric("⭐ Активность (баллы/день)", f"{points_per_day:.1f}")
            st.caption(f"{recent_points} начислений за период")
        
        if detailed_charts:
            # Детальные графики
            st.markdown("---")
            
            if focus_area == "Общая активность":
                show_general_activity_analysis(citizen_model, meeting_model, points_model, analysis_period)
            elif focus_area == "Посещаемость заседаний":
                show_attendance_analysis(meeting_model, analysis_period)
            elif focus_area == "Система баллов":
                show_points_analysis(points_model, analysis_period)
            elif focus_area == "Сравнительный анализ":
                show_comparative_analysis(citizen_model, meeting_model, points_model, analysis_period)
        
        if correlation_analysis:
            st.markdown("---")
            show_correlation_analysis(citizen_model, meeting_model, points_model)


def show_comprehensive_report(
    citizen_model: CitizenModel,
    meeting_model: MeetingModel,
    points_model: PointsModel,
    sms_model: SMSModel
):
    """Комплексный отчет по всей системе"""
    
    st.markdown("### 📁 Комплексный отчет системы")
    
    # Настройки комплексного отчета
    col1, col2 = st.columns(2)
    
    with col1:
        report_period = st.selectbox(
            "Период отчета",
            [30, 90, 180, 365],
            format_func=lambda x: f"За {x} дней",
            index=2
        )
        
        include_sections = st.multiselect(
            "Разделы отчета",
            ["Граждане", "Заседания", "Баллы", "SMS", "Аналитика"],
            default=["Граждане", "Заседания", "Баллы", "SMS"]
        )
    
    with col2:
        report_format = st.selectbox(
            "Формат отчета",
            ["Веб-отчет", "Excel-файл", "PDF-документ"]
        )
        
        include_charts = st.checkbox("Включить графики", value=True)
        
        executive_summary = st.checkbox("Краткая сводка", value=True)
    
    # Генерация комплексного отчета
    if st.button("📊 Создать комплексный отчет", use_container_width=True, type="primary"):
        start_date = date.today() - timedelta(days=report_period)
        
        if executive_summary:
            st.markdown("---")
            st.markdown("## 📋 Краткая сводка")
            
            # Ключевые показатели
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_citizens = citizen_model.count("is_active = 1")
                new_citizens = citizen_model.count(
                    f"is_active = 1 AND created_at >= '{start_date.isoformat()}'"
                )
                
                st.metric("👥 Граждан", total_citizens, delta=f"+{new_citizens}")
            
            with col2:
                total_meetings = meeting_model.count(
                    f"meeting_date >= '{start_date.isoformat()}'"
                )
                completed = meeting_model.count(
                    f"meeting_date >= '{start_date.isoformat()}' AND status = 'COMPLETED'"
                )
                
                st.metric("🏛️ Заседаний", total_meetings, delta=f"{completed} завершено")
            
            with col3:
                total_points = points_model.count(
                    f"date_earned >= '{start_date.isoformat()}'"
                )
                
                st.metric("⭐ Начислений", total_points)
            
            with col4:
                total_sms = sms_model.count(
                    f"created_at >= '{start_date.isoformat()}'"
                )
                
                st.metric("📱 SMS кампаний", total_sms)
        
        # Генерируем разделы отчета
        for section in include_sections:
            st.markdown("---")
            
            if section == "Граждане":
                generate_citizens_section(citizen_model, start_date, include_charts)
            elif section == "Заседания":
                generate_meetings_section(meeting_model, start_date, include_charts)
            elif section == "Баллы":
                generate_points_section(points_model, start_date, include_charts)
            elif section == "SMS":
                generate_sms_section(sms_model, start_date, include_charts)
            elif section == "Аналитика":
                generate_analytics_section(citizen_model, meeting_model, points_model, start_date)
        
        # Экспорт отчета
        if report_format != "Веб-отчет":
            st.markdown("---")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if report_format == "Excel-файл":
                # Здесь была бы логика создания Excel файла
                st.success("📥 Excel отчет будет готов для скачивания")
                
                # Заглушка для демо
                st.download_button(
                    label="📥 Скачать комплексный отчет (Excel)",
                    data="Mock Excel data",
                    file_name=f"комплексный_отчет_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            elif report_format == "PDF-документ":
                st.success("📥 PDF отчет будет готов для скачивания")
                
                # Заглушка для демо
                st.download_button(
                    label="📥 Скачать комплексный отчет (PDF)",
                    data="Mock PDF data",
                    file_name=f"комплексный_отчет_{timestamp}.pdf",
                    mime="application/pdf"
                )


# Вспомогательные функции для аналитики

def get_attendance_trend_data(meeting_model: MeetingModel) -> List[Dict[str, Any]]:
    """Получение данных о тренде посещаемости"""
    
    query = """
        SELECT 
            meeting_date as date,
            title,
            CASE WHEN total_invited > 0 
                 THEN (attendance_count * 100.0 / total_invited) 
                 ELSE 0 END as attendance_rate
        FROM meetings 
        WHERE status = 'COMPLETED' 
        AND meeting_date >= date('now', '-180 days')
        ORDER BY meeting_date
    """
    
    result = meeting_model.db.execute_query(query)
    return [dict(row) for row in result] if result else []


def get_points_trend_data(points_model: PointsModel) -> List[Dict[str, Any]]:
    """Получение данных о тренде начисления баллов"""
    
    query = """
        SELECT 
            date_earned as date,
            SUM(points) as points_awarded,
            COUNT(*) as activities_count
        FROM citizen_points 
        WHERE date_earned >= date('now', '-30 days')
        GROUP BY date_earned
        ORDER BY date_earned
    """
    
    result = points_model.db.execute_query(query)
    return [dict(row) for row in result] if result else []


def get_recent_system_events(
    citizen_model: CitizenModel,
    meeting_model: MeetingModel,
    points_model: PointsModel,
    sms_model: SMSModel
) -> List[Dict[str, Any]]:
    """Получение последних событий в системе"""
    
    events = []
    
    # Последние граждане
    recent_citizens = citizen_model.get_all(
        "created_at >= date('now', '-7 days')",
        order_by="created_at DESC"
    )[:5]
    
    for citizen in recent_citizens:
        events.append({
            'date': citizen['created_at'],
            'type': '👥 Граждане',
            'description': f"Добавлен гражданин: {citizen['full_name']}",
            'details': f"Адрес: {citizen['address'] or 'Не указан'}"
        })
    
    # Последние заседания
    recent_meetings = meeting_model.get_all(
        "created_at >= date('now', '-7 days')",
        order_by="created_at DESC"
    )[:5]
    
    for meeting in recent_meetings:
        events.append({
            'date': meeting['created_at'],
            'type': '🏛️ Заседания',
            'description': f"Создано заседание: {meeting['title']}",
            'details': f"Дата: {format_date(meeting['meeting_date'])}"
        })
    
    # Сортируем по дате
    events.sort(key=lambda x: x['date'], reverse=True)
    
    return events[:10]


def calculate_age_distribution(citizens: List[Dict]) -> Dict[str, int]:
    """Расчет возрастного распределения"""
    
    distribution = {
        "До 18": 0,
        "18-30": 0,
        "31-50": 0,
        "51-70": 0,
        "70+": 0
    }
    
    today = date.today()
    
    for citizen in citizens:
        if citizen['birth_date']:
            try:
                birth_date = datetime.strptime(citizen['birth_date'], '%Y-%m-%d').date()
                age = today.year - birth_date.year
                
                if age < 18:
                    distribution["До 18"] += 1
                elif 18 <= age <= 30:
                    distribution["18-30"] += 1
                elif 31 <= age <= 50:
                    distribution["31-50"] += 1
                elif 51 <= age <= 70:
                    distribution["51-70"] += 1
                else:
                    distribution["70+"] += 1
            except:
                pass
    
    return distribution


def calculate_points_distribution(citizens: List[Dict]) -> Dict[str, int]:
    """Расчет распределения по баллам"""
    
    distribution = {
        "0 баллов": 0,
        "1-50": 0,
        "51-100": 0,
        "100+": 0
    }
    
    for citizen in citizens:
        points = citizen['total_points'] or 0
        
        if points == 0:
            distribution["0 баллов"] += 1
        elif 1 <= points <= 50:
            distribution["1-50"] += 1
        elif 51 <= points <= 100:
            distribution["51-100"] += 1
        else:
            distribution["100+"] += 1
    
    return distribution


def create_backup(db: DatabaseManager):
    """Создание резервной копии базы данных"""
    
    try:
        backup_path = db.backup_database()
        
        # Читаем файл резервной копии для скачивания
        with open(backup_path, 'rb') as f:
            backup_data = f.read()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📥 Скачать резервную копию",
            data=backup_data,
            file_name=f"backup_mahalla_{timestamp}.db",
            mime="application/octet-stream"
        )
        
        show_success_message("Резервная копия создана успешно!")
        
    except Exception as e:
        show_error_message(f"Ошибка создания резервной копии: {str(e)}")


def generate_citizens_pdf_report(citizens, age_distribution, points_distribution):
    """Генерация PDF отчета по гражданам (заглушка)"""
    # В реальной реализации здесь был бы код генерации PDF
    return b"Mock PDF content for citizens report"


# Заглушки для дополнительных аналитических функций

def show_general_activity_analysis(citizen_model, meeting_model, points_model, period):
    """Анализ общей активности"""
    st.markdown("#### 📊 Анализ общей активности")
    st.info("Детальный анализ общей активности системы")


def show_attendance_analysis(meeting_model, period):
    """Анализ посещаемости"""
    st.markdown("#### 🏛️ Анализ посещаемости заседаний")
    st.info("Углубленный анализ посещаемости заседаний")


def show_points_analysis(points_model, period):
    """Анализ системы баллов"""
    st.markdown("#### ⭐ Анализ системы баллов")
    st.info("Детальный анализ эффективности системы поощрений")


def show_comparative_analysis(citizen_model, meeting_model, points_model, period):
    """Сравнительный анализ"""
    st.markdown("#### 📈 Сравнительный анализ")
    st.info("Сравнительный анализ различных показателей")


def show_correlation_analysis(citizen_model, meeting_model, points_model):
    """Корреляционный анализ"""
    st.markdown("#### 🔬 Корреляционный анализ")
    st.info("Анализ взаимосвязей между различными показателями")


def generate_citizens_section(citizen_model, start_date, include_charts):
    """Генерация раздела по гражданам"""
    st.markdown("## 👥 Раздел: Граждане")
    st.info("Подробная информация о гражданах махалли")


def generate_meetings_section(meeting_model, start_date, include_charts):
    """Генерация раздела по заседаниям"""
    st.markdown("## 🏛️ Раздел: Заседания")
    st.info("Подробная информация о заседаниях")


def generate_points_section(points_model, start_date, include_charts):
    """Генерация раздела по баллам"""
    st.markdown("## ⭐ Раздел: Система баллов")
    st.info("Подробная информация о системе поощрений")


def generate_sms_section(sms_model, start_date, include_charts):
    """Генерация раздела по SMS"""
    st.markdown("## 📱 Раздел: SMS-рассылки")
    st.info("Подробная информация о SMS-кампаниях")


def generate_analytics_section(citizen_model, meeting_model, points_model, start_date):
    """Генерация аналитического раздела"""
    st.markdown("## 📈 Раздел: Аналитика")
    st.info("Углубленная аналитика системы")
    