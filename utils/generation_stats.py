"""
Единый runtime-слой статистики генерации для browser и API режимов.

Источники baseline-оценок:
- OpenAI API Pricing / GPT-image-2 pricing page, проверено 2026-04-23:
  https://openai.com/api/pricing/
- OpenAI models pages для image pricing baselines, проверено 2026-04-23:
  https://developers.openai.com/api/docs/models/gpt-image-2
  https://developers.openai.com/api/docs/models/chatgpt-image-latest
- Google Gemini API pricing, проверено 2026-04-23:
  https://ai.google.dev/pricing
  https://ai.google.dev/gemini-api/docs/image-generation

Стоимость в API режиме носит оценочный характер. Фактический billing из ответа API
в текущей версии не извлекается.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta


MOVING_AVERAGE_WINDOW = 5
CHATGPT_API_BASELINE_SECONDS = 22.0
GOOGLE_API_BASELINE_SECONDS = 10.0


@dataclass
class FailedGeneration:
    label: str
    reason: str


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_money(amount: float | None) -> str:
    if amount is None:
        return "н/д"
    return f"${amount:.3f}"


def _parse_aspect_ratio(aspect_ratio: str | None) -> tuple[float, float] | None:
    if not aspect_ratio or ":" not in str(aspect_ratio):
        return None
    left_raw, right_raw = str(aspect_ratio).split(":", 1)
    try:
        left = float(left_raw)
        right = float(right_raw)
    except ValueError:
        return None
    if left <= 0 or right <= 0:
        return None
    return left, right


def _aspect_bucket(aspect_ratio: str | None) -> str:
    parsed = _parse_aspect_ratio(aspect_ratio)
    if parsed is None:
        return "square"
    left, right = parsed
    if abs(left - right) < 0.01:
        return "square"
    if left > right:
        return "landscape"
    return "portrait"


def estimate_api_cost_per_image(
    provider: str,
    model: str,
    quality: str = "",
    aspect_ratio: str | None = None,
) -> float | None:
    provider = str(provider or "").strip().lower()
    model = str(model or "").strip().lower()
    quality = str(quality or "").strip().lower()

    if provider == "chatgpt":
        bucket = _aspect_bucket(aspect_ratio)
        # Baseline from official OpenAI image model pricing pages, checked 2026-04-23.
        # We treat these as estimate tables for gpt-image-2 class pricing in this runtime.
        cost_table = {
            "low": {"square": 0.009, "landscape": 0.013, "portrait": 0.013},
            "medium": {"square": 0.034, "landscape": 0.050, "portrait": 0.050},
            "high": {"square": 0.133, "landscape": 0.200, "portrait": 0.200},
        }
        return cost_table.get(quality, cost_table["low"]).get(bucket)

    if provider != "nanobanana":
        return None

    # Google official pricing baselines, checked 2026-04-23.
    if model.startswith("imagen-4.0-fast"):
        return 0.020
    if model.startswith("imagen-4.0-ultra"):
        return 0.060
    if model.startswith("imagen-4.0-generate"):
        return 0.040
    if "gemini-2.5-flash-image" in model or "flash-image" in model:
        return 0.039
    if "gemini" in model and "image" in model:
        return 0.039
    return None


def estimate_baseline_seconds(
    generation_method: str,
    mode_name: str,
    settings: dict,
    provider: str | None = None,
    model: str | None = None,
    with_reference: bool = False,
) -> float:
    generation_method = str(generation_method or "browser").strip().lower()
    mode_name = str(mode_name or "").strip().lower()
    provider = str(provider or "").strip().lower()
    model = str(model or "").strip().lower()

    if generation_method == "browser":
        generation_wait = float(settings.get("GENERATION_WAIT", 20.0))
        save_overhead = 6.0
        if mode_name == "standard":
            base = generation_wait + save_overhead + 5.0
        elif mode_name == "multiformat":
            base = generation_wait + save_overhead + 7.0
        else:
            base = generation_wait + save_overhead + 10.0
        if with_reference:
            base += 3.0
        return base

    if provider == "chatgpt":
        return CHATGPT_API_BASELINE_SECONDS

    return GOOGLE_API_BASELINE_SECONDS


def estimate_api_totals(estimate_items: list[dict]) -> tuple[float | None, float | None]:
    total_cost = 0.0
    total_count = 0

    for item in estimate_items:
        count = int(item.get("count", 0) or 0)
        if count <= 0:
            continue
        total_count += count
        per_image = estimate_api_cost_per_image(
            provider=item.get("provider", ""),
            model=item.get("model", ""),
            quality=item.get("quality", ""),
            aspect_ratio=item.get("aspect_ratio"),
        )
        if per_image is None:
            return None, None
        total_cost += per_image * count

    if total_count == 0:
        return 0.0, 0.0
    return total_cost, total_cost / total_count


def estimate_total_seconds(
    planned_total: int,
    generation_method: str,
    mode_name: str,
    settings: dict,
    estimate_items: list[dict] | None = None,
) -> float:
    estimate_items = estimate_items or []
    if estimate_items:
        return sum(
            estimate_baseline_seconds(
                generation_method=generation_method,
                mode_name=mode_name,
                settings=settings,
                provider=item.get("provider"),
                model=item.get("model"),
                with_reference=bool(item.get("with_reference", False)),
            )
            * int(item.get("count", 0) or 0)
            for item in estimate_items
        )
    return estimate_baseline_seconds(
        generation_method=generation_method,
        mode_name=mode_name,
        settings=settings,
    ) * max(0, int(planned_total))


def normalize_attempt_result(task: dict, result) -> tuple[bool, str]:
    if isinstance(result, tuple):
        ok = bool(result[0])
        reason = str(result[1] or "").strip()
    else:
        ok = bool(result)
        reason = ""

    if ok:
        task.pop("_last_failure_reason", None)
        return True, ""

    task_reason = str(task.get("_last_failure_reason", "") or "").strip()
    if task_reason:
        return False, task_reason
    if reason:
        return False, reason
    return False, "ошибка генерации"


class GenerationRunStats:
    def __init__(
        self,
        planned_total: int,
        generation_method: str,
        mode_name: str,
        estimated_total_seconds: float | None = None,
        estimated_cost_total: float | None = None,
        estimated_cost_per_image: float | None = None,
    ) -> None:
        self.planned_total = max(0, int(planned_total))
        self.generation_method = str(generation_method or "browser")
        self.mode_name = str(mode_name or "")
        self.started_wall = datetime.now()
        self.started_monotonic = time.monotonic()
        self.attempted = 0
        self.succeeded = 0
        self.failed = 0
        self.failed_items: list[FailedGeneration] = []
        self.success_durations: list[float] = []
        self.attempt_durations: list[float] = []
        self._recent_successes: list[float] = []
        self.estimated_total_seconds = estimated_total_seconds
        self.estimated_cost_total = estimated_cost_total
        self.estimated_cost_per_image = estimated_cost_per_image
        self.actual_cost_total: float | None = None
        self.actual_cost_label = "Фактические расходы"
        self.actual_cost_error: str | None = None

    def elapsed_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_monotonic)

    def started_epoch_seconds(self) -> int:
        return int(self.started_wall.timestamp())

    def finished_epoch_seconds(self) -> int:
        return int(datetime.now().timestamp())

    def register_attempt(
        self,
        label: str,
        ok: bool,
        duration_seconds: float,
        reason: str = "",
    ) -> None:
        duration_seconds = max(0.0, float(duration_seconds))
        self.attempted += 1
        self.attempt_durations.append(duration_seconds)
        if ok:
            self.succeeded += 1
            self.success_durations.append(duration_seconds)
            self._recent_successes.append(duration_seconds)
            self._recent_successes = self._recent_successes[-MOVING_AVERAGE_WINDOW:]
            return

        self.failed += 1
        self.failed_items.append(FailedGeneration(label=label, reason=reason or "ошибка генерации"))

    def average_seconds(self) -> float:
        if self.success_durations:
            return sum(self.success_durations) / len(self.success_durations)
        if self.attempt_durations:
            return sum(self.attempt_durations) / len(self.attempt_durations)
        return 0.0

    def moving_average_seconds(self) -> float:
        if self._recent_successes:
            return sum(self._recent_successes) / len(self._recent_successes)
        if self.estimated_total_seconds is not None and self.planned_total > 0:
            return self.estimated_total_seconds / self.planned_total
        return self.average_seconds()

    def eta_time(self) -> str:
        remaining = max(0, self.planned_total - self.attempted)
        eta_seconds = self.moving_average_seconds() * remaining
        eta_dt = datetime.now() + timedelta(seconds=eta_seconds)
        return eta_dt.strftime("%H:%M")

    def progress_line(self, last_duration_seconds: float) -> str:
        return (
            f"Генерация {self.succeeded}/{self.attempted} из {self.planned_total} - "
            f"{format_duration(last_duration_seconds)} - {format_duration(self.elapsed_seconds())} - "
            f"avg {format_duration(self.average_seconds())} - fail {self.failed} - ETA {self.eta_time()}"
        )

    def progress_log_line(self, label: str, last_duration_seconds: float, ok: bool, reason: str = "") -> str:
        status = "OK" if ok else "FAILED"
        suffix = f", reason={reason}" if reason else ""
        return (
            f"[PROGRESS] {label}: {status}; success={self.succeeded}; attempted={self.attempted}; "
            f"planned={self.planned_total}; item={format_duration(last_duration_seconds)}; "
            f"elapsed={format_duration(self.elapsed_seconds())}; avg={format_duration(self.average_seconds())}; "
            f"failed={self.failed}; eta={self.eta_time()}{suffix}"
        )

    def set_actual_cost(self, amount: float, label: str = "Фактические расходы") -> None:
        self.actual_cost_total = max(0.0, float(amount))
        self.actual_cost_label = label
        self.actual_cost_error = None

    def set_actual_cost_error(self, message: str) -> None:
        self.actual_cost_total = None
        self.actual_cost_error = str(message or "").strip() or "не удалось получить данные billing API"

    def start_summary_lines(self, context_lines: list[str] | None = None) -> list[str]:
        lines = ["Сводка перед стартом:"]
        lines.extend(context_lines or [])
        lines.append(f"Запланировано изображений: {self.planned_total}")
        if self.estimated_total_seconds is not None:
            lines.append(f"Примерное время: {format_duration(self.estimated_total_seconds)}")
            eta_dt = self.started_wall + timedelta(seconds=self.estimated_total_seconds)
            lines.append(f"Примерное окончание: {eta_dt.strftime('%H:%M')}")
        if self.generation_method == "api":
            lines.append(f"Примерная стоимость: {format_money(self.estimated_cost_total)}")
            lines.append(f"Примерная стоимость за изображение: {format_money(self.estimated_cost_per_image)}")
        lines.append("ETA будет уточняться по фактическому среднему после первых успешных генераций.")
        return lines

    def summary_lines(self) -> list[str]:
        elapsed = self.elapsed_seconds()
        duration_sample = self.success_durations or self.attempt_durations
        median_seconds = statistics.median(duration_sample) if duration_sample else 0.0
        min_seconds = min(duration_sample) if duration_sample else 0.0
        max_seconds = max(duration_sample) if duration_sample else 0.0

        lines = [
            "Итоги генерации:",
            f"Запланировано: {self.planned_total}",
            f"Попыток: {self.attempted}",
            f"Успешно: {self.succeeded}",
            f"Неудачно: {self.failed}",
            f"Общее время: {format_duration(elapsed)}",
            f"Среднее время: {format_duration(self.average_seconds())}",
            f"Медиана: {format_duration(median_seconds)}",
            f"Мин/макс: {format_duration(min_seconds)} / {format_duration(max_seconds)}",
        ]
        if self.generation_method == "api":
            if self.actual_cost_total is not None:
                lines.append(f"{self.actual_cost_label}: {format_money(self.actual_cost_total)}")
            elif self.actual_cost_error:
                lines.append(f"{self.actual_cost_label}: н/д ({self.actual_cost_error})")

            if self.estimated_cost_per_image is None:
                lines.append("Оценка стоимости: н/д")
            else:
                lines.append(
                    f"Оценка стоимости по попыткам: {format_money(self.estimated_cost_per_image * self.attempted)}"
                )

        if self.failed_items:
            lines.append("Не удалось сгенерировать:")
            for item in self.failed_items:
                lines.append(f"- {item.label} — {item.reason}")
        else:
            lines.append("Все запланированные изображения обработаны без неудачных генераций.")
        return lines
