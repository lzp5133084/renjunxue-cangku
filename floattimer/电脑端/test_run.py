# -*- coding: utf-8 -*-
"""快速测试脚本"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget, QLabel

print("1. 创建QApplication...")
app = QApplication(sys.argv)
print("2. QApplication创建成功")

from timer_core import TimerCore, TimerMode
print("3. TimerCore导入成功")

from floating_ball import FloatingBall
print("4. FloatingBall导入成功")

from main_panel import MainPanel
print("5. MainPanel导入成功")

from system_tray import SystemTray
print("6. SystemTray导入成功")

from sound_manager import SoundManager
print("7. SoundManager导入成功")

# 创建悬浮球
print("8. 创建悬浮球...")
ball = FloatingBall()
ball.update_time("00:10")
ball.update_mode("⏱")
ball.show()
print("9. 悬浮球已显示")

# 创建主面板
print("10. 创建主面板...")
panel = MainPanel()
panel.show()
print("11. 主面板已显示")

# 创建托盘
print("12. 创建系统托盘...")
tray = SystemTray(app)
tray.show()
print("13. 系统托盘已显示")

print("\n=== 所有组件初始化成功！===")
print("窗口应该已经显示在屏幕上了")

sys.exit(app.exec())
