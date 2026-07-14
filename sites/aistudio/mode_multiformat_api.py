"""
Мультиформатный режим генерации через API.
"""
import os
import time
from datetime import datetime

from utils import api_client
from utils.agent_run_result import make_error_result, make_success_result
from utils import chatgpt_parallel
from utils import generation_stats
from utils.log_writer import write_log_line
from utils.paths import LOGS_DIR
from utils.prompt_parsers import (
    filter_tasks_by_range,
    get_plan_info_multiformat,
    parse_multiformat_prompts,
)


API_REQUEST_DELAY = 1.0


def _make_card_completion_tracker(tasks: list[dict], save_progress: bool = True):
    from utils.settings_store import update_start_card

    remaining_by_card = {}
    for task in tasks:
        card_number = int(task["card_number"])
        remaining_by_card[card_number] = remaining_by_card.get(card_number, 0) + 1

    def mark_task_done(task: dict) -> None:
        card_number = int(task["card_number"])
        if card_number not in remaining_by_card:
            return
        remaining_by_card[card_number] -= 1
        if remaining_by_card[card_number] == 0:
            if not save_progress:
                return
            update_start_card(card_number + 1)

    return mark_task_done


def load_tasks_from_file(path: str) -> list[dict]:
    return parse_multiformat_prompts(path)


def get_plan_info(tasks: list[dict]) -> dict:
    return get_plan_info_multiformat(tasks)


def _get_log_filepath() -> str:
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(str(LOGS_DIR), f"auto-gen_{timestamp}.log")


def _make_filename(card_number: int, side: str, pair_num: int) -> str:
    return f"Карточка_{card_number}_{side}_промпт_{pair_num}.png"


def _make_task_label(task: dict) -> str:
    return f"карточка {task['card_number']} {task['side']} пара {task['pair_number']}"


def _generate_single_image_api(task: dict, client, settings: dict, log_file) -> bool:
    card_number = task["card_number"]
    pair_num = task["pair_number"]
    side = task["side"]
    prompt_text = task.get("prompt_text", "").strip()
    task.pop("_last_failure_reason", None)

    if not prompt_text:
        task["_last_failure_reason"] = "пустой промпт"
        write_log_line(log_file, f"[WARN] Пропуск: пустой промпт карточка {card_number} пара {pair_num} {side}")
        return False

    provider = api_client.get_api_provider(settings, with_reference=False)
    provider_name = api_client.get_provider_display_name(provider)
    model = api_client.get_api_model(settings, provider, with_reference=False)
    quality = api_client.get_api_quality(settings, provider)
    raw_image_size = api_client.resolve_image_size(settings, side)
    image_size, size_error = api_client.normalize_image_size_for_provider(provider, raw_image_size)
    if size_error:
        image_size = raw_image_size
    timeout = float(settings.get("API_TIMEOUT", 60.0))
    aspect_ratio = settings.get("FACE_ASPECT_RATIO", "4:3") if side == "лицо" else settings.get("BACK_ASPECT_RATIO", "16:9")
    file_name = _make_filename(card_number, side, pair_num)

    write_log_line(log_file, f"[SIDE] {side}: генерация через API")
    write_log_line(
        log_file,
        f"[API_REQUEST] provider={provider_name}, model={model}, size={image_size}, aspect={aspect_ratio}, prompt_length={len(prompt_text)}",
    )

    image_bytes, error_msg = api_client.generate_image(
        client=client,
        prompt=prompt_text,
        model=model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        timeout=timeout,
        provider=provider,
        quality=quality,
    )

    if not image_bytes:
        if error_msg:
            task["_last_failure_reason"] = error_msg.splitlines()[0].strip() or "API ошибка"
            write_log_line(log_file, f"[ERROR] API ошибка для {file_name}:")
            for line in error_msg.split("\n"):
                if line.strip():
                    write_log_line(log_file, f"[ERROR]   {line}")
        else:
            task["_last_failure_reason"] = "API вернул пустой результат"
            write_log_line(log_file, f"[ERROR] API вернул пустой результат для {file_name}")
        return False

    write_log_line(log_file, f"[API_RESPONSE] Получено изображение, размер: {len(image_bytes)} байт")
    if not api_client.save_image_bytes(image_bytes, file_name):
        task["_last_failure_reason"] = "не удалось сохранить файл"
        write_log_line(log_file, f"[ERROR] Не удалось сохранить файл: {file_name}")
        return False

    task.pop("_last_failure_reason", None)
    write_log_line(log_file, f"[OK] Файл сохранён: {file_name}")
    return True


def run_mode(
    tasks: list[dict],
    settings: dict,
    coordinates: dict = None,
    relative_movements: dict = None,
) -> None:
    mode_name = "multiformat"
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)

    tasks = filter_tasks_by_range(tasks, start_card, end_card)
    actual_end = end_card if end_card is not None else (max(t["card_number"] for t in tasks) if tasks else start_card)
    if not tasks:
        message = "Нет задач в выбранном диапазоне карточек."
        print(message)
        return make_error_result(mode_name, message)

    provider = api_client.get_api_provider(settings, with_reference=False)
    provider_name = api_client.get_provider_display_name(provider)
    api_key = api_client.get_api_key(settings, provider)
    if not api_key:
        message = f"Ошибка: не задан API ключ для провайдера {provider_name}."
        print(message)
        return make_error_result(mode_name, message)

    key_valid, key_error = api_client.check_api_key_format(api_key, provider=provider)
    if not key_valid:
        message = f"Ошибка: {provider_name}: {key_error}"
        print(message)
        return make_error_result(mode_name, message)

    try:
        client = api_client.init_client(api_key, provider=provider)
    except ImportError as e:
        message = f"Ошибка: {e}"
        print(message)
        return make_error_result(mode_name, message)
    except Exception as e:
        message = f"Ошибка инициализации API клиента: {e}"
        print(message)
        return make_error_result(mode_name, message)

    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        prompts_file = settings.get("PROMPTS_FILE", "")
        model = api_client.get_api_model(settings, provider)
        quality = api_client.get_api_quality(settings, provider)
        session_folder = api_client.get_session_output_folder(settings)
        face_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
        back_ratio = settings.get("BACK_ASPECT_RATIO", "16:9")
        raw_face_image_size = api_client.resolve_image_size(settings, "лицо")
        raw_back_image_size = api_client.resolve_image_size(settings, "оборот")
        face_image_size, _ = api_client.normalize_image_size_for_provider(provider, raw_face_image_size)
        back_image_size, _ = api_client.normalize_image_size_for_provider(provider, raw_back_image_size)
        face_image_size = face_image_size or raw_face_image_size
        back_image_size = back_image_size or raw_back_image_size

        write_log_line(
            log_file,
            f"[PLAN] Режим: multiformat (API). Карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}",
        )
        write_log_line(log_file, f"[PLAN] Диапазон карточек: {start_card}–{actual_end}")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")
        write_log_line(log_file, f"[PLAN] Провайдер: {provider_name}")
        write_log_line(log_file, f"[PLAN] API модель: {model}")
        write_log_line(log_file, f"[PLAN] Aspect ratio: лицо={face_ratio}, оборот={back_ratio}")
        write_log_line(log_file, f"[PLAN] Image size: лицо={face_image_size}, оборот={back_image_size}")
        write_log_line(log_file, f"[PLAN] Папка для сохранения изображений: {session_folder}")

        face_count = sum(1 for task in tasks if task["side"] == "лицо")
        back_count = len(tasks) - face_count
        estimate_items = [
            {"count": face_count, "provider": provider, "model": model, "quality": quality, "aspect_ratio": face_ratio},
            {"count": back_count, "provider": provider, "model": model, "quality": quality, "aspect_ratio": back_ratio},
        ]
        estimated_cost_total, estimated_cost_per_image = generation_stats.estimate_api_totals(estimate_items)
        stats = generation_stats.GenerationRunStats(
            planned_total=len(tasks),
            generation_method="api",
            mode_name="multiformat",
            estimated_total_seconds=generation_stats.estimate_total_seconds(
                planned_total=len(tasks),
                generation_method="api",
                mode_name="multiformat",
                settings=settings,
                estimate_items=estimate_items,
            ),
            estimated_cost_total=estimated_cost_total,
            estimated_cost_per_image=estimated_cost_per_image,
        )
        start_lines = stats.start_summary_lines(
            [
                "Режим: multiformat (API)",
                f"Провайдер: {provider_name}",
                f"Модель: {model}",
                f"Quality: {quality or 'n/a'}",
                f"Aspect ratio: лицо={face_ratio}, оборот={back_ratio}",
                f"Image size: лицо={face_image_size}, оборот={back_image_size}",
                f"Диапазон карточек: {start_card}–{actual_end}",
                f"Файл промптов: {prompts_file or 'не указан'}",
                (
                    f"Параллельных воркеров: {chatgpt_parallel.get_parallel_config(settings)['max_workers']}"
                    if chatgpt_parallel.is_parallel_enabled(settings, provider)
                    else "Параллельных воркеров: 1"
                ),
                (
                    "Лимит запусков: "
                    f"{chatgpt_parallel.get_parallel_config(settings)['rate_limit_ipm']} за "
                    f"{chatgpt_parallel.get_parallel_config(settings)['window_seconds']} сек"
                    if chatgpt_parallel.is_parallel_enabled(settings, provider)
                    else "Лимит запусков: последовательный режим"
                ),
                (
                    "Алгоритм: скользящее окно"
                    if chatgpt_parallel.is_parallel_enabled(settings, provider)
                    else "Алгоритм: последовательный запуск"
                ),
            ]
        )
        for line in start_lines:
            print(line)
            write_log_line(log_file, f"[PLAN] {line}")

        print(f"Изображения будут сохранены в: {session_folder}")
        print("Генерация через API запущена. Esc — остановка.")

        total_images = len(tasks)
        cards_seen = {task["card_number"] for task in tasks}
        pairs_seen = {(task["card_number"], task["pair_number"]) for task in tasks}
        card_tracker = _make_card_completion_tracker(
            tasks,
            save_progress=bool(settings.get("SAVE_PROGRESS_TO_SETTINGS", True)),
        )

        if chatgpt_parallel.is_parallel_enabled(settings, provider):
            chatgpt_parallel.run_parallel_chatgpt_tasks(
                tasks=tasks,
                settings=settings,
                stats=stats,
                log_file=log_file,
                execute_task=lambda task, worker_id: _generate_single_image_api(task, client, settings, log_file),
                normalize_result=generation_stats.normalize_attempt_result,
                label_for_task=_make_task_label,
                on_task_completed=lambda task, ok, reason: card_tracker(task),
                print_fn=print,
            )
        else:
            last_card = None
            last_pair = None
            for task in tasks:
                card_number = task["card_number"]
                pair_number = task["pair_number"]
                pair_key = (card_number, pair_number)

                if card_number != last_card:
                    if last_card is not None:
                        time.sleep(0.5)
                    write_log_line(log_file, f"[CARD] Карточка {card_number}")
                    last_card = card_number

                if pair_key != last_pair:
                    write_log_line(log_file, f"[PAIR] Пара {pair_number}")
                    last_pair = pair_key

                label = _make_task_label(task)
                attempt_started = time.monotonic()
                result = _generate_single_image_api(task, client, settings, log_file)
                duration_seconds = time.monotonic() - attempt_started
                ok, reason = generation_stats.normalize_attempt_result(task, result)
                stats.register_attempt(label, ok, duration_seconds, reason)

                print(stats.progress_line(duration_seconds))
                write_log_line(log_file, stats.progress_log_line(label, duration_seconds, ok, reason))
                card_tracker(task)

                if stats.attempted < total_images:
                    time.sleep(API_REQUEST_DELAY)

        if provider == api_client.PROVIDER_CHATGPT:
            actual_cost, actual_error = api_client.fetch_openai_costs(
                api_key=api_key,
                start_time=stats.started_epoch_seconds(),
                end_time=stats.finished_epoch_seconds(),
            )
            if actual_cost is not None:
                stats.set_actual_cost(actual_cost, "Фактические расходы ChatGPT")
                write_log_line(log_file, f"[SUMMARY] Фактические расходы ChatGPT: {actual_cost:.3f} USD")
            else:
                stats.set_actual_cost_error(actual_error or "billing API ещё не синхронизирован")

        write_log_line(
            log_file,
            f"[SUMMARY] Карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {stats.succeeded}/{total_images}",
        )
        for line in stats.summary_lines():
            print(line)
            if line.startswith("- "):
                write_log_line(log_file, f"[FAILED] {line[2:]}")
            else:
                write_log_line(log_file, f"[SUMMARY] {line}")
        print(f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {stats.succeeded}/{total_images}")
        print(f"Лог сохранён: {log_path}")
        return make_success_result(
            mode_name,
            planned=total_images,
            succeeded=stats.succeeded,
            output_dir=session_folder,
            log_file=log_path,
        )
    finally:
        log_file.close()
