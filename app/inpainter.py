# -*- coding: utf-8 -*-
"""背景修复模块：调用 LaMa 模型，把掩码区域抹掉并补全出自然的背景。

大白话：把「被抠空的洞」交给它，它参考周围画面把洞填得看不出痕迹。
"""
import os

os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np
import torch


class 背景修复器:
    """封装 IOPaint 的 LaMa 模型。"""

    def __init__(self, 设备: str = None):
        from iopaint.model_manager import ModelManager

        self.设备 = 设备 or ("cuda" if torch.cuda.is_available() else "cpu")
        self.模型 = ModelManager(name="lama", device=torch.device(self.设备))

    def 修复(self, 图片bgr: np.ndarray, 掩码: np.ndarray) -> np.ndarray:
        """输入 cv2 BGR 图片与 0/255 掩码（255=要抹掉），返回修复后的 BGR 图片。

        掩码为空（没有目标）时直接返回原图，避免无谓计算。
        """
        if 掩码 is None or int(掩码.max()) == 0:
            return 图片bgr

        from iopaint.schema import InpaintRequest
        return self.模型(图片bgr, 掩码, InpaintRequest())
