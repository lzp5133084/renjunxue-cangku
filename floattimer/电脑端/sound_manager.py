# -*- coding: utf-8 -*-
"""
声音管理模块
作者：军哥懂保
微信号：xunijiayuan

功能：
- 计时结束提醒音（系统蜂鸣 + 可选自定义）
- 番茄钟阶段切换提示音
- 开始/暂停操作反馈音
"""

import sys
import threading
from PyQt6.QtCore import QObject
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl


class SoundManager(QObject):
    """
    声音管理器
    优先使用系统声音，Windows下调用winsound
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.volume = 0.5

    def set_enabled(self, enabled: bool):
        """开关声音"""
        self.enabled = enabled

    def set_volume(self, volume: float):
        """设置音量 0.0-1.0"""
        self.volume = max(0.0, min(1.0, volume))

    def _system_beep(self, frequency: int = 880, duration: int = 200):
        """系统蜂鸣"""
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(frequency, duration)
            elif sys.platform == "darwin":
                # macOS用系统命令
                import subprocess
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
        except Exception:
            pass

    def play_start(self):
        """开始计时 - 清脆短音"""
        if not self.enabled:
            return
        self._system_beep(880, 100)

    def play_pause(self):
        """暂停 - 柔和短音"""
        if not self.enabled:
            return
        self._system_beep(660, 100)

    def play_reset(self):
        """重置 - 低沉短音"""
        if not self.enabled:
            return
        self._system_beep(440, 150)

    def play_finish(self):
        """计时结束 - 两组三连音（加长，避免一次响完听不到）"""
        if not self.enabled:
            return
        pattern = [
            (1047, 250), (1319, 250), (1568, 550),
            (1047, 250), (1319, 250), (1568, 700),
        ]
        self._play_pattern(pattern)

    def play_pre_alert(self):
        """结束前提醒 - 两声上扬短音"""
        if not self.enabled:
            return
        self._play_pattern([(880, 180), (1175, 240)])

    def _play_pattern(self, pattern):
        """后台线程逐个播放蜂鸣，避免 time.sleep 卡住界面"""
        def run():
            try:
                import time
                for freq, dur in pattern:
                    self._system_beep(freq, dur)
                    time.sleep(dur / 1000.0 + 0.06)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def speak(self, text: str):
        """用 Windows 系统语音（System.Speech）播报中文，后台执行不阻塞界面"""
        if not self.enabled or not text:
            return

        def run():
            try:
                import base64
                import subprocess
                if sys.platform != "win32":
                    return
                safe = text.replace("'", "''")
                script = (
                    "Add-Type -AssemblyName System.Speech;"
                    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                    "$s.Volume = 100; $s.Rate = 1;"
                    f"$s.Speak('{safe}');"
                )
                encoded = base64.b64encode(
                    script.encode("utf-16-le")
                ).decode("ascii")
                subprocess.run(
                    ["powershell", "-NoProfile", "-EncodedCommand", encoded],
                    capture_output=True,
                    timeout=20,
                )
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play_pomodoro_switch(self):
        """番茄钟切换阶段 - 双音"""
        if not self.enabled:
            return
        self._system_beep(784, 150)  # G4
        import time
        time.sleep(0.1)
        self._system_beep(988, 300)  # B4
