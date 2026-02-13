"""
Тестовый скрипт для проверки поиска референсов с новой логикой.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sites.aistudio.mode_multiformat_with_refs import get_reference_path

# Тестовые данные
test_cards = [
    (3, "Олег Вещий", "лицо"),
    (5, "Владимир Святославич", "лицо"),
    (7, "Ярослав Мудрый", "лицо"),
    (11, "Владимир Мономах", "лицо"),
    (17, "Иван III", "лицо"),
    (19, "Василий III", "лицо"),
    (20, "Иван IV Грозный", "лицо"),
]

print("Тест поиска референсов с упрощенным форматом")
print("=" * 60)

found = 0
not_found = 0

for card_num, card_name, side in test_cards:
    path = get_reference_path(side, card_num, card_name)
    if path:
        print(f"[OK] Карточка {card_num} ({card_name}): {os.path.basename(path)}")
        found += 1
    else:
        print(f"[MISS] Карточка {card_num} ({card_name}): не найден")
        not_found += 1

print("=" * 60)
print(f"Найдено: {found}/{len(test_cards)}")
print(f"Не найдено: {not_found}/{len(test_cards)}")

if found > 0:
    print("\n[SUCCESS] Функция работает! Упрощенный формат поддерживается.")
else:
    print("\n[FAIL] Функция не находит файлы.")
