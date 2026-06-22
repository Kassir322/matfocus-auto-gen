"""
Мультиформатный режим с референсами через API.

Может использовать разные провайдеры:
- без референса: API_PROVIDER
- с референсом: API_PROVIDER_WITH_REFS
"""
import os
import sys
import time
import traceback
from datetime import datetime

from utils import api_client
from utils.agent_run_result import make_error_result, make_success_result
from utils import chatgpt_parallel
from utils import generation_stats
from utils.log_writer import write_log_line
from utils.prompt_parsers import (
    filter_tasks_by_range,
    get_plan_info_multiformat,
    parse_multiformat_prompts,
)


API_REQUEST_DELAY = 1.0


def _safe_print(message: str) -> None:
    text = str(message)
    try:
        print(text)
        return
    except UnicodeEncodeError:
        pass

    stream = sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    buffer = getattr(stream, "buffer", None)
    encoded = text.encode(encoding, errors="replace") + b"\n"

    if buffer is not None:
        buffer.write(encoded)
        buffer.flush()
        return

    fallback_text = encoded.decode(encoding, errors="replace")
    stream.write(fallback_text)
    stream.flush()


def safe_filename(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    for char in [":", "*", "?", '"', "<", ">", "|"]:
        safe = safe.replace(char, "")
    return safe


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


def _prepare_task_provider_metadata(tasks: list[dict], settings: dict) -> tuple[list[dict], list[dict]]:
    chatgpt_tasks = []
    other_tasks = []
    for task in tasks:
        ref_path = get_reference_path(task["side"], task["card_number"], task["card_name"])
        with_reference = ref_path is not None
        task["_with_reference"] = with_reference
        provider = api_client.get_api_provider(settings, with_reference=with_reference)
        task["_planned_provider"] = provider
        if provider == api_client.PROVIDER_CHATGPT:
            chatgpt_tasks.append(task)
        else:
            other_tasks.append(task)
    return chatgpt_tasks, other_tasks


def get_reference_path(side: str, card_number: int, card_name: str):
    base_folder = os.path.join("data", "images", side)
    for ext in ["png", "jpg"]:
        simple_name = os.path.join(base_folder, f"{card_number}_{side}.{ext}")
        if os.path.exists(simple_name):
            return simple_name

    safe_name = safe_filename(card_name)
    for ext in ["png", "jpg"]:
        full_name = os.path.join(base_folder, f"{side}_{card_number}_{safe_name}.{ext}")
        if os.path.exists(full_name):
            return full_name
    return None


def load_tasks_from_file(path: str) -> list[dict]:
    return parse_multiformat_prompts(path)


def get_plan_info(tasks: list[dict]) -> dict:
    return get_plan_info_multiformat(tasks)


def _get_log_filepath() -> str:
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join("logs", f"auto-gen_{timestamp}.log")


def _make_filename(card_number: int, card_name: str, side: str, pair_num: int, provider: str, model_name: str) -> str:
    safe_name = safe_filename(card_name)
    provider_name = api_client.get_provider_display_name(provider)
    return f"Карточка_{card_number}_{safe_name}_{side}_промпт_{pair_num}_{provider_name}_{model_name}.png"


def _make_task_label(task: dict, with_reference: bool) -> str:
    ref_mark = " with_ref" if with_reference else ""
    return f"карточка {task['card_number']} {task['side']} пара {task['pair_number']}{ref_mark}"


def _generate_single_image_api(task: dict, clients: dict, settings: dict, log_file) -> bool:
    card_number = task["card_number"]
    card_name = task["card_name"]
    pair_num = task["pair_number"]
    side = task["side"]
    prompt_text = task.get("prompt_text", "").strip()
    task.pop("_last_failure_reason", None)

    if not prompt_text:
        task["_last_failure_reason"] = "пустой промпт"
        write_log_line(log_file, f"[WARN] Пропуск: пустой промпт карточка {card_number} пара {pair_num} {side}")
        return False

    ref_path = get_reference_path(side, card_number, card_name)
    with_reference = bool(task.get("_with_reference", ref_path is not None))
    task["_with_reference"] = with_reference
    provider = api_client.get_api_provider(settings, with_reference=with_reference)
    provider_name = api_client.get_provider_display_name(provider)
    model = api_client.get_api_model(settings, provider, with_reference=with_reference)
    quality = api_client.get_api_quality(settings, provider)
    raw_image_size = api_client.resolve_image_size(settings, side)
    image_size, size_error = api_client.normalize_image_size_for_provider(provider, raw_image_size)
    if size_error:
        image_size = raw_image_size
    timeout = float(settings.get("API_TIMEOUT", 60.0))
    aspect_ratio = settings.get("FACE_ASPECT_RATIO", "4:3") if side == "лицо" else settings.get("BACK_ASPECT_RATIO", "16:9")
    client = clients[provider]

    if ref_path:
        write_log_line(log_file, f"[REF] Найден референс: {ref_path}")
    else:
        write_log_line(log_file, "[INFO] Референс не найден, генерация без референса")

    write_log_line(log_file, f"[MODEL] Провайдер: {provider_name}, модель: {model}")
    file_name = _make_filename(card_number, card_name, side, pair_num, provider, model)
    write_log_line(log_file, f"[GEN] Генерация: {file_name}")
    write_log_line(
        log_file,
        f"[API_REQUEST] provider={provider_name}, model={model}, size={image_size}, aspect={aspect_ratio}, prompt_length={len(prompt_text)}, with_ref={with_reference}",
    )

    if ref_path:
        image_bytes, error_msg = api_client.generate_image_with_reference(
            client=client,
            prompt=prompt_text,
            reference_image_path=ref_path,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            timeout=timeout,
            provider=provider,
            quality=quality,
        )
    else:
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
    mode_name = "multiformat_with_refs"
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)

    tasks = filter_tasks_by_range(tasks, start_card, end_card)
    actual_end = end_card if end_card is not None else (max(t["card_number"] for t in tasks) if tasks else start_card)
    if not tasks:
        message = "Нет задач в выбранном диапазоне карточек."
        _safe_print(message)
        return make_error_result(mode_name, message)

    providers = {
        api_client.get_api_provider(settings, with_reference=False),
        api_client.get_api_provider(settings, with_reference=True),
    }
    clients = {}

    for provider in providers:
        provider_name = api_client.get_provider_display_name(provider)
        api_key = api_client.get_api_key(settings, provider)
        if not api_key:
            message = f"Ошибка: не задан API ключ для провайдера {provider_name}."
            _safe_print(message)
            return make_error_result(mode_name, message)

        key_valid, key_error = api_client.check_api_key_format(api_key, provider=provider)
        if not key_valid:
            message = f"Ошибка: {provider_name}: {key_error}"
            _safe_print(message)
            return make_error_result(mode_name, message)

        try:
            clients[provider] = api_client.init_client(api_key, provider=provider)
        except ImportError as e:
            message = f"Ошибка: {e}"
            _safe_print(message)
            return make_error_result(mode_name, message)
        except Exception as e:
            message = f"Ошибка инициализации API клиента {provider_name}: {e}"
            _safe_print(message)
            return make_error_result(mode_name, message)

    session_folder = None
    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        prompts_file = settings.get("PROMPTS_FILE", "")
        provider_no_ref = api_client.get_api_provider(settings, with_reference=False)
        provider_with_ref = api_client.get_api_provider(settings, with_reference=True)
        model_no_ref = api_client.get_api_model(settings, provider_no_ref, with_reference=False)
        model_with_ref = api_client.get_api_model(settings, provider_with_ref, with_reference=True)
        quality_no_ref = api_client.get_api_quality(settings, provider_no_ref)
        quality_with_ref = api_client.get_api_quality(settings, provider_with_ref)
        face_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
        back_ratio = settings.get("BACK_ASPECT_RATIO", "16:9")
        raw_face_image_size = api_client.resolve_image_size(settings, "лицо")
        raw_back_image_size = api_client.resolve_image_size(settings, "оборот")
        face_image_size_no_ref, _ = api_client.normalize_image_size_for_provider(provider_no_ref, raw_face_image_size)
        back_image_size_no_ref, _ = api_client.normalize_image_size_for_provider(provider_no_ref, raw_back_image_size)
        face_image_size_with_ref, _ = api_client.normalize_image_size_for_provider(provider_with_ref, raw_face_image_size)
        back_image_size_with_ref, _ = api_client.normalize_image_size_for_provider(provider_with_ref, raw_back_image_size)
        face_image_size_no_ref = face_image_size_no_ref or raw_face_image_size
        back_image_size_no_ref = back_image_size_no_ref or raw_back_image_size
        face_image_size_with_ref = face_image_size_with_ref or raw_face_image_size
        back_image_size_with_ref = back_image_size_with_ref or raw_back_image_size
        session_folder = api_client.get_session_output_folder(settings)

        write_log_line(
            log_file,
            f"[PLAN] Режим: multiformat_with_refs (API). Карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}",
        )
        write_log_line(log_file, f"[PLAN] Диапазон карточек: {start_card}–{actual_end}")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")
        write_log_line(
            log_file,
            f"[PLAN] Без референсов: provider={api_client.get_provider_display_name(provider_no_ref)}, model={model_no_ref}",
        )
        write_log_line(
            log_file,
            f"[PLAN] С референсами: provider={api_client.get_provider_display_name(provider_with_ref)}, model={model_with_ref}",
        )
        write_log_line(log_file, f"[PLAN] Aspect ratio: лицо={face_ratio}, оборот={back_ratio}")
        write_log_line(log_file, f"[PLAN] Image size без refs: лицо={face_image_size_no_ref}, оборот={back_image_size_no_ref}")
        write_log_line(log_file, f"[PLAN] Image size с refs: лицо={face_image_size_with_ref}, оборот={back_image_size_with_ref}")
        write_log_line(log_file, f"[PLAN] Папка для сохранения изображений: {session_folder}")

        chatgpt_tasks, non_chatgpt_tasks = _prepare_task_provider_metadata(tasks, settings)
        estimate_items = []
        chatgpt_tasks_count = 0
        refs_found = 0
        refs_missing = 0
        for task in tasks:
            with_reference = bool(task.get("_with_reference", False))
            if with_reference:
                refs_found += 1
            else:
                refs_missing += 1
            provider = task.get("_planned_provider") or api_client.get_api_provider(settings, with_reference=with_reference)
            model = api_client.get_api_model(settings, provider, with_reference=with_reference)
            quality = api_client.get_api_quality(settings, provider)
            aspect_ratio = face_ratio if task["side"] == "лицо" else back_ratio
            if provider == api_client.PROVIDER_CHATGPT:
                chatgpt_tasks_count += 1
            estimate_items.append(
                {
                    "count": 1,
                    "provider": provider,
                    "model": model,
                    "quality": quality,
                    "aspect_ratio": aspect_ratio,
                    "with_reference": with_reference,
                }
            )

        estimated_cost_total, estimated_cost_per_image = generation_stats.estimate_api_totals(estimate_items)
        stats = generation_stats.GenerationRunStats(
            planned_total=len(tasks),
            generation_method="api",
            mode_name="multiformat_with_refs",
            estimated_total_seconds=generation_stats.estimate_total_seconds(
                planned_total=len(tasks),
                generation_method="api",
                mode_name="multiformat_with_refs",
                settings=settings,
                estimate_items=estimate_items,
            ),
            estimated_cost_total=estimated_cost_total,
            estimated_cost_per_image=estimated_cost_per_image,
        )
        start_lines = stats.start_summary_lines(
            [
                "Режим: multiformat_with_refs (API)",
                f"Без референсов: {api_client.get_provider_display_name(provider_no_ref)} / {model_no_ref}",
                f"С референсами: {api_client.get_provider_display_name(provider_with_ref)} / {model_with_ref}",
                f"Quality без refs: {quality_no_ref or 'n/a'}",
                f"Quality с refs: {quality_with_ref or 'n/a'}",
                f"Aspect ratio: лицо={face_ratio}, оборот={back_ratio}",
                f"Image size без refs: лицо={face_image_size_no_ref}, оборот={back_image_size_no_ref}",
                f"Image size с refs: лицо={face_image_size_with_ref}, оборот={back_image_size_with_ref}",
                f"Диапазон карточек: {start_card}–{actual_end}",
                f"Файл промптов: {prompts_file or 'не указан'}",
                f"Референсы найдены: {refs_found}, без референсов: {refs_missing}",
                (
                    f"Параллельных воркеров: {chatgpt_parallel.get_parallel_config(settings)['max_workers']}"
                    if chatgpt_tasks_count > 0 and bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True))
                    else "Параллельных воркеров: 1"
                ),
                (
                    "Лимит запусков: "
                    f"{chatgpt_parallel.get_parallel_config(settings)['rate_limit_ipm']} за "
                    f"{chatgpt_parallel.get_parallel_config(settings)['window_seconds']} сек"
                    if chatgpt_tasks_count > 0 and bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True))
                    else "Лимит запусков: последовательный режим"
                ),
                (
                    "Алгоритм: скользящее окно"
                    if chatgpt_tasks_count > 0 and bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True))
                    else "Алгоритм: последовательный запуск"
                ),
            ]
        )
        for line in start_lines:
            write_log_line(log_file, f"[PLAN] {line}")
            _safe_print(line)

        _safe_print(f"Изображения будут сохранены в: {session_folder}")
        _safe_print("Генерация через API запущена. Esc — остановка.")

        total_images = len(tasks)
        cards_seen = {task["card_number"] for task in tasks}
        pairs_seen = {(task["card_number"], task["pair_number"]) for task in tasks}
        card_tracker = _make_card_completion_tracker(
            tasks,
            save_progress=bool(settings.get("SAVE_PROGRESS_TO_SETTINGS", True)),
        )

        def run_sequential(task_list: list[dict]) -> None:
            last_card = None
            last_pair = None
            for task in task_list:
                card_number = task["card_number"]
                pair_number = task["pair_number"]
                pair_key = (card_number, pair_number)
                label = _make_task_label(task, bool(task.get("_with_reference", False)))

                try:
                    if card_number != last_card:
                        if last_card is not None:
                            time.sleep(0.5)
                        write_log_line(log_file, f"[CARD] Карточка {card_number}")
                        last_card = card_number

                    if pair_key != last_pair:
                        write_log_line(log_file, f"[PAIR] Пара {pair_number}")
                        last_pair = pair_key

                    attempt_started = time.monotonic()
                    result = _generate_single_image_api(task, clients, settings, log_file)
                    duration_seconds = time.monotonic() - attempt_started
                    ok, reason = generation_stats.normalize_attempt_result(task, result)
                    stats.register_attempt(label, ok, duration_seconds, reason)

                    _safe_print(stats.progress_line(duration_seconds))
                    write_log_line(log_file, stats.progress_log_line(label, duration_seconds, ok, reason))
                    card_tracker(task)

                    if stats.attempted < total_images:
                        time.sleep(API_REQUEST_DELAY)
                except Exception as e:
                    duration_seconds = 0.0
                    reason = f"unexpected runtime error: {e}"
                    stats.register_attempt(label, False, duration_seconds, reason)
                    write_log_line(log_file, f"[ERROR] Неожиданная ошибка runtime для {label}: {e}")
                    for line in traceback.format_exc().splitlines():
                        if line.strip():
                            write_log_line(log_file, f"[ERROR]   {line}")
                    _safe_print(stats.progress_line(duration_seconds))
                    write_log_line(log_file, stats.progress_log_line(label, duration_seconds, False, reason))
                    card_tracker(task)

        parallel_enabled = bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True)) and chatgpt_tasks_count > 0
        if non_chatgpt_tasks:
            run_sequential(non_chatgpt_tasks)
        if chatgpt_tasks and parallel_enabled:
            chatgpt_parallel.run_parallel_chatgpt_tasks(
                tasks=chatgpt_tasks,
                settings=settings,
                stats=stats,
                log_file=log_file,
                execute_task=lambda task, worker_id: _generate_single_image_api(task, clients, settings, log_file),
                normalize_result=generation_stats.normalize_attempt_result,
                label_for_task=lambda task: _make_task_label(task, bool(task.get("_with_reference", False))),
                on_task_completed=lambda task, ok, reason: card_tracker(task),
                print_fn=_safe_print,
            )
        elif chatgpt_tasks:
            run_sequential(chatgpt_tasks)

        if chatgpt_tasks_count > 0:
            chatgpt_api_key = api_client.get_api_key(settings, api_client.PROVIDER_CHATGPT)
            actual_cost, actual_error = api_client.fetch_openai_costs(
                api_key=chatgpt_api_key,
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
            _safe_print(line)
            if line.startswith("- "):
                write_log_line(log_file, f"[FAILED] {line[2:]}")
            else:
                write_log_line(log_file, f"[SUMMARY] {line}")
        _safe_print(f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {stats.succeeded}/{total_images}")
        _safe_print(f"Лог сохранён: {log_path}")
        return make_success_result(
            mode_name,
            planned=total_images,
            succeeded=stats.succeeded,
            output_dir=session_folder,
            log_file=log_path,
        )
    except Exception as e:
        write_log_line(log_file, f"[ERROR] Неожиданная ошибка верхнего уровня: {e}")
        for line in traceback.format_exc().splitlines():
            if line.strip():
                write_log_line(log_file, f"[ERROR]   {line}")
        message = f"Ошибка генерации: {e}"
        _safe_print(message)
        return make_error_result(mode_name, message, output_dir=session_folder, log_file=log_path)
    finally:
        log_file.close()
