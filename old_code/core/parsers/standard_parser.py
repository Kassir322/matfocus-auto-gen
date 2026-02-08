"""
Парсер промптов для стандартного режима генерации
Формат: Карточка X - Промпт Y: текст
"""
import re
from .base_parser import BaseParser


class StandardParser(BaseParser):
    """Парсер для стандартного режима (множественные генерации на карточку)"""
    
    def load_prompts(self):
        """
        Загружает промпты из файла в формате стандартного режима
        
        Формат строки: Карточка X - Промпт Y: текст
        
        Returns:
            dict: {card_num: (card_name, [prompt1, prompt2, ...])}
        """
        prompts_file = self.settings_manager.get('PROMPTS_FILE')
        print(f"[ПАРСЕР] Загружаем промпты из файла: {prompts_file}")
        
        prompts_by_card = {}
        
        try:
            lines = self._read_file(prompts_file)
            if lines is None:
                return {}
            
            # Регулярное выражение для формата: Карточка X - Промпт Y: текст
            pattern = r'Карточка (\d+) - Промпт (\d+): (.+)'
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and 'Карточка' in line:
                    match = re.search(pattern, line)
                    if match:
                        card_num = int(match.group(1))
                        prompt_num = int(match.group(2))
                        prompt_text = match.group(3).strip()
                        
                        # Инициализация структуры для карточки
                        if card_num not in prompts_by_card:
                            prompts_by_card[card_num] = []
                        
                        # Добавляем промпт (может быть несколько промптов на карточку)
                        # Сортируем по номеру промпта, но сохраняем все
                        prompts_by_card[card_num].append((prompt_num, prompt_text))
                    else:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Строка {line_num} не соответствует формату: {line[:50]}...")
            
            # Преобразуем в финальную структуру: сортируем промпты по номеру
            valid_prompts = {}
            for card_num in sorted(prompts_by_card.keys()):
                # Сортируем промпты по номеру и извлекаем только текст
                sorted_prompts = sorted(prompts_by_card[card_num], key=lambda x: x[0])
                prompts_list = [prompt_text for _, prompt_text in sorted_prompts]
                
                # Название карточки по умолчанию
                card_name = f"Карточка {card_num}"
                
                if prompts_list:
                    valid_prompts[card_num] = (card_name, prompts_list)
            
            print(f"[ЗАГРУЗКА] Загружено {len(valid_prompts)} карточек с промптами")
            
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
        Получает список карточек для обработки в стандартном режиме
        
        Returns:
            list: список кортежей (card_num, card_name, prompts_list)
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
                card_name, prompts_list = all_prompts[card_num]
                print(f"[ПАРСЕР] Карточка {card_num} ({card_name}): {len(prompts_list)} промптов")
                
                # Для стандартного режима возвращаем кортеж (номер, название, список промптов)
                cards_to_process_list.append((card_num, card_name, prompts_list))
                
                cards_processed_count += 1
                
                # Останавливаемся после обработки нужного количества карточек
                if cards_processed_count >= cards_to_process:
                    print(f"[ПАРСЕР] Достигнут лимит карточек: {cards_processed_count}/{cards_to_process}")
                    break
        
        print(f"[ПАРСЕР] Итого карточек для обработки: {len(cards_to_process_list)}")
        return cards_to_process_list
