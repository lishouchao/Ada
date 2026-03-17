#!/usr/bin/env python3
"""
Ada AI Assistant - Launcher Script
正确配置 Python 路径后启动 GTK 应用
"""

import sys
import os

# 添加 UI 模块路径
script_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(script_dir, "ui", "gtk")

if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# 现在可以正确导入
from gi.repository import GLib

def main():
    from ada.ui.app import Application

    app = Application()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
