# -*- coding: utf-8 -*-
"""总流水线：抽帧 → 逐帧「定位→掩码→修复」→ 合成回视频。

界面和命令行都调这里；进度通过回调函数往外抛，方便界面显示进度条。
"""
import glob
import os
import shutil
import tempfile

import cv2
from PIL import Image

from .command import 解析命令
from .detector import 目标定位器, 膨胀掩码
from .inpainter import 背景修复器
from .video_io import 读取视频信息, 抽帧, 合成视频


def 消除图片(图片路径: str, 输出路径: str, 命令文本: str,
             定位器: 目标定位器 = None, 修复器: 背景修复器 = None) -> dict:
    """单张图片消除（V0.1 验证用）。返回统计信息。"""
    命令 = 解析命令(命令文本)
    定位器 = 定位器 or 目标定位器()
    修复器 = 修复器 or 背景修复器()

    图片 = Image.open(图片路径).convert("RGB")
    掩码 = 定位器.生成掩码(图片, 命令.目标英文)
    掩码 = 膨胀掩码(掩码, 像素=8)

    图bgr = cv2.imread(图片路径)
    结果 = 修复器.修复(图bgr, 掩码)

    os.makedirs(os.path.dirname(输出路径), exist_ok=True)
    cv2.imwrite(输出路径, 结果)

    return {
        "命令": 命令,
        "掩码覆盖率": float((掩码 > 0).mean()),
        "输出": 输出路径,
    }


def 消除视频(视频路径: str, 输出路径: str, 命令文本: str,
             进度回调=None, 日志回调=None) -> dict:
    """整段视频消除。进度回调签名：(当前帧, 总帧数, 阶段文字)。"""
    命令 = 解析命令(命令文本)

    def 日志(文本):
        if 日志回调:
            日志回调(文本)

    日志(f"开始解析命令：{命令.动作} {命令.目标中文}（提示词：{命令.目标英文 or '无'}）")
    if 命令.未识别词:
        日志(f"提示：{'、'.join(命令.未识别词)} 不在内置词典，本次忽略")

    信息 = 读取视频信息(视频路径)
    日志(f"视频信息：{信息['宽']}x{信息['高']} @ {信息['帧率']:.2f}fps，共约 {信息['总帧数']} 帧")

    临时根 = tempfile.mkdtemp(prefix="消除_")
    原帧目录 = os.path.join(临时根, "原帧")
    成品帧目录 = os.path.join(临时根, "成品帧")

    try:
        if 进度回调:
            进度回调(0, 100, "正在抽帧…")
        抽帧(视频路径, 原帧目录)

        帧列表 = sorted(glob.glob(os.path.join(原帧目录, "*.png")))
        总帧数 = len(帧列表)
        if 总帧数 == 0:
            raise RuntimeError("抽帧结果为空，请确认视频能正常播放")

        日志("正在加载 AI 模型（首次运行需下载，请耐心等待）…")
        定位器 = 目标定位器()
        修复器 = 背景修复器()
        日志(f"模型就绪，运行设备：{定位器.设备}")

        os.makedirs(成品帧目录, exist_ok=True)
        for 序号, 帧路径 in enumerate(帧列表):
            图片 = Image.open(帧路径).convert("RGB")
            掩码 = 膨胀掩码(定位器.生成掩码(图片, 命令.目标英文), 像素=8)
            图bgr = cv2.imread(帧路径)
            结果 = 修复器.修复(图bgr, 掩码)
            cv2.imwrite(os.path.join(成品帧目录, os.path.basename(帧路径)), 结果)

            if 进度回调:
                进度回调(序号 + 1, 总帧数, f"正在修复第 {序号 + 1}/{总帧数} 帧")

        if 进度回调:
            进度回调(总帧数, 总帧数, "正在合成视频…")
        合成视频(成品帧目录, 信息["帧率"], 视频路径, 输出路径)
        日志(f"完成！成品：{输出路径}")

        return {"输出": 输出路径, "总帧数": 总帧数, "命令": 命令}
    finally:
        shutil.rmtree(临时根, ignore_errors=True)
