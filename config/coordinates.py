"""
Управление координатами интерфейса и временными задержками
"""
import json
import os

class CoordinatesManager:
    def __init__(self):
        self.coordinates_file = 'data/coordinates.json'
        
        # Координаты по умолчанию
        self.default_coordinates = {
            'PROMPT_INPUT': [828, 484],           # Поле ввода промпта
            'IMAGE_LOCATION': [459, 571],         # Место клика на сгенерированное изображение
            'NEW_CHAT_BUTTON': [67, 281],        # Кнопка создания нового чата
            'CHAT_NAME_INPUT': [500, 161],        # Поле ввода названия чата (первый клик)
            'CHAT_NAME_POPUP': [903, 509],        # Поле ввода в попапе
            'CHAT_NAME_CONFIRM': [0, 0],          # Кнопка подтверждения в попапе (если есть)
            'FORMAT_SELECTOR': [0, 0],            # Выпадающий список выбора формата изображения
        }
        
        # Относительные движения по умолчанию
        self.default_relative_movements = {
            'TO_SAVE_OPTION': [124, 15],           # Относительное движение к "сохранить картинку как" в контекстном меню
        }
        
        self.coordinates = {}
        self.relative_movements = {}
        self.load_coordinates()
    
    def load_coordinates(self):
        """Загрузка координат из файла"""
        try:
            # Создаем папку data если её нет
            os.makedirs('data', exist_ok=True)
            
            if os.path.exists(self.coordinates_file):
                with open(self.coordinates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Загружаем координаты из файла
                file_coordinates = data.get('coordinates', {})
                file_movements = data.get('relative_movements', {})
                
                # Объединяем с координатами по умолчанию (файл имеет приоритет)
                self.coordinates = self.default_coordinates.copy()
                self.coordinates.update(file_coordinates)
                
                self.relative_movements = self.default_relative_movements.copy()
                self.relative_movements.update(file_movements)
                
                # Преобразуем списки в кортежи для совместимости
                for key, value in self.coordinates.items():
                    if isinstance(value, list):
                        self.coordinates[key] = tuple(value)
                        
                for key, value in self.relative_movements.items():
                    if isinstance(value, list):
                        self.relative_movements[key] = tuple(value)
                
                print(f"[КООРДИНАТЫ] Загружены из {self.coordinates_file}")
            else:
                print(f"[КООРДИНАТЫ] Файл {self.coordinates_file} не найден, используются координаты по умолчанию")
                self.coordinates = {k: tuple(v) for k, v in self.default_coordinates.items()}
                self.relative_movements = {k: tuple(v) for k, v in self.default_relative_movements.items()}
                self.save_coordinates()
                
        except Exception as e:
            print(f"[ОШИБКА] При загрузке координат: {e}")
            print("[КООРДИНАТЫ] Используются координаты по умолчанию")
            self.coordinates = {k: tuple(v) for k, v in self.default_coordinates.items()}
            self.relative_movements = {k: tuple(v) for k, v in self.default_relative_movements.items()}
    
    def save_coordinates(self):
        """Сохранение координат в файл"""
        try:
            os.makedirs('data', exist_ok=True)
            
            data = {
                'coordinates': {k: list(v) for k, v in self.coordinates.items()},
                'relative_movements': {k: list(v) for k, v in self.relative_movements.items()}
            }
            
            with open(self.coordinates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"[КООРДИНАТЫ] Сохранены в {self.coordinates_file}")
            
        except Exception as e:
            print(f"[ОШИБКА] При сохранении координат: {e}")
    
    def update_coordinate(self, coord_name, x, y):
        """Обновление координаты"""
        if coord_name in self.coordinates:
            self.coordinates[coord_name] = (x, y)
            self.save_coordinates()
            print(f"✓ Координата {coord_name} обновлена: ({x}, {y})")
            return True
        elif coord_name in self.relative_movements:
            self.relative_movements[coord_name] = (x, y)
            self.save_coordinates()
            print(f"✓ Относительное движение {coord_name} обновлено: ({x}, {y})")
            return True
        else:
            print(f"❌ Неизвестная координата: {coord_name}")
            return False
    
    def get_coordinate(self, coord_name):
        """Получение координаты"""
        if coord_name in self.coordinates:
            return self.coordinates[coord_name]
        elif coord_name in self.relative_movements:
            return self.relative_movements[coord_name]
        return (0, 0)
    
    def list_coordinates(self):
        """Получение списка всех координат"""
        coords_info = []
        
        coords_info.append("=== КООРДИНАТЫ ===")
        for name, coord in self.coordinates.items():
            status = "✓ задана" if coord != (0, 0) else "⚠️ не задана"
            if name == 'FORMAT_SELECTOR':
                coords_info.append(f"  {name}: {coord} - {status} [ДЛЯ МУЛЬТИФОРМАТНОГО РЕЖИМА]")
            else:
                coords_info.append(f"  {name}: {coord} - {status}")
        
        coords_info.append("\n=== ОТНОСИТЕЛЬНЫЕ ДВИЖЕНИЯ ===")
        for name, movement in self.relative_movements.items():
            status = "✓ задано" if movement != (0, 0) else "⚠️ не задано"
            coords_info.append(f"  {name}: {movement} - {status}")
        
        return "\n".join(coords_info)

# Создаем глобальный экземпляр менеджера координат
_coordinates_manager = CoordinatesManager()

# Экспортируем координаты для обратной совместимости
COORDINATES = _coordinates_manager.coordinates
RELATIVE_MOVEMENTS = _coordinates_manager.relative_movements

# Задержки между действиями (в секундах)
DELAYS = {
    'BETWEEN_CLICKS': 0.5,            # Между кликами
    'AFTER_PASTE': 1.0,               # После вставки промпта
    'GENERATION_WAIT': 20.0,          # Ожидание генерации изображения
    'IMAGE_OPEN_WAIT': 1.0,           # Ожидание открытия полного изображения
    'CONTEXT_MENU_WAIT': 0.5,         # Ожидание появления контекстного меню
    'SAVE_DIALOG_WAIT': 1.0,          # Ожидание открытия диалога сохранения
    'AFTER_SAVE': 2.0,                # После сохранения файла
    'NEW_CHAT_WAIT': 2.0,             # Ожидание создания нового чата
    'CHAT_RENAME_WAIT': 1.0,          # Ожидание переименования чата
    'POPUP_OPEN_WAIT': 0.5,           # Ожидание открытия попапа
    'BETWEEN_GENERATIONS': 1.0,       # Между генерациями одной карточки
    'BETWEEN_CARDS': 2.0,             # Между обработкой карточек
}

# Функции для управления координатами
def get_coordinates_manager():
    """Получение менеджера координат"""
    return _coordinates_manager