# -*- coding: utf-8 -*-
"""程序入口：双击运行打开图形界面。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app.ui.main_window import 主窗口


def main():
    应用 = QApplication(sys.argv)
    窗口 = 主窗口()
    窗口.show()
    sys.exit(应用.exec())


if __name__ == "__main__":
    main()
