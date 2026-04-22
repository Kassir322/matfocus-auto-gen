"""
Legacy compatibility shim for the old ProcessManager API.

The active v2 runtime does not use this module. `main.py` starts workers via
`utils.process_control` and generation entrypoints from `utils.generation_runner`.

This shim stays only for backward compatibility and legacy tests. New runtime
code should not depend on it.
"""

from multiprocessing import Event
import warnings

from utils import process_control
from utils.window_manager import WindowManager


class ProcessManager:
    """
    Legacy wrapper retained for compatibility.

    Not part of the active v2 public runtime contract.
    """

    def __init__(self):
        self.automation_process = None
        self.stop_event = None
        self.window_manager = WindowManager()

    def _warn_legacy(self) -> None:
        warnings.warn(
            "utils.process_manager.ProcessManager is legacy and is not used by "
            "the active v2 runtime. Use utils.process_control and "
            "utils.generation_runner instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def start_automation(self, settings_manager):
        """
        Legacy automation start path.

        Kept only for compatibility with the old API shape. Active v2 startup
        goes through `main.py` and `utils.generation_runner`.
        """
        self._warn_legacy()

        if self.automation_process and self.automation_process.is_alive():
            print("[LEGACY] Автоматизация уже запущена.")
            return None

        print("[LEGACY] Запуск через compatibility shim. Для v2 используйте main.py.")

        if not self.window_manager.setup_automation_window():
            print("[LEGACY] Не удалось настроить рабочее окно, но запуск продолжается.")

        generation_mode = settings_manager.get("GENERATION_MODE")
        start_card = settings_manager.get("START_FROM_CARD")
        generations_per_card = settings_manager.get("GENERATIONS_PER_CARD")
        check_image_enabled = settings_manager.get("CHECK_IMAGE_GENERATED")
        cards_to_process = settings_manager.get("CARDS_TO_PROCESS")
        self.stop_event = Event()

        if generation_mode in ["multi_format", "multi_format_with_refs"]:
            from core.multi_format_generator import MultiFormatGenerator
            from config.coordinates import DELAYS

            generator = MultiFormatGenerator(settings_manager)
            target_fn = generator.automation_worker
            worker_args = (
                self.stop_event,
                start_card,
                check_image_enabled,
                DELAYS["GENERATION_WAIT"],
                cards_to_process,
            )
        elif generation_mode == "standard":
            from core.image_generator import ImageGenerator
            from config.coordinates import DELAYS

            generator = ImageGenerator(settings_manager)
            target_fn = generator.automation_worker
            worker_args = (
                self.stop_event,
                start_card,
                generations_per_card,
                check_image_enabled,
                DELAYS["GENERATION_WAIT"],
                cards_to_process,
            )
        else:
            print(f"[LEGACY] Неизвестный режим генерации: {generation_mode}")
            self.stop_event = None
            return None

        self.automation_process = process_control.start_worker(target_fn, worker_args)
        if self.automation_process is None:
            self.stop_event = None
        return self.automation_process

    def stop_automation(self):
        """Legacy stop path routed through v2 low-level process control."""
        self._warn_legacy()
        process_control.stop_worker(self.automation_process)
        self.automation_process = None
        self.stop_event = None

    def setup_window(self):
        """Legacy helper for manual browser-window setup."""
        self._warn_legacy()
        print("[LEGACY] Ручная настройка рабочего окна...")
        if self.window_manager.quick_setup_window():
            print("[LEGACY] Рабочее окно настроено успешно.")
            return True
        print("[LEGACY] Не удалось настроить рабочее окно.")
        return False
