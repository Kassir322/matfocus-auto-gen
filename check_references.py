"""
Скрипт проверки соответствия референсов и промптов для режима multiformat_with_refs.
Проверяет наличие всех референсных изображений для промптов из файла.
"""
import os
import sys

# Добавляем корневую папку в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sites.aistudio.mode_multiformat import load_tasks_from_file
from sites.aistudio.mode_multiformat_with_refs import get_reference_path, safe_filename

def check_references(prompts_file: str):
    """
    Проверяет наличие референсов для всех задач из файла промптов.
    """
    print(f"Проверка файла промптов: {prompts_file}")
    print("=" * 60)
    
    # Загружаем задачи
    tasks = load_tasks_from_file(prompts_file)
    
    if not tasks:
        print("❌ Не удалось загрузить задачи из файла!")
        return False
    
    print(f"[OK] Загружено задач: {len(tasks)}")
    
    # Подсчитываем карточки
    cards = set(t["card_number"] for t in tasks)
    print(f"[OK] Карточек: {len(cards)} (номера: {min(cards)}-{max(cards)})")
    
    # Проверяем референсы
    found_count = 0
    missing = []
    
    for task in tasks:
        side = task["side"]
        card_number = task["card_number"]
        card_name = task["card_name"]
        
        ref_path = get_reference_path(side, card_number, card_name)
        
        if ref_path:
            found_count += 1
        else:
            safe_name = safe_filename(card_name)
            expected = f"{side}_{card_number}_{safe_name}.png/.jpg"
            missing.append((side, card_number, card_name, expected))
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ ПРОВЕРКИ РЕФЕРЕНСОВ:")
    print("=" * 60)
    print(f"Найдено: {found_count}/{len(tasks)}")
    
    if missing:
        print(f"\n[WARN] Отсутствуют референсы ({len(missing)}):")
        for side, card_num, card_name, expected in missing:
            print(f"  - {side} карточки {card_num} ({card_name})")
            print(f"    Ожидается: {expected}")
        return False
    else:
        print("\n[OK] Все референсы найдены!")
        return True

if __name__ == "__main__":
    # Проверяем файл из настроек
    prompts_file = "data/prompts_ref.txt"
    
    if not os.path.exists(prompts_file):
        print(f"[ERROR] Файл не найден: {prompts_file}")
        sys.exit(1)
    
    success = check_references(prompts_file)
    sys.exit(0 if success else 1)
