"""
Обработка файлов с промптами
Делегирует работу специализированным парсерам в зависимости от режима генерации
"""
class FileHandler:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self._parser = None  # Кэш парсера
    
    def get_parser(self):
        """
        Получает парсер для текущего режима генерации
        
        Returns:
            BaseParser: парсер для соответствующего режима
        """
        if self._parser is None:
            generation_mode = self.settings_manager.get('GENERATION_MODE')
            
            if generation_mode == 'standard':
                from .parsers.standard_parser import StandardParser
                self._parser = StandardParser(self.settings_manager)
            else:
                # Для multi_format и multi_format_with_refs используется один парсер
                from .parsers.multi_format_parser import MultiFormatParser
                self._parser = MultiFormatParser(self.settings_manager)
        
        return self._parser
    
    def load_prompts(self):
        """
        Загружает промпты из файла через соответствующий парсер
        
        Returns:
            dict: словарь с промптами в формате, специфичном для режима
        """
        parser = self.get_parser()
        return parser.load_prompts()
    
    def get_cards_to_process(self):
        """
        Получает список карточек для обработки через соответствующий парсер
        
        Returns:
            list: список кортежей с данными карточек
        """
        parser = self.get_parser()
        return parser.get_cards_to_process()

    def test_new_format(self):
        """Тестовый метод для проверки нового формата"""
        print("=== ТЕСТ НОВОГО ФОРМАТА ===")
        
        # Временно меняем файл на тестовый и сбрасываем кэш парсера
        original_file = self.settings_manager.get('PROMPTS_FILE')
        self.settings_manager.set('PROMPTS_FILE', 'data/test_new_format.txt')
        self._parser = None  # Сбрасываем кэш парсера
        
        try:
            prompts_data = self.load_prompts()
            
            print(f"Карточек загружено: {len(prompts_data)}")
            for card_num, card_data in prompts_data.items():
                card_name, pairs_list = card_data
                print(f"Карточка {card_num} ({card_name}): {len(pairs_list)} пар")
                for i, pair in enumerate(pairs_list, 1):
                    face_text = pair.get('лицо', 'None')
                    back_text = pair.get('оборот', 'None')
                    face_preview = face_text[:30] + '...' if face_text and len(face_text) > 30 else (face_text or 'None')
                    back_preview = back_text[:30] + '...' if back_text and len(back_text) > 30 else (back_text or 'None')
                    print(f"  Пара {i}: лицо='{face_preview}', оборот='{back_preview}'")
            
            return True
            
        except Exception as e:
            print(f"Ошибка в тесте: {e}")
            return False
        finally:
            # Восстанавливаем оригинальный файл и сбрасываем кэш
            self.settings_manager.set('PROMPTS_FILE', original_file)
            self._parser = None
