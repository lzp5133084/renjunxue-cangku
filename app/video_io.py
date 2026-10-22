# -*- coding: utf-8 -*-
"""视频读写模块：封装 ffmpeg，负责抽帧、合成、保留原音频。

大白话：把视频拆成一张张图片交给 AI 处理，处理完再拼回视频，声音原样贴回。
"""
import json
import os
import subprocess


def _找ffmpeg(程序名: str) -> str:
    """优先用项目内置的便携版 ffmpeg，找不到再退回系统 PATH。"""
    项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    便携路径 = os.path.join(项目根, "runtime", "ffmpeg", "bin", f"{程序名}.exe")
    return 便携路径 if os.path.exists(便携路径) else 程序名


def 读取视频信息(视频路径: str) -> dict:
    """返回 {fps, 宽, 高, 总帧数, 时长秒}。"""
    命令 = [
        _找ffmpeg("ffprobe"), "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", 视频路径,
    ]
    结果 = subprocess.run(命令, capture_output=True, text=True, encoding="utf-8", errors="replace")
    信息 = json.loads(结果.stdout)
    视频流 = next(s for s in 信息["streams"] if s["codec_type"] == "video")

    分子, 分母 = 视频流["r_frame_rate"].split("/")
    帧率 = float(分子) / float(分母)
    return {
        "帧率": 帧率,
        "宽": int(视频流["width"]),
        "高": int(视频流["height"]),
        "总帧数": int(视频流.get("nb_frames") or round(float(信息["format"]["duration"]) * 帧率)),
        "时长秒": float(信息["format"]["duration"]),
    }


def 抽帧(视频路径: str, 帧目录: str) -> None:
    """把视频拆成 PNG 序列（无损，避免二次压缩干扰修复质量）。"""
    os.makedirs(帧目录, exist_ok=True)
    命令 = [
        _找ffmpeg("ffmpeg"), "-y", "-i", 视频路径,
        "-start_number", "0", os.path.join(帧目录, "%06d.png"),
    ]
    subprocess.run(命令, check=True, capture_output=True)


def 合成视频(帧目录: str, 帧率: float, 原视频: str, 输出路径: str) -> None:
    """把处理后的帧序列合成 MP4，并从原视频贴回音频（没有音频就静默跳过）。"""
    os.makedirs(os.path.dirname(输出路径), exist_ok=True)
    命令 = [
        _找ffmpeg("ffmpeg"), "-y",
        "-framerate", str(帧率), "-i", os.path.join(帧目录, "%06d.png"),
        "-i", 原视频,
        "-map", "0:v", "-map", "1:a?",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-shortest",
        输出路径,
    ]
    subprocess.run(命令, check=True, capture_output=True)
