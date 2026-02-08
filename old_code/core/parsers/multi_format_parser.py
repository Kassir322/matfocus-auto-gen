"""
Парсер промптов для мультиформатного режима генерации
Формат: Карточка X лицо Название - Промпт Y: текст
Поддерживает неполные пары (только лицо или только оборот)
"""
import re
from .base_parser import BaseParser


class MultiFormatParser(BaseParser):
    """Парсер для мультиформатного режима с настраиваемыми соотношениями сторон"""
    
    def load_prompts(self):
        """
        Загружает промпты из файла в формате мультиформатного режима
        
        Формат строки: Карточка X лицо Название - Промпт Y: текст
        или: Карточка X оборот Название - Промпт Y: текст
        
        Returns:
            dict: {card_num: (card_name, [{'лицо': text, 'оборот': text}, ...])}
        """
        prompts_file = self.settings_manager.get('PROMPTS_FILE')
        print(f"[ПАРСЕР] Загружаем промпты из файла: {prompts_file}")
        
        prompts_by_card = {}
        card_names = {}  # Словарь для хранения названий карточек
        
        try:
            lines = self._read_file(prompts_file)
            if lines is None:
                return {}
            
            # Регулярное выражение для формата: Карточка X лицо/оборот Название - Промпт Y: текст
            pattern = r'Карточка (\d+) (лицо|оборот) ([^-]+) - Промпт (\d+): (.+)'
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and 'Карточка' in line:
                    match = re.search(pattern, line)
                    if match:
                        card_num = int(match.group(1))
                        side_type = match.group(2)  # "лицо" или "оборот"
                        card_name = match.group(3).strip()  # Название карточки
                        prompt_num = int(match.group(4))
                        prompt_text = match.group(5)
                        
                        # Сохраняем название карточки (если еще не сохранено)
                        if card_num not in card_names:
                            card_names[card_num] = card_name
                        elif card_names[card_num] != card_name:
                            print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} имеет разное название в разных строках!")
                        
                        # Инициализация структуры для карточки
                        if card_num not in prompts_by_card:
                            prompts_by_card[card_num] = {}
                        
                        # Инициализация структуры для пары промптов
                        if prompt_num not in prompts_by_card[card_num]:
                            prompts_by_card[card_num][prompt_num] = {}
                        
                        # Сохранение промпта по типу стороны
                        prompts_by_card[card_num][prompt_num][side_type] = prompt_text
                    else:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Строка {line_num} не соответствует формату: {line[:50]}...")
            
            # Преобразуем в финальную структуру с поддержкой неполных пар
            valid_prompts = {}
            total_pairs = 0
            
            for card_num in sorted(prompts_by_card.keys()):
                valid_pairs = []
                card_name = card_names.get(card_num, f"Карточка {card_num}")
                
                for pair_num in sorted(prompts_by_card[card_num].keys()):
                    pair_dict = prompts_by_card[card_num][pair_num]
                    
                    # Проверка полноты пары
                    has_face = 'лицо' in pair_dict
                    has_back = 'оборот' in pair_dict
                    
                    if not has_face:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: отсутствует 'лицо'")
                    if not has_back:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: отсутствует 'оборот'")
                    
                    # Создаем пару (может быть неполной - с None значениями)
                    pair = {
                        'лицо': pair_dict.get('лицо'),
                        'оборот': pair_dict.get('оборот')
                    }
                    
                    # Добавляем пару даже если она неполная
                    valid_pairs.append(pair)
                    total_pairs += 1
                    
                    if has_face and has_back:
                        # Полная пара
                        pass
                    else:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: неполная пара (лицо={has_face}, оборот={has_back})")
                
                if valid_pairs:
                    # Сохраняем структуру: номер карточки -> (название, список пар)
                    valid_prompts[card_num] = (card_name, valid_pairs)
            
            print(f"[ЗАГРУЗКА] Загружено {len(valid_prompts)} карточек с промптами")
            print(f"[ЗАГРУЗКА] Найдено {total_pairs} пар промптов (включая неполные)")
            
            # Подсчитываем количество изображений (только для полных пар)
            full_pairs = sum(1 for card_data in valid_prompts.values() 
                           for pair in card_data[1] 
                           if pair['лицо'] is not None and pair['оборот'] is not None)
            incomplete_pairs = total_pairs - full_pairs
            
            if incomplete_pairs > 0:
                print(f"[ЗАГРУЗКА] Полных пар: {full_pairs}, неполных пар: {incomplete_pairs}")
                print(f"[ЗАГРУЗКА] Будет создано {full_pairs * 2 + incomplete_pairs} изображений")
            else:
                print(f"[ЗАГРУЗКА] Будет создано {total_pairs * 2} изображений")
            
            if valid_prompts:
                min_card = min(valid_prompts.keys())
                max_card = max(valid_prompts.keys())
                print(f"[ЗАГРУЗКА] Карточки от {min_card} до {max_card}")
            
            return valid_prompts
            
        except Exception as e:
            print(f"[ОШИБКА] При загрузке промптов: {e}")
            return {}
    
    def get_cards_to_process(self):
        """
        Получает список карточек для обработки в мультиформатном режиме
        
        Returns:
            list: список кортежей (card_num, card_name, pairs_list)
        """
        all_prompts = self.load_prompts()
        if not all_prompts:
            return []
        
        available_cards = sorted(all_prompts.keys())
        start_card = self.settings_manager.get('START_FROM_CARD')
        cards_to_process = self.settings_manager.get('CARDS_TO_PROCESS')
        generation_mode = self.settings_manager.get('GENERATION_MODE')
        
        available_cards, end_card = self._validate_card_range(
            available_cards, start_card, cards_to_process
        )
        print(f"[ПАРСЕР] Режим генерации: {generation_mode}")
        
        cards_to_process_list = []
        cards_processed_count = 0
        
        for card_num in available_cards:
            if card_num >= start_card:
                card_name, pairs_list = all_prompts[card_num]
                print(f"[ПАРСЕР] Карточка {card_num} ({card_name}): {len(pairs_list)} пар")
                
                # Для мультиформатного режима возвращаем кортеж (номер, название, список пар)
                cards_to_process_list.append((card_num, card_name, pairs_list))
                
                cards_processed_count += 1
                
                # Останавливаемся после обработки нужного количества карточек
                if cards_processed_count >= cards_to_process:
                    print(f"[ПАРСЕР] Достигнут лимит карточек: {cards_processed_count}/{cards_to_process}")
                    break
        
        print(f"[ПАРСЕР] Итого карточек для обработки: {len(cards_to_process_list)}")
        return cards_to_process_list
