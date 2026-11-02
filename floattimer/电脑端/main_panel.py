# -*- coding: utf-8 -*-
"""
主面板UI模块
作者：军哥懂保
微信号：xunijiayuan

功能：
- 正计时/倒计时/番茄钟三模式
- 2027科技感毛玻璃深色主题
- 可折叠面板
- 设置区域
- 计次记录列表
- 保存/恢复配置
"""

import json
import os
import sys
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QIcon, QColor, QLinearGradient, QBrush, QPainterPath, QCursor, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QSlider, QFrame, QScrollArea, QListWidget,
    QListWidgetItem, QTabWidget, QCheckBox, QGroupBox, QMessageBox,
    QGraphicsDropShadowEffect, QToolTip, QSizePolicy, QSizeGrip, QDialog
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


# ==================== 2027科技感样式表 ====================

MAIN_STYLE = """
/* ========== 全局 ========== */
QWidget {
    font-family: "微软雅黑", "Segoe UI", "PingFang SC", sans-serif;
    color: #e0e0f0;
}

/* ========== 主容器 ========== */
#MainContainer {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d0d1a, stop:0.5 #12122a, stop:1 #0d0d1a);
    border-radius: 20px;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

/* ========== 标题栏 ========== */
#TitleBar {
    background: transparent;
    padding: 12px 20px;
}

#AppTitle {
    font-size: 16pt;
    font-weight: bold;
    color: #c4b5fd;
    background: transparent;
}

#SubTitle {
    font-size: 9pt;
    color: #6b6b8b;
}

/* ========== 模式切换按钮 ========== */
#ModeButton {
    background: rgba(30, 30, 50, 0.8);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 12px;
    padding: 12px 24px;
    color: #a0a0c0;
    font-size: 11pt;
    font-weight: 500;
    min-width: 100px;
}

#ModeButton:hover {
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(99, 102, 241, 0.6);
    color: #c4b5fd;
}

#ModeButton[selected="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(99, 102, 241, 0.4), stop:1 rgba(236, 72, 153, 0.4));
    border: 1px solid #818cf8;
    color: white;
    font-weight: bold;
}

/* ========== 时间显示（字号由代码随窗口宽度自适应，防止出框） ========== */
#TimeDisplay {
    font-family: "Consolas", "Courier New", monospace;
    font-weight: bold;
    color: #ffffff;
    padding: 8px;
    background: transparent;
}

#TimeDisplay[running="true"] {
    color: #34d399;
}

#TimeDisplay[paused="true"] {
    color: #fbbf24;
}

/* ========== 本机时间参考 ========== */
#ClockRef {
    color: #6b6b8b;
    font-size: 9pt;
    padding-bottom: 2px;
}

/* ========== 进度条 ========== */
QProgressBar {
    background: rgba(30, 30, 50, 0.8);
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #a78bfa, stop:1 #ec4899);
    border-radius: 6px;
}

/* ========== 控制按钮 ========== */
#ControlButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:1 #ec4899);
    border: none;
    border-radius: 25px;
    padding: 14px 20px;
    color: white;
    font-size: 11pt;
    font-weight: bold;
    min-width: 100px;
}

#ControlButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #818cf8, stop:1 #f472b6);
}

#ControlButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:1 #db2777);
}

#SecondaryButton {
    background: rgba(30, 30, 50, 0.8);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 20px;
    padding: 10px 14px;
    color: #c4b5fd;
    font-size: 10pt;
    min-width: 72px;
}

#SecondaryButton:hover {
    background: rgba(99, 102, 241, 0.2);
    border-color: #818cf8;
}

#SecondaryButton#DangerButton {
    border-color: rgba(239, 68, 68, 0.4);
    color: #fca5a5;
}

#SecondaryButton#DangerButton:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: #ef4444;
}

/* ========== 输入框 ========== */
QLineEdit, QSpinBox {
    background: rgba(20, 20, 35, 0.9);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 8px;
    padding: 8px 12px;
    color: #e0e0f0;
    font-size: 11pt;
    min-width: 64px;
    selection-background-color: rgba(99, 102, 241, 0.5);
}

QLineEdit:focus, QSpinBox:focus {
    border-color: #818cf8;
}

/* ========== 分组框 ========== */
QGroupBox {
    background: rgba(20, 20, 35, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 12px;
    margin-top: 16px;
    padding-top: 12px;
    font-weight: bold;
    color: #c4b5fd;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
}

/* ========== 标签页 ========== */
QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabBar::tab {
    background: rgba(30, 30, 50, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 8px 8px 0 0;
    padding: 8px 12px;
    margin-right: 3px;
    color: #8888a0;
    font-size: 9pt;
}

QTabBar::tab:selected {
    background: rgba(99, 102, 241, 0.25);
    border-color: #818cf8;
    color: #c4b5fd;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background: rgba(99, 102, 241, 0.1);
    color: #a0a0c0;
}

/* ========== 计次列表 ========== */
QListWidget {
    background: rgba(20, 20, 35, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 10px;
    padding: 6px;
    color: #e0e0f0;
    font-family: "Consolas", monospace;
    font-size: 10pt;
    outline: none;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background: rgba(99, 102, 241, 0.3);
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(99, 102, 241, 0.4);
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(99, 102, 241, 0.7);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ========== 复选框 ========== */
QCheckBox {
    color: #c4b5fd;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid rgba(99, 102, 241, 0.5);
    background: rgba(20, 20, 35, 0.8);
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #ec4899);
    border-color: #818cf8;
}

/* ========== 滑块 ========== */
QSlider::groove:horizontal {
    height: 6px;
    background: rgba(99, 102, 241, 0.2);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:1 #ec4899);
    border: 2px solid white;
}

/* ========== 关闭按钮 ========== */
#CloseButton {
    background: transparent;
    border: none;
    color: #8888a0;
    font-size: 14pt;
    padding: 8px 12px;
    border-radius: 8px;
}

#CloseButton:hover {
    background: rgba(239, 68, 68, 0.3);
    color: #ef4444;
}

/* ========== 折叠按钮 ========== */
#CollapseButton {
    background: rgba(30, 30, 50, 0.8);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 12px;
    padding: 6px 10px;
    color: #c4b5fd;
    font-size: 9pt;
}

#CollapseButton:hover {
    background: rgba(99, 102, 241, 0.2);
}

/* ========== 番茄钟阶段标签 ========== */
#PhaseLabel {
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 16px;
    padding: 6px 20px;
    color: #c4b5fd;
    font-size: 11pt;
    font-weight: bold;
}

#PhaseLabel[phase="work"] {
    background: rgba(16, 185, 129, 0.2);
    border-color: rgba(16, 185, 129, 0.5);
    color: #34d399;
}

#PhaseLabel[phase="short_break"] {
    background: rgba(59, 130, 246, 0.2);
    border-color: rgba(59, 130, 246, 0.5);
    color: #60a5fa;
}

#PhaseLabel[phase="long_break"] {
    background: rgba(236, 72, 153, 0.2);
    border-color: rgba(236, 72, 153, 0.5);
    color: #f472b6;
}

/* ========== 底部作者信息 ========== */
#FooterInfo {
    color: #4a4a60;
    font-size: 8pt;
}
"""


class NameDialog(QDialog):
    """
    计时结束命名保存对话框
    深色科技风自定义弹窗（替代系统原生 QInputDialog，避免白底违和）
    """

    def __init__(self, parent=None, mode_text="", duration_text="",
                 title_text="📝 保存本次计时", default_name=""):
        super().__init__(parent)
        self.record_name = ""

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("NameDialogContainer")
        root.addWidget(container)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        title = QLabel(title_text)
        title.setObjectName("NameDialogTitle")
        lay.addWidget(title)

        if mode_text:
            summary = QLabel(f"⏱ {mode_text} · {duration_text} 已完成")
            summary.setObjectName("NameDialogSummary")
            lay.addWidget(summary)

        tip = QLabel("为本次计时命名（如：写方案 / 看书 / 运动）：")
        tip.setObjectName("NameDialogTip")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        self.edit_name = QLineEdit()
        self.edit_name.setObjectName("NameDialogEdit")
        self.edit_name.setPlaceholderText("输入项目名称…")
        self.edit_name.setFixedHeight(38)
        if default_name:
            self.edit_name.setText(default_name)
            self.edit_name.selectAll()
        lay.addWidget(self.edit_name)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("不保存")
        btn_cancel.setObjectName("NameDialogCancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 保存")
        btn_save.setObjectName("NameDialogSave")
        btn_save.setFixedHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save, 1)

        lay.addLayout(btn_row)

        self.setStyleSheet("""
            #NameDialogContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #23234a, stop:1 #14142b);
                border: 1px solid #6366f1;
                border-radius: 16px;
            }
            QLabel { background: transparent; }
            #NameDialogTitle {
                color: #ffffff;
                font-size: 15pt;
                font-weight: bold;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogSummary {
                color: #a5b4fc;
                font-size: 10pt;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogTip {
                color: #8b8ba7;
                font-size: 9pt;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogEdit {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid #3a3a5e;
                border-radius: 8px;
                color: #ffffff;
                padding: 0 12px;
                font-size: 11pt;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogEdit:focus { border: 1px solid #818cf8; }
            #NameDialogCancel {
                background: rgba(255, 255, 255, 0.08);
                color: #a0a0c0;
                border: 1px solid #3a3a5e;
                border-radius: 8px;
                font-size: 10pt;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogCancel:hover { background: rgba(255, 255, 255, 0.14); }
            #NameDialogSave {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #ec4899);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 10pt;
                font-weight: bold;
                font-family: "微软雅黑", "Segoe UI", sans-serif;
            }
            #NameDialogSave:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #818cf8, stop:1 #f472b6);
            }
        """)

        self.edit_name.setFocus()

    def _on_save(self):
        """保存按钮：记录名称并关闭"""
        self.record_name = self.edit_name.text().strip()
        self.accept()

    # ===== 无边框窗口拖动支持 =====
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class ShareDialog(QDialog):
    """
    分享有奖 · VIP尊享弹窗
    深色科技风，含活动规则、VIP权益、邀请码、分享按钮、推广二维码
    """

    # 推广信息常量
    SITE_URL = "www.ecojia.cn"
    WECHAT = "xunijiayuan"
    # V2：邀请码不再固定，注册账号+实名认证后系统生成专属邀请码（ECJ开头）
    REG_URL = "https://ecojia.cn/login"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 780)
        self._drag_pos = None

        # 专属邀请码需登录官网注册+实名认证后生成
        self.invite_code = "注册实名后自动生成"

        self._build_ui()

    def _build_ui(self):
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, \
            QFrame, QScrollArea, QWidget, QGridLayout
        from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush
        from PyQt6.QtCore import Qt, QSize, QRect
        import random

        # 外层容器（圆角+紫边）
        outer = QFrame(self)
        outer.setGeometry(0, 0, 520, 780)
        outer.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d0d1a, stop:0.5 #12122a, stop:1 #0d0d1a);
                border-radius: 20px;
                border: 1px solid rgba(99, 102, 241, 0.4);
            }
        """)

        layout = QVBoxLayout(outer)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # ===== 标题 =====
        title = QLabel("🎁 推广有惊喜 · 大使招募")
        title.setStyleSheet("font-size:20pt;font-weight:bold;color:#fbbf24;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("注册账号并完成实名认证，生成专属邀请码 · 好友经你的链接/邀请码注册才计入你名下")
        subtitle.setStyleSheet("font-size:10pt;color:#a0a0c0;background:transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # ===== 分割线 =====
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background:rgba(99,102,241,0.3);max-height:1px;")
        layout.addWidget(line)

        # ===== 阶梯奖励 =====
        reward_title = QLabel("🏆 阶梯奖励")
        reward_title.setStyleSheet("font-size:12pt;font-weight:bold;color:#c4b5fd;background:transparent;")
        layout.addWidget(reward_title)

        rewards = [
            ("邀请1人", "推广大使 · 开盲盒", "#6366f1"),
            ("邀请5人", "精英级大使 · 开盲盒", "#a78bfa"),
            ("邀请10人", "骨灰级大使 · 开盲盒", "#ec4899"),
            ("邀请20人", "项目合伙人 · ¥999扫码加入", "#fbbf24"),
        ]
        for cond, prize, color in rewards:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color};font-size:14pt;background:transparent;")
            cond_lbl = QLabel(cond)
            cond_lbl.setStyleSheet("font-size:10pt;color:#e0e0f0;background:transparent;min-width:80px;")
            prize_lbl = QLabel(prize)
            prize_lbl.setStyleSheet(f"font-size:10pt;color:{color};font-weight:bold;background:transparent;")
            row.addWidget(dot)
            row.addWidget(cond_lbl)
            row.addWidget(prize_lbl)
            row.addStretch()
            layout.addLayout(row)

        # ===== 规则说明 =====
        rule_lbl = QLabel("🎁 盲盒福利后期公布 · 满20人扫码支付¥999加入项目合伙人（利益详情咨询站长）\n"
                          "📌 新用户须通过你的推广链接或邀请码注册才计入你名下，否则算网站自然获客\n"
                          "👥 推广微信群二维码见官网 ecojia.cn 弹窗（后台统一设置）")
        rule_lbl.setStyleSheet("font-size:8.5pt;color:#8888a0;background:transparent;line-height:1.5;")
        rule_lbl.setWordWrap(True)
        layout.addWidget(rule_lbl)

        # ===== VIP权益 =====
        vip_title = QLabel("👑 VIP专属权益")
        vip_title.setStyleSheet("font-size:12pt;font-weight:bold;color:#fbbf24;background:transparent;margin-top:6px;")
        layout.addWidget(vip_title)

        benefits = [
            ("🌈", "2027科技风专属主题皮肤"),
            ("☁️", "计时数据云同步（多设备）"),
            ("🔔", "自定义提醒音效上传"),
            ("📋", "无限计次记录保存"),
            ("📤", "记录一键导出 Excel/PDF"),
            ("📈", "番茄钟专注效率统计图表"),
        ]
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (icon, text) in enumerate(benefits):
            r, c = i // 2, i % 2
            cell = QFrame()
            cell.setStyleSheet("""
                QFrame {
                    background: rgba(99,102,241,0.1);
                    border: 1px solid rgba(99,102,241,0.25);
                    border-radius: 10px;
                    padding: 8px;
                }
            """)
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(10, 8, 10, 8)
            ic = QLabel(icon)
            ic.setStyleSheet("font-size:14pt;background:transparent;")
            tx = QLabel(text)
            tx.setStyleSheet("font-size:9pt;color:#e0e0f0;background:transparent;")
            tx.setWordWrap(True)
            cell_layout.addWidget(ic)
            cell_layout.addWidget(tx, 1)
            grid.addWidget(cell, r, c)
        layout.addLayout(grid)

        # ===== 我的邀请码 =====
        code_frame = QFrame()
        code_frame.setStyleSheet("""
            QFrame {
                background: rgba(251,191,36,0.08);
                border: 1px dashed rgba(251,191,36,0.5);
                border-radius: 12px;
                padding: 12px;
            }
        """)
        code_layout = QHBoxLayout(code_frame)
        code_layout.setContentsMargins(16, 12, 16, 12)
        code_lbl = QLabel("我的专属邀请码")
        code_lbl.setStyleSheet("font-size:10pt;color:#a0a0c0;background:transparent;")
        code_val = QLabel(self.invite_code)
        code_val.setStyleSheet("font-size:10.5pt;font-weight:bold;color:#fbbf24;background:transparent;")
        copy_btn = QPushButton("📋 复制")
        copy_btn.setFixedHeight(32)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(251,191,36,0.15);
                border: 1px solid rgba(251,191,36,0.5);
                border-radius: 8px;
                color: #fbbf24;
                padding: 4px 12px;
                font-size: 9pt;
            }
            QPushButton:hover { background: rgba(251,191,36,0.3); }
        """)
        copy_btn.clicked.connect(self._copy_invite_code)
        code_layout.addWidget(code_lbl)
        code_layout.addWidget(code_val)
        code_layout.addStretch()
        code_layout.addWidget(copy_btn)
        layout.addWidget(code_frame)

        # ===== 推广二维码（装饰性伪二维码）=====
        qr_row = QHBoxLayout()
        qr_row.setSpacing(16)

        qr_label = QLabel()
        qr_pixmap = self._generate_qr_pixmap()
        qr_label.setPixmap(qr_pixmap)
        qr_label.setFixedSize(110, 110)
        qr_label.setStyleSheet("background:white;padding:6px;border-radius:8px;")
        qr_row.addWidget(qr_label)

        qr_text_layout = QVBoxLayout()
        qr_text_layout.setSpacing(6)
        qr_title = QLabel("📱 推广咨询中心")
        qr_title.setStyleSheet("font-size:11pt;font-weight:bold;color:#c4b5fd;background:transparent;")
        qr_desc = QLabel("扫码添加微信\n获取推广素材与佣金政策")
        qr_desc.setStyleSheet("font-size:9pt;color:#8888a0;background:transparent;")
        qr_desc.setWordWrap(True)
        qr_text_layout.addWidget(qr_title)
        qr_text_layout.addWidget(qr_desc)
        qr_text_layout.addStretch()
        qr_row.addLayout(qr_text_layout, 1)
        layout.addLayout(qr_row)

        # ===== 分享按钮 =====
        share_row = QHBoxLayout()
        share_row.setSpacing(10)
        for text, color in [("💬 微信", "#07c160"), ("🐧 QQ", "#12b7f5"), ("🔗 复制链接", "#6366f1")]:
            btn = QPushButton(text)
            btn.setFixedHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: none;
                    border-radius: 10px;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{ opacity: 0.85; }}
            """)
            btn.clicked.connect(lambda checked, t=text: self._do_share(t))
            share_row.addWidget(btn)
        layout.addLayout(share_row)

        # ===== 底部联系方式 =====
        footer = QLabel(f"🌐 {self.SITE_URL}    |    微信：{self.WECHAT}    |    作者：军哥懂保")
        footer.setStyleSheet("font-size:8pt;color:#4a4a60;background:transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        # ===== 关闭按钮 =====
        close_btn = QPushButton("✕", outer)
        close_btn.setGeometry(480, 12, 28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8888a0;
                font-size: 14pt;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.3); color: #ef4444; }
        """)
        close_btn.clicked.connect(self.accept)

    def _generate_qr_pixmap(self):
        """生成装饰性二维码图案（无需外部库）"""
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        from PyQt6.QtCore import Qt, QRect
        import random
        size = 98
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.white)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        cell = 7
        grid = size // cell
        # 固定种子保证每次一样
        rng = random.Random(42)
        for y in range(grid):
            for x in range(grid):
                # 三个角放定位框
                in_corner = (x < 7 and y < 7) or (x >= grid - 7 and y < 7) or (x < 7 and y >= grid - 7)
                if in_corner:
                    # 画定位框（7x7）
                    cx, cy = x, y
                    if (x < 7 and y < 7):
                        bx, by = 0, 0
                    elif (x >= grid - 7 and y < 7):
                        bx, by = grid - 7, 0
                    else:
                        bx, by = 0, grid - 7
                    lx, ly = x - bx, y - by
                    if lx == 0 or lx == 6 or ly == 0 or ly == 6:
                        painter.fillRect(x * cell, y * cell, cell, cell, QColor(0, 0, 0))
                    elif 2 <= lx <= 4 and 2 <= ly <= 4:
                        painter.fillRect(x * cell, y * cell, cell, cell, QColor(0, 0, 0))
                else:
                    if rng.random() > 0.5:
                        painter.fillRect(x * cell, y * cell, cell, cell, QColor(0, 0, 0))
        painter.end()
        return pm

    def _copy_invite_code(self):
        from PyQt6.QtWidgets import QApplication, QMessageBox
        QApplication.clipboard().setText(self.REG_URL)
        QMessageBox.information(self, "已复制",
                                "专属邀请码需在官网注册并完成实名认证后自动生成\n"
                                f"注册入口已复制：{self.REG_URL}")

    def _do_share(self, platform):
        from PyQt6.QtWidgets import QApplication, QMessageBox
        link = self.REG_URL + "  （打开注册后，在弹窗中查看你的专属邀请码链接）"
        if "复制链接" in platform:
            QApplication.clipboard().setText(link)
            QMessageBox.information(self, "已复制", f"分享链接已复制：\n{link}")
        else:
            QApplication.clipboard().setText(link)
            QMessageBox.information(self, "分享", f"已复制分享链接，请在{platform}中粘贴发送给好友\n\n{link}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos") and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class AdDialog(QDialog):
    """
    广告视频弹窗（配置化，三端统一读取服务端 ad.json）
    - 启动时从 https://ecojia.cn/timer/ad.json 拉取广告配置
    - 播放远程广告视频，可关闭、可点击跳转
    - 后期替换广告商只需更新服务端 ad.json 与视频，无需重新打包
    """

    AD_CONFIG_URL = "https://ecojia.cn/timer/ad.json"

    def __init__(self, parent=None, config: dict = None):
        super().__init__(parent)
        self.config = config or {}
        self._player = None
        self._audio = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(MAIN_STYLE)
        self.setFixedSize(560, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 标题栏
        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 14, 10)
        header.setSpacing(8)
        badge = QLabel("广告")
        badge.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f59e0b,stop:1 #ef4444);"
            "color:white;padding:2px 8px;border-radius:6px;font-weight:bold;font-size:11px;"
        )
        title = QLabel(self.config.get("title") or "广告位招租")
        title.setStyleSheet("color:#e0e0f0;font-weight:bold;font-size:14px;")
        close_btn = QPushButton("✕")
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#8888a0;font-size:14px;border-radius:8px;}"
            "QPushButton:hover{background:rgba(239,68,68,0.3);color:#ef4444;}"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(badge)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        root.addLayout(header)

        # 视频区
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background:#000;")
        root.addWidget(self.video_widget, stretch=1)

        # 底部信息
        footer = QHBoxLayout()
        footer.setContentsMargins(14, 8, 14, 10)
        footer.setSpacing(8)
        advertiser = self.config.get("advertiser") or "广告位招租"
        info = QLabel(f"{advertiser} · 联系微信 xunijiayuan")
        info.setStyleSheet("color:#8888a0;font-size:12px;")
        footer.addWidget(info)
        footer.addStretch()
        link = self.config.get("link")
        if link:
            link_btn = QPushButton(self.config.get("linkText") or "了解详情 →")
            link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            link_btn.setStyleSheet(
                "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6366f1,stop:1 #ec4899);"
                "color:white;border:none;border-radius:14px;padding:6px 16px;font-weight:bold;font-size:12px;}"
                "QPushButton:hover{opacity:0.85;}"
            )
            link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(link)))
            footer.addWidget(link_btn)
        root.addLayout(footer)

        self._setup_player()

    def _setup_player(self):
        video_url = self.config.get("video")
        if not video_url:
            return
        # 相对路径补齐为完整 URL
        if not video_url.startswith("http"):
            video_url = "https://ecojia.cn/timer/" + video_url.lstrip("/")
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self.video_widget)
        self._player.setSource(QUrl(video_url))
        self._player.play()

    def closeEvent(self, event):
        try:
            if self._player:
                self._player.stop()
        except Exception:
            pass
        super().closeEvent(event)


class MainPanel(QWidget):
    """
    主面板
    无边框 + 毛玻璃效果 + 可拖动
    """

    # 信号
    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()      # 停止（结束本次计时）
    reset_requested = pyqtSignal()
    lap_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    collapse_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)
    preset_changed = pyqtSignal()   # 预设时间/参数被修改（用于联动刷新显示）

    def __init__(self, parent=None):
        super().__init__(parent)

        self._collapsed = False
        self._drag_pos = None
        self._history = []           # 使用记录 [{name, mode, duration, end_time}]
        self._data_dir = self._resolve_data_dir()
        self._config_path = os.path.join(self._data_dir, "timer_config.json")
        self._history_path = os.path.join(self._data_dir, "timer_history.json")

        self._setup_ui()
        self._load_config()
        self._load_history()
        self._switch_mode("countdown")   # 应用初始模式UI（隐藏计次按钮等）

        # 本机时间参考（每秒刷新）
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

    @staticmethod
    def _resolve_data_dir():
        """确定配置文件存放目录：打包成EXE时用EXE所在目录，源码运行时用脚本所在目录"""
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def _setup_ui(self):
        """设置UI"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumSize(480, 680)   # 窗口可调大小（无上限，内部布局自适应；480保证4控制按钮不挤压）
        self.resize(560, 740)

        self.setStyleSheet(MAIN_STYLE)

        # 主容器
        self.container = QFrame()
        self.container.setObjectName("MainContainer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.addWidget(self.container)

        self._build_content()

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(99, 102, 241, 80))
        self.container.setGraphicsEffect(shadow)

    def _build_content(self):
        """构建内容"""
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 16, 24, 20)
        layout.setSpacing(12)

        # ===== 标题栏 =====
        title_row = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.lbl_title = QLabel("⏱ 悬浮计时器")
        self.lbl_title.setObjectName("AppTitle")
        self.lbl_subtitle = QLabel("军哥懂保 · 2027科技版")
        self.lbl_subtitle.setObjectName("SubTitle")
        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_subtitle)

        title_row.addLayout(title_col)
        title_row.addStretch()

        # 折叠按钮
        self.btn_collapse = QPushButton("收起")
        self.btn_collapse.setObjectName("CollapseButton")
        self.btn_collapse.setFixedSize(64, 32)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.clicked.connect(self._toggle_collapse)
        title_row.addWidget(self.btn_collapse)

        # 关闭按钮
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.clicked.connect(self.quit_requested.emit)
        title_row.addWidget(self.btn_close)

        layout.addLayout(title_row)

        # ===== 模式切换 =====
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self.btn_mode_stopwatch = QPushButton("⏱ 正计时")
        self.btn_mode_stopwatch.setObjectName("ModeButton")
        self.btn_mode_stopwatch.setProperty("selected", "false")
        self.btn_mode_stopwatch.clicked.connect(lambda: self._switch_mode("stopwatch"))

        self.btn_mode_countdown = QPushButton("⏳ 倒计时")
        self.btn_mode_countdown.setObjectName("ModeButton")
        self.btn_mode_countdown.setProperty("selected", "true")
        self.btn_mode_countdown.clicked.connect(lambda: self._switch_mode("countdown"))

        self.btn_mode_pomodoro = QPushButton("🍅 番茄钟")
        self.btn_mode_pomodoro.setObjectName("ModeButton")
        self.btn_mode_pomodoro.setProperty("selected", "false")
        self.btn_mode_pomodoro.clicked.connect(lambda: self._switch_mode("pomodoro"))

        self._mode_btns = [self.btn_mode_stopwatch, self.btn_mode_countdown, self.btn_mode_pomodoro]
        mode_row.addWidget(self.btn_mode_stopwatch)
        mode_row.addWidget(self.btn_mode_countdown)
        mode_row.addWidget(self.btn_mode_pomodoro)

        self.mode_widget = QWidget()
        self.mode_widget.setLayout(mode_row)
        layout.addWidget(self.mode_widget)

        # ===== 番茄钟阶段标签（仅番茄钟模式）=====
        self.lbl_phase = QLabel("工作中 🍅")
        self.lbl_phase.setObjectName("PhaseLabel")
        self.lbl_phase.setProperty("phase", "work")
        self.lbl_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_phase.hide()
        layout.addWidget(self.lbl_phase, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ===== 时间显示（字号随窗口自适应）=====
        self.lbl_time = QLabel("00:00")
        self.lbl_time.setObjectName("TimeDisplay")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = QFont("Consolas", 48)
        time_font.setBold(True)
        self.lbl_time.setFont(time_font)
        layout.addWidget(self.lbl_time)

        # ===== 本机时间参考 =====
        self.lbl_clock = QLabel("🕐 本机时间 --:--:--")
        self.lbl_clock.setObjectName("ClockRef")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_clock)

        # ===== 进度条 =====
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # ===== 设置区域（Tab）=====
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(230)   # 容纳：Tab栏+分组框+快捷按钮行

        # Tab1：倒计时设置
        tab_countdown = QWidget()
        cd_layout = QVBoxLayout(tab_countdown)
        cd_layout.setContentsMargins(12, 8, 12, 8)

        cd_group = QGroupBox("⏳ 倒计时时长")
        cd_form = QHBoxLayout(cd_group)
        cd_form.setSpacing(12)

        cd_form.addWidget(QLabel("时:"))
        self.spin_hours = QSpinBox()
        self.spin_hours.setRange(0, 24)
        self.spin_hours.setValue(0)
        cd_form.addWidget(self.spin_hours)

        cd_form.addWidget(QLabel("分:"))
        self.spin_minutes = QSpinBox()
        self.spin_minutes.setRange(0, 59)
        self.spin_minutes.setValue(10)
        cd_form.addWidget(self.spin_minutes)

        cd_form.addWidget(QLabel("秒:"))
        self.spin_seconds = QSpinBox()
        self.spin_seconds.setRange(0, 59)
        self.spin_seconds.setValue(0)
        cd_form.addWidget(self.spin_seconds)

        cd_layout.addWidget(cd_group)

        # 快捷时间按钮
        cd_shortcuts = QHBoxLayout()
        cd_shortcuts.setSpacing(8)
        for label, seconds in [("1分钟", 60), ("5分钟", 300), ("10分钟", 600), ("25分钟", 1500), ("1小时", 3600)]:
            btn = QPushButton(label)
            btn.setObjectName("SecondaryButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, s=seconds: self._set_countdown_seconds(s))
            cd_shortcuts.addWidget(btn)
        cd_layout.addLayout(cd_shortcuts)
        cd_layout.addStretch()

        # 预设时间联动：修改时分秒/点快捷按钮时立即刷新时间显示
        for spin in (self.spin_hours, self.spin_minutes, self.spin_seconds):
            spin.valueChanged.connect(lambda *_: self.preset_changed.emit())

        # Tab2：番茄钟设置
        tab_pomodoro = QWidget()
        pm_layout = QVBoxLayout(tab_pomodoro)
        pm_layout.setContentsMargins(12, 8, 12, 8)

        pm_group = QGroupBox("🍅 番茄钟参数")
        pm_form = QVBoxLayout(pm_group)
        pm_form.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("工作时长(分):"))
        self.spin_pm_work = QSpinBox()
        self.spin_pm_work.setRange(1, 180)
        self.spin_pm_work.setValue(25)
        row1.addWidget(self.spin_pm_work)
        row1.addStretch()
        pm_form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("短休息(分):"))
        self.spin_pm_short = QSpinBox()
        self.spin_pm_short.setRange(1, 60)
        self.spin_pm_short.setValue(5)
        row2.addWidget(self.spin_pm_short)
        row2.addWidget(QLabel("长休息(分):"))
        self.spin_pm_long = QSpinBox()
        self.spin_pm_long.setRange(1, 120)
        self.spin_pm_long.setValue(15)
        row2.addWidget(self.spin_pm_long)
        row2.addStretch()
        pm_form.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("几轮后长休息:"))
        self.spin_pm_cycles = QSpinBox()
        self.spin_pm_cycles.setRange(2, 10)
        self.spin_pm_cycles.setValue(4)
        row3.addWidget(self.spin_pm_cycles)
        row3.addStretch()
        pm_form.addLayout(row3)

        pm_layout.addWidget(pm_group)
        pm_layout.addStretch()

        # 番茄钟参数变化联动
        for spin in (self.spin_pm_work, self.spin_pm_short, self.spin_pm_long, self.spin_pm_cycles):
            spin.valueChanged.connect(lambda *_: self.preset_changed.emit())

        # Tab3：声音设置
        tab_sound = QWidget()
        sd_layout = QVBoxLayout(tab_sound)
        sd_layout.setContentsMargins(12, 8, 12, 8)

        sd_group = QGroupBox("🔊 声音设置")
        sd_form = QVBoxLayout(sd_group)
        sd_form.setSpacing(10)

        self.chk_sound = QCheckBox("✅ 开启声音提醒")
        self.chk_sound.setChecked(True)
        sd_form.addWidget(self.chk_sound)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("音量:"))
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(50)
        vol_row.addWidget(self.slider_volume)
        self.lbl_volume = QLabel("50%")
        self.lbl_volume.setFixedWidth(40)
        vol_row.addWidget(self.lbl_volume)
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume.setText(f"{v}%"))
        sd_form.addLayout(vol_row)

        # 倒计时结束前语音提醒：剩余 N 秒时语音播报，仅提醒不打断计时
        pre_row = QHBoxLayout()
        self.chk_pre_alert = QCheckBox("🔔 结束前提醒")
        self.chk_pre_alert.setChecked(True)
        self.chk_pre_alert.setToolTip("倒计时剩余设定秒数时语音播报「还剩 N 秒」\n（仅提醒，计时继续走；重置后可再次触发）")
        pre_row.addWidget(self.chk_pre_alert)
        self.spin_pre_alert_sec = QSpinBox()
        self.spin_pre_alert_sec.setRange(1, 600)
        self.spin_pre_alert_sec.setValue(3)
        self.spin_pre_alert_sec.setSuffix(" 秒")
        pre_row.addWidget(self.spin_pre_alert_sec)
        pre_row.addStretch()
        sd_form.addLayout(pre_row)

        tip_pre = QLabel("倒计时剩余设定秒数时语音播报，默认 3 秒，可关闭")
        tip_pre.setStyleSheet("font-size:8.5pt;color:#8888a0;background:transparent;")
        sd_form.addWidget(tip_pre)

        sd_layout.addWidget(sd_group)
        sd_layout.addStretch()

        # Tab4：计次记录
        tab_laps = QWidget()
        lp_layout = QVBoxLayout(tab_laps)
        lp_layout.setContentsMargins(12, 8, 12, 8)

        # 正计时到时提醒（仅正计时模式生效：到达设定分钟数提醒一次，计时不中断）
        remind_row = QHBoxLayout()
        self.chk_remind = QCheckBox("⏰ 到时提醒")
        self.chk_remind.setToolTip("正计时到达设定分钟时声音+消息提醒一次\n（仅提醒，计时继续走；重置后可再次提醒）")
        remind_row.addWidget(self.chk_remind)
        self.spin_remind_min = QSpinBox()
        self.spin_remind_min.setRange(1, 999)
        self.spin_remind_min.setValue(25)
        self.spin_remind_min.setSuffix(" 分钟")
        remind_row.addWidget(self.spin_remind_min)
        remind_row.addStretch()
        lp_layout.addLayout(remind_row)

        self.lap_list = QListWidget()
        self.lap_list.setAlternatingRowColors(True)
        lp_layout.addWidget(self.lap_list)

        lap_btn_row = QHBoxLayout()
        btn_clear_laps = QPushButton("🗑 清空记录")
        btn_clear_laps.setObjectName("SecondaryButton")
        btn_clear_laps.setFixedHeight(36)
        btn_clear_laps.setMinimumWidth(120)
        btn_clear_laps.clicked.connect(self.lap_list.clear)
        lap_btn_row.addWidget(btn_clear_laps)
        lap_btn_row.addStretch()
        lp_layout.addLayout(lap_btn_row)

        # Tab5：使用记录
        tab_records = QWidget()
        rc_layout = QVBoxLayout(tab_records)
        rc_layout.setContentsMargins(12, 8, 12, 8)
        rc_layout.setSpacing(8)

        # 命名保存开关（开=弹窗自定义命名；关=自动以当前时间命名保存，可事后重命名）
        self.chk_name_prompt = QCheckBox("📝 计时结束后弹出命名保存窗口")
        self.chk_name_prompt.setChecked(True)
        self.chk_name_prompt.setToolTip("打开：计时结束或停止时弹窗，由您为本次计时命名\n关闭：不弹窗，自动以当前时间命名保存（选中记录点「重命名」可随时改）")
        rc_layout.addWidget(self.chk_name_prompt)

        self.record_list = QListWidget()
        self.record_list.setAlternatingRowColors(True)
        rc_layout.addWidget(self.record_list)

        rc_btn_row = QHBoxLayout()
        btn_rename_record = QPushButton("✏️ 重命名")
        btn_rename_record.setObjectName("SecondaryButton")
        btn_rename_record.setFixedHeight(36)
        btn_rename_record.setMinimumWidth(120)
        btn_rename_record.clicked.connect(self._rename_selected_record)
        rc_btn_row.addWidget(btn_rename_record)
        btn_del_record = QPushButton("🗑 删除选中")
        btn_del_record.setObjectName("SecondaryButton")
        btn_del_record.setFixedHeight(36)
        btn_del_record.setMinimumWidth(120)
        btn_del_record.clicked.connect(self._delete_selected_record)
        btn_clear_records = QPushButton("🗑 清空记录")
        btn_clear_records.setObjectName("SecondaryButton")
        btn_clear_records.setFixedHeight(36)
        btn_clear_records.setMinimumWidth(120)
        btn_clear_records.clicked.connect(self._clear_records)
        rc_btn_row.addWidget(btn_del_record)
        rc_btn_row.addWidget(btn_clear_records)
        rc_btn_row.addStretch()
        rc_layout.addLayout(rc_btn_row)

        self.tabs.addTab(tab_countdown, "⏳ 倒计时")
        self.tabs.addTab(tab_pomodoro, "🍅 番茄钟")
        self.tabs.addTab(tab_sound, "🔊 声音")
        self.tabs.addTab(tab_laps, "📋 计次")
        self.tabs.addTab(tab_records, "📁 记录")

        layout.addWidget(self.tabs, 1)   # stretch=1：窗口拉高时Tab区吸收多余空间

        # Tab与模式联动：点设置Tab即切模式（倒计时Tab→倒计时模式，番茄钟Tab→番茄钟，计次Tab→正计时）
        self._syncing = False
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ===== 控制按钮 =====
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.btn_reset = QPushButton("🔄 重置")
        self.btn_reset.setObjectName("SecondaryButton")
        self.btn_reset.setFixedHeight(48)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_requested.emit)

        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setObjectName("SecondaryButton")
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)   # 仅计时中/暂停时可用
        self.btn_stop.setToolTip("结束本次计时（若开启命名保存，将弹窗保存记录）")
        self.btn_stop.clicked.connect(self.stop_requested.emit)

        self.btn_lap = QPushButton("📝 计次")
        self.btn_lap.setObjectName("SecondaryButton")
        self.btn_lap.setFixedHeight(48)
        self.btn_lap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lap.clicked.connect(self.lap_requested.emit)

        self.btn_start = QPushButton("▶ 开始")
        self.btn_start.setObjectName("ControlButton")
        self.btn_start.setFixedHeight(48)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_main_button_clicked)

        ctrl_row.addWidget(self.btn_reset)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addWidget(self.btn_lap)
        ctrl_row.addWidget(self.btn_start, 2)

        self.ctrl_widget = QWidget()
        self.ctrl_widget.setLayout(ctrl_row)
        layout.addWidget(self.ctrl_widget)

        # ===== 底部信息（右侧放窗口大小调节手柄）=====
        footer_row = QHBoxLayout()
        footer_row.addWidget(QLabel("作者：军哥懂保 | 微信：xunijiayuan"))
        footer_row.addStretch()
        self.lbl_config_size = QLabel("")
        self.lbl_config_size.setObjectName("FooterInfo")
        footer_row.addWidget(self.lbl_config_size)
        footer_row.addWidget(QSizeGrip(self.container))   # 拖这里调整窗口大小

        self.footer_widget = QWidget()
        self.footer_widget.setLayout(footer_row)
        layout.addWidget(self.footer_widget)

        # ===== 默认：倒计时模式（与倒计时Tab一致）=====
        self.tabs.setCurrentIndex(0)
        self._current_mode = "countdown"

    # ==================== 模式切换 ====================

    def _switch_mode(self, mode: str):
        """切换模式（同步高亮按钮+联动Tab页）"""
        self._current_mode = mode
        for btn in [self.btn_mode_stopwatch, self.btn_mode_countdown, self.btn_mode_pomodoro]:
            btn.setProperty("selected", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "stopwatch":
            self.btn_mode_stopwatch.setProperty("selected", "true")
            self.btn_lap.show()
            self.progress_bar.hide()
            self.lbl_phase.hide()
        elif mode == "countdown":
            self.btn_mode_countdown.setProperty("selected", "true")
            self.btn_lap.hide()
            self.progress_bar.show()
            self.lbl_phase.hide()
        elif mode == "pomodoro":
            self.btn_mode_pomodoro.setProperty("selected", "true")
            self.btn_lap.hide()
            self.progress_bar.show()
            self.lbl_phase.show()

        for btn in [self.btn_mode_stopwatch, self.btn_mode_countdown, self.btn_mode_pomodoro]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # 反向联动Tab页（防止与Tab→模式联动互相死循环）
        if not getattr(self, "_syncing", False):
            tab_map = {"countdown": 0, "pomodoro": 1, "stopwatch": 3}
            self._syncing = True
            self.tabs.setCurrentIndex(tab_map.get(mode, 0))
            self._syncing = False

        self.mode_changed.emit(mode)

    def _on_tab_changed(self, idx: int):
        """Tab切换时联动切换计时模式"""
        if self._syncing:
            return
        mode_map = {0: "countdown", 1: "pomodoro", 3: "stopwatch"}  # 2声音/4记录不切模式
        mode = mode_map.get(idx)
        if mode and mode != self._current_mode:
            self._syncing = True
            self._switch_mode(mode)
            self._syncing = False

    def _set_countdown_seconds(self, seconds: int):
        """通过快捷按钮设置倒计时（阻断spin自身信号，统一发一次联动信号）"""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        for spin, v in ((self.spin_hours, h), (self.spin_minutes, m), (self.spin_seconds, s)):
            spin.blockSignals(True)
            spin.setValue(v)
            spin.blockSignals(False)
        self.preset_changed.emit()

    def is_name_prompt_enabled(self) -> bool:
        """是否开启计时结束命名提示"""
        return self.chk_name_prompt.isChecked()

    def is_remind_enabled(self) -> bool:
        """正计时到时提醒是否开启"""
        return self.chk_remind.isChecked()

    def get_remind_seconds(self) -> int:
        """正计时到时提醒秒数"""
        return self.spin_remind_min.value() * 60

    # ==================== 本机时间参考 ====================

    def _update_clock(self):
        """每秒刷新本机时间显示"""
        from datetime import datetime
        self.lbl_clock.setText(f"🕐 本机时间 {datetime.now().strftime('%H:%M:%S')}")

    # ==================== 窗口自适应 ====================

    def resizeEvent(self, event):
        """窗口大小变化时，时间字号随宽度自适应，防止文字出框"""
        super().resizeEvent(event)
        w = self.width()
        # 520宽→48pt基准，宽度每增减10px字号增减2pt，限制在26~56之间
        size = max(26, min(56, 48 + (w - 520) // 10 * 2))
        f = self.lbl_time.font()
        if f.pointSize() != size:
            f.setPointSize(size)
            self.lbl_time.setFont(f)

    # ==================== 使用记录（增删查）====================

    def add_history(self, name: str, mode_text: str, duration_text: str):
        """新增一条使用记录"""
        from datetime import datetime
        self._history.insert(0, {
            "name": name,
            "mode": mode_text,
            "duration": duration_text,
            "end_time": datetime.now().strftime("%Y/%m/%d %H:%M"),
        })
        self._save_history()

    def _render_history(self):
        """刷新记录列表显示"""
        self.record_list.clear()
        if not self._history:
            self.record_list.addItem(QListWidgetItem("暂无使用记录"))
            return
        for rec in self._history:
            self.record_list.addItem(QListWidgetItem(
                f"{rec['name']} ｜ {rec['mode']} · {rec['duration']} ｜ {rec['end_time']}"
            ))

    def _delete_selected_record(self):
        """删除选中的记录"""
        row = self.record_list.currentRow()
        if 0 <= row < len(self._history):
            del self._history[row]
            self._save_history()

    def _clear_records(self):
        """清空所有记录"""
        self._history.clear()
        self._save_history()

    def _rename_selected_record(self):
        """重命名选中的记录（复用命名弹窗，预填当前名称）"""
        row = self.record_list.currentRow()
        if not (0 <= row < len(self._history)):
            return
        rec = self._history[row]
        dlg = NameDialog(self, title_text="✏️ 重命名记录", default_name=rec["name"])
        geo = self.frameGeometry()
        dlg.move(geo.center().x() - dlg.width() // 2,
                 geo.center().y() - dlg.sizeHint().height() // 2)
        if dlg.exec() and dlg.record_name:
            rec["name"] = dlg.record_name
            self._save_history()

    def _save_history(self):
        """记录持久化到JSON"""
        try:
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._render_history()

    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self._history_path):
                with open(self._history_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
        except Exception:
            self._history = []
        self._render_history()

    def _on_main_button_clicked(self):
        """主按钮（开始/暂停/继续）"""
        text = self.btn_start.text()
        if text == "▶ 开始":
            self.start_requested.emit()
        elif text == "⏸ 暂停":
            self.pause_requested.emit()
        elif text == "▶ 继续":
            self.start_requested.emit()

    def update_main_button(self, state: str):
        """根据状态更新主按钮和停止按钮可用性"""
        if state == "idle":
            self.btn_start.setText("▶ 开始")
        elif state == "running":
            self.btn_start.setText("⏸ 暂停")
        elif state == "paused":
            self.btn_start.setText("▶ 继续")
        elif state == "finished":
            self.btn_start.setText("▶ 重新开始")
        # 停止按钮：仅运行中/暂停时可用
        self.btn_stop.setEnabled(state in ("running", "paused"))

    def update_time_display(self, time_text: str, state: str = "idle"):
        """更新时间显示"""
        self.lbl_time.setText(time_text)
        self.lbl_time.setProperty("running", "true" if state == "running" else "false")
        self.lbl_time.setProperty("paused", "true" if state == "paused" else "false")
        self.lbl_time.style().unpolish(self.lbl_time)
        self.lbl_time.style().polish(self.lbl_time)

    def update_progress(self, progress: float):
        """更新进度条 0-1"""
        self.progress_bar.setValue(int(progress * 100))

    def update_phase(self, phase: str):
        """更新番茄钟阶段"""
        if phase == "work":
            self.lbl_phase.setText("🔥 专注工作中")
        elif phase == "short_break":
            self.lbl_phase.setText("☕ 短休息中")
        elif phase == "long_break":
            self.lbl_phase.setText("🌴 长休息中")
        self.lbl_phase.setProperty("phase", phase)
        self.lbl_phase.style().unpolish(self.lbl_phase)
        self.lbl_phase.style().polish(self.lbl_phase)

    def add_lap(self, total: float, interval_text: str):
        """添加计次记录"""
        h = int(total // 3600)
        m = int((total % 3600) // 60)
        s = int(total % 60)
        total_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

        count = self.lap_list.count() + 1
        item_text = f"#{count:02d}  累计 {total_str}  |  +{interval_text}"
        item = QListWidgetItem(item_text)
        self.lap_list.addItem(item)
        self.lap_list.scrollToBottom()

    # ==================== 折叠/展开 ====================

    def _toggle_collapse(self):
        """折叠/展开：收起时真正隐藏内容区，只留标题栏+时间"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            # 隐藏内容区
            self.mode_widget.hide()
            self.lbl_phase.hide()
            self.progress_bar.hide()
            self.lbl_clock.hide()
            self.tabs.hide()
            self.ctrl_widget.hide()
            self.footer_widget.hide()
            self.setFixedHeight(210)
            self.btn_collapse.setText("展开")
        else:
            self.setMaximumHeight(16777215)   # 解除固定高度
            self.setMinimumSize(480, 600)
            # 恢复内容区
            self.mode_widget.show()
            self.lbl_clock.show()
            self.tabs.show()
            self.ctrl_widget.show()
            self.footer_widget.show()
            # 按当前模式恢复进度条/阶段标签
            if self._current_mode in ("countdown", "pomodoro"):
                self.progress_bar.show()
            if self._current_mode == "pomodoro":
                self.lbl_phase.show()
            self.resize(560, 720)
            self.btn_collapse.setText("收起")

    # ==================== 拖动 + 边缘调整大小 ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            margin = 12
            near_right = pos.x() > self.width() - margin
            near_bottom = pos.y() > self.height() - margin
            # 边缘按下 = 调整窗口大小（折叠状态禁用）
            if (near_right or near_bottom) and not self._collapsed:
                self._resizing = True
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                self._resize_dir = (near_right, near_bottom)
                event.accept()
                return
            # 标题栏区域（顶部80px内）按住 = 拖动窗口
            if pos.y() < 80:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if getattr(self, "_resizing", False):
            delta = event.globalPosition().toPoint() - self._resize_start
            geo = self._resize_geo
            nw, nh = geo.width(), geo.height()
            if self._resize_dir[0]:
                nw = max(480, geo.width() + delta.x())
            if self._resize_dir[1]:
                nh = max(600, geo.height() + delta.y())
            self.resize(nw, nh)
            return
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False

    # ==================== 配置持久化 ====================

    def get_countdown_seconds(self) -> int:
        """获取倒计时设置的秒数"""
        return (
            self.spin_hours.value() * 3600 +
            self.spin_minutes.value() * 60 +
            self.spin_seconds.value()
        )

    def get_pomodoro_config(self) -> dict:
        """获取番茄钟设置"""
        return {
            "work_min": self.spin_pm_work.value(),
            "short_break_min": self.spin_pm_short.value(),
            "long_break_min": self.spin_pm_long.value(),
            "cycles_before_long": self.spin_pm_cycles.value(),
        }

    def get_sound_config(self) -> dict:
        """获取声音设置"""
        return {
            "enabled": self.chk_sound.isChecked(),
            "volume": self.slider_volume.value() / 100.0,
            "pre_alert_enabled": self.chk_pre_alert.isChecked(),
            "pre_alert_seconds": self.spin_pre_alert_sec.value(),
        }

    def is_pre_alert_enabled(self) -> bool:
        """倒计时结束前语音提醒是否开启（受总声音开关约束）"""
        return self.chk_sound.isChecked() and self.chk_pre_alert.isChecked()

    def get_pre_alert_seconds(self) -> int:
        """结束前提前多少秒提醒"""
        return self.spin_pre_alert_sec.value()

    def _save_config(self):
        """保存配置"""
        config = {
            "countdown": {
                "hours": self.spin_hours.value(),
                "minutes": self.spin_minutes.value(),
                "seconds": self.spin_seconds.value(),
            },
            "pomodoro": self.get_pomodoro_config(),
            "sound": self.get_sound_config(),
            "name_prompt": self.chk_name_prompt.isChecked(),
            "remind": {
                "enabled": self.chk_remind.isChecked(),
                "minutes": self.spin_remind_min.value(),
            },
            "pre_alert": {
                "enabled": self.chk_pre_alert.isChecked(),
                "seconds": self.spin_pre_alert_sec.value(),
            },
            "geometry": {
                "x": self.x(),
                "y": self.y(),
                "w": self.width(),
                "h": self.height(),
            },
        }
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            size = os.path.getsize(self._config_path)
            mtime = os.path.getmtime(self._config_path)
            from datetime import datetime
            self.lbl_config_size.setText(
                f"📁 {size}B · {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}"
            )
        except Exception:
            pass

    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                cd = config.get("countdown", {})
                self.spin_hours.setValue(cd.get("hours", 0))
                self.spin_minutes.setValue(cd.get("minutes", 10))
                self.spin_seconds.setValue(cd.get("seconds", 0))

                pm = config.get("pomodoro", {})
                self.spin_pm_work.setValue(pm.get("work_min", 25))
                self.spin_pm_short.setValue(pm.get("short_break_min", 5))
                self.spin_pm_long.setValue(pm.get("long_break_min", 15))
                self.spin_pm_cycles.setValue(pm.get("cycles_before_long", 4))

                sd = config.get("sound", {})
                self.chk_sound.setChecked(sd.get("enabled", True))
                self.slider_volume.setValue(int(sd.get("volume", 0.5) * 100))
                self.chk_pre_alert.setChecked(sd.get("pre_alert_enabled", True))
                self.spin_pre_alert_sec.setValue(sd.get("pre_alert_seconds", 3))
                self.chk_name_prompt.setChecked(config.get("name_prompt", True))

                rm = config.get("remind", {})
                self.chk_remind.setChecked(rm.get("enabled", False))
                self.spin_remind_min.setValue(rm.get("minutes", 25))

                geo = config.get("geometry", {})
                if geo:
                    self.move(geo.get("x", 200), geo.get("y", 100))
                    self.resize(geo.get("w", 520), geo.get("h", 720))

                size = os.path.getsize(self._config_path)
                mtime = os.path.getmtime(self._config_path)
                from datetime import datetime
                self.lbl_config_size.setText(
                    f"📁 {size}B · {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}"
                )
        except Exception:
            pass

    def save_config(self):
        """外部调用保存"""
        self._save_config()

    def closeEvent(self, event):
        """关闭时保存配置"""
        self._save_config()
        super().closeEvent(event)
