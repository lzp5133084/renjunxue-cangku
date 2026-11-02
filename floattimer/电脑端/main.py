# -*- coding: utf-8 -*-
"""
悬浮计时器 - 主入口
作者：军哥懂保
微信号：xunijiayuan

整合模块：
- TimerCore: 计时器核心逻辑
- FloatingBall: 悬浮球UI
- MainPanel: 主面板UI
- SystemTray: 系统托盘
- SoundManager: 声音管理
"""

import sys
import os
import json
import threading

# 确保电脑端目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtWidgets import QApplication, QMessageBox

from timer_core import TimerCore, TimerMode, TimerState, PomodoroPhase
from floating_ball import FloatingBall
from main_panel import MainPanel, NameDialog, ShareDialog, AdDialog
from system_tray import SystemTray
from sound_manager import SoundManager

# ============ 版本信息 ============
CURRENT_VERSION = "1.0.4"
CURRENT_VERSION_CODE = 5
VERSION_CHECK_URL = "https://ecojia.cn/timer/version.json"


class TimerApp:
    """计时器主应用类"""

    MODE_ICONS = {
        "stopwatch": "⏱",
        "countdown": "⏳",
        "pomodoro": "🍅",
    }

    def __init__(self):
        # ===== Qt应用 =====
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 关闭主窗口不退出

        # ===== 核心模块 =====
        self.timer = TimerCore()
        self.sound = SoundManager()

        # ===== UI模块 =====
        self.main_panel = MainPanel()
        self.floating_ball = FloatingBall()
        self.tray = SystemTray(self.app)

        # ===== 面板显示状态 =====
        self.panel_visible = True

        # ===== 正计时到时提醒标记（提醒过一次后置True，重置时清除）=====
        self._reminded = False
        # ===== 倒计时结束前提醒标记（提醒过一次后置True，重置时清除）=====
        self._pre_alerted = False

        # ===== 初始化 =====
        self._setup_connections()
        self._setup_initial_state()
        # 面板默认倒计时模式，同步给计时核心
        self._on_panel_mode_changed(self.main_panel._current_mode)

    def _setup_connections(self):
        """连接所有信号"""

        # ===== TimerCore 信号 =====
        self.timer.tick.connect(self._on_tick)
        self.timer.state_changed.connect(self._on_state_changed)
        self.timer.mode_changed.connect(self._on_mode_changed)
        self.timer.phase_changed.connect(self._on_phase_changed)
        self.timer.finished.connect(self._on_finished)
        self.timer.lap_recorded.connect(self._on_lap_recorded)

        # ===== MainPanel 信号 =====
        self.main_panel.start_requested.connect(self._start_timer)
        self.main_panel.pause_requested.connect(self._pause_timer)
        self.main_panel.stop_requested.connect(self._stop_timer)
        self.main_panel.reset_requested.connect(self._reset_timer)
        self.main_panel.lap_requested.connect(self._lap_timer)
        self.main_panel.quit_requested.connect(self._quit_app)
        self.main_panel.mode_changed.connect(self._on_panel_mode_changed)
        self.main_panel.preset_changed.connect(self._on_preset_changed)

        # ===== FloatingBall 信号 =====
        self.floating_ball.double_clicked.connect(self._toggle_panel)
        self.floating_ball.menu_show_panel.connect(self._show_panel)
        self.floating_ball.menu_start.connect(self._start_timer)
        self.floating_ball.menu_pause.connect(self._pause_timer)
        self.floating_ball.menu_reset.connect(self._reset_timer)
        self.floating_ball.menu_repeat.connect(self._repeat_timer)
        self.floating_ball.menu_share.connect(self._show_share_dialog)
        self.floating_ball.menu_quit.connect(self._quit_app)

        # ===== SystemTray 回调 =====
        self.tray.on_show_panel = self._toggle_panel
        self.tray.on_start = self._start_timer
        self.tray.on_pause = self._pause_timer
        self.tray.on_reset = self._reset_timer
        self.tray.on_check_update = self._check_update
        self.tray.on_quit = self._quit_app

    def _setup_initial_state(self):
        """初始化状态"""
        # 位置：悬浮球右下角，主面板右侧
        screen = self.app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.floating_ball.move(geo.right() - 90, geo.bottom() - 90)
            self.main_panel.move(geo.right() - 560, geo.center().y() - 360)

        # 显示托盘
        self.tray.show()

        # 初始UI更新
        mode_icon = self.MODE_ICONS.get(self.timer.mode.value, "⏱")
        self.floating_ball.update_mode(mode_icon)
        self.floating_ball.update_time("00:00")
        self.tray.set_tooltip("悬浮计时器 - 就绪")

        # 显示悬浮球
        self.floating_ball.show()

        # 默认显示主面板
        self._show_panel()

        # 启动2秒后后台检查更新（不阻塞UI）
        QTimer.singleShot(2000, self._check_update)
        # 启动1.5秒后尝试加载广告（后台拉取配置，失败静默跳过）
        QTimer.singleShot(1500, self._show_ad_if_needed)

    # ==================== 槽函数 ====================

    def _on_tick(self, time_text: str):
        """时间tick"""
        self.main_panel.update_time_display(time_text, self.timer.state.value)
        self.floating_ball.update_time(time_text)

        # 正计时到时提醒（到时提醒一次，计时不中断；重置后可再次提醒）
        if (
            self.timer.mode == TimerMode.STOPWATCH
            and self.timer.state == TimerState.RUNNING
            and not self._reminded
            and self.main_panel.is_remind_enabled()
            and self.timer._elapsed >= self.main_panel.get_remind_seconds()
        ):
            self._reminded = True
            self.sound.play_finish()
            self.tray.show_message("⏰ 到时提醒", "正计时已到达设定时间！")

        # 倒计时结束前语音提醒（剩余 N 秒时播报一次，仅提醒不打断；重置后可再次触发）
        if (
            self.timer.mode != TimerMode.STOPWATCH
            and self.timer.state == TimerState.RUNNING
            and not self._pre_alerted
            and self.main_panel.is_pre_alert_enabled()
        ):
            sec = self.main_panel.get_pre_alert_seconds()
            remaining = self.timer._remaining
            if 0 < remaining <= sec:
                self._pre_alerted = True
                self.sound.play_pre_alert()
                self.sound.speak(f"还剩 {int(round(remaining))} 秒")

        # 更新进度（倒计时和番茄钟模式）
        if self.timer.mode != TimerMode.STOPWATCH:
            progress = self.timer.get_progress()
            self.main_panel.update_progress(progress)
            self.floating_ball.set_progress(progress)

        # 更新托盘图标文字（显示剩余分钟数）
        if self.timer.mode != TimerMode.STOPWATCH:
            remaining_min = int(self.timer._remaining // 60)
            if remaining_min > 99:
                remaining_min = "99+"
            text = f"{remaining_min}" if isinstance(remaining_min, int) else remaining_min
            self.tray.update_icon_with_text(text, self.timer.state == TimerState.RUNNING)

    def _on_state_changed(self, state: str):
        """状态变化"""
        self.main_panel.update_main_button(state)
        is_running = state == "running"
        self.floating_ball.set_running(is_running)

        if state == "running":
            self.sound.play_start()
        elif state == "paused":
            self.sound.play_pause()
            self.tray.set_tooltip("悬浮计时器 - 已暂停")
        elif state == "idle":
            self.tray.set_tooltip("悬浮计时器 - 就绪")
        elif state == "finished":
            self.tray.set_tooltip("悬浮计时器 - 已完成")

    def _on_mode_changed(self, mode: str):
        """模式变化"""
        icon = self.MODE_ICONS.get(mode, "⏱")
        self.floating_ball.update_mode(icon)

    def _on_phase_changed(self, phase: str):
        """番茄钟阶段变化"""
        self.main_panel.update_phase(phase)

    def _on_finished(self):
        """计时结束"""
        if self.timer.mode == TimerMode.POMODORO:
            self.sound.play_pomodoro_switch()
        else:
            self.sound.play_finish()
            self.sound.speak("时间到，计时结束")
            self.tray.show_message(
                "⏰ 计时结束！",
                "时间到啦！休息一下吧～",
            )
            # 开启命名弹窗：用户自定义命名；关闭：自动以当前时间命名保存
            if self.main_panel.is_name_prompt_enabled():
                self._prompt_save_record()
            else:
                self._auto_save_record()

    def _on_preset_changed(self):
        """预设时间/参数被修改 - 空闲时立即联动刷新时间显示"""
        if self.timer.state != TimerState.IDLE:
            return
        if self.timer.mode == TimerMode.COUNTDOWN:
            self.timer.set_countdown_duration(self.main_panel.get_countdown_seconds())
        elif self.timer.mode == TimerMode.POMODORO:
            config = self.main_panel.get_pomodoro_config()
            self.timer.set_pomodoro_config(**config)

    def _auto_save_record(self, mode_text=None, duration_text=None):
        """关闭命名弹窗时：自动以当前时间命名保存记录"""
        from datetime import datetime
        if mode_text is None or duration_text is None:
            if self.timer.mode == TimerMode.COUNTDOWN:
                mode_text = "倒计时"
                duration_text = TimerCore.format_time(self.timer._total_duration)
            else:
                mode_text = "正计时"
                duration_text = TimerCore.format_time(self.timer._elapsed)
        name = f"计时 {datetime.now().strftime('%m-%d %H:%M')}"
        self.main_panel.add_history(name, mode_text, duration_text)

    def _prompt_save_record(self, mode_text=None, duration_text=None):
        """弹出深色科技风命名框，让用户为本次计时命名保存"""
        if mode_text is None or duration_text is None:
            if self.timer.mode == TimerMode.COUNTDOWN:
                mode_text = "倒计时"
                duration_text = TimerCore.format_time(self.timer._total_duration)
            else:
                mode_text = "正计时"
                duration_text = TimerCore.format_time(self.timer._elapsed)

        dlg = NameDialog(self.main_panel, mode_text, duration_text)
        # 居中显示到主面板
        geo = self.main_panel.frameGeometry()
        dlg.move(geo.center().x() - dlg.width() // 2,
                 geo.center().y() - dlg.sizeHint().height() // 2)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        if dlg.exec() and dlg.record_name:
            self.main_panel.add_history(dlg.record_name, mode_text, duration_text)

    def _on_lap_recorded(self, total: float, interval_text: str):
        """秒表计次"""
        self.main_panel.add_lap(total, interval_text)

    def _on_panel_mode_changed(self, mode: str):
        """面板切换模式"""
        mode_map = {
            "stopwatch": TimerMode.STOPWATCH,
            "countdown": TimerMode.COUNTDOWN,
            "pomodoro": TimerMode.POMODORO,
        }
        timer_mode = mode_map.get(mode)
        if timer_mode:
            if timer_mode == TimerMode.COUNTDOWN:
                seconds = self.main_panel.get_countdown_seconds()
                self.timer.set_countdown_duration(seconds)
            elif timer_mode == TimerMode.POMODORO:
                config = self.main_panel.get_pomodoro_config()
                self.timer.set_pomodoro_config(**config)
                self.timer.set_mode(timer_mode)
            else:
                self.timer.set_mode(timer_mode)

    # ==================== 控制方法 ====================

    def _start_timer(self):
        """开始/继续计时"""
        # 从面板读取设置
        if self.timer.mode == TimerMode.COUNTDOWN and self.timer.state == TimerState.IDLE:
            seconds = self.main_panel.get_countdown_seconds()
            self.timer.set_countdown_duration(seconds)
        elif self.timer.mode == TimerMode.POMODORO and self.timer.state == TimerState.IDLE:
            config = self.main_panel.get_pomodoro_config()
            self.timer.set_pomodoro_config(**config)

        self.timer.start()

    def _pause_timer(self):
        """暂停计时"""
        self.timer.pause()

    def _stop_timer(self):
        """停止（结束）本次计时：开启命名保存且有效时长时先弹窗保存，再归零"""
        if self.timer.state not in (TimerState.RUNNING, TimerState.PAUSED):
            return
        elapsed = self.timer._elapsed   # 三模式下均为本次已进行秒数
        if elapsed > 1:
            mode_map = {
                TimerMode.STOPWATCH: "正计时",
                TimerMode.COUNTDOWN: "倒计时",
                TimerMode.POMODORO: "番茄钟",
            }
            mode_text = mode_map.get(self.timer.mode, "计时")
            duration_text = TimerCore.format_time(elapsed)
            # 开启命名弹窗：用户自定义命名；关闭：自动以当前时间命名保存
            if self.main_panel.is_name_prompt_enabled():
                self._prompt_save_record(mode_text, duration_text)
            else:
                self._auto_save_record(mode_text, duration_text)
        self.sound.play_reset()
        self.timer.reset()
        self.floating_ball.set_progress(0.0)
        self.tray.update_icon_with_text("⏱", False)

    def _reset_timer(self):
        """重置计时（仅清零显示，不触发命名保存；保存请用停止按钮）"""
        self._reminded = False
        self._pre_alerted = False
        self.sound.play_reset()
        self.timer.reset()
        self.floating_ball.set_progress(0.0)
        self.tray.update_icon_with_text("⏱", False)

    def _repeat_timer(self):
        """重复上次计时：按当前模式与预设重置并立即开始"""
        self._reminded = False
        self._pre_alerted = False
        self.timer.reset()
        self.floating_ball.set_progress(0.0)
        self.tray.update_icon_with_text("⏱", False)
        self._start_timer()

    def _show_share_dialog(self):
        """显示分享有奖弹窗"""
        dlg = ShareDialog(self.main_panel)
        dlg.exec()

    def _lap_timer(self):
        """秒表计次"""
        self.timer.lap()

    def _toggle_panel(self):
        """切换主面板显示"""
        if self.panel_visible:
            self._hide_panel()
        else:
            self._show_panel()

    def _show_panel(self):
        """显示主面板"""
        self.main_panel.show()
        self.main_panel.raise_()
        self.panel_visible = True

    def _hide_panel(self):
        """隐藏主面板"""
        self.main_panel.hide()
        self.panel_visible = False

    def _quit_app(self):
        """退出应用"""
        reply = QMessageBox.question(
            None, "退出确认",
            "确定要退出悬浮计时器吗？\n所有计时数据将丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 保存配置
            self.main_panel.save_config()
            # 停止计时器
            self.timer.stop()
            # 隐藏托盘
            self.tray.hide()
            # 退出
            self.app.quit()

    # ==================== 版本检查 ====================

    def _check_update(self):
        """后台线程检查更新，网络请求不阻塞UI"""
        def worker():
            try:
                import urllib.request
                req = urllib.request.Request(
                    VERSION_CHECK_URL,
                    headers={'User-Agent': 'FloatTimer/1.0'}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                desktop = data.get('desktop', {})
                if desktop.get('versionCode', 0) > CURRENT_VERSION_CODE:
                    # 回主线程弹框
                    QTimer.singleShot(0, lambda: self._show_update_dialog(desktop))
            except Exception:
                pass  # 网络异常静默处理，不打扰用户

        threading.Thread(target=worker, daemon=True).start()

    def _show_update_dialog(self, info: dict):
        """在主线程显示更新对话框"""
        version_name = info.get('versionName', '?')
        update_log = info.get('updateLog', '')
        download_url = info.get('downloadUrl', '')

        msg = QMessageBox(self.main_panel)
        msg.setWindowTitle("发现新版本")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"🎉 发现新版本 v{version_name}")
        msg.setInformativeText(f"更新内容：\n{update_log}")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.button(QMessageBox.StandardButton.Yes).setText("立即下载")
        msg.button(QMessageBox.StandardButton.No).setText("稍后")
        if msg.exec() == QMessageBox.StandardButton.Yes and download_url:
            QDesktopServices.openUrl(QUrl(download_url))

    def _show_ad_if_needed(self):
        """后台拉取广告配置，有广告则弹窗播放（失败/无广告静默跳过，不干扰使用）"""
        def worker():
            try:
                import urllib.request
                req = urllib.request.Request(
                    AdDialog.AD_CONFIG_URL,
                    headers={'User-Agent': 'FloatTimer/1.0'}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    config = json.loads(resp.read().decode('utf-8'))
                if not config or not config.get('enabled') or not config.get('video'):
                    return
                QTimer.singleShot(0, lambda: self._open_ad_dialog(config))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _open_ad_dialog(self, config: dict):
        dlg = AdDialog(self.main_panel, config)
        dlg.exec()

    # ==================== 运行 ====================

    def run(self):
        """运行应用"""
        return self.app.exec()


def main():
    app = TimerApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
