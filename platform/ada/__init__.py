"""
Platform Adaptation Layer - Platform-specific implementations
"""

from ada.platform.perception import ATSPIMonitor, UIElement, UITree, ScreenReader
from ada.platform.execution import DBusBackend, CLIBackend, GUIBackend, APIBackend
from ada.platform.adapters import AdaDBusService, SystemdIntegration

__all__ = [
    # Perception
    "ATSPIMonitor",
    "UIElement",
    "UITree",
    "ScreenReader",
    # Execution
    "DBusBackend",
    "CLIBackend",
    "GUIBackend",
    "APIBackend",
    # Adapters
    "AdaDBusService",
    "SystemdIntegration",
]
