"""
Обработка файлов с промптами
"""
import os
import re

class FileHandler:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
    
    def load_prompts(self):
        """Загружает промпты из файла в новом формате"""
        prompts_file = self.settings_manager.get('PROMPTS_FILE')
        prompts = {}
        
        try:
            if not os.path.exists(prompts_file):
                print(f"[ОШИБКА] Файл {prompts_file} не найден!")
                return prompts
                
            for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
                try:
                    with open(prompts_file, 'r', encoding=encoding) as file:
                        print(f"[ЗАГРУЗКА] Используется кодировка: {encoding}")
                        
                        for line_num, line in enumerate(file, 1):
                            line = line.strip()
                            if line and 'Карточка' in line:
                                match = re.search(r'Карточка (\d+) - Промпт (\d+): (.+)', line)
                                if match:
                                    card_num = int(match.group(1))
                                    prompt_num = int(match.group(2))
                                    prompt_text = match.group(3)
                                    
                                    if card_num not in prompts:
                                        prompts[card_num] = ['', '', '']
                                    
                                    while len(prompts[card_num]) < prompt_num:
                                        prompts[card_num].append('')
                                    
                                    if prompt_num >= 1:
                                        prompts[card_num][prompt_num - 1] = prompt_text
                                else:
                                    print(f"[ПРЕДУПРЕЖДЕНИЕ] Строка {line_num} не соответствует формату: {line[:50]}...")
                        break
                        
                except UnicodeDecodeError:
                    continue
                    
            print(f"[ЗАГРУЗКА] Загружено {len(prompts)} карточек с промптами")
            
            if prompts:
                min_card = min(prompts.keys())
                max_card = max(prompts.keys())
                print(f"[ЗАГРУЗКА] Карточки от {min_card} до {max_card}")
            
            return prompts
            
        except Exception as e:
            print(f"[ОШИБКА] При загрузке промптов: {e}")
            return prompts
    
    def get_cards_to_process(self):
        """Получает список карточек для обработки"""
        all_prompts = self.load_prompts()
        if not all_prompts:
            return []
        
        available_cards = sorted(all_prompts.keys())
        start_card = self.settings_manager.get('START_FROM_CARD')
        cards_to_process = self.settings_manager.get('CARDS_TO_PROCESS')
        
        cards_to_process_list = [] 
        cards_processed_count = 0
        
        for card_num in available_cards:
            if card_num >= start_card:
                cards_to_process_list.append((card_num, all_prompts[card_num]))
                cards_processed_count += 1
                
                if cards_processed_count >= cards_to_process:
                    break
        
        return cards_to_process_list