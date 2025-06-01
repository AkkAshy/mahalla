"""
Страница системы баллов и поощрений
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from config.database import DatabaseManager
from models.points import PointsModel
from models.citizen import CitizenModel
from models.meeting import MeetingModel
from utils.helpers import (
    format_date, format_datetime, Paginator,
    create_excel_download_button, show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission

def show_points_page():
    """Главная функция страницы системы баллов"""
    
    st.markdown("# ⭐ Система баллов и поощрений")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('points'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Инициализируем модели
    db = DatabaseManager()
    points_model = PointsModel(db)
    citizen_model = CitizenModel(db)
    meeting_model = MeetingModel(db)
    
    # Боковая панель с действиями
    with st.sidebar:
        st.markdown("### 🔧 Действия")
        
        if st.button("🏆 Начислить баллы", use_container_width=True):
            st.session_state.points_action = "award"
        
        if st.button("📊 Рейтинг граждан", use_container_width=True):
            st.session_state.points_action = "leaderboard"
        
        if st.button("📈 Статистика", use_container_width=True):
            st.session_state.points_action = "stats"
        
        if st.button("⚙️ Настройки баллов", use_container_width=True):
            st.session_state.points_action = "settings"
        
        st.markdown("---")
        
        # Быстрая статистика
        st.markdown("### 📈 Сводка")
        
        quick_stats = get_quick_points_stats(points_model, citizen_model)
        
        st.metric("🏆 Активных граждан", quick_stats.get('active_citizens', 0))
        st.metric("⭐ Всего баллов", quick_stats.get('total_points', 0))
        st.metric("📅 За месяц", quick_stats.get('monthly_activities', 0))
        
        # Система начисления
        st.markdown("---")
        st.markdown("### 💡 Система баллов")
        
        points_config = {
            "🏛️ Заседание": "10 баллов",
            "🧹 Субботник": "15 баллов", 
            "🤝 Общ. работа": "10 баллов",
            "❤️ Волонтерство": "12 баллов"
        }
        
        for activity, points in points_config.items():
            st.caption(f"{activity}: **{points}**")
        
        st.info("💫 Бонус за регулярность: +50%")
    
    # Обработка действий
    action = st.session_state.get('points_action', 'main')
    
    if action == "award":
        show_award_points_form(points_model, citizen_model, meeting_model)
    elif action == "leaderboard":
        show_leaderboard(points_model)
    elif action == "stats":
        show_points_statistics(points_model)
    elif action == "settings":
        show_points_settings(points_model)
    elif action == "citizen_details":
        citizen_id = st.session_state.get('citizen_details_id')
        if citizen_id:
            show_citizen_points_details(points_model, citizen_model, citizen_id)
        else:
            st.error("ID гражданина не найден")
            st.session_state.points_action = "main"
    else:
        show_points_main(points_model, citizen_model)


def show_points_main(points_model: PointsModel, citizen_model: CitizenModel):
    """Главная страница системы баллов"""
    
    st.markdown("### 🏆 Система поощрений")
    
    # Топ граждан
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🏆 Топ активных граждан")
        
        top_citizens = points_model.get_leaderboard(limit=10)
        
        if top_citizens:
            # Создаем красивое отображение топа
            for i, citizen in enumerate(top_citizens, 1):
                points = citizen.get('total_points', citizen.get('period_points', 0))
                activities = citizen.get('activities_count', 0)
                
                # Медали для топ-3
                if i == 1:
                    medal = "🥇"
                    color = "#FFD700"
                elif i == 2:
                    medal = "🥈" 
                    color = "#C0C0C0"
                elif i == 3:
                    medal = "🥉"
                    color = "#CD7F32"
                else:
                    medal = f"{i}."
                    color = "#f8f9fa"
                
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(45deg, {color}20, {color}10);
                        border-left: 4px solid {color};
                        padding: 15px;
                        border-radius: 8px;
                        margin: 8px 0;
                        display: flex;
                        align-items: center;
                    ">
                        <div style="font-size: 24px; margin-right: 15px;">{medal}</div>
                        <div style="flex-grow: 1;">
                            <b>{citizen['full_name']}</b><br>
                            <small>🏆 {points} баллов | 📊 {activities} активностей</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_view, col_award = st.columns([1, 1])
                    
                    with col_view:
                        if st.button("👁️ Подробнее", key=f"view_{citizen['id']}"):
                            st.session_state.points_action = "citizen_details"
                            st.session_state.citizen_details_id = citizen['id']
                            st.rerun()
                    
                    with col_award:
                        if st.button("🏆 Начислить", key=f"award_{citizen['id']}"):
                            st.session_state.points_action = "award"
                            st.session_state.selected_citizen_id = citizen['id']
                            st.rerun()
        else:
            st.info("🏆 Пока нет активных граждан с баллами")
    
    with col2:
        st.markdown("#### 📊 Статистика активности")
        
        # Получаем статистику за последний месяц
        monthly_stats = points_model.get_activity_statistics(30)
        
        if monthly_stats['by_activity_type']:
            # График активности по типам
            activity_data = monthly_stats['by_activity_type']
            
            # Переводим названия активностей
            activity_names = {
                'meeting_attendance': 'Заседания',
                'subbotnik': 'Субботники',
                'community_work': 'Общ. работы',
                'volunteer_work': 'Волонтерство',
                'initiative': 'Инициативы'
            }
            
            df_activity = pd.DataFrame(activity_data)
            df_activity['display_name'] = df_activity['activity_type'].map(
                lambda x: activity_names.get(x, x)
            )
            
            fig = px.pie(
                df_activity,
                values='total_points',
                names='display_name',
                title="Баллы по видам активности"
            )
            
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Баллы: %{value}<br>Процент: %{percent}<extra></extra>'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Нет данных за последний месяц")
        
        # Общие метрики за месяц
        totals = monthly_stats.get('totals', {})
        
        st.metric("📈 Активностей", totals.get('total_activities', 0))
        st.metric("⭐ Баллов начислено", totals.get('total_points_awarded', 0))
        st.metric("👥 Активных граждан", totals.get('active_citizens_count', 0))
    
    st.markdown("---")
    
    # Последние начисления
    st.markdown("#### 📋 Последние начисления баллов")
    
    recent_awards = get_recent_point_awards(points_model)
    
    if recent_awards:
        for award in recent_awards[:10]:
            show_point_award_card(award)
    else:
        st.info("📭 Недавних начислений нет")
    
    # Распределение граждан по баллам
    st.markdown("---")
    st.markdown("#### 📊 Распределение граждан по баллам")
    
    distribution = points_model.get_points_distribution()
    
    if distribution:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # График распределения
            fig = px.bar(
                x=list(distribution.keys()),
                y=list(distribution.values()),
                title="Количество граждан по диапазонам баллов",
                labels={'x': 'Диапазон баллов', 'y': 'Количество граждан'}
            )
            
            fig.update_layout(
                showlegend=False,
                xaxis_tickangle=-45
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Таблица с распределением
            df_dist = pd.DataFrame([
                {"Диапазон": k, "Граждан": v, "Процент": f"{v/sum(distribution.values())*100:.1f}%"}
                for k, v in distribution.items()
            ])
            
            st.dataframe(
                df_dist,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("📊 Нет данных для отображения распределения")


def show_award_points_form(points_model: PointsModel, citizen_model: CitizenModel, meeting_model: MeetingModel):
    """Форма начисления баллов"""
    
    st.markdown("### 🏆 Начисление баллов")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.points_action = "main"
            st.rerun()
    
    # Выбор типа начисления
    award_type = st.radio(
        "Тип начисления:",
        ["👤 Одному гражданину", "👥 Группе граждан", "🏛️ За участие в заседании"],
        help="Выберите способ начисления баллов"
    )
    
    if award_type == "👤 Одному гражданину":
        show_single_citizen_award_form(points_model, citizen_model)
    elif award_type == "👥 Группе граждан":
        show_bulk_award_form(points_model, citizen_model)
    elif award_type == "🏛️ За участие в заседании":
        show_meeting_award_form(points_model, citizen_model, meeting_model)


# def show_single_citizen_award_form(points_model: PointsModel, citizen_model: CitizenModel):
#     """Форма начисления баллов одному гражданину - исправленная версия"""
    
#     # Создаем meeting_model внутри функции
#     from models.meeting import MeetingModel
#     from utils.helpers import format_date
#     meeting_model = MeetingModel(citizen_model.db)
    
#     with st.form("single_award_form"):
#         col1, col2 = st.columns(2)
        
#         with col1:
#             # Выбор гражданина
#             try:
#                 st.write("🔍 Получаем список граждан...")
#                 citizens_raw = citizen_model.get_active_citizens()
#                 st.write(f"✅ Получено {len(citizens_raw)} граждан")
                
#                 # Преобразуем sqlite3.Row объекты в словари
#                 citizens = []
#                 for row in citizens_raw:
#                     try:
#                         # Преобразуем Row в словарь
#                         citizen_dict = dict(row)
#                         citizens.append(citizen_dict)
#                     except Exception as row_error:
#                         st.error(f"❌ Ошибка преобразования строки: {str(row_error)}")
#                         # Альтернативный способ - через индексы
#                         try:
#                             citizen_dict = {
#                                 'id': row[0],  # Предполагаем что id первый
#                                 'full_name': row[1] if len(row) > 1 else 'Неизвестно',
#                                 'total_points': row[2] if len(row) > 2 else 0
#                             }
#                             citizens.append(citizen_dict)
#                         except:
#                             st.error(f"❌ Не удалось обработать строку базы данных")
#                             continue
                
#                 # Проверяем структуру данных граждан
#                 if citizens:
#                     st.write("🔍 Структура первого гражданина:")
#                     first_citizen = citizens[0]
#                     st.write(f"Keys: {list(first_citizen.keys())}")
#                     st.write(f"Sample data: {first_citizen}")
                
#                 citizen_options = {}
#                 for c in citizens:
#                     try:
#                         # Теперь это должно работать
#                         if 'id' in c and 'full_name' in c:
#                             citizen_options[c['id']] = c['full_name']
#                         else:
#                             st.error(f"❌ У гражданина нет нужных полей: {c}")
#                     except Exception as citizen_error:
#                         st.error(f"❌ Ошибка обработки гражданина: {str(citizen_error)}")
                
#                 st.write(f"✅ Создан словарь с {len(citizen_options)} гражданами")
                
#             except Exception as e:
#                 st.error(f"❌ Ошибка получения граждан: {str(e)}")
#                 st.error(f"Тип ошибки: {type(e).__name__}")
#                 return
            
#             if not citizen_options:
#                 st.error("❌ Нет активных граждан в системе")
#                 return
            
#             selected_citizen_id = st.selectbox(
#                 "Выберите гражданина *",
#                 options=list(citizen_options.keys()),
#                 format_func=lambda x: citizen_options.get(x, f"ID: {x}"),
#                 help="Гражданин для начисления баллов"
#             )
            
#             st.write(f"🔍 Выбранный ID: {selected_citizen_id} (type: {type(selected_citizen_id)})")
            
#             # Показываем текущие баллы
#             if selected_citizen_id:
#                 try:
#                     citizen_raw = citizen_model.get_by_id(selected_citizen_id)
#                     if citizen_raw:
#                         # Преобразуем в словарь если это Row объект
#                         if hasattr(citizen_raw, 'keys'):
#                             citizen = dict(citizen_raw)
#                         else:
#                             citizen = citizen_raw
                        
#                         st.write(f"🔍 Данные гражданина: {citizen}")
#                         current_points = citizen.get('total_points', 0) or 0
#                         st.info(f"💰 Текущие баллы: **{current_points}**")
#                     else:
#                         st.warning("⚠️ Не удалось получить данные гражданина")
#                 except Exception as citizen_error:
#                     st.error(f"❌ Ошибка получения данных гражданина: {str(citizen_error)}")
            
#             # Тип активности
#             activity_types = {
#                 'meeting_attendance': {'display_name': 'Посещение заседания', 'points_value': 10},
#                 'subbotnik': {'display_name': 'Участие в субботнике', 'points_value': 15},
#                 'community_work': {'display_name': 'Общественная работа', 'points_value': 10},
#                 'volunteer_work': {'display_name': 'Волонтерская деятельность', 'points_value': 12},
#                 'initiative': {'display_name': 'Инициатива', 'points_value': 8}
#             }
            
#             selected_activity = st.selectbox(
#                 "Тип активности *",
#                 options=list(activity_types.keys()),
#                 format_func=lambda x: activity_types[x]['display_name'],
#                 help="Вид деятельности за который начисляются баллы"
#             )
            
#             default_points = activity_types[selected_activity]['points_value']
#             st.caption(f"💡 Стандартно: {default_points} баллов")
        
#         with col2:
#             # Количество баллов
#             use_custom_points = st.checkbox("Использовать другое количество баллов")
            
#             if use_custom_points:
#                 custom_points = st.number_input(
#                     "Количество баллов *",
#                     min_value=-1000,
#                     max_value=1000,
#                     value=default_points,
#                     help="Пользовательское количество баллов"
#                 )
#                 points_to_award = custom_points
#             else:
#                 points_to_award = default_points
#                 st.info(f"🏆 Будет начислено: **{points_to_award} баллов**")
            
#             # Описание
#             description = st.text_area(
#                 "Описание (опционально)",
#                 placeholder="Дополнительная информация о начислении",
#                 height=100,
#                 help="Комментарий к начислению баллов"
#             )
            
#             # Связь с заседанием - упрощенная версия
#             st.info("📭 Связь с заседаниями временно отключена для диагностики")
#             linked_meeting = None
        
#         # Кнопка отправки
#         submitted = st.form_submit_button(
#             f"🏆 Начислить {points_to_award} баллов",
#             use_container_width=True,
#             type="primary"
#         )
        
#         if submitted:
#             st.write("🔍 Начинаем процесс начисления баллов...")
            
#             if not selected_citizen_id or not selected_activity:
#                 st.error("❌ Заполните все обязательные поля")
#                 return
            
#             # Проверяем доступность ключей в citizen_options
#             try:
#                 st.write(f"🔍 Проверяем citizen_options для ID {selected_citizen_id}")
#                 st.write(f"citizen_options keys: {list(citizen_options.keys())}")
#                 st.write(f"selected_citizen_id in citizen_options: {selected_citizen_id in citizen_options}")
                
#                 if selected_citizen_id in citizen_options:
#                     citizen_name = citizen_options[selected_citizen_id]
#                     st.write(f"✅ Имя гражданина: {citizen_name}")
#                 else:
#                     st.error(f"❌ ID {selected_citizen_id} не найден в citizen_options!")
#                     st.write(f"Available IDs: {list(citizen_options.keys())}")
#                     return
                    
#             except Exception as name_error:
#                 st.error(f"❌ Ошибка получения имени гражданина: {str(name_error)}")
#                 st.error(f"Тип ошибки: {type(name_error).__name__}")
#                 return
            
#             # Начисляем баллы - максимально упрощенная версия
#             try:
#                 st.write("🔍 Начинаем SQL операцию...")
                
#                 # Фиксированный user ID для диагностики
#                 current_user_id = 1
#                 st.write(f"✅ Используем user ID: {current_user_id}")
                
#                 from datetime import datetime
                
#                 # Простейший SQL запрос
#                 insert_query = """
#                     INSERT INTO citizen_points 
#                     (citizen_id, activity_type, points, description, date_earned, created_by, created_at)
#                     VALUES (?, ?, ?, ?, ?, ?, ?)
#                 """
                
#                 today = datetime.now().date().isoformat()
#                 now = datetime.now().isoformat()
#                 desc = description.strip() if description else f"Начисление за {activity_types[selected_activity]['display_name']}"
                
#                 params = (
#                     int(selected_citizen_id),
#                     selected_activity,
#                     int(points_to_award),
#                     desc,
#                     today,
#                     current_user_id,
#                     now
#                 )
                
#                 st.write(f"🔍 SQL параметры: {params}")
                
#                 # Выполняем запрос
#                 result = points_model.db.execute_query(insert_query, params, fetch=False)
#                 st.write(f"✅ Результат SQL вставки: {result}")
                
#                 if result is not None:
#                     # Обновляем общие баллы гражданина
#                     update_query = """
#                         UPDATE citizens 
#                         SET total_points = (
#                             SELECT COALESCE(SUM(points), 0) 
#                             FROM citizen_points 
#                             WHERE citizen_id = ?
#                         )
#                         WHERE id = ?
#                     """
                    
#                     update_result = points_model.db.execute_query(
#                         update_query, 
#                         (int(selected_citizen_id), int(selected_citizen_id)), 
#                         fetch=False
#                     )
#                     st.write(f"✅ Результат обновления баллов: {update_result}")
                    
#                     show_success_message(f"✅ Начислено {points_to_award} баллов гражданину {citizen_name}")
                    
#                     # Показываем новые баллы
#                     try:
#                         updated_citizen = citizen_model.get_by_id(selected_citizen_id)
#                         if updated_citizen:
#                             new_total = updated_citizen.get('total_points', 0) or 0
#                             st.success(f"💰 Новый баланс: **{new_total} баллов**")
#                     except Exception as e:
#                         st.warning(f"Не удалось обновить отображение баланса: {str(e)}")
                    
#                     st.session_state.points_action = "main"
#                     st.rerun()
#                 else:
#                     show_error_message("❌ Ошибка при начислении баллов - SQL вернул None")
                    
#             except Exception as e:
#                 show_error_message(f"❌ Ошибка при начислении баллов: {str(e)}")
#                 st.error(f"Детали ошибки: {type(e).__name__}")
#                 if hasattr(e, 'args') and e.args:
#                     st.error(f"Аргументы ошибки: {e.args}")
                
#                 # Показываем stack trace для лучшей диагностики
#                 import traceback
#                 st.text("Stack trace:")
#                 st.code(traceback.format_exc())

def show_single_citizen_award_form(points_model: PointsModel, citizen_model: CitizenModel):
    """Форма начисления баллов одному гражданину - исправленная версия"""
    
    # Создаем meeting_model внутри функции
    from models.meeting import MeetingModel
    from utils.helpers import format_date
    meeting_model = MeetingModel(citizen_model.db)
    
    # Вспомогательная функция для безопасного получения значений из Row
    def safe_get(row_obj, key, default=None):
        """Безопасное получение значения из sqlite3.Row или dict"""
        try:
            if hasattr(row_obj, key):
                return getattr(row_obj, key)
            elif hasattr(row_obj, '__getitem__'):
                return row_obj[key]
            else:
                return default
        except (KeyError, AttributeError, IndexError):
            return default
    
    # Функция для преобразования Row в dict
    def row_to_dict(row):
        """Преобразование sqlite3.Row в словарь"""
        try:
            return dict(row)
        except:
            try:
                # Альтернативный способ
                result = {}
                for key in row.keys():
                    result[key] = row[key]
                return result
            except:
                return {}
    
    with st.form("single_award_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Выбор гражданина
            try:
                citizens_raw = citizen_model.get_active_citizens()
                
                # Преобразуем sqlite3.Row объекты в словари
                citizens = []
                citizen_options = {}
                
                for row in citizens_raw:
                    try:
                        citizen_dict = row_to_dict(row)
                        if citizen_dict and 'id' in citizen_dict and 'full_name' in citizen_dict:
                            citizens.append(citizen_dict)
                            citizen_options[citizen_dict['id']] = citizen_dict['full_name']
                    except:
                        # Если row_to_dict не работает, пробуем прямой доступ
                        try:
                            citizen_id = safe_get(row, 'id')
                            full_name = safe_get(row, 'full_name')
                            if citizen_id is not None and full_name is not None:
                                citizen_options[citizen_id] = full_name
                        except:
                            continue
                
            except Exception as e:
                st.error(f"❌ Ошибка получения граждан: {str(e)}")
                return
            
            if not citizen_options:
                st.error("❌ Нет активных граждан в системе")
                return
            
            selected_citizen_id = st.selectbox(
                "Выберите гражданина *",
                options=list(citizen_options.keys()),
                format_func=lambda x: citizen_options.get(x, f"ID: {x}"),
                help="Гражданин для начисления баллов"
            )
            
            # Показываем текущие баллы
            if selected_citizen_id:
                try:
                    citizen_raw = citizen_model.get_by_id(selected_citizen_id)
                    if citizen_raw:
                        current_points = safe_get(citizen_raw, 'total_points', 0) or 0
                        st.info(f"💰 Текущие баллы: **{current_points}**")
                except:
                    pass
            
            # Тип активности
            activity_types = {
                'meeting_attendance': {'display_name': 'Посещение заседания', 'points_value': 10},
                'subbotnik': {'display_name': 'Участие в субботнике', 'points_value': 15},
                'community_work': {'display_name': 'Общественная работа', 'points_value': 10},
                'volunteer_work': {'display_name': 'Волонтерская деятельность', 'points_value': 12},
                'initiative': {'display_name': 'Инициатива', 'points_value': 8}
            }
            
            selected_activity = st.selectbox(
                "Тип активности *",
                options=list(activity_types.keys()),
                format_func=lambda x: activity_types[x]['display_name'],
                help="Вид деятельности за который начисляются баллы"
            )
            
            default_points = activity_types[selected_activity]['points_value']
            st.caption(f"💡 Стандартно: {default_points} баллов")
        
        with col2:
            # Количество баллов
            use_custom_points = st.checkbox("Использовать другое количество баллов")
            
            if use_custom_points:
                custom_points = st.number_input(
                    "Количество баллов *",
                    min_value=-1000,
                    max_value=1000,
                    value=default_points,
                    help="Пользовательское количество баллов"
                )
                points_to_award = custom_points
            else:
                points_to_award = default_points
                st.info(f"🏆 Будет начислено: **{points_to_award} баллов**")
            
            # Описание
            description = st.text_area(
                "Описание (опционально)",
                placeholder="Дополнительная информация о начислении",
                height=100,
                help="Комментарий к начислению баллов"
            )
            
            # Связь с заседанием (упрощенная версия)
            try:
                recent_meetings = meeting_model.get_all(
                    "meeting_date >= date('now', '-30 days')",
                    order_by="meeting_date DESC"
                )
                
                if recent_meetings:
                    meeting_options = {None: "Не связано с заседанием"}
                    for m in recent_meetings:
                        try:
                            meeting_id = safe_get(m, 'id')
                            meeting_title = safe_get(m, 'title', 'Без названия')
                            meeting_date = safe_get(m, 'meeting_date', '')
                            
                            if meeting_id is not None:
                                try:
                                    formatted_date = format_date(meeting_date) if meeting_date else ''
                                    meeting_options[meeting_id] = f"{meeting_title} ({formatted_date})"
                                except:
                                    meeting_options[meeting_id] = meeting_title
                        except:
                            continue
                    
                    linked_meeting = st.selectbox(
                        "Связанное заседание",
                        options=list(meeting_options.keys()),
                        format_func=lambda x: meeting_options.get(x, "Неизвестно"),
                        help="Опционально: заседание, за которое начисляются баллы"
                    )
                else:
                    linked_meeting = None
                    st.info("📭 Нет недавних заседаний")
            except:
                linked_meeting = None
                st.info("📭 Заседания недоступны")
        
        # Кнопка отправки
        submitted = st.form_submit_button(
            f"🏆 Начислить {points_to_award} баллов",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            if not selected_citizen_id or not selected_activity:
                st.error("❌ Заполните все обязательные поля")
                return
            
            # Начисляем баллы
            try:
                # Получаем имя гражданина
                citizen_name = citizen_options.get(selected_citizen_id, "Неизвестный")
                
                # Фиксированный user ID
                current_user_id = 1
                
                from datetime import datetime
                
                # SQL запрос для начисления баллов
                insert_query = """
                    INSERT INTO citizen_points 
                    (citizen_id, activity_type, points, description, date_earned, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                today = datetime.now().date().isoformat()
                now = datetime.now().isoformat()
                desc = description.strip() if description else f"Начисление за {activity_types[selected_activity]['display_name']}"
                
                params = (
                    int(selected_citizen_id),
                    selected_activity,
                    int(points_to_award),
                    desc,
                    today,
                    current_user_id,
                    now
                )
                
                # Выполняем запрос
                result = points_model.db.execute_query(insert_query, params, fetch=False)
                
                if result is not None:
                    # Обновляем общие баллы гражданина
                    update_query = """
                        UPDATE citizens 
                        SET total_points = (
                            SELECT COALESCE(SUM(points), 0) 
                            FROM citizen_points 
                            WHERE citizen_id = ?
                        )
                        WHERE id = ?
                    """
                    
                    points_model.db.execute_query(
                        update_query, 
                        (int(selected_citizen_id), int(selected_citizen_id)), 
                        fetch=False
                    )
                    
                    show_success_message(f"✅ Начислено {points_to_award} баллов гражданину {citizen_name}")
                    
                    # Показываем новые баллы
                    try:
                        updated_citizen_raw = citizen_model.get_by_id(selected_citizen_id)
                        if updated_citizen_raw:
                            new_total = safe_get(updated_citizen_raw, 'total_points', 0) or 0
                            st.success(f"💰 Новый баланс: **{new_total} баллов**")
                    except:
                        pass
                    
                    st.session_state.points_action = "main"
                    st.rerun()
                else:
                    show_error_message("❌ Ошибка при начислении баллов")
                    
            except Exception as e:
                show_error_message(f"❌ Ошибка при начислении баллов: {str(e)}")


def show_bulk_award_form(points_model: PointsModel, citizen_model: CitizenModel):
    """Форма массового начисления баллов"""
    
    st.markdown("#### 👥 Массовое начисление баллов")
    
    with st.form("bulk_award_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Критерии отбора граждан
            selection_criteria = st.selectbox(
                "Кому начислить баллы:",
                ["Всем активным гражданам", "По возрастной группе", "С определенным количеством баллов"],
                help="Критерии для отбора получателей"
            )
            
            if selection_criteria == "По возрастной группе":
                age_group = st.selectbox(
                    "Возрастная группа:",
                    ["18-30 лет", "31-50 лет", "51-70 лет", "70+ лет"]
                )
            elif selection_criteria == "С определенным количеством баллов":
                points_range = st.selectbox(
                    "Диапазон баллов:",
                    ["0 баллов", "1-50 баллов", "51-100 баллов", "100+ баллов"]
                )
            
            # Тип активности - используем предопределенные типы (как в single_citizen_award_form)
            activity_types = {
                'meeting_attendance': {'display_name': 'Посещение заседания', 'points_value': 10},
                'subbotnik': {'display_name': 'Участие в субботнике', 'points_value': 15},
                'community_work': {'display_name': 'Общественная работа', 'points_value': 10},
                'volunteer_work': {'display_name': 'Волонтерская деятельность', 'points_value': 12},
                'initiative': {'display_name': 'Инициатива', 'points_value': 8}
            }
            
            selected_activity = st.selectbox(
                "Тип активности *",
                options=list(activity_types.keys()),
                format_func=lambda x: activity_types[x]['display_name'],
                help="Вид деятельности за который начисляются баллы"
            )
            
            # Получаем стандартное количество баллов
            default_points = activity_types[selected_activity]['points_value']
        
        with col2:
            # Количество баллов
            points_to_award = st.number_input(
                "Баллы каждому *",
                min_value=1,
                max_value=1000,
                value=default_points,
                help="Количество баллов для каждого получателя"
            )
            
            # Описание
            description = st.text_area(
                "Описание начисления *",
                placeholder="Например: Участие в общегородском субботнике",
                height=100
            )
            
            # Предварительный подсчет получателей
            recipient_count = get_bulk_recipients_count(citizen_model, selection_criteria)
            st.metric("👥 Получателей", recipient_count)
            st.metric("⭐ Всего баллов", recipient_count * points_to_award)
        
        # Кнопка отправки
        submitted = st.form_submit_button(
            f"🏆 Начислить баллы {recipient_count} гражданам",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            if not selected_activity or not description.strip():
                st.error("❌ Заполните все обязательные поля")
                return
            
            # Получаем список получателей
            recipients = get_bulk_recipients_list(citizen_model, selection_criteria)
            
            if not recipients:
                st.error("❌ Не найдено граждан по заданным критериям")
                return
            
            # Массовое начисление баллов - упрощенная версия
            try:
                # Получаем ID пользователя
                current_user_id = get_current_user_id()
                if isinstance(current_user_id, dict):
                    current_user_id = current_user_id.get('id', 1)
                elif current_user_id is None:
                    current_user_id = 1
                
                from datetime import datetime
                
                successful = 0
                failed = 0
                errors = []
                
                for recipient in recipients:
                    try:
                        # Добавляем запись о баллах для каждого получателя
                        query = """
                            INSERT INTO citizen_points 
                            (citizen_id, activity_type, points, description, date_earned, created_by, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        
                        params = (
                            recipient['id'],
                            selected_activity,
                            points_to_award,
                            description.strip(),
                            datetime.now().date().isoformat(),
                            current_user_id,
                            datetime.now().isoformat()
                        )
                        
                        result = points_model.db.execute_query(query, params, fetch=False)
                        
                        if result is not None:
                            # Обновляем общие баллы гражданина
                            update_query = """
                                UPDATE citizens 
                                SET total_points = (
                                    SELECT COALESCE(SUM(points), 0) 
                                    FROM citizen_points 
                                    WHERE citizen_id = ?
                                )
                                WHERE id = ?
                            """
                            
                            points_model.db.execute_query(
                                update_query, 
                                (recipient['id'], recipient['id']), 
                                fetch=False
                            )
                            
                            successful += 1
                        else:
                            failed += 1
                            errors.append(f"Ошибка для {recipient['full_name']}")
                            
                    except Exception as e:
                        failed += 1
                        errors.append(f"Ошибка для {recipient['full_name']}: {str(e)}")
                
                if successful > 0:
                    show_success_message(
                        f"✅ Успешно начислено баллов: {successful} гражданам. "
                        f"Ошибок: {failed}"
                    )
                    st.session_state.points_action = "main"
                    st.rerun()
                else:
                    show_error_message("❌ Ошибка при массовом начислении баллов")
                    if errors:
                        for error in errors[:5]:  # Показываем первые 5 ошибок
                            st.error(error)
                            
            except Exception as e:
                show_error_message(f"❌ Ошибка при массовом начислении баллов: {str(e)}")



def show_meeting_award_form(points_model: PointsModel, citizen_model: CitizenModel, meeting_model: MeetingModel):
    """Форма начисления баллов за участие в заседании"""
    
    st.markdown("#### 🏛️ Начисление за участие в заседании")
    
    # Выбор заседания
    recent_meetings = meeting_model.get_all(
        "meeting_date >= date('now', '-90 days') AND status = 'COMPLETED'",
        order_by="meeting_date DESC"
    )
    
    if not recent_meetings:
        st.warning("📭 Нет завершенных заседаний за последние 3 месяца")
        return
    
    meeting_options = {
        m['id']: f"{m['title']} ({format_date(m['meeting_date'])})"
        for m in recent_meetings
    }
    
    selected_meeting_id = st.selectbox(
        "Выберите заседание:",
        options=list(meeting_options.keys()),
        format_func=lambda x: meeting_options[x],
        help="Заседание для начисления баллов участникам"
    )
    
    if selected_meeting_id:
        # Получаем данные о посещаемости
        meeting_data = meeting_model.get_meeting_with_attendance(selected_meeting_id)
        
        if meeting_data:
            meeting = meeting_data['meeting']
            attendance_list = meeting_data['attendance']
            
            # Информация о заседании
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("👥 Всего участников", len(attendance_list))
            
            with col2:
                present_count = sum(1 for a in attendance_list if a['is_present'])
                st.metric("✅ Присутствовали", present_count)
            
            with col3:
                already_awarded = sum(1 for a in attendance_list if a['points_earned'])
                st.metric("🏆 Уже начислено", already_awarded)
            
            # Настройки начисления
            col1, col2 = st.columns(2)
            
            with col1:
                points_per_participant = st.number_input(
                    "Баллы за участие:",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="Количество баллов каждому участнику"
                )
                
                award_mode = st.radio(
                    "Кому начислить:",
                    ["Только присутствующим", "Всем участникам", "Только без баллов"],
                    help="Критерии для начисления баллов"
                )
            
            with col2:
                # Предварительный расчет
                if award_mode == "Только присутствующим":
                    eligible_count = sum(1 for a in attendance_list if a['is_present'] and not a['points_earned'])
                elif award_mode == "Всем участникам":
                    eligible_count = sum(1 for a in attendance_list if not a['points_earned'])
                else:  # Только без баллов
                    eligible_count = sum(1 for a in attendance_list if not a['points_earned'])
                
                st.metric("👥 Получат баллы", eligible_count)
                st.metric("⭐ Всего баллов", eligible_count * points_per_participant)
            
            # Кнопка начисления
            if st.button(
                f"🏆 Начислить {points_per_participant} баллов {eligible_count} участникам",
                use_container_width=True,
                type="primary"
            ):
                if eligible_count == 0:
                    st.warning("⚠️ Нет участников для начисления баллов")
                    return
                
                # Определяем кому начислять
                attendance_data = {}
                for attendance in attendance_list:
                    citizen_id = attendance['citizen_id']
                    
                    should_award = False
                    if award_mode == "Только присутствующим":
                        should_award = attendance['is_present'] and not attendance['points_earned']
                    elif award_mode == "Всем участникам":
                        should_award = not attendance['points_earned']
                    else:  # Только без баллов
                        should_award = not attendance['points_earned']
                    
                    if should_award:
                        attendance_data[citizen_id] = True
                
                # Начисляем баллы
                awarded_count = points_model.award_meeting_attendance_points(
                    selected_meeting_id, 
                    attendance_data
                )
                
                if awarded_count > 0:
                    show_success_message(f"✅ Баллы начислены {awarded_count} участникам заседания")
                    st.rerun()
                else:
                    show_error_message("❌ Ошибка при начислении баллов")


def show_leaderboard(points_model: PointsModel):
    """Отображение рейтинга граждан"""
    
    st.markdown("### 🏆 Рейтинг активных граждан")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.points_action = "main"
            st.rerun()
    
    # Настройки рейтинга
    col1, col2, col3 = st.columns(3)
    
    with col1:
        period = st.selectbox(
            "Период рейтинга:",
            ["За все время", "За год", "За квартал", "За месяц"],
            help="Временной период для подсчета баллов"
        )
    
    with col2:
        limit = st.selectbox(
            "Количество позиций:",
            [10, 20, 50, 100],
            help="Количество граждан в рейтинге"
        )
    
    with col3:
        export_format = st.selectbox(
            "Экспорт:",
            ["Не экспортировать", "Excel", "CSV"]
        )
    
    # Получаем рейтинг
    period_days = None
    if period == "За месяц":
        period_days = 30
    elif period == "За квартал":
        period_days = 90
    elif period == "За год":
        period_days = 365
    
    leaderboard = points_model.get_leaderboard(limit=limit, period_days=period_days)
    
    if leaderboard:
        # Отображаем рейтинг
        st.success(f"🏆 Рейтинг {period.lower()}: {len(leaderboard)} граждан")
        
        # Создаем DataFrame для отображения
        df_leaderboard = pd.DataFrame([dict(citizen) for citizen in leaderboard])
        
        # Добавляем позицию в рейтинге
        df_leaderboard['position'] = range(1, len(df_leaderboard) + 1)
        
        # Переименовываем колонки
        column_config = {
            "position": st.column_config.NumberColumn("🏆 Место", width="small"),
            "full_name": st.column_config.TextColumn("ФИО", width="medium"),
            "total_points": st.column_config.NumberColumn("⭐ Баллы", width="small") if period_days is None else None,
            "period_points": st.column_config.NumberColumn("⭐ Баллы", width="small") if period_days else None,
            "activities_count": st.column_config.NumberColumn("📊 Активностей", width="small"),
            "phone": st.column_config.TextColumn("📞 Телефон", width="medium"),
            "address": st.column_config.TextColumn("📍 Адрес", width="large")
        }
        
        # Убираем None значения
        column_config = {k: v for k, v in column_config.items() if v is not None}
        
        # Отображаем таблицу
        st.dataframe(
            df_leaderboard[list(column_config.keys())],
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )
        
        # Экспорт
        if export_format != "Не экспортировать":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"рейтинг_граждан_{timestamp}"
            
            if export_format == "Excel":
                create_excel_download_button(
                    df_leaderboard[list(column_config.keys())],
                    f"{filename}.xlsx",
                    "📥 Скачать рейтинг (Excel)"
                )
            else:  # CSV
                csv_data = df_leaderboard[list(column_config.keys())].to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📥 Скачать рейтинг (CSV)",
                    data=csv_data,
                    file_name=f"{filename}.csv",
                    mime="text/csv"
                )
    else:
        st.info("🏆 Нет данных для рейтинга")


def show_points_statistics(points_model: PointsModel):
    """Статистика системы баллов"""
    
    st.markdown("### 📈 Статистика системы баллов")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.points_action = "main"
            st.rerun()
    
    # Выбор периода
    period = st.selectbox(
        "Период анализа:",
        [30, 90, 180, 365],
        format_func=lambda x: f"За {x} дней",
        index=1
    )
    
    # Получаем статистику
    stats = points_model.get_activity_statistics(period)
    
    # Основные метрики
    totals = stats.get('totals', {})
    
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
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # Активность по типам
        activity_data = stats.get('by_activity_type', [])
        if activity_data:
            st.markdown("#### 📊 Активность по типам")
            
            df_activity = pd.DataFrame(activity_data)
            
            # Переводим названия
            activity_names = {
                'meeting_attendance': 'Заседания',
                'subbotnik': 'Субботники',
                'community_work': 'Общ. работы',
                'volunteer_work': 'Волонтерство',
                'initiative': 'Инициативы'
            }
            
            df_activity['display_name'] = df_activity['activity_type'].map(
                lambda x: activity_names.get(x, x)
            )
            
            fig = px.bar(
                df_activity,
                x='display_name',
                y='total_points',
                title="Баллы по видам активности",
                labels={'display_name': 'Тип активности', 'total_points': 'Всего баллов'}
            )
            
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных по активности")
    
    with col2:
        # Динамика по дням
        daily_data = stats.get('daily_breakdown', [])
        if daily_data:
            st.markdown("#### 📈 Динамика активности")
            
            df_daily = pd.DataFrame(daily_data)
            df_daily['date_earned'] = pd.to_datetime(df_daily['date_earned'])
            
            fig = px.line(
                df_daily,
                x='date_earned',
                y='points_awarded',
                title="Баллы по дням",
                labels={'date_earned': 'Дата', 'points_awarded': 'Баллы'},
                markers=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных по дням")
    
    # Месячная сводка
    st.markdown("---")
    st.markdown("#### 📋 Месячная сводка")
    
    current_date = datetime.now()
    monthly_summary = points_model.get_monthly_summary(current_date.year, current_date.month)
    
    if monthly_summary['top_citizens']:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏆 Топ граждан месяца:**")
            
            for i, citizen in enumerate(monthly_summary['top_citizens'][:5], 1):
                st.markdown(f"{i}. **{citizen['full_name']}** - {citizen['month_points']} баллов")
        
        with col2:
            st.markdown("**📊 Статистика месяца:**")
            
            month_totals = monthly_summary.get('totals', {})
            st.write(f"• Активностей: {month_totals.get('total_activities', 0)}")
            st.write(f"• Баллов начислено: {month_totals.get('total_points', 0)}")
            st.write(f"• Активных граждан: {month_totals.get('active_citizens', 0)}")
    else:
        st.info("📭 Нет данных за текущий месяц")


def show_points_settings(points_model: PointsModel):
    """Настройки системы баллов"""
    
    st.markdown("### ⚙️ Настройки системы баллов")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.points_action = "main"
            st.rerun()
    
    # Используем предопределенные типы активности
    activity_types = [
        {
            'name': 'meeting_attendance',
            'display_name': 'Посещение заседания',
            'points_value': 10,
            'description': 'Баллы за участие в заседаниях махалли',
            'is_active': True
        },
        {
            'name': 'subbotnik',
            'display_name': 'Участие в субботнике',
            'points_value': 15,
            'description': 'Баллы за участие в субботниках и уборке территории',
            'is_active': True
        },
        {
            'name': 'community_work',
            'display_name': 'Общественная работа',
            'points_value': 10,
            'description': 'Баллы за различные виды общественной деятельности',
            'is_active': True
        },
        {
            'name': 'volunteer_work',
            'display_name': 'Волонтерская деятельность',
            'points_value': 12,
            'description': 'Баллы за волонтерскую помощь и добровольную работу',
            'is_active': True
        },
        {
            'name': 'initiative',
            'display_name': 'Инициатива',
            'points_value': 8,
            'description': 'Баллы за проявление инициативы и предложения',
            'is_active': True
        }
    ]
    
    st.markdown("#### 📋 Типы активности и баллы")
    
    if activity_types:
        # Отображаем текущие типы активности
        for activity_type in activity_types:
            with st.expander(f"📌 {activity_type['display_name']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Системное имя:** {activity_type['name']}")
                    st.write(f"**Описание:** {activity_type['description']}")
                
                with col2:
                    st.metric("Баллы", activity_type['points_value'])
                
                with col3:
                    status = "✅ Активен" if activity_type['is_active'] else "❌ Неактивен"
                    st.write(f"**Статус:** {status}")
    else:
        st.info("📭 Нет настроенных типов активности")
    
    st.markdown("---")
    
    # Форма добавления нового типа активности (информационная)
    st.markdown("#### ➕ Добавить новый тип активности")
    
    st.info("💡 **Информация:** В данной версии системы типы активности предопределены. Для добавления новых типов обратитесь к администратору системы.")
    
    with st.form("add_activity_type_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            display_name = st.text_input(
                "Название *",
                placeholder="Например: Участие в мероприятии",
                help="Отображаемое название типа активности",
                disabled=True
            )
            
            name = st.text_input(
                "Системное имя *",
                placeholder="event_participation",
                help="Имя для использования в системе (латинские буквы, подчеркивания)",
                disabled=True
            )
        
        with col2:
            points_value = st.number_input(
                "Количество баллов *",
                min_value=1,
                max_value=1000,
                value=10,
                help="Стандартное количество баллов за этот тип активности",
                disabled=True
            )
            
            description = st.text_area(
                "Описание",
                placeholder="Подробное описание типа активности",
                help="Описание для справки администраторов",
                disabled=True
            )
        
        submitted = st.form_submit_button("➕ Добавить тип активности", use_container_width=True, disabled=True)
        
        if submitted:
            st.info("Функция добавления новых типов активности отключена в демо-версии")


def show_citizen_points_details(points_model: PointsModel, citizen_model: CitizenModel, citizen_id: int):
    """Подробная информация о баллах гражданина"""
    
    st.markdown("### 👤 Детали по баллам гражданина")
    
    # Получаем данные гражданина
    citizen = citizen_model.get_by_id(citizen_id)
    if not citizen:
        st.error("Гражданин не найден")
        st.session_state.points_action = "main"
        return
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад"):
            st.session_state.points_action = "main"
            st.rerun()
    
    with col2:
        st.info(f"Гражданин: {citizen['full_name']}")
    
    # Получаем достижения и статистику
    achievements = points_model.get_citizen_achievements(citizen_id)
    
    # Основная информация
    col1, col2, col3, col4 = st.columns(4)
    
    total_stats = achievements.get('total_stats', {})
    
    with col1:
        st.metric("⭐ Всего баллов", total_stats.get('total_points', 0))
    
    with col2:
        st.metric("📊 Активностей", total_stats.get('total_activities', 0))
    
    with col3:
        rank = achievements.get('rank')
        st.metric("🏆 Место в рейтинге", rank if rank else "Н/Д")
    
    with col4:
        first_activity = total_stats.get('first_activity')
        if first_activity:
            st.metric("📅 Первая активность", format_date(first_activity, 'short'))
    
    # Достижения
    achievements_list = achievements.get('achievements', [])
    if achievements_list:
        st.markdown("#### 🏅 Достижения")
        
        cols = st.columns(len(achievements_list))
        for i, achievement in enumerate(achievements_list):
            with cols[i % len(cols)]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(45deg, #FFD700, #FFA500);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    margin: 5px;
                ">
                    <h4>{achievement['name']}</h4>
                    <small>{achievement['description']}</small>
                </div>
                """, unsafe_allow_html=True)
    
    # История активности
    st.markdown("---")
    st.markdown("#### 📋 История активности")
    
    # Разбивка по типам активности
    activity_breakdown = achievements.get('activity_breakdown', [])
    if activity_breakdown:
        col1, col2 = st.columns(2)
        
        with col1:
            # График по типам активности
            df_breakdown = pd.DataFrame(activity_breakdown)
            
            activity_names = {
                'meeting_attendance': 'Заседания',
                'subbotnik': 'Субботники',
                'community_work': 'Общ. работы',
                'volunteer_work': 'Волонтерство',
                'initiative': 'Инициативы'
            }
            
            df_breakdown['display_name'] = df_breakdown['activity_type'].map(
                lambda x: activity_names.get(x, x)
            )
            
            fig = px.pie(
                df_breakdown,
                values='points',
                names='display_name',
                title="Баллы по типам активности"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Таблица с разбивкой
            st.markdown("**📊 Детализация по активности:**")
            
            for activity in activity_breakdown:
                activity_name = activity_names.get(activity['activity_type'], activity['activity_type'])
                st.markdown(f"• **{activity_name}**: {activity['count']} раз, {activity['points']} баллов")
    
    # Подробная история
    st.markdown("#### 📝 Подробная история начислений")
    
    points_history = points_model.get_citizen_points_history(citizen_id, limit=50)
    
    if points_history:
        # Фильтры
        col1, col2 = st.columns(2)
        
        with col1:
            activity_filter = st.selectbox(
                "Тип активности:",
                ["Все"] + list(set(h['activity_type'] for h in points_history))
            )
        
        with col2:
            period_filter = st.selectbox(
                "Период:",
                ["Все время", "За месяц", "За квартал", "За год"]
            )
        
        # Фильтруем историю
        filtered_history = filter_points_history(points_history, activity_filter, period_filter)
        
        if filtered_history:
            # Отображаем историю
            for record in filtered_history:
                show_point_record_card(record)
        else:
            st.info("📭 Нет записей по заданным фильтрам")
    else:
        st.info("📭 История начислений пуста")


# Вспомогательные функции

def get_quick_points_stats(points_model: PointsModel, citizen_model: CitizenModel) -> Dict[str, Any]:
    """Получение быстрой статистики системы баллов"""
    
    # Активные граждане с баллами
    active_citizens = citizen_model.count("is_active = 1 AND total_points > 0")
    
    # Общая сумма баллов
    total_points_query = "SELECT COALESCE(SUM(total_points), 0) as total FROM citizens WHERE is_active = 1"
    total_result = citizen_model.db.execute_query(total_points_query)
    total_points = total_result[0]['total'] if total_result else 0
    
    # Активности за месяц
    monthly_activities = points_model.count("date_earned >= date('now', '-30 days')")
    
    return {
        'active_citizens': active_citizens,
        'total_points': total_points,
        'monthly_activities': monthly_activities
    }


def get_recent_point_awards(points_model: PointsModel, limit: int = 10) -> List[Dict[str, Any]]:
    """Получение недавних начислений баллов"""
    
    query = """
        SELECT 
            cp.*,
            c.full_name,
            m.title as meeting_title
        FROM citizen_points cp
        JOIN citizens c ON cp.citizen_id = c.id
        LEFT JOIN meetings m ON cp.meeting_id = m.id
        ORDER BY cp.created_at DESC
        LIMIT ?
    """
    
    result = points_model.db.execute_query(query, (limit,))
    return [dict(row) for row in result] if result else []


def show_point_award_card(award: Dict[str, Any]):
    """Отображение карточки начисления баллов"""
    
    activity_icons = {
        'meeting_attendance': '🏛️',
        'subbotnik': '🧹',
        'community_work': '🤝',
        'volunteer_work': '❤️',
        'initiative': '💡'
    }
    
    icon = activity_icons.get(award['activity_type'], '⭐')
    points = award['points']
    
    color = "green" if points > 0 else "red"
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"{icon} **{award['full_name']}**")
            
            if award['description']:
                st.caption(f"📝 {award['description']}")
            
            if award['meeting_title']:
                st.caption(f"🏛️ {award['meeting_title']}")
        
        with col2:
            st.markdown(f"""
            <div style="
                color: {color};
                font-size: 18px;
                font-weight: bold;
                text-align: center;
            ">
                {'+' if points > 0 else ''}{points} баллов
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.caption(format_datetime(award['created_at'], 'short'))
        
        st.markdown("---")


def show_point_record_card(record: Dict[str, Any]):
    """Отображение карточки записи в истории баллов"""
    
    activity_names = {
        'meeting_attendance': '🏛️ Заседание',
        'subbotnik': '🧹 Субботник',
        'community_work': '🤝 Общественная работа',
        'volunteer_work': '❤️ Волонтерство',
        'initiative': '💡 Инициатива'
    }
    
    activity_name = activity_names.get(record['activity_type'], record['activity_type'])
    points = record['points']
    
    with st.expander(f"{activity_name} - {points} баллов ({format_date(record['date_earned'])})"):
        if record['description']:
            st.write(f"**Описание:** {record['description']}")
        
        if record['meeting_title']:
            st.write(f"**Связанное заседание:** {record['meeting_title']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Дата:** {format_date(record['date_earned'])}")
        
        with col2:
            st.write(f"**Начислено:** {format_datetime(record['created_at'])}")


def get_bulk_recipients_count(citizen_model: CitizenModel, selection_criteria: str) -> int:
    """Подсчет получателей для массового начисления"""
    
    if selection_criteria == "Всем активным гражданам":
        return citizen_model.count("is_active = 1")
    elif selection_criteria == "По возрастной группе":
        # Упрощенная логика для демо
        return citizen_model.count("is_active = 1 AND birth_date IS NOT NULL") // 2
    elif selection_criteria == "С определенным количеством баллов":
        # Упрощенная логика для демо
        return citizen_model.count("is_active = 1") // 3
    else:
        return 0


def get_bulk_recipients_list(citizen_model: CitizenModel, selection_criteria: str) -> List[Dict[str, Any]]:
    """Получение списка получателей для массового начисления"""
    
    if selection_criteria == "Всем активным гражданам":
        return citizen_model.get_active_citizens()
    elif selection_criteria == "По возрастной группе":
        # Упрощенная логика - берем первую половину граждан
        all_citizens = citizen_model.get_active_citizens()
        return all_citizens[:len(all_citizens)//2]
    elif selection_criteria == "С определенным количеством баллов":
        # Упрощенная логика - берем каждого третьего
        all_citizens = citizen_model.get_active_citizens()
        return all_citizens[::3]
    else:
        return []


def filter_points_history(history: List[Dict], activity_filter: str, period_filter: str) -> List[Dict]:
    """Фильтрация истории начислений"""
    
    filtered = history
    
    # Фильтр по типу активности
    if activity_filter != "Все":
        filtered = [h for h in filtered if h['activity_type'] == activity_filter]
    
    # Фильтр по периоду
    if period_filter != "Все время":
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if period_filter == "За месяц":
            cutoff = now - timedelta(days=30)
        elif period_filter == "За квартал":
            cutoff = now - timedelta(days=90)
        elif period_filter == "За год":
            cutoff = now - timedelta(days=365)
        else:
            cutoff = None
        
        if cutoff:
            filtered = [
                h for h in filtered 
                if datetime.fromisoformat(h['created_at'].replace('Z', '+00:00')) >= cutoff
            ]
    
    return filtered