# -*- coding: utf-8 -*-
"""主界面：拖入视频或图片 → 输入大白话命令 → 一键消除 → 前后对比预览。"""
import os
import shutil
import subprocess
import tempfile

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QPlainTextEdit, QFrame, QFileDialog,
    QToolTip, QSizePolicy,
)

from app.pipeline import 消除图片, 消除视频

深色样式 = """
QMainWindow, QWidget { background: #14171C; color: #E6E8EB; font-family: "Microsoft YaHei", "PingFang SC"; font-size: 14px; }
QFrame#卡片 { background: #1C2129; border: 1px solid #2A3038; border-radius: 12px; }
QLabel#标题 { font-size: 20px; font-weight: 600; }
QLabel#副标 { color: #8A919E; font-size: 12px; }
QLabel#术语 { color: #3ECF8E; font-weight: 600; }
QLineEdit { background: #14171C; border: 1px solid #2A3038; border-radius: 8px; padding: 10px 12px; color: #E6E8EB; }
QLineEdit:focus { border-color: #3ECF8E; }
QPushButton#主按钮 { background: #3ECF8E; color: #0B2E1F; border: none; border-radius: 8px; padding: 12px; font-size: 15px; font-weight: 600; }
QPushButton#主按钮:hover { background: #55DAA0; }
QPushButton#主按钮:disabled { background: #2A3038; color: #6B7280; }
QPushButton#次按钮 { background: transparent; color: #8A919E; border: 1px solid #2A3038; border-radius: 8px; padding: 8px 14px; }
QPushButton#主按钮2 { background: #232A33; color: #E6E8EB; border: 1px solid #2A3038; border-radius: 8px; padding: 8px 14px; }
QPushButton#目标标签 { background: #232A33; color: #B9BFC9; border: 1px solid #2A3038; border-radius: 14px; padding: 6px 14px; font-size: 13px; }
QPushButton#目标标签:hover { border-color: #3ECF8E; color: #3ECF8E; }
QProgressBar { background: #232A33; border: none; border-radius: 6px; height: 12px; text-align: center; color: #8A919E; font-size: 11px; }
QProgressBar::chunk { background: #3ECF8E; border-radius: 6px; }
QPlainTextEdit { background: #10131A; border: 1px solid #232A33; border-radius: 8px; color: #8A919E; font-family: Consolas, "Microsoft YaHei"; font-size: 12px; padding: 8px; }
QLabel#预览框 { background: #10131A; border: 1px dashed #2A3038; border-radius: 12px; color: #525A66; }
"""

术语解释 = {
    "掩码": "掩码（yǎn mǎ）：就是 AI 标记出来的「待清除区域」的黑白图，白色部分就是要抹掉的地方。",
    "帧": "视频本质上是一秒几十张连续图片，每一张叫一「帧」。本工具就是逐帧消除再拼回视频。",
    "GPU": "显卡（图形处理器）。你的 RTX 5080 显卡会让消除速度快几十倍。",
    "GroundingDINO": "一个能听懂文字描述的 AI 模型，你说「女人」它就在画面里圈出女人的位置。",
    "SAM": "一个专门抠轮廓的 AI 模型，把目标的边缘抠得严丝合缝。",
    "LaMa": "一个专门「填坑」的 AI 模型，把抹掉的区域根据周围画面补全得看不出痕迹。",
}


def 术语标签(文字: str) -> QLabel:
    """带 ⓘ 帮助气泡的术语标签。"""
    标签 = QLabel(f'{文字} <span style="color:#3ECF8E;">ⓘ</span>')
    标签.setObjectName("术语")
    标签.setCursor(Qt.WhatsThisCursor)
    标签.setToolTip(术语解释.get(文字, ""))
    return 标签


class 处理线程(QThread):
    进度 = Signal(int, int, str)
    日志 = Signal(str)
    完成 = Signal(dict)
    失败 = Signal(str)

    def __init__(self, 文件路径: str, 命令: str, 输出路径: str):
        super().__init__()
        self.文件路径, self.命令, self.输出路径 = 文件路径, 命令, 输出路径

    def run(self):
        try:
            if self.文件路径.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                结果 = 消除视频(
                    self.文件路径, self.输出路径, self.命令,
                    进度回调=lambda 当前, 总数, 阶段: self.进度.emit(当前, 总数, 阶段),
                    日志回调=self.日志.emit,
                )
            else:
                self.日志.emit("正在加载模型并处理图片…")
                结果 = 消除图片(self.文件路径, self.输出路径, self.命令)
                self.进度.emit(1, 1, "完成")
            self.完成.emit(结果)
        except Exception as e:
            self.失败.emit(str(e))


class 拖放区(QFrame):
    文件进入 = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("卡片")
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        布局 = QVBoxLayout(self)
        布局.setAlignment(Qt.AlignCenter)
        self.提示 = QLabel("把视频或图片拖到这里\n或点击选择文件")
        self.提示.setAlignment(Qt.AlignCenter)
        self.提示.setStyleSheet("color:#8A919E; font-size:15px;")
        布局.addWidget(self.提示)
        self.路径 = None

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        路径 = e.mimeData().urls()[0].toLocalFile()
        self.设置文件(路径)

    def mousePressEvent(self, e):
        路径, _ = QFileDialog.getOpenFileName(self, "选择视频或图片", "", "媒体文件 (*.mp4 *.mov *.avi *.mkv *.webm *.jpg *.jpeg *.png *.bmp)")
        if 路径:
            self.设置文件(路径)

    def 设置文件(self, 路径: str):
        self.路径 = 路径
        self.提示.setText(f"已选择：{os.path.basename(路径)}\n点击可重新选择")
        self.提示.setStyleSheet("color:#3ECF8E; font-size:14px;")
        self.文件进入.emit(路径)


class 对比预览(QWidget):
    """处理完成后显示 原图/成品 左右对比（视频则抽首帧对比）。"""

    def __init__(self):
        super().__init__()
        布局 = QHBoxLayout(self)
        布局.setContentsMargins(0, 0, 0, 0)
        self.左 = QLabel("处理后显示原片")
        self.右 = QLabel("处理后显示成品")
        for 标签 in (self.左, self.右):
            标签.setObjectName("预览框")
            标签.setAlignment(Qt.AlignCenter)
            标签.setScaledContents(False)
            标签.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            标签.setMinimumHeight(280)
        布局.addWidget(self.左)
        布局.addWidget(self.右)

    def 显示对比(self, 原图路径: str, 成品路径: str):
        for 标签, 路径 in ((self.左, 原图路径), (self.右, 成品路径)):
            图 = QPixmap(路径)
            if not 图.isNull():
                标签.setPixmap(图.scaled(标签.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class 主窗口(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 消除工具 · 视频图片批量消除")
        self.resize(1060, 720)
        self.setStyleSheet(深色样式)
        self._临时目录 = None

        根 = QWidget()
        总布局 = QVBoxLayout(根)
        总布局间距 = 14
        总布局.setContentsMargins(20, 18, 20, 14)
        总布局.setSpacing(总布局间距)

        # 标题区
        标题行 = QHBoxLayout()
        标题框 = QVBoxLayout()
        标题 = QLabel("AI 消除工具")
        标题.setObjectName("标题")
        副标 = QLabel("一句话命令，批量抹掉视频/图片中的任何目标")
        副标.setObjectName("副标")
        标题框.addWidget(标题)
        标题框.addWidget(副标)
        标题行.addLayout(标题框)
        标题行.addStretch()
        标题行.addWidget(术语标签("帧"))
        标题行.addWidget(术语标签("GPU"))
        标题行.addWidget(术语标签("掩码"))
        总布局.addLayout(标题行)

        # 中间主区
        主区 = QHBoxLayout()
        主区.setSpacing(14)

        # 左列：拖放 + 命令
        左列 = QVBoxLayout()
        左列.setSpacing(12)
        self.拖放 = 拖放区()
        self.拖放.文件进入.connect(self._文件就绪)
        左列.addWidget(self.拖放)

        命令卡 = QFrame()
        命令卡.setObjectName("卡片")
        命令布局 = QVBoxLayout(命令卡)
        命令布局.addWidget(QLabel("输入消除命令"))
        self.命令框 = QLineEdit()
        self.命令框.setPlaceholderText("例如：消除 女人　或　消除 女人和帽子")
        命令布局.addWidget(self.命令框)

        目标行 = QHBoxLayout()
        目标行.addWidget(QLabel("常用目标："))
        for 词 in ["女人", "路人", "LOGO", "文字", "帽子", "猫", "头发"]:
            钮 = QPushButton(词)
            钮.setObjectName("目标标签")
            钮.setCursor(Qt.PointingHandCursor)
            钮.clicked.connect(lambda _, w=词: self.命令框.setText(f"消除 {w}"))
            目标行.addWidget(钮)
        目标行.addStretch()
        命令布局.addLayout(目标行)

        self.开始钮 = QPushButton("开始消除")
        self.开始钮.setObjectName("主按钮")
        self.开始钮.setCursor(Qt.PointingHandCursor)
        self.开始钮.setEnabled(False)
        self.开始钮.clicked.connect(self._开始处理)
        命令布局.addWidget(self.开始钮)
        左列.addWidget(命令卡)
        主区.addLayout(左列, 2)

        # 右列：对比预览
        self.预览 = 对比预览()
        主区.addWidget(self.预览, 3)
        总布局.addLayout(主区, 1)

        # 底部：进度 + 日志
        底部 = QFrame()
        底部.setObjectName("卡片")
        底部布局 = QVBoxLayout(底部)
        self.阶段标签 = QLabel("待命")
        self.阶段标签.setObjectName("副标")
        self.进度条 = QProgressBar()
        self.进度条.setRange(0, 100)
        self.进度条.setValue(0)
        self.日志框 = QPlainTextEdit()
        self.日志框.setReadOnly(True)
        self.日志框.setMaximumHeight(110)
        底部布局.addWidget(self.阶段标签)
        底部布局.addWidget(self.进度条)
        底部布局.addWidget(self.日志框)
        总布局.addWidget(底部)

        self.setCentralWidget(根)
        self._线程 = None
        self._当前文件 = None

    def _文件就绪(self, 路径: str):
        self._当前文件 = 路径
        self.开始钮.setEnabled(True)
        self._记录(f"已载入：{路径}")

    def _开始处理(self):
        命令 = self.命令框.text().strip()
        if not 命令:
            QToolTip.showText(self.命令框.mapToGlobal(self.命令框.rect().bottomLeft()), "先输入要消除的目标，例如：消除 女人")
            return
        if not self._当前文件:
            return

        项目根 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        扩展名 = os.path.splitext(self._当前文件)[1]
        输出路径 = os.path.join(项目根, "output", f"成品_{os.path.splitext(os.path.basename(self._当前文件))[0]}{扩展名 if 扩展名 else '.mp4'}")

        self.开始钮.setEnabled(False)
        self.开始钮.setText("处理中…")
        self.日志框.clear()
        self.进度条.setValue(0)

        self._线程 = 处理线程(self._当前文件, 命令, 输出路径)
        self._线程.进度.connect(self._更新进度)
        self._线程.日志.connect(self._记录)
        self._线程.完成.connect(lambda r: self._处理完成(输出路径))
        self._线程.失败.connect(self._处理失败)
        self._线程.start()

    def _更新进度(self, 当前: int, 总数: int, 阶段: str):
        self.阶段标签.setText(阶段)
        if 总数 > 0:
            self.进度条.setValue(int(当前 / 总数 * 100))

    def _记录(self, 文本: str):
        self.日志框.appendPlainText(文本)

    def _处理完成(self, 输出路径: str):
        self.开始钮.setEnabled(True)
        self.开始钮.setText("开始消除")
        self.阶段标签.setText(f"完成！成品已保存到 output 文件夹")
        self._记录(f"全部完成 → {输出路径}")

        # 对比预览：图片直接显示；视频各抽首帧
        try:
            if self._当前文件.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                self._临时目录 = tempfile.mkdtemp(prefix="预览_")
                原帧 = os.path.join(self._临时目录, "原帧.png")
                成品帧 = os.path.join(self._临时目录, "成品帧.png")
                from app.video_io import _找ffmpeg
                subprocess.run([_找ffmpeg("ffmpeg"), "-y", "-i", self._当前文件, "-frames:v", "1", 原帧], capture_output=True)
                subprocess.run([_找ffmpeg("ffmpeg"), "-y", "-i", 输出路径, "-frames:v", "1", 成品帧], capture_output=True)
                self.预览.显示对比(原帧, 成品帧)
            else:
                self.预览.显示对比(self._当前文件, 输出路径)
        except Exception as e:
            self._记录(f"预览加载失败（不影响成品）：{e}")

    def _处理失败(self, 错误: str):
        self.开始钮.setEnabled(True)
        self.开始钮.setText("开始消除")
        self.阶段标签.setText("出错了，请查看日志")
        self._记录(f"错误：{错误}")
