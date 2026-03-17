#!/usr/bin/env python3
"""
Ada AI Assistant - 启动脚本
"""
import sys
import os

# 设置工作目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# 添加 UI 模块路径 (ui/gtk 包含 ada 包)
ui_path = os.path.join(script_dir, "ui", "gtk")
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# 导入并运行应用
from ada.ui.app import Application

def main():
    app = Application()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
