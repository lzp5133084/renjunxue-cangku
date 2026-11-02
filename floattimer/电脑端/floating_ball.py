# -*- coding: utf-8 -*-
"""
悬浮球组件模块（已修复信号定义）
作者：军哥懂保
微信号：xunijiayuan

功能：
- 无边框圆形悬浮球
- 可自由拖动
- 松开自动吸附屏幕边缘
- 显示当前时间/模式图标
- 左键双击切换展开/收起主面板
- 右键菜单
"""

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPainterPath, QCursor
from PyQt6.QtWidgets import QWidget, QMenu, QApplication


class FloatingBall(QWidget):
    """
    悬浮球
    - 圆形无边框
    - 半透明毛玻璃效果
    - 拖动 + 边缘吸附
    - 实时显示计时状态
    """

    # ===== 信号定义 =====
    double_clicked = pyqtSignal()          # 双击（展开/收起面板）
    menu_show_panel = pyqtSignal()         # 菜单-显示主面板
    menu_start = pyqtSignal()              # 菜单-开始
    menu_pause = pyqtSignal()              # 菜单-暂停
    menu_reset = pyqtSignal()              # 菜单-重置
    menu_repeat = pyqtSignal()             # 菜单-重复上次计时
    menu_share = pyqtSignal()              # 菜单-分享有奖
    menu_quit = pyqtSignal()               # 菜单-退出

    # 边缘吸附方向
    EDGE_NONE = 0
    EDGE_LEFT = 1
    EDGE_RIGHT = 2
    EDGE_TOP = 3
    EDGE_BOTTOM = 4

    def __init__(self, parent=None):
        super().__init__(parent)

        # ===== 基础设置 =====
        self.ball_size = 72  # 悬浮球直径
        self.setFixedSize(self.ball_size, self.ball_size)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |      # 无边框
            Qt.WindowType.WindowStaysOnTopHint |     # 置顶
            Qt.WindowType.Tool                      # 工具窗口（不占任务栏）
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # 不抢焦点

        # ===== 拖动相关 =====
        self._dragging = False
        self._drag_offset = QPoint()
        self._edge_attached = self.EDGE_NONE

        # ===== 显示内容 =====
        self._time_text = "00:00"
        self._mode_text = "⏱"  # 模式图标
        self._is_running = False
        self._progress = 0.0  # 0-1 进度

        # ===== 颜色主题 =====
        self._accent_color = QColor(99, 102, 241)      # 靛紫
        self._accent_color2 = QColor(236, 72, 153)     # 粉红

        # ===== 边缘吸附定时器 =====
        self._edge_timer = QTimer(self)
        self._edge_timer.setSingleShot(True)
        self._edge_timer.setInterval(300)
        self._edge_timer.timeout.connect(self._attach_to_edge)

        # ===== 拖动检测定时器 =====
        self._check_timer = QTimer(self)
        self._check_timer.setInterval(50)
        self._check_timer.timeout.connect(self._check_drag_end)

        # ===== 动画变量 =====
        self._anim_x = 0
        self._anim_y = 0
        self._target_x = 0
        self._target_y = 0
        self._anim_progress = 0.0
        self._anim_timer = None

    # ==================== 外观更新接口 ====================

    def update_time(self, time_text: str):
        """更新时间显示"""
        self._time_text = time_text
        self.update()

    def update_mode(self, mode_icon: str):
        """更新模式图标"""
        self._mode_text = mode_icon
        self.update()

    def set_running(self, running: bool):
        """设置运行状态（影响颜色）"""
        self._is_running = running
        self.update()

    def set_progress(self, progress: float):
        """设置进度（影响外圈弧）"""
        self._progress = max(0.0, min(1.0, progress))
        self.update()

    # ==================== 绘制 ====================

    def paintEvent(self, event):
        """绘制悬浮球（网页端同款：渐变球体+光晕+双色外环+顶部高光）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        center = QPoint(w // 2, h // 2)
        radius = min(w, h) // 2 - 2

        # ===== 外层光晕（3层同心圆，透明度递减，不用径向渐变避免崩溃）=====
        glow_color = QColor(129, 140, 248) if not self._is_running else QColor(16, 185, 129)
        painter.setPen(Qt.PenStyle.NoPen)
        for expand, alpha in ((6, 14), (3, 26), (1, 40)):
            c = QColor(glow_color)
            c.setAlpha(alpha)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(center, radius + expand, radius + expand)

        # ===== 背景圆形（对角线性渐变：左上亮紫→右下深空）=====
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor(58, 58, 105, 235))
        gradient.setColorAt(0.5, QColor(32, 32, 62, 240))
        gradient.setColorAt(1.0, QColor(16, 16, 34, 245))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # ===== 顶部高光弧（模拟玻璃质感）=====
        highlight = QLinearGradient(0, 4, 0, h // 2)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 46))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center.x() - radius + 8, center.y() - radius + 5,
                            (radius - 8) * 2, radius)

        # ===== 外圈双色环（上半靛紫弧 + 下半粉红弧，模拟渐变环）=====
        if self._is_running:
            # 运行中 - 绿色整圈
            pen = QPen(QColor(16, 185, 129))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius - 2, radius - 2)
        elif self._progress > 0 and self._progress < 1:
            # 暂停中 - 橙色整圈
            pen = QPen(QColor(245, 158, 11))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius - 2, radius - 2)
        else:
            # 空闲 - 上半靛紫弧 + 下半粉红弧
            rect = (center.x() - radius + 2, center.y() - radius + 2,
                    (radius - 2) * 2, (radius - 2) * 2)
            pen1 = QPen(QColor(129, 140, 248))
            pen1.setWidth(3)
            pen1.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen1)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(*rect, 30 * 16, 120 * 16)   # 上半圈
            pen2 = QPen(QColor(236, 72, 153))
            pen2.setWidth(3)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen2)
            painter.drawArc(*rect, 210 * 16, 120 * 16)  # 下半圈

        # ===== 进度弧（如果有进度）=====
        if self._progress > 0:
            pen = QPen()
            pen.setWidth(4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            color = QColor(52, 211, 153) if self._is_running else QColor(251, 191, 36)
            pen.setColor(color)
            painter.setPen(pen)
            start_angle = 90 * 16  # 12点钟方向
            span_angle = -int(360 * self._progress * 16)
            painter.drawArc(6, 6, w - 12, h - 12, start_angle, span_angle)

        # ===== 模式图标（上半）=====
        painter.setPen(QColor(196, 181, 253))
        font = painter.font()
        font.setPointSize(13)
        painter.setFont(font)
        painter.drawText(0, 8, w, 22, Qt.AlignmentFlag.AlignCenter, self._mode_text)

        # ===== 时间显示（下半）=====
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 28, w, 38, Qt.AlignmentFlag.AlignCenter, self._time_text)

        painter.end()

    # ==================== 拖动 ====================

    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._check_timer.start()
            self._edge_attached = self.EDGE_NONE
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._check_timer.stop()
            self._edge_timer.start()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """双击 - 切换面板"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()

    def _check_drag_end(self):
        """检测拖动结束"""
        if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._dragging = False
            self._check_timer.stop()
            self._edge_timer.start()

    # ==================== 边缘吸附 ====================

    def _attach_to_edge(self):
        """吸附到最近屏幕边缘"""
        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()

        dist_left = x - screen_geo.left()
        dist_right = screen_geo.right() - (x + w)
        dist_top = y - screen_geo.top()
        dist_bottom = screen_geo.bottom() - (y + h)

        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
        margin = 8

        target_x = x
        target_y = y
        self._edge_attached = self.EDGE_NONE

        if min_dist == dist_left and dist_left < 80:
            target_x = screen_geo.left() + margin
            target_y = max(screen_geo.top() + margin, min(y, screen_geo.bottom() - h - margin))
            self._edge_attached = self.EDGE_LEFT
        elif min_dist == dist_right and dist_right < 80:
            target_x = screen_geo.right() - w - margin
            target_y = max(screen_geo.top() + margin, min(y, screen_geo.bottom() - h - margin))
            self._edge_attached = self.EDGE_RIGHT
        elif min_dist == dist_top and dist_top < 80:
            target_y = screen_geo.top() + margin
            self._edge_attached = self.EDGE_TOP
        elif min_dist == dist_bottom and dist_bottom < 80:
            target_y = screen_geo.bottom() - h - margin
            self._edge_attached = self.EDGE_BOTTOM

        self._animate_to(target_x, target_y)

    def _animate_to(self, target_x: int, target_y: int):
        """平滑动画移动"""
        self._anim_x = self.x()
        self._anim_y = self.y()
        self._target_x = target_x
        self._target_y = target_y
        self._anim_progress = 0.0

        if self._anim_timer:
            self._anim_timer.stop()

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._anim_step)
        self._anim_timer.start()

    def _anim_step(self):
        """动画帧"""
        self._anim_progress += 0.15
        if self._anim_progress >= 1.0:
            self._anim_progress = 1.0
            if self._anim_timer:
                self._anim_timer.stop()

        t = self._anim_progress
        eased = 1 - (1 - t) * (1 - t)  # easeOutQuad

        new_x = int(self._anim_x + (self._target_x - self._anim_x) * eased)
        new_y = int(self._anim_y + (self._target_y - self._anim_y) * eased)
        self.move(new_x, new_y)

    # ==================== 右键菜单 ====================

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
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
        """)

        action_show = menu.addAction("📋 显示主面板")
        action_start = menu.addAction("▶ 开始")
        action_pause = menu.addAction("⏸ 暂停")
        action_repeat = menu.addAction("🔁 重复计时")
        action_reset = menu.addAction("🔄 重置")
        menu.addSeparator()
        action_share = menu.addAction("🎁 推广有惊喜")
        menu.addSeparator()
        action_quit = menu.addAction("❌ 退出")

        action = menu.exec(pos)

        if action == action_show:
            self.menu_show_panel.emit()
        elif action == action_repeat:
            self.menu_repeat.emit()
        elif action == action_start:
            self.menu_start.emit()
        elif action == action_pause:
            self.menu_pause.emit()
        elif action == action_reset:
            self.menu_reset.emit()
        elif action == action_share:
            self.menu_share.emit()
        elif action == action_quit:
            self.menu_quit.emit()
