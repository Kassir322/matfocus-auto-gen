"""
Базовый класс для парсеров промптов
"""
import os
from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров промптов"""
    
    def __init__(self, settings_manager):
        """
        Инициализация парсера
        
        Args:
            settings_manager: менеджер настроек
        """
        self.settings_manager = settings_manager
    
    @abstractmethod
    def load_prompts(self):
        """
        Загружает промпты из файла
        
        Returns:
            dict: словарь с промптами в формате, специфичном для режима
        """
        pass
    
    @abstractmethod
    def get_cards_to_process(self):
        """
        Получает список карточек для обработки
        
        Returns:
            list: список кортежей с данными карточек
        """
        pass
    
    def _read_file(self, file_path):
        """
        Читает файл с промптами, пробуя разные кодировки
        
        Args:
            file_path: путь к файлу
            
        Returns:
            list: список строк файла или None, если файл не удалось прочитать
        """
        if not os.path.exists(file_path):
            print(f"[ОШИБКА] Файл {file_path} не найден!")
            return None
        
        # Пробуем разные кодировки
        encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    print(f"[ЗАГРУЗКА] Используется кодировка: {encoding}")
                    lines = file.readlines()
                    return lines
            except UnicodeDecodeError:
                continue
        
        print(f"[ОШИБКА] Не удалось прочитать файл {file_path} ни с одной кодировкой!")
        return None
    
    def _validate_card_range(self, available_cards, start_card, cards_to_process):
        """
        Валидирует диапазон карточек для обработки
        
        Args:
            available_cards: список доступных номеров карточек
            start_card: номер карточки для начала
            cards_to_process: количество карточек для обработки
            
        Returns:
            tuple: (доступные карточки, конечная карточка)
        """
        end_card = start_card + cards_to_process - 1
        
        print(f"[ПАРСЕР] Доступные карточки: {available_cards}")
        print(f"[ПАРСЕР] Диапазон: карточки {start_card}-{end_card}")
        print(f"[ПАРСЕР] Будет обработано карточек: {cards_to_process}")
        
        return available_cards, end_card
