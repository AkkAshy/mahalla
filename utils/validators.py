"""
Валидаторы для проверки данных
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging
from .validators import BaseValidator

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    pass

class BaseValidator:
    """Базовый класс для валидаторов"""
    
    def __init__(self):
        self.errors = []
    
    def is_valid(self, value: Any) -> bool:
        """
        Проверка валидности значения
        
        Args:
            value: Значение для проверки
            
        Returns:
            True если значение валидно
        """
        self.errors = []
        return self.validate(value)
    

    """Комплексный валидатор для форм"""
    
    def __init__(self):
        self.validators = {}
        self.errors = {}
    
    def add_validator(self, field_name: str, validator: BaseValidator):
        """
        Добавление валидатора для поля
        
        Args:
            field_name: Имя поля
            validator: Экземпляр валидатора
        """
        self.validators[field_name] = validator
    
    def validate_form(self, form_data: Dict[str, Any]) -> bool:
        """
        Валидация всей формы
        
        Args:
            form_data: Данные формы
            
        Returns:
            True если все поля валидны
        """
        self.errors = {}
        is_valid = True
        
        for field_name, validator in self.validators.items():
            value = form_data.get(field_name)
            
            if not validator.is_valid(value):
                self.errors[field_name] = validator.get_errors()
                is_valid = False
        
        return is_valid
    
    def get_field_errors(self, field_name: str) -> List[str]:
        """Получение ошибок для конкретного поля"""
        return self.errors.get(field_name, [])
    
    def get_all_errors(self) -> Dict[str, List[str]]:
        """Получение всех ошибок"""
        return self.errors.copy()
    
    def has_errors(self) -> bool:
        """Проверка наличия ошибок"""
        return bool(self.errors)


# Готовые валидаторы для часто используемых полей
def validate_citizen_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных гражданина
    
    Args:
        data: Данные гражданина
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # ФИО
    form_validator.add_validator(
        'full_name', 
        TextValidator(min_length=2, max_length=255, required=True)
    )
    
    # Телефон
    if data.get('phone'):
        form_validator.add_validator('phone', PhoneValidator())
    
    # Паспорт
    if data.get('passport_data'):
        form_validator.add_validator('passport_data', PassportValidator())
    
    # Дата рождения
    if data.get('birth_date'):
        min_date = date(1920, 1, 1)  # Минимум 100 лет назад
        form_validator.add_validator(
            'birth_date', 
            DateValidator(min_date=min_date, max_date=date.today())
        )
    
    # Адрес
    if data.get('address'):
        form_validator.add_validator(
            'address',
            TextValidator(min_length=5, max_length=500, required=False)
        )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_meeting_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных заседания
    
    Args:
        data: Данные заседания
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Название
    form_validator.add_validator(
        'title',
        TextValidator(min_length=3, max_length=255, required=True)
    )
    
    # Дата заседания
    form_validator.add_validator(
        'meeting_date',
        DateValidator(min_date=date(2020, 1, 1))
    )
    
    # Место проведения
    if data.get('location'):
        form_validator.add_validator(
            'location',
            TextValidator(min_length=3, max_length=255, required=False)
        )
    
    # Повестка дня
    if data.get('agenda'):
        form_validator.add_validator(
            'agenda',
            TextValidator(min_length=10, max_length=5000, required=False)
        )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_sms_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных SMS кампании
    
    Args:
        data: Данные SMS кампании
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Заголовок
    form_validator.add_validator(
        'title',
        TextValidator(min_length=3, max_length=255, required=True)
    )
    
    # Текст сообщения
    form_validator.add_validator(
        'message_text',
        TextValidator(min_length=10, max_length=160, required=True)
    )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_user_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных пользователя
    
    Args:
        data: Данные пользователя
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Имя пользователя
    form_validator.add_validator(
        'username',
        TextValidator(min_length=3, max_length=50, required=True)
    )
    
    # Полное имя
    form_validator.add_validator(
        'full_name',
        TextValidator(min_length=2, max_length=255, required=True)
    )
    
    # Email (если указан)
    if data.get('email'):
        form_validator.add_validator('email', EmailValidator())
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


class StreamlitValidationHelper:
    """Хелпер для интеграции валидации со Streamlit"""
    
    @staticmethod
    def show_field_errors(field_name: str, errors: Dict[str, List[str]]):
        """
        Отображение ошибок для поля в Streamlit
        
        Args:
            field_name: Имя поля
            errors: Словарь с ошибками
        """
        import streamlit as st
        
        field_errors = errors.get(field_name, [])
        if field_errors:
            for error in field_errors:
                st.error(f"❌ {error}")
    
    @staticmethod
    def show_all_errors(errors: Dict[str, List[str]]):
        """
        Отображение всех ошибок валидации
        
        Args:
            errors: Словарь с ошибками
        """
        import streamlit as st
        
        if errors:
            st.error("❌ Обнаружены ошибки валидации:")
            
            for field_name, field_errors in errors.items():
                for error in field_errors:
                    st.write(f"• **{field_name}**: {error}")
    
    @staticmethod
    def validate_and_show(data: Dict[str, Any], validation_func) -> bool:
        """
        Валидация данных с отображением ошибок
        
        Args:
            data: Данные для валидации
            validation_func: Функция валидации
            
        Returns:
            True если данные валидны
        """
        import streamlit as st
        
        errors = validation_func(data)
        
        if errors:
            StreamlitValidationHelper.show_all_errors(errors)
            return False
        
        return True


# Утилиты для работы с конкретными типами данных
def clean_phone_number(phone: str) -> str:
    """
    Очистка номера телефона от лишних символов
    
    Args:
        phone: Исходный номер
        
    Returns:
        Очищенный номер
    """
    if not phone:
        return ""
    
    # Удаляем все символы кроме цифр и +
    return re.sub(r'[^\d\+]', '', phone)


def normalize_passport(passport: str) -> str:
    """
    Нормализация паспортных данных
    
    Args:
        passport: Исходные данные
        
    Returns:
        Нормализованные данные
    """
    if not passport:
        return ""
    
    # Приводим к верхнему регистру и удаляем пробелы
    return passport.upper().replace(' ', '')


def validate_file_upload(uploaded_file, allowed_extensions: List[str], max_size_mb: int = 10) -> List[str]:
    """
    Валидация загруженного файла
    
    Args:
        uploaded_file: Загруженный файл (Streamlit)
        allowed_extensions: Разрешенные расширения
        max_size_mb: Максимальный размер в МБ
        
    Returns:
        Список ошибок
    """
    errors = []
    
    if not uploaded_file:
        errors.append("Файл не выбран")
        return errors
    
    # Проверяем расширение
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in [ext.lower() for ext in allowed_extensions]:
        errors.append(f"Недопустимое расширение файла. Разрешены: {', '.join(allowed_extensions)}")
    
    # Проверяем размер
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        errors.append(f"Файл слишком большой. Максимальный размер: {max_size_mb} МБ")
    
    return errors


# Валидаторы для специфических бизнес-правил
def validate_meeting_date_time(meeting_date: date, meeting_time: str) -> List[str]:
    """
    Валидация даты и времени заседания
    
    Args:
        meeting_date: Дата заседания
        meeting_time: Время заседания
        
    Returns:
        Список ошибок
    """
    errors = []
    
    # Проверяем что дата не в прошлом (кроме сегодняшней)
    if meeting_date < date.today():
        errors.append("Дата заседания не может быть в прошлом")
    
    # Проверяем время (должно быть в рабочее время)
    if meeting_time:
        try:
            time_obj = datetime.strptime(meeting_time, '%H:%M').time()
            
            # Рекомендуемое время: с 8:00 до 20:00
            if time_obj.hour < 8 or time_obj.hour > 20:
                errors.append("Рекомендуется проводить заседания с 8:00 до 20:00")
                
        except ValueError:
            errors.append("Неверный формат времени")
    
    return errors


def validate_points_award(citizen_id: int, points: int, activity_type: str) -> List[str]:
    """
    Валидация начисления баллов
    
    Args:
        citizen_id: ID гражданина
        points: Количество баллов
        activity_type: Тип активности
        
    Returns:
        Список ошибок
    """
    errors = []
    
    # Проверяем разумность количества баллов
    if points < -1000 or points > 1000:
        errors.append("Количество баллов должно быть от -1000 до 1000")
    
    # Проверяем тип активности
    from config.settings import get_settings
    settings = get_settings()
    
    if activity_type not in settings.POINTS_CONFIG and activity_type != 'penalty':
        errors.append("Неизвестный тип активности")

    return errors


class BaseValidator:
    """Базовый класс валидатора"""

    def __init__(self, required: bool = False, min_value: float = None, max_value: float = None, integer_only: bool = False):
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
        self.errors = []

    def add_error(self, message: str):
        """Добавление ошибки валидации"""
        self.errors.append(message)

    def get_errors(self) -> List[str]:
        """Получение списка ошибок"""
        return self.errors

    def is_valid(self, value: Any) -> bool:
        """Валидация числового значения"""
        if value is None:
            self.add_error("Значение не может быть пустым")
            return False
        
        # Преобразуем к числу
        try:
            if self.integer_only:
                num_value = int(value)
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            self.add_error("Значение должно быть числом")
            return False
        
        # Проверяем диапазон
        if self.min_value is not None and num_value < self.min_value:
            self.add_error(f"Значение не может быть меньше {self.min_value}")
            return False
        
        if self.max_value is not None and num_value > self.max_value:
            self.add_error(f"Значение не может быть больше {self.max_value}")
            return False
        
        return True


class FormValidator:
    """Комплексный валидатор для форм"""
    
    def __init__(self):
        self.validators = {}
        self.errors = {}
    
    def add_validator(self, field_name: str, validator: BaseValidator):
        """
        Добавление валидатора для поля
        
        Args:
            field_name: Имя поля
            validator: Экземпляр валидатора
        """
        self.validators[field_name] = validator
    
    def validate_form(self, form_data: Dict[str, Any]) -> bool:
        """
        Валидация всей формы
        
        Args:
            form_data: Данные формы
            
        Returns:
            True если все поля валидны
        """
        self.errors = {}
        is_valid = True
        
        for field_name, validator in self.validators.items():
            value = form_data.get(field_name)
            
            if not validator.is_valid(value):
                self.errors[field_name] = validator.get_errors()
                is_valid = False
        
        return is_valid
    
    def get_field_errors(self, field_name: str) -> List[str]:
        """Получение ошибок для конкретного поля"""
        return self.errors.get(field_name, [])
    
    def get_all_errors(self) -> Dict[str, List[str]]:
        """Получение всех ошибок"""
        return self.errors.copy()
    
    def has_errors(self) -> bool:
        """Проверка наличия ошибок"""
        return bool(self.errors)


# Готовые валидаторы для часто используемых полей
def validate_citizen_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных гражданина
    
    Args:
        data: Данные гражданина
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # ФИО
    form_validator.add_validator(
        'full_name', 
        TextValidator(min_length=2, max_length=255, required=True)
    )
    
    # Телефон
    if data.get('phone'):
        form_validator.add_validator('phone', PhoneValidator())
    
    # Паспорт
    if data.get('passport_data'):
        form_validator.add_validator('passport_data', PassportValidator())
    
    # Дата рождения
    if data.get('birth_date'):
        min_date = date(1920, 1, 1)  # Минимум 100 лет назад
        form_validator.add_validator(
            'birth_date', 
            DateValidator(min_date=min_date, max_date=date.today())
        )
    
    # Адрес
    if data.get('address'):
        form_validator.add_validator(
            'address',
            TextValidator(min_length=5, max_length=500, required=False)
        )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_meeting_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных заседания
    
    Args:
        data: Данные заседания
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Название
    form_validator.add_validator(
        'title',
        TextValidator(min_length=3, max_length=255, required=True)
    )
    
    # Дата заседания
    form_validator.add_validator(
        'meeting_date',
        DateValidator(min_date=date(2020, 1, 1))
    )
    
    # Место проведения
    if data.get('location'):
        form_validator.add_validator(
            'location',
            TextValidator(min_length=3, max_length=255, required=False)
        )
    
    # Повестка дня
    if data.get('agenda'):
        form_validator.add_validator(
            'agenda',
            TextValidator(min_length=10, max_length=5000, required=False)
        )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_sms_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных SMS кампании
    
    Args:
        data: Данные SMS кампании
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Заголовок
    form_validator.add_validator(
        'title',
        TextValidator(min_length=3, max_length=255, required=True)
    )
    
    # Текст сообщения
    form_validator.add_validator(
        'message_text',
        TextValidator(min_length=10, max_length=160, required=True)
    )
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


def validate_user_data(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Валидация данных пользователя
    
    Args:
        data: Данные пользователя
        
    Returns:
        Словарь с ошибками валидации
    """
    form_validator = FormValidator()
    
    # Имя пользователя
    form_validator.add_validator(
        'username',
        TextValidator(min_length=3, max_length=50, required=True)
    )
    
    # Полное имя
    form_validator.add_validator(
        'full_name',
        TextValidator(min_length=2, max_length=255, required=True)
    )
    
    # Email (если указан)
    if data.get('email'):
        form_validator.add_validator('email', EmailValidator())
    
    form_validator.validate_form(data)
    return form_validator.get_all_errors()


class StreamlitValidationHelper:
    """Хелпер для интеграции валидации со Streamlit"""
    
    @staticmethod
    def show_field_errors(field_name: str, errors: Dict[str, List[str]]):
        """
        Отображение ошибок для поля в Streamlit
        
        Args:
            field_name: Имя поля
            errors: Словарь с ошибками
        """
        import streamlit as st
        
        field_errors = errors.get(field_name, [])
        if field_errors:
            for error in field_errors:
                st.error(f"❌ {error}")
    
    @staticmethod
    def show_all_errors(errors: Dict[str, List[str]]):
        """
        Отображение всех ошибок валидации
        
        Args:
            errors: Словарь с ошибками
        """
        import streamlit as st
        
        if errors:
            st.error("❌ Обнаружены ошибки валидации:")
            
            for field_name, field_errors in errors.items():
                for error in field_errors:
                    st.write(f"• **{field_name}**: {error}")
    
    @staticmethod
    def validate_and_show(data: Dict[str, Any], validation_func) -> bool:
        """
        Валидация данных с отображением ошибок
        
        Args:
            data: Данные для валидации
            validation_func: Функция валидации
            
        Returns:
            True если данные валидны
        """
        import streamlit as st
        
        errors = validation_func(data)
        
        if errors:
            StreamlitValidationHelper.show_all_errors(errors)
            return False
        
        return True


# Утилиты для работы с конкретными типами данных
def clean_phone_number(phone: str) -> str:
    """
    Очистка номера телефона от лишних символов
    
    Args:
        phone: Исходный номер
        
    Returns:
        Очищенный номер
    """
    if not phone:
        return ""
    
    # Удаляем все символы кроме цифр и +
    return re.sub(r'[^\d\+]', '', phone)


def normalize_passport(passport: str) -> str:
    """
    Нормализация паспортных данных
    
    Args:
        passport: Исходные данные
        
    Returns:
        Нормализованные данные
    """
    if not passport:
        return ""
    
    # Приводим к верхнему регистру и удаляем пробелы
    return passport.upper().replace(' ', '')


def validate_file_upload(uploaded_file, allowed_extensions: List[str], max_size_mb: int = 10) -> List[str]:
    """
    Валидация загруженного файла
    
    Args:
        uploaded_file: Загруженный файл (Streamlit)
        allowed_extensions: Разрешенные расширения
        max_size_mb: Максимальный размер в МБ
        
    Returns:
        Список ошибок
    """
    errors = []
    
    if not uploaded_file:
        errors.append("Файл не выбран")
        return errors
    
    # Проверяем расширение
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in [ext.lower() for ext in allowed_extensions]:
        errors.append(f"Недопустимое расширение файла. Разрешены: {', '.join(allowed_extensions)}")
    
    # Проверяем размер
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        errors.append(f"Файл слишком большой. Максимальный размер: {max_size_mb} МБ")
    
    return errors


# Валидаторы для специфических бизнес-правил
def validate_meeting_date_time(meeting_date: date, meeting_time: str) -> List[str]:
    """
    Валидация даты и времени заседания
    
    Args:
        meeting_date: Дата заседания
        meeting_time: Время заседания
        
    Returns:
        Список ошибок
    """
    errors = []
    
    # Проверяем что дата не в прошлом (кроме сегодняшней)
    if meeting_date < date.today():
        errors.append("Дата заседания не может быть в прошлом")
    
    # Проверяем время (должно быть в рабочее время)
    if meeting_time:
        try:
            time_obj = datetime.strptime(meeting_time, '%H:%M').time()
            
            # Рекомендуемое время: с 8:00 до 20:00
            if time_obj.hour < 8 or time_obj.hour > 20:
                errors.append("Рекомендуется проводить заседания с 8:00 до 20:00")
                
        except ValueError:
            errors.append("Неверный формат времени")
    
    return errors


def validate_points_award(citizen_id: int, points: int, activity_type: str) -> List[str]:
    """
    Валидация начисления баллов
    
    Args:
        citizen_id: ID гражданина
        points: Количество баллов
        activity_type: Тип активности
        
    Returns:
        Список ошибок
    """
    errors = []
    
    # Проверяем разумность количества баллов
    if points < -1000 or points > 1000:
        errors.append("Количество баллов должно быть от -1000 до 1000")
    
    # Проверяем тип активности
    from config.settings import get_settings
    settings = get_settings()
    
    if activity_type not in settings.POINTS_CONFIG and activity_type != 'penalty':
        errors.append("Неизвестный тип активности")

    return errors


class BaseValidator:
    """Базовый класс валидатора"""

    def __init__(self, required: bool = False, min_value: float = None, max_value: float = None, integer_only: bool = False):
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
        self.errors = []

    def add_error(self, message: str):
        """Добавление ошибки валидации"""
        self.errors.append(message)

    def get_errors(self) -> List[str]:
        """Получение списка ошибок"""
        return self.errors

    def is_valid(self, value: Any) -> bool:
        """
        Метод валидации (переопределяется в дочерних классах)

        Args:
            value: Значение для проверки
            
        Returns:
            True если значение валидно
        """
        raise NotImplementedError
    
    def add_error(self, message: str):
        """Добавление ошибки валидации"""
        self.errors.append(message)
    
    def get_errors(self) -> List[str]:
        """Получение списка ошибок"""
        return self.errors.copy()


class PhoneValidator(BaseValidator):
    """Валидатор номеров телефонов"""
    
    def __init__(self, country_code: str = "998"):
        super().__init__()
        self.country_code = country_code
        
        # Паттерны для разных форматов
        self.patterns = [
            r'^\+998[0-9]{9}$',           # +998xxxxxxxxx
            r'^998[0-9]{9}$',             # 998xxxxxxxxx  
            r'^8[0-9]{9}$',               # 8xxxxxxxxx
            r'^[0-9]{9}$',                # xxxxxxxxx (без кода страны)
            r'^\+998\s?\([0-9]{2}\)\s?[0-9]{3}-?[0-9]{2}-?[0-9]{2}$',  # +998 (xx) xxx-xx-xx
        ]
    
    def validate(self, phone: str) -> bool:
        """Валидация номера телефона"""
        if not phone:
            self.add_error("Номер телефона не может быть пустым")
            return False
        
        # Удаляем пробелы и специальные символы для проверки
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Проверяем по паттернам
        for pattern in self.patterns:
            if re.match(pattern, clean_phone):
                return True
        
        self.add_error("Неверный формат номера телефона")
        return False
    
    def format_phone(self, phone: str) -> str:
        """
        Форматирование номера телефона к стандартному виду
        
        Args:
            phone: Исходный номер
            
        Returns:
            Отформатированный номер
        """
        if not self.is_valid(phone):
            return phone
        
        # Удаляем все символы кроме цифр и +
        clean_phone = re.sub(r'[^\d\+]', '', phone)
        
        # Приводим к формату +998xxxxxxxxx
        if clean_phone.startswith('998') and len(clean_phone) == 12:
            return f"+{clean_phone}"
        elif clean_phone.startswith('8') and len(clean_phone) == 10:
            return f"+998{clean_phone[1:]}"
        elif clean_phone.startswith('9') and len(clean_phone) == 9:
            return f"+998{clean_phone}"
        elif clean_phone.startswith('+998') and len(clean_phone) == 13:
            return clean_phone
        
        return phone


class PassportValidator(BaseValidator):
    """Валидатор паспортных данных"""
    
    def __init__(self, country: str = "UZ"):
        super().__init__()
        self.country = country
        
        # Паттерны для разных стран
        self.patterns = {
            "UZ": r'^[A-Z]{2}[0-9]{7}$',      # Узбекистан: AA1234567
            "RU": r'^[0-9]{4}\s?[0-9]{6}$',   # Россия: 1234 567890
            "KZ": r'^[0-9]{9}$',              # Казахстан: 123456789
        }
    
    def validate(self, passport: str) -> bool:
        """Валидация паспортных данных"""
        if not passport:
            self.add_error("Паспортные данные не могут быть пустыми")
            return False
        
        # Приводим к верхнему регистру и удаляем пробелы
        clean_passport = passport.upper().replace(' ', '')
        
        pattern = self.patterns.get(self.country)
        if not pattern:
            self.add_error(f"Неподдерживаемая страна: {self.country}")
            return False
        
        if not re.match(pattern, clean_passport):
            self.add_error("Неверный формат паспортных данных")
            return False
        
        return True
    
    def format_passport(self, passport: str) -> str:
        """
        Форматирование паспортных данных
        
        Args:
            passport: Исходные данные
            
        Returns:
            Отформатированные данные
        """
        if not self.is_valid(passport):
            return passport
        
        clean_passport = passport.upper().replace(' ', '')
        
        if self.country == "UZ":
            # Формат: AA1234567
            return clean_passport
        elif self.country == "RU":
            # Формат: 1234 567890
            if len(clean_passport) == 10:
                return f"{clean_passport[:4]} {clean_passport[4:]}"
        
        return clean_passport


class EmailValidator(BaseValidator):
    """Валидатор email адресов"""
    
    def __init__(self):
        super().__init__()
        self.pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def validate(self, email: str) -> bool:
        """Валидация email адреса"""
        if not email:
            self.add_error("Email не может быть пустым")
            return False
        
        if not re.match(self.pattern, email):
            self.add_error("Неверный формат email адреса")
            return False
        
        # Дополнительные проверки
        if len(email) > 254:
            self.add_error("Email слишком длинный")
            return False
        
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            self.add_error("Локальная часть email слишком длинная")
            return False
        
        return True


class DateValidator(BaseValidator):
    """Валидатор дат"""
    
    def __init__(self, min_date: Optional[date] = None, max_date: Optional[date] = None):
        super().__init__()
        self.min_date = min_date
        self.max_date = max_date or date.today()
    
    def validate(self, date_value: Any) -> bool:
        """Валидация даты"""
        if not date_value:
            self.add_error("Дата не может быть пустой")
            return False
        
        # Преобразуем к объекту date
        if isinstance(date_value, str):
            try:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                self.add_error("Неверный формат даты (YYYY-MM-DD)")
                return False
        elif isinstance(date_value, datetime):
            date_obj = date_value.date()
        elif isinstance(date_value, date):
            date_obj = date_value
        else:
            self.add_error("Неподдерживаемый тип даты")
            return False
        
        # Проверяем диапазон
        if self.min_date and date_obj < self.min_date:
            self.add_error(f"Дата не может быть раньше {self.min_date}")
            return False
        
        if self.max_date and date_obj > self.max_date:
            self.add_error(f"Дата не может быть позже {self.max_date}")
            return False
        
        return True


class TextValidator(BaseValidator):
    """Валидатор текстовых полей"""
    
    def __init__(self, min_length: int = 0, max_length: int = 1000, required: bool = True):
        super().__init__()
        self.min_length = min_length
        self.max_length = max_length
        self.required = required
    
    def validate(self, text: str) -> bool:
        """Валидация текста"""
        if not text and self.required:
            self.add_error("Поле обязательно для заполнения")
            return False
        
        if not text and not self.required:
            return True
        
        text = text.strip()
        
        if len(text) < self.min_length:
            self.add_error(f"Минимальная длина: {self.min_length} символов")
            return False
        
        if len(text) > self.max_length:
            self.add_error(f"Максимальная длина: {self.max_length} символов")
            return False
        
        return True


class NumberValidator(BaseValidator):
    """Валидатор числовых значений"""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None, 
                 integer_only: bool = False):
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.integer_only = integer_only
    
    def validate(self, value: Any) -> bool:
        """Валидация числового значения"""
        if value is None:
            self.add_error("Значение не может быть пустым")
            return False
        
        # Преобразуем к числу
        try:
            if self.integer_only:
                num_value = int(value)
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            self.add_error("Значение должно быть числом")
            return False
        
        # Проверяем диапазон
        if self.min_value is not None and num_value < self.min_value:
            self.add_error(f"Значение не может быть меньше {self.min_value}")
            return False
        
        if self.max_value is not None and num_value > self.max_value:
            self.add_error(f"Значение не может быть больше {self.max_value}")
            return False
        
        return True