"""
Главная страница (Dashboard) с общей статистикой
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import pandas as pd
from typing import Dict, Any, List

from config.database import DatabaseManager
from models.citizen import CitizenModel
from models.meeting import MeetingModel
from models.points import PointsModel
from models.sms import SMSModel
from utils.helpers import create_metrics_row, create_pie_chart, create_bar_chart, format_date
from utils.auth import get_current_user

def show_dashboard():
    """Отображение главной страницы с дашбордом"""
    
    st.markdown("# 📊 Главная панель")
    st.markdown("---")
    
    # Инициализируем модели
    db = DatabaseManager()
    citizen_model = CitizenModel(db)
    meeting_model = MeetingModel(db)
    points_model = PointsModel(db)
    sms_model = SMSModel(db)
    
    # Получаем данные пользователя
    user = get_current_user()
    user_name = user['full_name'] if user else "Пользователь"
    
    # Приветствие
    current_time = datetime.now()
    if current_time.hour < 12:
        greeting = "Доброе утро"
    elif current_time.hour < 18:
        greeting = "Добрый день"
    else:
        greeting = "Добрый вечер"
    
    st.markdown(f"## {greeting}, {user_name}! 👋")
    st.markdown(f"*Сегодня: {format_date(date.today(), 'long')}*")
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    # Общее количество граждан
    with col1:
        total_citizens = citizen_model.count("is_active = 1")
        st.metric(
            label="👥 Всего граждан",
            value=total_citizens,
            help="Количество активных граждан в системе"
        )
    
    # Предстоящие заседания
    with col2:
        upcoming_meetings = meeting_model.count(
            "meeting_date >= date('now') AND status = 'PLANNED'"
        )
        st.metric(
            label="🏛️ Предстоящие заседания",
            value=upcoming_meetings,
            help="Запланированные заседания на ближайшее время"
        )
    
    # SMS за месяц
    with col3:
        start_month = date.today().replace(day=1)
        sms_count = sms_model.count(
            "created_at >= ?", (start_month.isoformat(),)
        )
        st.metric(
            label="📱 SMS за месяц",
            value=sms_count,
            help="Количество отправленных SMS кампаний за текущий месяц"
        )
    
    # Активные граждане (с баллами)
    with col4:
        active_citizens = citizen_model.count(
            "is_active = 1 AND total_points > 0"
        )
        st.metric(
            label="⭐ Активные граждане",
            value=active_citizens,
            help="Граждане с начисленными баллами"
        )
    
    st.markdown("---")
    
    # Блок с детальной информацией
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # График посещаемости заседаний за последние месяцы
        st.markdown("### 📈 Динамика посещаемости заседаний")
        
        # Получаем данные за последние 6 месяцев
        attendance_data = get_attendance_dynamics(meeting_model)
        
        if attendance_data:
            df = pd.DataFrame(attendance_data)
            
            fig = px.line(
                df, x='month', y='attendance_rate',
                title="Посещаемость заседаний по месяцам (%)",
                markers=True
            )
            
            fig.update_layout(
                xaxis_title="Месяц",
                yaxis_title="Посещаемость (%)",
                showlegend=False,
                height=400
            )
            
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Посещаемость: %{y:.1f}%<extra></extra>"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Недостаточно данных для отображения графика")
    
    with col_right:
        # Топ активных граждан
        st.markdown("### 🏆 Топ активных граждан")
        
        top_citizens = points_model.get_leaderboard(limit=5)
        
        if top_citizens:
            for i, citizen in enumerate(top_citizens, 1):
                points = citizen.get('total_points', citizen.get('period_points', 0))
                
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(45deg, #f8f9fa, #e3f2fd);
                        padding: 10px;
                        border-radius: 8px;
                        margin: 5px 0;
                        border-left: 4px solid {'#ffd700' if i == 1 else '#c0c0c0' if i == 2 else '#cd7f32' if i == 3 else '#dee2e6'};
                    ">
                        <b>{i}. {citizen['full_name']}</b><br>
                        <small>🏆 {points} баллов</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("🏆 Пока нет активных граждан")
    
    st.markdown("---")
    
    # Блок со статистикой
    col1, col2 = st.columns(2)
    
    with col1:
        # Распределение граждан по возрастным группам
        st.markdown("### 👨‍👩‍👧‍👦 Возрастные группы")
        
        age_stats = citizen_model.get_age_statistics()
        
        if age_stats:
            fig = create_pie_chart(
                age_stats,
                "Распределение граждан по возрасту"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Нет данных о возрасте граждан")
    
    with col2:
        # Статистика заседаний по статусам
        st.markdown("### 📋 Статистика заседаний")
        
        meeting_stats = get_meeting_statistics(meeting_model)
        
        if meeting_stats:
            # Цветовая схема для статусов
            colors = {
                'PLANNED': '#2196F3',    # Синий
                'COMPLETED': '#4CAF50',  # Зеленый  
                'CANCELLED': '#F44336'   # Красный
            }
            
            status_names = {
                'PLANNED': 'Запланировано',
                'COMPLETED': 'Проведено',
                'CANCELLED': 'Отменено'
            }
            
            labels = [status_names.get(k, k) for k in meeting_stats.keys()]
            values = list(meeting_stats.values())
            plot_colors = [colors.get(k, '#999999') for k in meeting_stats.keys()]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker_colors=plot_colors,
                hovertemplate='<b>%{label}</b><br>Количество: %{value}<br>Процент: %{percent}<extra></extra>'
            )])
            
            fig.update_layout(
                title="Заседания по статусам",
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Нет данных о заседаниях")
    
    # Блок с последними активностями
    st.markdown("---")
    st.markdown("### 📅 Последние события")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏛️ Недавние заседания")
        recent_meetings = meeting_model.get_all(
            "meeting_date >= date('now', '-30 days')",
            order_by="meeting_date DESC"
        )[:5]
        
        if recent_meetings:
            for meeting in recent_meetings:
                status_colors = {
                    'PLANNED': '🔵',
                    'COMPLETED': '✅',
                    'CANCELLED': '❌'
                }
                
                status_icon = status_colors.get(meeting['status'], '⚪')
                meeting_date = format_date(meeting['meeting_date'])
                
                st.markdown(f"""
                <div style="
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 5px 0;
                    border-left: 3px solid #dee2e6;
                ">
                    {status_icon} <b>{meeting['title']}</b><br>
                    <small>📅 {meeting_date} | 👥 {meeting['attendance_count']}/{meeting['total_invited']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Нет недавних заседаний")
    
    with col2:
        st.markdown("#### ⭐ Недавние начисления баллов")
        recent_points = points_model.get_all(
            "date_earned >= date('now', '-7 days')",
            order_by="created_at DESC"
        )[:5]
        
        if recent_points:
            for point_record in recent_points:
                # Получаем информацию о гражданине
                citizen = citizen_model.get_by_id(point_record['citizen_id'])
                citizen_name = citizen['full_name'] if citizen else "Неизвестный"
                
                activity_icons = {
                    'meeting_attendance': '🏛️',
                    'subbotnik': '🧹',
                    'community_work': '🤝',
                    'volunteer_work': '❤️'
                }
                
                icon = activity_icons.get(point_record['activity_type'], '⭐')
                points = point_record['points']
                date_earned = format_date(point_record['date_earned'])
                
                st.markdown(f"""
                <div style="
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 5px 0;
                    border-left: 3px solid #4CAF50;
                ">
                    {icon} <b>{citizen_name}</b><br>
                    <small>+{points} баллов | {date_earned}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Нет недавних начислений")
    
    # Быстрые действия
    st.markdown("---")
    st.markdown("### ⚡ Быстрые действия")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Добавить гражданина", use_container_width=True):
            st.session_state.quick_action = "add_citizen"
            st.rerun()
    
    with col2:
        if st.button("📅 Создать заседание", use_container_width=True):
            st.session_state.quick_action = "create_meeting"
            st.rerun()
    
    with col3:
        if st.button("📱 Отправить SMS", use_container_width=True):
            st.session_state.quick_action = "send_sms"
            st.rerun()
    
    with col4:
        if st.button("📊 Экспорт данных", use_container_width=True):
            st.session_state.quick_action = "export_data"
            st.rerun()
    
    # Обработка быстрых действий
    if hasattr(st.session_state, 'quick_action'):
        handle_quick_actions()


def get_attendance_dynamics(meeting_model: MeetingModel) -> List[Dict[str, Any]]:
    """
    Получение динамики посещаемости заседаний за последние месяцы
    
    Args:
        meeting_model: Модель заседаний
        
    Returns:
        Список данных по месяцам
    """
    # Получаем данные за последние 6 месяцев
    end_date = date.today()
    start_date = end_date - timedelta(days=180)
    
    query = """
        SELECT 
            strftime('%Y-%m', meeting_date) as month,
            AVG(CASE WHEN total_invited > 0 
                THEN (attendance_count * 100.0 / total_invited) 
                ELSE 0 END) as attendance_rate,
            COUNT(*) as meetings_count
        FROM meetings 
        WHERE meeting_date BETWEEN ? AND ?
        AND status = 'COMPLETED'
        GROUP BY strftime('%Y-%m', meeting_date)
        ORDER BY month
    """
    
    result = meeting_model.db.execute_query(
        query, 
        (start_date.isoformat(), end_date.isoformat())
    )
    
    if result:
        data = []
        for row in result:
            # Преобразуем месяц в читаемый формат
            month_str = row['month']
            try:
                month_date = datetime.strptime(month_str, '%Y-%m')
                month_name = month_date.strftime('%b %Y')
            except:
                month_name = month_str
            
            data.append({
                'month': month_name,
                'attendance_rate': round(row['attendance_rate'], 1),
                'meetings_count': row['meetings_count']
            })
        
        return data
    
    return []


def get_meeting_statistics(meeting_model: MeetingModel) -> Dict[str, int]:
    """
    Получение статистики заседаний по статусам
    
    Args:
        meeting_model: Модель заседаний
        
    Returns:
        Словарь со статистикой
    """
    query = """
        SELECT status, COUNT(*) as count
        FROM meetings
        WHERE meeting_date >= date('now', '-365 days')
        GROUP BY status
    """
    
    result = meeting_model.db.execute_query(query)
    
    if result:
        return {row['status']: row['count'] for row in result}
    
    return {}


def handle_quick_actions():
    """Обработка быстрых действий"""
    action = st.session_state.quick_action
    
    if action == "add_citizen":
        st.info("🔄 Перенаправление на страницу добавления гражданина...")
        # Здесь можно добавить логику перехода на нужную страницу
        
    elif action == "create_meeting":
        st.info("🔄 Перенаправление на страницу создания заседания...")
        
    elif action == "send_sms":
        st.info("🔄 Перенаправление на страницу SMS-рассылки...")
        
    elif action == "export_data":
        st.info("🔄 Подготовка экспорта данных...")
    
    # Очищаем действие
    del st.session_state.quick_action


def show_system_info():
    """Отображение информации о системе"""
    
    with st.expander("ℹ️ Информация о системе"):
        st.markdown("""
        ### 🏛️ Система управления махалли
        
        **Версия:** 1.0.0  
        **Дата разработки:** 2024  
        **Технологии:** Python, Streamlit, SQLite
        
        **Функциональность:**
        - 👥 Управление реестром граждан
        - 🏛️ Планирование и проведение заседаний
        - 📱 SMS-рассылки и уведомления
        - ⚡ Экстренные оповещения
        - ⭐ Система поощрений и баллов
        - 📊 Отчеты и аналитика
        
        **Контакты разработчика:**  
        📧 support@mahalla-system.uz  
        📞 +998 (71) 123-45-67
        """)


# CSS стили для дашборда
def apply_dashboard_styles():
    """Применение кастомных стилей для дашборда"""
    st.markdown("""
    <style>
        /* Стили для метрик */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        [data-testid="metric-container"] label {
            color: white !important;
        }
        
        [data-testid="metric-container"] [data-testid="metric-value"] {
            color: white !important;
            font-size: 2rem !important;
            font-weight: bold !important;
        }
        
        /* Стили для контейнеров */
        .metric-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Стили для карточек событий */
        .event-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #2196F3;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Стили для кнопок быстрых действий */
        .stButton > button {
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 10px 20px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    </style>
    """, unsafe_allow_html=True)


# Применяем стили при загрузке модуля
apply_dashboard_styles()