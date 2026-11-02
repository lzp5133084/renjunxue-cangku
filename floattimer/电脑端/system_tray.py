# -*- coding: utf-8 -*-
"""
系统托盘模块
作者：军哥懂保
微信号：xunijiayuan

功能：
- 最小化到系统托盘
- 托盘图标实时显示剩余分钟数
- 托盘菜单
- 双击恢复窗口
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QBrush, QPen, QLinearGradient
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


class SystemTray:
    """
    系统托盘管理器
    支持动态更新图标内容
    """

    def __init__(self, app: QApplication):
        self.app = app
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._create_default_icon())
        self.tray.setToolTip("悬浮计时器")

        # 创建菜单
        self.menu = QMenu()
        self._setup_menu()
        self.tray.setContextMenu(self.menu)

        # 信号连接
        self.tray.activated.connect(self._on_tray_activated)

        # 回调
        self.on_show_panel = None
        self.on_start = None
        self.on_pause = None
        self.on_reset = None
        self.on_check_update = None
        self.on_quit = None

    def _setup_menu(self):
        """设置托盘菜单"""
        self.menu.setStyleSheet("""
            QMenu {
                background: rgba(25, 25, 40, 245);
                color: #e0e0f0;
                border: 1px solid rgba(99, 102, 241, 0.5);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(99, 102, 241, 0.3);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(99, 102, 241, 0.3);
                margin: 4px 8px;
            }
        """)

        self.action_show = self.menu.addAction("📋 显示主面板")
        self.menu.addSeparator()
        self.action_start = self.menu.addAction("▶ 开始计时")
        self.action_pause = self.menu.addAction("⏸ 暂停计时")
        self.action_reset = self.menu.addAction("🔄 重置")
        self.menu.addSeparator()
        self.action_check_update = self.menu.addAction("🔍 检查更新")
        self.action_quit = self.menu.addAction("❌ 退出")

        self.action_show.triggered.connect(lambda: self.on_show_panel and self.on_show_panel())
        self.action_start.triggered.connect(lambda: self.on_start and self.on_start())
        self.action_pause.triggered.connect(lambda: self.on_pause and self.on_pause())
        self.action_reset.triggered.connect(lambda: self.on_reset and self.on_reset())
        self.action_check_update.triggered.connect(lambda: self.on_check_update and self.on_check_update())
        self.action_quit.triggered.connect(lambda: self.on_quit and self.on_quit())

    def _on_tray_activated(self, reason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.on_show_panel:
                self.on_show_panel()

    # ==================== 图标生成 ====================

    def _create_default_icon(self) -> QIcon:
        """创建默认图标"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 圆形背景（线性渐变替代RadialGradient避免崩溃）
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0.0, QColor(129, 140, 248))
        gradient.setColorAt(1.0, QColor(67, 56, 202))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(6, 6, 52, 52)

        # 时钟指针
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(32, 32, 32, 16)  # 时针
        painter.setPen(QPen(QColor(236, 72, 153), 2))
        painter.drawLine(32, 32, 44, 32)  # 分针

        painter.end()
        return QIcon(pixmap)

    def update_icon_with_text(self, text: str, is_running: bool = False):
        """更新托盘图标，显示剩余时间"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景色（运行=绿，暂停=橙，空闲=靛）
        if is_running:
            bg_color = QColor(16, 185, 129)
        else:
            bg_color = QColor(99, 102, 241)

        # 圆形背景
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)

        # 白色边框
        painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
        painter.drawEllipse(4, 4, 56, 56)

        # 时间文字
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
        self.tray.setIcon(QIcon(pixmap))

    # ==================== 接口 ====================

    def show(self):
        """显示托盘图标"""
        self.tray.show()

    def hide(self):
        """隐藏托盘图标"""
        self.tray.hide()

    def set_tooltip(self, text: str):
        """设置提示"""
        self.tray.setToolTip(text)

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information):
        """显示系统通知"""
        self.tray.showMessage(title, message, icon, 3000)
