"""
Модуль конфигурации
"""
from .settings import SettingsManager
from .coordinates import COORDINATES, RELATIVE_MOVEMENTS, DELAYS, get_coordinates_manager

__all__ = ['SettingsManager', 'COORDINATES', 'RELATIVE_MOVEMENTS', 'DELAYS', 'get_coordinates_manager']