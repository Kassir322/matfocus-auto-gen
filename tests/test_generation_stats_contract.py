"""Focused checks for generation runtime statistics and estimate helpers."""

from utils import generation_stats


def test_chatgpt_cost_estimate_changes_by_quality():
    low = generation_stats.estimate_api_cost_per_image("chatgpt", "gpt-image-2", quality="low", aspect_ratio="1:1")
    medium = generation_stats.estimate_api_cost_per_image("chatgpt", "gpt-image-2", quality="medium", aspect_ratio="1:1")
    high = generation_stats.estimate_api_cost_per_image("chatgpt", "gpt-image-2", quality="high", aspect_ratio="1:1")

    assert low < medium < high


def test_google_cost_estimate_handles_known_and_unknown_models():
    imagen = generation_stats.estimate_api_cost_per_image("nanobanana", "imagen-4.0-generate-001")
    gemini = generation_stats.estimate_api_cost_per_image("nanobanana", "gemini-2.5-flash-image")
    unknown = generation_stats.estimate_api_cost_per_image("nanobanana", "mystery-model")

    assert imagen == 0.04
    assert gemini == 0.039
    assert unknown is None


def test_api_time_baseline_uses_fixed_provider_defaults():
    chatgpt_seconds = generation_stats.estimate_baseline_seconds(
        generation_method="api",
        mode_name="standard",
        settings={"API_CHATGPT_QUALITY": "high"},
        provider="chatgpt",
        model="gpt-image-2",
    )
    google_seconds = generation_stats.estimate_baseline_seconds(
        generation_method="api",
        mode_name="multiformat_with_refs",
        settings={},
        provider="nanobanana",
        model="imagen-4.0-ultra-generate-001",
        with_reference=True,
    )

    assert chatgpt_seconds == 22.0
    assert google_seconds == 10.0


def test_generation_run_stats_summary_tracks_failures():
    stats = generation_stats.GenerationRunStats(
        planned_total=3,
        generation_method="api",
        mode_name="standard",
        estimated_total_seconds=90.0,
        estimated_cost_total=0.12,
        estimated_cost_per_image=0.04,
    )

    stats.register_attempt("card 1", True, 20.0)
    stats.register_attempt("card 2", False, 30.0, "timeout")
    stats.register_attempt("card 3", True, 25.0)

    rendered = "\n".join(stats.summary_lines())
    assert "Неудачно: 1" in rendered
    assert "Оценка стоимости по попыткам: $0.120" in rendered
    assert "- card 2 — timeout" in rendered


def test_generation_run_stats_summary_prefers_actual_cost_when_available():
    stats = generation_stats.GenerationRunStats(
        planned_total=2,
        generation_method="api",
        mode_name="standard",
        estimated_total_seconds=60.0,
        estimated_cost_total=0.20,
        estimated_cost_per_image=0.10,
    )
    stats.register_attempt("card 1", True, 20.0)
    stats.register_attempt("card 2", True, 25.0)
    stats.set_actual_cost(0.149, "Фактические расходы ChatGPT")

    rendered = "\n".join(stats.summary_lines())
    assert "Фактические расходы ChatGPT: $0.149" in rendered
    assert "Оценка стоимости по попыткам: $0.200" in rendered
