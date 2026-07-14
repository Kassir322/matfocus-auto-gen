"""Quick probe for OpenAI image generation with a custom size.

Reads two back-side prompts from data/countries_clear_nanobanana_prompts.txt
and tries to generate images with size="2508x627".
"""
from __future__ import annotations

import base64
import argparse
import re
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

from openai import OpenAI
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.settings_store import load_settings

PROMPTS_PATH = ROOT / "data" / "countries_clear_nanobanana_prompts.txt"
OUTPUT_DIR = ROOT / "generated_images" / f"custom_size_probe_{datetime.now():%Y-%m-%d_%H-%M-%S}"

MODEL = "gpt-image-2"
DEFAULT_SIZE = "2508x627"
MAX_PROMPTS = 2

LINE_RE = re.compile(
    r"^Карточка\s+(?P<card>\d+)\s+(?P<side>лицо|оборот)\s+"
    r"(?P<name>.+?)\s+-\s+Промпт\s+(?P<pair>\d+):\s+(?P<prompt>.+)$"
)


def load_api_key() -> str:
    settings = load_settings()
    api_key = str(settings.get("API_KEY_CHATGPT", "") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в окружении или локальном .env")
    return api_key


def load_back_prompts() -> list[dict]:
    prompts: list[dict] = []
    with PROMPTS_PATH.open("r", encoding="utf-8-sig") as f:
        for line in f:
            match = LINE_RE.match(line.strip())
            if not match or match.group("side") != "оборот":
                continue
            prompts.append(match.groupdict())
            if len(prompts) >= MAX_PROMPTS:
                break
    if not prompts:
        raise RuntimeError(f"Не найдено промптов оборота в {PROMPTS_PATH}")
    return prompts


def decode_and_save(b64_json: str, output_path: Path) -> tuple[int, int]:
    image_bytes = base64.b64decode(b64_json)
    image = Image.open(BytesIO(image_bytes))
    image.save(output_path, format="PNG")
    return image.size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", default=DEFAULT_SIZE, help="OpenAI Images API size, e.g. 2496x640")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    size = args.size
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=load_api_key())
    prompts = load_back_prompts()

    print(f"Пробую {len(prompts)} изображения: model={MODEL}, size={size}")
    print(f"Папка вывода: {OUTPUT_DIR}")

    for idx, item in enumerate(prompts, start=1):
        prompt = f"ar - 39:10. {item['prompt']}"
        print(f"\n[{idx}/{len(prompts)}] Карточка {item['card']} {item['name']} оборот, промпт {item['pair']}")
        try:
            response = client.images.generate(
                model=MODEL,
                prompt=prompt,
                size=size,
                n=1,
            )
        except Exception as exc:
            print(f"ОШИБКА API: {type(exc).__name__}: {exc}")
            continue

        data = getattr(response, "data", None) or []
        if not data:
            print("ОШИБКА: API вернул пустой data")
            continue

        b64_json = getattr(data[0], "b64_json", None)
        if not b64_json and isinstance(data[0], dict):
            b64_json = data[0].get("b64_json")
        if not b64_json:
            print("ОШИБКА: в ответе нет b64_json")
            continue

        safe_name = re.sub(r"[^\wа-яА-ЯёЁ-]+", "_", item["name"], flags=re.IGNORECASE).strip("_")
        output_path = OUTPUT_DIR / f"card_{item['card']}_{safe_name}_back_prompt_{item['pair']}.png"
        width, height = decode_and_save(b64_json, output_path)
        print(f"OK: {output_path.name} -> {width}x{height}, ratio={width / height:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
