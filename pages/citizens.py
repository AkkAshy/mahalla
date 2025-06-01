"""
Страница управления гражданами махалли
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from config.database import DatabaseManager
from models.citizen import CitizenModel
from utils.helpers import (
    format_phone, format_date, Paginator, 
    create_excel_download_button, show_success_message, show_error_message
)
from utils.auth import get_current_user_id, has_permission
from utils.validators import validate_citizen_data, StreamlitValidationHelper

def show_citizens_page():
    """Главная функция страницы граждан"""
    
    st.markdown("# 👥 Управление гражданами")
    st.markdown("---")
    
    # Проверяем права доступа
    if not has_permission('citizens'):
        st.error("❌ У вас нет прав доступа к этому разделу")
        return
    
    # Инициализируем модель
    db = DatabaseManager()
    citizen_model = CitizenModel(db)
    
    # Боковая панель с действиями
    with st.sidebar:
        st.markdown("### 🔧 Действия")
        
        if st.button("➕ Добавить гражданина", use_container_width=True):
            st.session_state.citizen_action = "add"
        
        if st.button("📊 Статистика", use_container_width=True):
            st.session_state.citizen_action = "stats"
        
        if st.button("📥 Экспорт в Excel", use_container_width=True):
            st.session_state.citizen_action = "export"
        
        st.markdown("---")
        
        # Фильтры
        st.markdown("### 🔍 Фильтры")
        
        search_term = st.text_input(
            "Поиск", 
            placeholder="ФИО, телефон, адрес...",
            help="Поиск по ФИО, номеру телефона, адресу или паспорту"
        )
        
        # Дополнительные фильтры
        with st.expander("Дополнительные фильтры"):
            age_filter = st.selectbox(
                "Возрастная группа",
                ["Все", "До 18", "18-30", "31-50", "51-70", "70+"]
            )
            
            points_filter = st.selectbox(
                "По баллам",
                ["Все", "Без баллов", "1-50", "51-100", "100+"]
            )
            
            phone_filter = st.checkbox("Только с телефонами")
    
    # Обработка действий
    action = st.session_state.get('citizen_action', 'list')
    
    if action == "add":
        show_add_citizen_form(citizen_model)
    elif action == "edit":
        citizen_id = st.session_state.get('edit_citizen_id')
        if citizen_id:
            show_edit_citizen_form(citizen_model, citizen_id)
        else:
            st.error("ID гражданина не найден")
            st.session_state.citizen_action = "list"
    elif action == "stats":
        show_citizens_statistics(citizen_model)
    elif action == "export":
        handle_export(citizen_model)
    else:
        show_citizens_list(
            citizen_model, 
            search_term, 
            age_filter, 
            points_filter, 
            phone_filter
        )


def show_citizens_list(
    citizen_model: CitizenModel, 
    search_term: str, 
    age_filter: str, 
    points_filter: str, 
    phone_filter: bool
):
    """Отображение списка граждан с фильтрацией"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📋 Список граждан")
    
    with col2:
        if st.button("🔄 Обновить", use_container_width=True):
            st.rerun()
    
    # Формируем условия поиска
    where_conditions = ["is_active = 1"]
    params = []
    
    # Текстовый поиск
    if search_term:
        search_conditions = [
            "UPPER(full_name) LIKE UPPER(?)",
            "phone LIKE ?",
            "UPPER(address) LIKE UPPER(?)",
            "UPPER(passport_data) LIKE UPPER(?)"
        ]
        where_conditions.append(f"({' OR '.join(search_conditions)})")
        search_param = f"%{search_term}%"
        params.extend([search_param] * 4)
    
    # Фильтр по возрасту
    if age_filter != "Все":
        age_condition = get_age_filter_condition(age_filter)
        if age_condition:
            where_conditions.append(age_condition)
    
    # Фильтр по баллам
    if points_filter != "Все":
        points_condition = get_points_filter_condition(points_filter)
        if points_condition:
            where_conditions.append(points_condition)
    
    # Фильтр по телефонам
    if phone_filter:
        where_conditions.append("phone IS NOT NULL AND phone != ''")
    
    # Выполняем запрос
    where_clause = " AND ".join(where_conditions)
    citizens = citizen_model.get_all(where_clause, tuple(params), "full_name")
    
    if not citizens:
        st.info("👥 Граждане не найдены по заданным критериям")
        return
    
    # Показываем количество найденных записей
    st.success(f"✅ Найдено граждан: {len(citizens)}")
    
    # Пагинация
    paginator = Paginator(citizens, items_per_page=20)
    current_page = paginator.show_pagination_controls("citizens_pagination")
    page_citizens = paginator.get_page(current_page)
    
    # Отображаем список граждан
    for citizen in page_citizens:
        show_citizen_card(citizen, citizen_model)


def show_citizen_card(citizen: Dict[str, Any], citizen_model: CitizenModel):
    """Отображение карточки гражданина"""
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            st.markdown(f"**{citizen['full_name']}**")
            
            if citizen['birth_date']:
                age = calculate_age(citizen['birth_date'])
                st.caption(f"🎂 {format_date(citizen['birth_date'])} ({age} лет)")
            
            if citizen['address']:
                st.caption(f"📍 {citizen['address']}")
        
        with col2:
            if citizen['phone']:
                st.caption(f"📞 {format_phone(citizen['phone'])}")
            
            if citizen['passport_data']:
                st.caption(f"🆔 {citizen['passport_data']}")
        
        with col3:
            points = citizen['total_points'] or 0
            if points > 0:
                st.success(f"⭐ {points} баллов")
            else:
                st.info("0 баллов")
        
        with col4:
            if st.button("✏️", key=f"edit_{citizen['id']}", help="Редактировать"):
                st.session_state.citizen_action = "edit"
                st.session_state.edit_citizen_id = citizen['id']
                st.rerun()
            
            if st.button("🗑️", key=f"delete_{citizen['id']}", help="Удалить"):
                if st.session_state.get(f"confirm_delete_{citizen['id']}"):
                    # Подтверждение удаления
                    success = citizen_model.deactivate_citizen(
                        citizen['id'], 
                        "Удален через интерфейс"
                    )
                    if success:
                        show_success_message("Гражданин успешно удален")
                        st.rerun()
                    else:
                        show_error_message("Ошибка при удалении гражданина")
                else:
                    st.session_state[f"confirm_delete_{citizen['id']}"] = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения удаления")
        
        st.markdown("---")


def show_add_citizen_form(citizen_model: CitizenModel):
    """Форма добавления нового гражданина"""
    
    st.markdown("### ➕ Добавление нового гражданина")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.citizen_action = "list"
            st.rerun()
    
    with col2:
        st.empty()
    
    with st.form("add_citizen_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "ФИО *",
                placeholder="Иванов Иван Иванович",
                help="Полное имя гражданина"
            )
            
            birth_date = st.date_input(
                "Дата рождения",
                value=None,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
                help="Дата рождения гражданина"
            )
            
            phone = st.text_input(
                "Номер телефона",
                placeholder="+998901234567",
                help="Номер телефона для SMS-уведомлений"
            )
        
        with col2:
            address = st.text_area(
                "Адрес проживания",
                placeholder="ул. Навои, дом 123, кв. 45",
                help="Полный адрес проживания",
                height=100
            )
            
            passport_data = st.text_input(
                "Паспортные данные",
                placeholder="AB1234567",
                help="Серия и номер паспорта"
            )
            
            notes = st.text_area(
                "Дополнительные заметки",
                placeholder="Любая дополнительная информация",
                height=100
            )
        
        submitted = st.form_submit_button("💾 Добавить гражданина", use_container_width=True)
        
        if submitted:
            # Подготавливаем данные
            citizen_data = {
                'full_name': full_name.strip() if full_name else '',
                'birth_date': birth_date,
                'address': address.strip() if address else '',
                'phone': phone.strip() if phone else '',
                'passport_data': passport_data.strip().upper() if passport_data else '',
                'notes': notes.strip() if notes else ''
            }
            
            # Валидация
            if StreamlitValidationHelper.validate_and_show(citizen_data, validate_citizen_data):
                # Добавляем гражданина
                citizen_id = citizen_model.add_citizen(
                    full_name=citizen_data['full_name'],
                    birth_date=citizen_data['birth_date'],
                    address=citizen_data['address'],
                    phone=citizen_data['phone'],
                    passport_data=citizen_data['passport_data'],
                    notes=citizen_data['notes']
                )
                
                if citizen_id:
                    show_success_message(f"Гражданин {full_name} успешно добавлен!")
                    st.session_state.citizen_action = "list"
                    st.rerun()
                else:
                    show_error_message("Ошибка при добавлении гражданина")


def show_edit_citizen_form(citizen_model: CitizenModel, citizen_id: int):
    """Форма редактирования гражданина"""
    
    st.markdown("### ✏️ Редактирование данных гражданина")
    
    # Получаем данные гражданина
    citizen = citizen_model.get_by_id(citizen_id)
    if not citizen:
        st.error("Гражданин не найден")
        st.session_state.citizen_action = "list"
        return
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.citizen_action = "list"
            st.rerun()
    
    with col2:
        st.info(f"Редактирование: {citizen['full_name']}")
    
    with st.form("edit_citizen_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "ФИО *",
                value=citizen['full_name'],
                help="Полное имя гражданина"
            )
            
            current_birth_date = None
            if citizen['birth_date']:
                try:
                    current_birth_date = datetime.strptime(citizen['birth_date'], '%Y-%m-%d').date()
                except:
                    pass
            
            birth_date = st.date_input(
                "Дата рождения",
                value=current_birth_date,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
                help="Дата рождения гражданина"
            )
            
            phone = st.text_input(
                "Номер телефона",
                value=citizen['phone'] or '',
                help="Номер телефона для SMS-уведомлений"
            )
        
        with col2:
            address = st.text_area(
                "Адрес проживания",
                value=citizen['address'] or '',
                help="Полный адрес проживания",
                height=100
            )
            
            passport_data = st.text_input(
                "Паспортные данные",
                value=citizen['passport_data'] or '',
                help="Серия и номер паспорта"
            )
            
            notes = st.text_area(
                "Дополнительные заметки",
                value=citizen['notes'] or '',
                height=100
            )
        
        col_save, col_delete = st.columns([3, 1])
        
        with col_save:
            submitted = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
        
        with col_delete:
            delete_clicked = st.form_submit_button("🗑️ Удалить", use_container_width=True, type="secondary")
        
        if submitted:
            # Подготавливаем данные для обновления
            update_data = {
                'full_name': full_name.strip(),
                'birth_date': birth_date,
                'address': address.strip(),
                'phone': phone.strip(),
                'passport_data': passport_data.strip().upper(),
                'notes': notes.strip()
            }
            
            # Валидация
            if StreamlitValidationHelper.validate_and_show(update_data, validate_citizen_data):
                # Обновляем данные
                success = citizen_model.update_citizen(citizen_id, **update_data)
                
                if success:
                    show_success_message("Данные гражданина успешно обновлены!")
                    st.session_state.citizen_action = "list"
                    st.rerun()
                else:
                    show_error_message("Ошибка при обновлении данных")
        
        if delete_clicked:
            success = citizen_model.deactivate_citizen(
                citizen_id, 
                "Удален через интерфейс редактирования"
            )
            if success:
                show_success_message("Гражданин успешно удален")
                st.session_state.citizen_action = "list"
                st.rerun()
            else:
                show_error_message("Ошибка при удалении гражданина")


def show_citizens_statistics(citizen_model: CitizenModel):
    """Отображение статистики по гражданам"""
    
    st.markdown("### 📊 Статистика по гражданам")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.citizen_action = "list"
            st.rerun()
    
    # Получаем статистику
    stats = citizen_model.get_statistics()
    
    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Всего граждан", stats.get('active_count', 0))
    
    with col2:
        st.metric("📱 С телефонами", stats.get('with_phones', 0))
    
    with col3:
        avg_age = stats.get('average_age', 0)
        st.metric("📊 Средний возраст", f"{avg_age} лет" if avg_age else "Н/Д")
    
    with col4:
        st.metric("📈 За месяц", stats.get('recent_count', 0))
    
    st.markdown("---")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        # Возрастные группы
        age_groups = stats.get('age_groups', {})
        if age_groups:
            st.markdown("#### 👨‍👩‍👧‍👦 Возрастные группы")
            
            import plotly.express as px
            fig = px.pie(
                values=list(age_groups.values()),
                names=list(age_groups.keys()),
                title="Распределение по возрасту"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о возрастных группах")
    
    with col2:
        # Топ по баллам
        top_citizens = stats.get('top_by_points', [])
        if top_citizens:
            st.markdown("#### 🏆 Топ по баллам")
            
            df = pd.DataFrame(top_citizens)
            st.dataframe(
                df,
                column_config={
                    "full_name": "ФИО",
                    "total_points": st.column_config.NumberColumn(
                        "Баллы",
                        help="Общее количество баллов"
                    )
                },
                use_container_width=True
            )
        else:
            st.info("Нет данных о баллах граждан")


def handle_export(citizen_model: CitizenModel):
    """Обработка экспорта данных"""
    
    st.markdown("### 📥 Экспорт данных граждан")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← Назад к списку"):
            st.session_state.citizen_action = "list"
            st.rerun()
    
    # Настройки экспорта
    col1, col2 = st.columns(2)
    
    with col1:
        include_inactive = st.checkbox(
            "Включить неактивных граждан",
            help="Включить в экспорт удаленных граждан"
        )
        
        export_format = st.selectbox(
            "Формат экспорта",
            ["Excel (.xlsx)", "CSV (.csv)"],
            help="Выберите формат для экспорта"
        )
    
    with col2:
        # Дополнительные настройки
        st.markdown("**Дополнительные поля:**")
        include_notes = st.checkbox("Включить заметки", value=True)
        include_creation_date = st.checkbox("Включить дату регистрации", value=True)
    
    if st.button("📥 Экспортировать данные", use_container_width=True):
        # Получаем данных для экспорта
        where_clause = "" if include_inactive else "is_active = 1"
        citizens = citizen_model.get_all(where_clause, order_by="full_name")
        
        if not citizens:
            st.warning("Нет данных для экспорта")
            return
        
        # Преобразуем в DataFrame
        df = citizen_model.to_dataframe(citizens)
        
        # Настраиваем колонки
        columns_config = {
            'id': 'ID',
            'full_name': 'ФИО',
            'birth_date': 'Дата рождения',
            'address': 'Адрес',
            'phone': 'Телефон',
            'passport_data': 'Паспорт',
            'registration_date': 'Дата регистрации',
            'total_points': 'Баллы',
            'is_active': 'Активен'
        }
        
        if include_notes:
            columns_config['notes'] = 'Заметки'
        
        # Фильтруем и переименовываем колонки
        export_columns = list(columns_config.keys())
        if not include_creation_date:
            export_columns.remove('registration_date')
            del columns_config['registration_date']
        
        df_export = df[export_columns].rename(columns=columns_config)
        
        # Форматируем данные
        if 'Дата рождения' in df_export.columns:
            df_export['Дата рождения'] = pd.to_datetime(df_export['Дата рождения'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        if 'Дата регистрации' in df_export.columns:
            df_export['Дата регистрации'] = pd.to_datetime(df_export['Дата регистрации'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        if 'Активен' in df_export.columns:
            df_export['Активен'] = df_export['Активен'].map({1: 'Да', 0: 'Нет'})
        
        # Экспорт
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format.startswith("Excel"):
            filename = f"граждане_махалли_{timestamp}.xlsx"
            create_excel_download_button(df_export, filename, "📥 Скачать Excel файл")
        else:
            filename = f"граждане_махалли_{timestamp}.csv"
            csv_data = df_export.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 Скачать CSV файл",
                data=csv_data,
                file_name=filename,
                mime="text/csv"
            )
        
        st.success(f"✅ Подготовлено {len(df_export)} записей для экспорта")


# Вспомогательные функции

def get_age_filter_condition(age_filter: str) -> str:
    """Получение условия для фильтрации по возрасту"""
    
    age_conditions = {
        "До 18": "(julianday('now') - julianday(birth_date))/365.25 < 18",
        "18-30": "(julianday('now') - julianday(birth_date))/365.25 BETWEEN 18 AND 30",
        "31-50": "(julianday('now') - julianday(birth_date))/365.25 BETWEEN 31 AND 50", 
        "51-70": "(julianday('now') - julianday(birth_date))/365.25 BETWEEN 51 AND 70",
        "70+": "(julianday('now') - julianday(birth_date))/365.25 > 70"
    }
    
    return age_conditions.get(age_filter, "")


def get_points_filter_condition(points_filter: str) -> str:
    """Получение условия для фильтрации по баллам"""
    
    points_conditions = {
        "Без баллов": "total_points = 0",
        "1-50": "total_points BETWEEN 1 AND 50",
        "51-100": "total_points BETWEEN 51 AND 100",
        "100+": "total_points > 100"
    }
    
    return points_conditions.get(points_filter, "")


def calculate_age(birth_date_str: str) -> int:
    """Вычисление возраста по дате рождения"""
    
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date.year
        
        # Корректируем если день рождения еще не прошел в этом году
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        
        return age
    except:
        return 0