"""
Скрипт для конвертации промптов из мультиформатного вида в стандартный формат.

Исходный формат (multiformat):
    Карточка {N} {сторона} {название} - Промпт {M}: {текст}

Целевой формат (standard):
    Карточка {N} - Промпт {M}: {текст}

Логика конвертации:
- Для каждой карточки собираются все промпты (сначала "лицо", потом "оборот")
- Промпты нумеруются последовательно (1, 2, 3, ...)
- Убираются сторона и название карточки
"""

import re
from collections import defaultdict


def parse_multiformat_line(line: str) -> dict | None:
    """
    Парсит строку в мультиформатном виде.
    
    Args:
        line: строка вида "Карточка {N} {сторона} {название} - Промпт {M}: {текст}"
    
    Returns:
        dict с ключами: card_number, side, name, prompt_number, prompt_text
        или None, если строка не соответствует формату
    """
    # Regex: Карточка {N} {сторона} {название} - Промпт {M}: {текст}
    pattern = r'^Карточка (\d+) (лицо|оборот) (.+?) - Промпт (\d+): (.+)$'
    match = re.match(pattern, line)
    
    if not match:
        return None
    
    return {
        'card_number': int(match.group(1)),
        'side': match.group(2),
        'name': match.group(3).strip(),
        'prompt_number': int(match.group(4)),
        'prompt_text': match.group(5).strip()
    }


def convert_multiformat_to_standard(input_file: str, output_file: str) -> None:
    """
    Конвертирует файл промптов из мультиформата в стандартный формат.
    
    Args:
        input_file: путь к исходному файлу (multiformat)
        output_file: путь к выходному файлу (standard)
    """
    # Временное хранилище: {card_number: {'лицо': [(prompt_num, text), ...], 'оборот': [...]}}
    cards_data = defaultdict(lambda: {'лицо': {}, 'оборот': {}})
    
    # Читаем и парсим исходный файл
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            
            # Пропускаем пустые строки
            if not line:
                continue
            
            # Парсим строку
            parsed = parse_multiformat_line(line)
            
            if parsed:
                card_num = parsed['card_number']
                side = parsed['side']
                prompt_num = parsed['prompt_number']
                prompt_text = parsed['prompt_text']
                
                # Сохраняем промпт
                cards_data[card_num][side][prompt_num] = prompt_text
            else:
                print(f"[WARN] Строка {line_num} не распознана: {line[:60]}...")
    
    # Формируем выходной файл
    with open(output_file, 'w', encoding='utf-8') as f:
        # Обрабатываем карточки по порядку номеров
        for card_num in sorted(cards_data.keys()):
            card = cards_data[card_num]
            
            # Собираем все промпты: сначала лицо, потом оборот
            all_prompts = []
            
            # Промпты лица (сортируем по номеру)
            if card['лицо']:
                for prompt_num in sorted(card['лицо'].keys()):
                    all_prompts.append(card['лицо'][prompt_num])
            
            # Промпты оборота (сортируем по номеру)
            if card['оборот']:
                for prompt_num in sorted(card['оборот'].keys()):
                    all_prompts.append(card['оборот'][prompt_num])
            
            # Записываем в стандартном формате с последовательной нумерацией
            for idx, prompt_text in enumerate(all_prompts, start=1):
                f.write(f"Карточка {card_num} - Промпт {idx}: {prompt_text}\n")
                
                # Пустая строка между промптами для читаемости
                if idx < len(all_prompts):
                    f.write("\n")
            
            # Пустая строка между карточками
            f.write("\n")
    
    # Статистика
    total_cards = len(cards_data)
    total_prompts = sum(
        len(card['лицо']) + len(card['оборот']) 
        for card in cards_data.values()
    )
    
    print(f"[OK] Конвертация завершена!")
    print(f"   Карточек обработано: {total_cards}")
    print(f"   Промптов всего: {total_prompts}")
    print(f"   Результат сохранён: {output_file}")


if __name__ == "__main__":
    # Пути к файлам
    input_file = "data/all_card_prompts.txt"
    output_file = "data/all_card_prompts_standard.txt"
    
    print("Конвертация промптов из мультиформата в стандартный формат...")
    print(f"Исходный файл: {input_file}")
    print(f"Выходной файл: {output_file}")
    print()
    
    try:
        convert_multiformat_to_standard(input_file, output_file)
    except FileNotFoundError:
        print(f"[ERROR] Файл {input_file} не найден")
    except Exception as e:
        print(f"[ERROR] {e}")
