"""
Вспомогательные функции для системы управления махалли
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date, timedelta
import re
import logging
import io
import base64

logger = logging.getLogger(__name__)

# ============== ФОРМАТИРОВАНИЕ ДАННЫХ ==============

def format_phone(phone: str) -> str:
    """
    Форматирование номера телефона
    
    Args:
        phone: Исходный номер
        
    Returns:
        Отформатированный номер
    """
    if not phone:
        return ""
    
    # Удаляем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d\+]', '', phone)
    
    # Приводим к формату +998 (XX) XXX-XX-XX
    if clean_phone.startswith('+998') and len(clean_phone) == 13:
        return f"{clean_phone[:4]} ({clean_phone[4:6]}) {clean_phone[6:9]}-{clean_phone[9:11]}-{clean_phone[11:]}"
    elif clean_phone.startswith('998') and len(clean_phone) == 12:
        return f"+{clean_phone[:3]} ({clean_phone[3:5]}) {clean_phone[5:8]}-{clean_phone[8:10]}-{clean_phone[10:]}"
    
    return phone


def format_date(date_value: Union[str, date, datetime], format_type: str = "short") -> str:
    """
    Форматирование даты
    
    Args:
        date_value: Дата для форматирования
        format_type: Тип форматирования (short, long, relative)
        
    Returns:
        Отформатированная дата
    """
    if not date_value:
        return ""
    
    # Преобразуем к объекту date
    if isinstance(date_value, str):
        try:
            date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            try:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                return str(date_value)
    elif isinstance(date_value, datetime):
        date_obj = date_value.date()
    else:
        date_obj = date_value
    
    if format_type == "short":
        return date_obj.strftime("%d.%m.%Y")
    elif format_type == "long":
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year} г."
    elif format_type == "relative":
        today = date.today()
        diff = (today - date_obj).days
        
        if diff == 0:
            return "Сегодня"
        elif diff == 1:
            return "Вчера"
        elif diff == -1:
            return "Завтра"
        elif -7 <= diff <= 7:
            days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            return days[date_obj.weekday()]
        else:
            return format_date(date_value, "short")
    
    return str(date_obj)


def format_datetime(datetime_value: Union[str, datetime], format_type: str = "short") -> str:
    """
    Форматирование даты и времени
    
    Args:
        datetime_value: Дата и время для форматирования
        format_type: Тип форматирования
        
    Returns:
        Отформатированная дата и время
    """
    if not datetime_value:
        return ""
    
    # Преобразуем к объекту datetime
    if isinstance(datetime_value, str):
        try:
            dt_obj = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt_obj = datetime.strptime(datetime_value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return str(datetime_value)
    else:
        dt_obj = datetime_value
    
    if format_type == "short":
        return dt_obj.strftime("%d.%m.%Y %H:%M")
    elif format_type == "long":
        return dt_obj.strftime("%d %B %Y г. в %H:%M")
    elif format_type == "time_only":
        return dt_obj.strftime("%H:%M")
    
    return str(dt_obj)


def format_currency(amount: float, currency: str = "сум") -> str:
    """
    Форматирование денежной суммы
    
    Args:
        amount: Сумма
        currency: Валюта
        
    Returns:
        Отформатированная сумма
    """
    if amount is None:
        return "0"
    
    # Форматируем с разделителями тысяч
    formatted = f"{amount:,.0f}".replace(",", " ")
    return f"{formatted} {currency}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезание текста с добавлением суффикса
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        Обрезанный текст
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Форматирование размера файла
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированный размер
    """
    if size_bytes == 0:
        return "0 Б"
    
    units = ["Б", "КБ", "МБ", "ГБ"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


# ============== РАБОТА С ДАННЫМИ ==============

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Безопасное получение значения из словаря
    
    Args:
        data: Словарь с данными
        key: Ключ
        default: Значение по умолчанию
        
    Returns:
        Значение или default
    """
    return data.get(key, default) if data else default


def clean_dict(data: Dict[str, Any], remove_none: bool = True, remove_empty: bool = True) -> Dict[str, Any]:
    """
    Очистка словаря от пустых значений
    
    Args:
        data: Исходный словарь
        remove_none: Удалять None значения
        remove_empty: Удалять пустые строки
        
    Returns:
        Очищенный словарь
    """
    cleaned = {}
    
    for key, value in data.items():
        if remove_none and value is None:
            continue
        if remove_empty and isinstance(value, str) and not value.strip():
            continue
        
        cleaned[key] = value
    
    return cleaned


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Объединение нескольких словарей
    
    Args:
        *dicts: Словари для объединения
        
    Returns:
        Объединенный словарь
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def group_by_key(items: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Группировка списка словарей по ключу
    
    Args:
        items: Список словарей
        key: Ключ для группировки
        
    Returns:
        Сгруппированные данные
    """
    groups = {}
    
    for item in items:
        group_key = item.get(key)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    
    return groups


# ============== STREAMLIT ХЕЛПЕРЫ ==============

def show_success_message(message: str, duration: int = 3):
    """
    Показ сообщения об успехе
    
    Args:
        message: Текст сообщения
        duration: Длительность показа (секунды)
    """
    placeholder = st.empty()
    placeholder.success(f"✅ {message}")
    
    # Можно добавить автоматическое скрытие через время
    # но в streamlit это сложно реализовать без перезагрузки


def show_error_message(message: str, details: Optional[str] = None):
    """
    Показ сообщения об ошибке
    
    Args:
        message: Текст сообщения
        details: Детали ошибки
    """
    st.error(f"❌ {message}")
    
    if details:
        with st.expander("Подробности ошибки"):
            st.code(details)


def show_info_message(message: str, icon: str = "💡"):
    """
    Показ информационного сообщения
    
    Args:
        message: Текст сообщения
        icon: Иконка
    """
    st.info(f"{icon} {message}")


def create_download_link(data: Union[str, bytes], filename: str, mime_type: str = "text/plain") -> str:
    """
    Создание ссылки для скачивания
    
    Args:
        data: Данные для скачивания
        filename: Имя файла
        mime_type: MIME тип
        
    Returns:
        HTML ссылка для скачивания
    """
    if isinstance(data, str):
        data = data.encode()
    
    b64_data = base64.b64encode(data).decode()
    
    return f'''
    <a href="data:{mime_type};base64,{b64_data}" download="{filename}">
        📥 Скачать {filename}
    </a>
    '''


def create_metrics_row(metrics: List[Dict[str, Any]], columns_count: int = 4):
    """
    Создание строки метрик
    
    Args:
        metrics: Список метрик с данными
        columns_count: Количество колонок
    """
    cols = st.columns(columns_count)
    
    for i, metric in enumerate(metrics):
        col_index = i % columns_count
        
        with cols[col_index]:
            st.metric(
                label=metric.get('label', ''),
                value=metric.get('value', 0),
                delta=metric.get('delta'),
                help=metric.get('help')
            )


def create_status_badge(status: str, status_config: Dict[str, Dict[str, str]]) -> str:
    """
    Создание цветного бейджа для статуса
    
    Args:
        status: Статус
        status_config: Конфигурация статусов
        
    Returns:
        HTML бейдж
    """
    config = status_config.get(status, {'color': 'gray', 'text': status})
    
    return f'''
    <span style="
        background-color: {config['color']};
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    ">
        {config['text']}
    </span>
    '''


# ============== РАБОТА С ФАЙЛАМИ ==============

def save_uploaded_file(uploaded_file, upload_dir: str = "uploads") -> Optional[str]:
    """
    Сохранение загруженного файла
    
    Args:
        uploaded_file: Файл из Streamlit
        upload_dir: Директория для сохранения
        
    Returns:
        Путь к сохраненному файлу или None
    """
    import os
    from pathlib import Path
    
    if not uploaded_file:
        return None
    
    try:
        # Создаем директорию если не существует
        Path(upload_dir).mkdir(parents=True, exist_ok=True)
        
        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{uploaded_file.name}"
        filepath = os.path.join(upload_dir, filename)
        
        # Сохраняем файл
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        logger.info(f"Файл сохранен: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Ошибка сохранения файла: {e}")
        return None


def export_dataframe_to_excel(df: pd.DataFrame, sheet_name: str = "Данные") -> bytes:
    """
    Экспорт DataFrame в Excel
    
    Args:
        df: DataFrame для экспорта
        sheet_name: Название листа
        
    Returns:
        Байты Excel файла
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    return output.getvalue()


# ============== ГРАФИКИ И ВИЗУАЛИЗАЦИЯ ==============

def create_pie_chart(data: Dict[str, int], title: str = "Распределение") -> go.Figure:
    """
    Создание круговой диаграммы
    
    Args:
        data: Данные для диаграммы
        title: Заголовок
        
    Returns:
        Объект графика Plotly
    """
    fig = px.pie(
        values=list(data.values()),
        names=list(data.keys()),
        title=title
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Количество: %{value}<br>Процент: %{percent}<extra></extra>'
    )
    
    return fig


def create_bar_chart(data: Dict[str, int], title: str = "Статистика", orientation: str = "v") -> go.Figure:
    """
    Создание столбчатой диаграммы
    
    Args:
        data: Данные для диаграммы
        title: Заголовок
        orientation: Ориентация (v - вертикальная, h - горизонтальная)
        
    Returns:
        Объект графика Plotly
    """
    if orientation == "h":
        fig = px.bar(
            x=list(data.values()),
            y=list(data.keys()),
            orientation='h',
            title=title
        )
    else:
        fig = px.bar(
            x=list(data.keys()),
            y=list(data.values()),
            title=title
        )
    
    fig.update_layout(
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def create_line_chart(dates: List[date], values: List[float], title: str = "Динамика") -> go.Figure:
    """
    Создание линейного графика
    
    Args:
        dates: Список дат
        values: Список значений
        title: Заголовок
        
    Returns:
        Объект графика Plotly
    """
    fig = px.line(
        x=dates,
        y=values,
        title=title,
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Значение",
        hovermode='x unified'
    )
    
    return fig


def create_gauge_chart(value: float, title: str = "Показатель", max_value: float = 100) -> go.Figure:
    """
    Создание круглого индикатора
    
    Args:
        value: Текущее значение
        title: Заголовок
        max_value: Максимальное значение
        
    Returns:
        Объект графика Plotly
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': max_value * 0.7},  # Целевое значение
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "lightgray"},
                {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    return fig


# ============== ПАГИНАЦИЯ ==============

class Paginator:
    """Класс для пагинации данных"""
    
    def __init__(self, items: List[Any], items_per_page: int = 20):
        self.items = items
        self.items_per_page = items_per_page
        self.total_items = len(items)
        self.total_pages = (self.total_items + items_per_page - 1) // items_per_page
    
    def get_page(self, page_number: int) -> List[Any]:
        """
        Получение элементов для страницы
        
        Args:
            page_number: Номер страницы (начиная с 1)
            
        Returns:
            Список элементов для страницы
        """
        if page_number < 1 or page_number > self.total_pages:
            return []
        
        start_index = (page_number - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        
        return self.items[start_index:end_index]
    
    def show_pagination_controls(self, key: str = "pagination") -> int:
        """
        Отображение элементов управления пагинацией
        
        Args:
            key: Уникальный ключ для состояния
            
        Returns:
            Номер текущей страницы
        """
        if self.total_pages <= 1:
            return 1
        
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        # Инициализируем текущую страницу
        if f"{key}_current_page" not in st.session_state:
            st.session_state[f"{key}_current_page"] = 1
        
        current_page = st.session_state[f"{key}_current_page"]
        
        with col1:
            if st.button("⏮️ Первая", key=f"{key}_first", disabled=current_page == 1):
                st.session_state[f"{key}_current_page"] = 1
                st.rerun()
        
        with col2:
            if st.button("⬅️ Пред", key=f"{key}_prev", disabled=current_page == 1):
                st.session_state[f"{key}_current_page"] = current_page - 1
                st.rerun()
        
        with col3:
            page = st.selectbox(
                f"Страница {current_page} из {self.total_pages}",
                range(1, self.total_pages + 1),
                index=current_page - 1,
                key=f"{key}_select"
            )
            if page != current_page:
                st.session_state[f"{key}_current_page"] = page
                st.rerun()
        
        with col4:
            if st.button("След ➡️", key=f"{key}_next", disabled=current_page == self.total_pages):
                st.session_state[f"{key}_current_page"] = current_page + 1
                st.rerun()
        
        with col5:
            if st.button("Последняя ⏭️", key=f"{key}_last", disabled=current_page == self.total_pages):
                st.session_state[f"{key}_current_page"] = self.total_pages
                st.rerun()
        
        # Информация о пагинации
        start_item = (current_page - 1) * self.items_per_page + 1
        end_item = min(current_page * self.items_per_page, self.total_items)
        
        st.caption(f"Показано {start_item}-{end_item} из {self.total_items} записей")
        
        return current_page


# ============== УВЕДОМЛЕНИЯ ==============

def show_notification(message: str, type_: str = "info", duration: int = 5):
    """
    Показ уведомления
    
    Args:
        message: Текст уведомления
        type_: Тип уведомления (success, error, warning, info)
        duration: Длительность показа
    """
    icons = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "💡"
    }
    
    icon = icons.get(type_, "💡")
    
    if type_ == "success":
        st.success(f"{icon} {message}")
    elif type_ == "error":
        st.error(f"{icon} {message}")
    elif type_ == "warning":
        st.warning(f"{icon} {message}")
    else:
        st.info(f"{icon} {message}")


# ============== КЭШИРОВАНИЕ ==============

@st.cache_data(ttl=300)  # Кэш на 5 минут
def cached_database_query(query: str, params: tuple = None):
    """
    Кэшированный запрос к базе данных
    
    Args:
        query: SQL запрос
        params: Параметры запроса
        
    Returns:
        Результат запроса
    """
    from config.database import DatabaseManager
    
    db = DatabaseManager()
    return db.execute_query(query, params)


def clear_cache():
    """Очистка кэша"""
    st.cache_data.clear()
    st.cache_resource.clear()


# ============== ЭКСПОРТ ДАННЫХ ==============

def export_to_csv(data: List[Dict[str, Any]], filename: str = "export.csv") -> str:
    """
    Экспорт данных в CSV
    
    Args:
        data: Данные для экспорта
        filename: Имя файла
        
    Returns:
        CSV строка
    """
    if not data:
        return ""
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False, encoding='utf-8')


def create_excel_download_button(data: Union[pd.DataFrame, List[Dict[str, Any]]], 
                                filename: str = "export.xlsx",
                                button_text: str = "📥 Скачать Excel"):
    """
    Создание кнопки для скачивания Excel файла
    
    Args:
        data: Данные для экспорта
        filename: Имя файла
        button_text: Текст кнопки
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data
    
    if df.empty:
        st.warning("Нет данных для экспорта")
        return
    
    excel_data = export_dataframe_to_excel(df)
    
    st.download_button(
        label=button_text,
        data=excel_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============== ПОИСК И ФИЛЬТРАЦИЯ ==============

def create_search_filters(search_fields: List[str], filter_options: Dict[str, List[str]] = None) -> Dict[str, Any]:
    """
    Создание элементов поиска и фильтрации
    
    Args:
        search_fields: Поля для поиска
        filter_options: Опции для фильтров
        
    Returns:
        Словарь с параметрами поиска и фильтров
    """
    filters = {}
    
    # Поисковая строка
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Поиск",
            placeholder=f"Поиск по: {', '.join(search_fields)}",
            help=f"Поиск выполняется по полям: {', '.join(search_fields)}"
        )
        filters['search_term'] = search_term
    
    with col2:
        if st.button("🗑️ Очистить фильтры"):
            st.rerun()
    
    # Дополнительные фильтры
    if filter_options:
        with st.expander("🔧 Дополнительные фильтры"):
            filter_cols = st.columns(len(filter_options))
            
            for i, (filter_name, options) in enumerate(filter_options.items()):
                with filter_cols[i]:
                    selected = st.selectbox(
                        filter_name,
                        ["Все"] + options,
                        key=f"filter_{filter_name}"
                    )
                    filters[filter_name] = selected if selected != "Все" else None
    
    return filters


# ============== УТИЛИТЫ ДЛЯ ВРЕМЕНИ ==============

def get_time_ago(date_time: Union[str, datetime]) -> str:
    """
    Получение относительного времени (например, "2 часа назад")
    
    Args:
        date_time: Дата и время
        
    Returns:
        Относительное время
    """
    if isinstance(date_time, str):
        try:
            dt = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
        except ValueError:
            return str(date_time)
    else:
        dt = date_time
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "Только что"


def is_business_hours(time_obj: Union[str, datetime]) -> bool:
    """
    Проверка рабочего времени
    
    Args:
        time_obj: Время для проверки
        
    Returns:
        True если рабочее время
    """
    if isinstance(time_obj, str):
        try:
            dt = datetime.strptime(time_obj, '%H:%M')
        except ValueError:
            return False
    else:
        dt = time_obj
    
    # Рабочее время: 8:00 - 18:00
    return 8 <= dt.hour < 18


# ============== БЕЗОПАСНОСТЬ ==============

def sanitize_input(text: str) -> str:
    """
    Очистка пользовательского ввода
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем потенциально опасные символы
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    # Ограничиваем длину
    return text[:1000].strip()


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Маскирование чувствительных данных
    
    Args:
        data: Исходные данные
        mask_char: Символ для маскирования
        visible_chars: Количество видимых символов
        
    Returns:
        Замаскированные данные
    """
    if not data or len(data) <= visible_chars:
        return data
    
    visible_part = data[-visible_chars:]
    masked_part = mask_char * (len(data) - visible_chars)
    
    return masked_part + visible_part


# ============== ЛОГИРОВАНИЕ ==============

def log_user_action(action: str, details: str = "", user_id: Optional[int] = None):
    """
    Логирование действий пользователя
    
    Args:
        action: Тип действия
        details: Детали действия
        user_id: ID пользователя
    """
    from utils.auth import get_current_user_id
    
    if not user_id:
        user_id = get_current_user_id()
    
    logger.info(f"User action: {action} | User ID: {user_id} | Details: {details}")


# ============== КОНФИГУРАЦИЯ ИНТЕРФЕЙСА ==============

def apply_custom_css():
    """Применение кастомных стилей"""
    st.markdown("""
    <style>
        /* Основные стили */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        
        /* Стили для метрик */
        [data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #007bff;
        }
        
        /* Стили для кнопок */
        .stButton > button {
            border-radius: 0.5rem;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        /* Стили для sidebar */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        
        /* Стили для таблиц */
        .dataframe {
            font-size: 0.9rem;
        }
        
        /* Стили для успешных сообщений */
        .stAlert[data-baseweb="notification"] {
            border-radius: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)


def set_page_config(title: str = "Система махалли", icon: str = "🏛️"):
    """
    Настройка конфигурации страницы
    
    Args:
        title: Заголовок страницы
        icon: Иконка страницы
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Применяем кастомные стили
    apply_custom_css()