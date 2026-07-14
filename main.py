"""Точка входа API-only приложения."""

import sys


def main() -> int:
    from utils import agent_cli

    if agent_cli.is_agent_command():
        return agent_cli.main()

    if len(sys.argv) == 1 or sys.argv[1:] == ["--menu"]:
        from ui.console_menu import show_main_menu
        from utils.settings_store import load_settings

        show_main_menu(load_settings())
        return 0

    print("Используйте python main.py --menu, agent-plan или agent-run-api.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
