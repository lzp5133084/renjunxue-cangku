# -*- coding: utf-8 -*-
"""
计时器核心逻辑模块
作者：军哥懂保
微信号：xunijiayuan

功能：
- 正计时（秒表模式）
- 倒计时模式
- 番茄钟模式（工作+休息循环）
- 暂停/恢复/重置
- 计时精度：毫秒级
"""

import time
from enum import Enum
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class TimerMode(Enum):
    """计时器模式枚举"""
    STOPWATCH = "stopwatch"      # 正计时/秒表
    COUNTDOWN = "countdown"      # 倒计时
    POMODORO = "pomodoro"        # 番茄钟


class TimerState(Enum):
    """计时器状态枚举"""
    IDLE = "idle"                # 空闲（未开始）
    RUNNING = "running"          # 运行中
    PAUSED = "paused"            # 暂停
    FINISHED = "finished"        # 已完成


class PomodoroPhase(Enum):
    """番茄钟阶段"""
    WORK = "work"                # 工作阶段
    SHORT_BREAK = "short_break"  # 短休息
    LONG_BREAK = "long_break"    # 长休息


class TimerCore(QObject):
    """
    计时器核心类
    负责所有计时逻辑，通过信号通知UI更新
    """

    # ===== 信号定义 =====
    tick = pyqtSignal(str)           # 每秒/每tick更新时间显示
    state_changed = pyqtSignal(str)  # 状态变化
    mode_changed = pyqtSignal(str)   # 模式变化
    phase_changed = pyqtSignal(str)  # 番茄钟阶段变化
    finished = pyqtSignal()          # 计时结束
    lap_recorded = pyqtSignal(float, str)  # 秒表计次记录

    def __init__(self, parent=None):
        super().__init__(parent)

        # ===== 当前状态 =====
        self.mode = TimerMode.STOPWATCH
        self.state = TimerState.IDLE
        self.pomodoro_phase = PomodoroPhase.WORK

        # ===== 时间变量 =====
        self._start_time = 0.0       # 开始时刻
        self._elapsed = 0.0          # 已过时间（秒）
        self._remaining = 0.0        # 剩余时间（倒计时）
        self._total_duration = 0.0   # 总时长（用于进度条）

        # ===== 番茄钟配置 =====
        self.pomodoro_work = 25 * 60        # 工作25分钟
        self.pomodoro_short_break = 5 * 60  # 短休息5分钟
        self.pomodoro_long_break = 15 * 60  # 长休息15分钟
        self.pomodoro_cycles_before_long = 4  # 4个工作周期后长休息
        self.pomodoro_current_cycle = 0      # 当前工作周期数

        # ===== 计次记录（秒表）=====
        self.laps = []  # [(累计时间, 间隔时间), ...]

        # ===== Qt定时器 =====
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(50)  # 50ms更新一次，保证流畅
        self._qt_timer.timeout.connect(self._on_tick)

    # ==================== 模式切换 ====================

    def set_mode(self, mode: TimerMode):
        """切换计时模式"""
        if self.state == TimerState.RUNNING:
            self.stop()
        self.mode = mode
        self.state = TimerState.IDLE
        self._elapsed = 0.0
        self._remaining = 0.0
        self.laps = []
        self.pomodoro_current_cycle = 0

        if mode == TimerMode.COUNTDOWN:
            self._total_duration = self._remaining if self._remaining > 0 else 600  # 默认10分钟
        elif mode == TimerMode.POMODORO:
            self.pomodoro_phase = PomodoroPhase.WORK
            self._total_duration = self.pomodoro_work
            self._remaining = self.pomodoro_work

        self.mode_changed.emit(mode.value)
        self.state_changed.emit(self.state.value)
        self.tick.emit(self.format_time(self._get_display_seconds()))

    def set_countdown_duration(self, seconds: float):
        """设置倒计时时长（秒）"""
        if self.mode != TimerMode.COUNTDOWN:
            self.set_mode(TimerMode.COUNTDOWN)
        self._total_duration = seconds
        self._remaining = seconds
        self._elapsed = 0.0
        self.state = TimerState.IDLE
        self.state_changed.emit(self.state.value)
        self.tick.emit(self.format_time(seconds))

    def set_pomodoro_config(self, work_min=25, short_break_min=5, long_break_min=15, cycles_before_long=4):
        """设置番茄钟参数"""
        self.pomodoro_work = work_min * 60
        self.pomodoro_short_break = short_break_min * 60
        self.pomodoro_long_break = long_break_min * 60
        self.pomodoro_cycles_before_long = cycles_before_long
        if self.mode == TimerMode.POMODORO and self.state == TimerState.IDLE:
            self._total_duration = self.pomodoro_work
            self._remaining = self.pomodoro_work
            self.tick.emit(self.format_time(self._remaining))

    # ==================== 控制方法 ====================

    def start(self):
        """开始计时"""
        if self.state == TimerState.RUNNING:
            return

        if self.state == TimerState.IDLE:
            # 全新开始
            if self.mode == TimerMode.STOPWATCH:
                self._start_time = time.time()
                self._elapsed = 0.0
            elif self.mode == TimerMode.COUNTDOWN:
                if self._remaining <= 0:
                    self._remaining = self._total_duration if self._total_duration > 0 else 600
                self._start_time = time.time()
            elif self.mode == TimerMode.POMODORO:
                self._start_time = time.time()

        elif self.state == TimerState.PAUSED:
            # 从暂停恢复 - 调整start_time补偿已过时间
            self._start_time = time.time() - self._elapsed

        self.state = TimerState.RUNNING
        self._qt_timer.start()
        self.state_changed.emit(self.state.value)

    def pause(self):
        """暂停计时"""
        if self.state != TimerState.RUNNING:
            return

        self._qt_timer.stop()
        # 保存当前已过时间
        if self.mode == TimerMode.STOPWATCH:
            self._elapsed = time.time() - self._start_time
        else:
            self._elapsed += time.time() - self._start_time
            self._remaining = max(0, self._total_duration - self._elapsed)

        self.state = TimerState.PAUSED
        self.state_changed.emit(self.state.value)
        self.tick.emit(self.format_time(self._get_display_seconds()))

    def stop(self):
        """停止计时（保留当前时间，不重置）"""
        self._qt_timer.stop()
        if self.state == TimerState.RUNNING:
            if self.mode == TimerMode.STOPWATCH:
                self._elapsed = time.time() - self._start_time
            else:
                self._elapsed += time.time() - self._start_time
                self._remaining = max(0, self._total_duration - self._elapsed)
        self.state = TimerState.IDLE
        self.state_changed.emit(self.state.value)

    def reset(self):
        """重置计时"""
        self._qt_timer.stop()
        self._elapsed = 0.0
        self.state = TimerState.IDLE
        self.laps = []

        if self.mode == TimerMode.STOPWATCH:
            self._remaining = 0.0
        elif self.mode == TimerMode.COUNTDOWN:
            self._remaining = self._total_duration
        elif self.mode == TimerMode.POMODORO:
            self.pomodoro_phase = PomodoroPhase.WORK
            self.pomodoro_current_cycle = 0
            self._total_duration = self.pomodoro_work
            self._remaining = self.pomodoro_work
            self.phase_changed.emit(self.pomodoro_phase.value)

        self.state_changed.emit(self.state.value)
        self.tick.emit(self.format_time(self._get_display_seconds()))

    def lap(self):
        """秒表计次"""
        if self.mode != TimerMode.STOPWATCH or self.state == TimerState.IDLE:
            return
        current_elapsed = time.time() - self._start_time
        if self.laps:
            interval = current_elapsed - self.laps[-1][0]
        else:
            interval = current_elapsed
        self.laps.append((current_elapsed, interval))
        self.lap_recorded.emit(current_elapsed, self.format_time(interval))

    # ==================== 内部更新 ====================

    def _on_tick(self):
        """定时器tick回调"""
        if self.mode == TimerMode.STOPWATCH:
            self._elapsed = time.time() - self._start_time
            display = self._elapsed
        else:
            self._elapsed = time.time() - self._start_time
            self._remaining = max(0, self._total_duration - self._elapsed)
            display = self._remaining

            # 倒计时/番茄钟结束检测
            if self._remaining <= 0:
                self._handle_finish()
                return

        self.tick.emit(self.format_time(display))

    def _handle_finish(self):
        """计时结束处理"""
        self._qt_timer.stop()

        if self.mode == TimerMode.POMODORO:
            # 番茄钟阶段切换
            if self.pomodoro_phase == PomodoroPhase.WORK:
                self.pomodoro_current_cycle += 1
                if self.pomodoro_current_cycle >= self.pomodoro_cycles_before_long:
                    self.pomodoro_phase = PomodoroPhase.LONG_BREAK
                    self._total_duration = self.pomodoro_long_break
                    self.pomodoro_current_cycle = 0
                else:
                    self.pomodoro_phase = PomodoroPhase.SHORT_BREAK
                    self._total_duration = self.pomodoro_short_break
            else:
                self.pomodoro_phase = PomodoroPhase.WORK
                self._total_duration = self.pomodoro_work

            self._elapsed = 0.0
            self._remaining = self._total_duration
            self._start_time = time.time()
            self.phase_changed.emit(self.pomodoro_phase.value)
            self.finished.emit()
            # 自动开始下一阶段
            self._qt_timer.start()
        else:
            self.state = TimerState.FINISHED
            self.state_changed.emit(self.state.value)
            self.finished.emit()

    # ==================== 工具方法 ====================

    def _get_display_seconds(self) -> float:
        """获取当前应显示的秒数"""
        if self.mode == TimerMode.STOPWATCH:
            return self._elapsed
        return self._remaining

    @staticmethod
    def format_time(seconds: float) -> str:
        """将秒数格式化为 HH:MM:SS.ms"""
        seconds = max(0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 100)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def format_time_with_ms(seconds: float) -> str:
        """将秒数格式化为 HH:MM:SS.ms（带毫秒）"""
        seconds = max(0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 100)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:02d}"
        return f"{m:02d}:{s:02d}.{ms:02d}"

    def get_progress(self) -> float:
        """获取当前进度 0.0 - 1.0"""
        if self._total_duration <= 0:
            return 0.0
        if self.mode == TimerMode.STOPWATCH:
            # 秒表没有总进度，返回0
            return 0.0
        return min(1.0, self._elapsed / self._total_duration)

    # ==================== 持久化 ====================

    def get_state_dict(self) -> dict:
        """获取状态字典（用于保存）"""
        return {
            "mode": self.mode.value,
            "state": self.state.value,
            "pomodoro_phase": self.pomodoro_phase.value,
            "elapsed": self._elapsed,
            "remaining": self._remaining,
            "total_duration": self._total_duration,
            "pomodoro_work": self.pomodoro_work,
            "pomodoro_short_break": self.pomodoro_short_break,
            "pomodoro_long_break": self.pomodoro_long_break,
            "pomodoro_cycles_before_long": self.pomodoro_cycles_before_long,
            "pomodoro_current_cycle": self.pomodoro_current_cycle,
        }

    def restore_state(self, data: dict):
        """从字典恢复状态"""
        try:
            self.mode = TimerMode(data.get("mode", "stopwatch"))
            self.pomodoro_phase = PomodoroPhase(data.get("pomodoro_phase", "work"))
            self._elapsed = data.get("elapsed", 0)
            self._remaining = data.get("remaining", 0)
            self._total_duration = data.get("total_duration", 0)
            self.pomodoro_work = data.get("pomodoro_work", 1500)
            self.pomodoro_short_break = data.get("pomodoro_short_break", 300)
            self.pomodoro_long_break = data.get("pomodoro_long_break", 900)
            self.pomodoro_cycles_before_long = data.get("pomodoro_cycles_before_long", 4)
            self.pomodoro_current_cycle = data.get("pomodoro_current_cycle", 0)
            self.state = TimerState.IDLE
            self.tick.emit(self.format_time(self._get_display_seconds()))
        except Exception:
            pass
