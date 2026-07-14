"""Парсер единственного формата лицо/оборот с референсами."""

import re
from collections import defaultdict


PROMPT_LINE_PATTERN = re.compile(
    r"^Карточка (\d+) (лицо|оборот) (.+?) - Промпт (\d+): (.+)$"
)


def parse_multiformat_prompts(path: str) -> list[dict]:
    cards: dict[int, dict] = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as source:
            for raw_line in source:
                match = PROMPT_LINE_PATTERN.match(raw_line.strip())
                if not match:
                    continue
                card_number = int(match.group(1))
                side = match.group(2)
                card_name = match.group(3).strip()
                pair_number = int(match.group(4))
                prompt_text = match.group(5).strip()
                card = cards.setdefault(card_number, {"name": card_name, "pairs": defaultdict(dict)})
                card["pairs"][pair_number][side] = prompt_text
    except (OSError, UnicodeDecodeError):
        return []

    tasks: list[dict] = []
    for card_number in sorted(cards):
        card = cards[card_number]
        for pair_number in sorted(card["pairs"]):
            for side in ("лицо", "оборот"):
                prompt_text = card["pairs"][pair_number].get(side)
                if prompt_text:
                    tasks.append({"card_number": card_number, "card_name": card["name"], "pair_number": pair_number, "side": side, "prompt_text": prompt_text})
    return tasks


def get_plan_info_multiformat(tasks: list[dict]) -> dict:
    if not tasks:
        return {"cards_count": 0, "pairs_count": 0, "images_planned": 0}
    return {"cards_count": len({task["card_number"] for task in tasks}), "pairs_count": len({(task["card_number"], task["pair_number"]) for task in tasks}), "images_planned": len(tasks)}


def filter_tasks_by_range(tasks: list[dict], start_card: int, end_card: int | None) -> list[dict]:
    if not tasks:
        return []
    if end_card is None:
        end_card = max(task["card_number"] for task in tasks)
    return [task for task in tasks if start_card <= task["card_number"] <= end_card]
