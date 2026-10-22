# -*- coding: utf-8 -*-
"""目标定位模块：GroundingDINO 按文字描述找目标框，SAM 把框转成精确像素掩码。

大白话：第一个模型负责「看懂你要找什么并圈出大致位置」，
第二个模型负责「沿着目标边缘把轮廓抠得严丝合缝」。
"""
import os

# 模型缓存放项目 models 目录；国内走 hf-mirror 镜像加速下载
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np
import torch
from PIL import Image

检测模型名 = "IDEA-Research/grounding-dino-tiny"  # 约700MB，文字描述定位
分割模型名 = "facebook/sam-vit-base"               # 约375MB，框转精确轮廓


class 目标定位器:
    """组合 GroundingDINO（找框）+ SAM（抠轮廓）。"""

    def __init__(self, 设备: str = None, 检测阈值: float = 0.35, 文字阈值: float = 0.25):
        from transformers import AutoProcessor, GroundingDINOForObjectDetection, SamModel, SamProcessor

        self.设备 = 设备 or ("cuda" if torch.cuda.is_available() else "cpu")
        self.检测阈值 = 检测阈值
        self.文字阈值 = 文字阈值

        self.检测处理器 = AutoProcessor.from_pretrained(检测模型名)
        self.检测模型 = GroundingDINOForObjectDetection.from_pretrained(检测模型名).to(self.设备)
        self.检测模型.eval()

        self.分割处理器 = SamProcessor.from_pretrained(分割模型名)
        self.分割模型 = SamModel.from_pretrained(分割模型名).to(self.设备)
        self.分割模型.eval()

    @torch.no_grad()
    def 生成掩码(self, 图片: Image.Image, 提示串: str) -> np.ndarray:
        """输入 PIL 图片与英文提示串，返回 0/255 的掩码（255=需要抹掉的区域）。

        若没找到目标，返回全 0 掩码。
        """
        宽, 高 = 图片.size

        # 第一步：GroundingDINO 找目标框
        输入 = self.检测处理器(images=图片, text=提示串, return_tensors="pt").to(self.设备)
        输出 = self.检测模型(**输入)
        结果 = self.检测处理器.post_process_grounded_object_detection(
            输出, 输入["input_ids"],
            threshold=self.检测阈值, text_threshold=self.文字阈值,
            target_sizes=[(高, 宽)],
        )[0]

        if len(结果["boxes"]) == 0:
            return np.zeros((高, 宽), dtype=np.uint8)

        # 第二步：SAM 按框抠精确轮廓
        框列表 = 结果["boxes"].cpu().tolist()  # [[x1,y1,x2,y2], ...]
        分割输入 = self.分割处理器(图片, input_boxes=[框列表], return_tensors="pt").to(self.设备)
        分割输出 = self.分割模型(**分割输入)
        掩码组 = self.分割处理器.image_processor.post_process_masks(
            分割输出.pred_masks.cpu(),
            分割输入["original_sizes"].cpu(),
            分割输入["reshaped_input_sizes"].cpu(),
        )[0]  # 形状：[目标数, 候选掩码数, 高, 宽]

        # 取每个目标得分最高的那张掩码，再合并成一张总掩码
        得分 = 分割输出.iou_scores.cpu()[0]  # [目标数, 候选掩码数]
        最佳 = 得分.argmax(dim=1)
        总掩码 = np.zeros((高, 宽), dtype=bool)
        for i, idx in enumerate(最佳):
            总掩码 |= 掩码组[i, idx].numpy().astype(bool)

        return (总掩码 * 255).astype(np.uint8)


def 膨胀掩码(掩码: np.ndarray, 像素: int = 8) -> np.ndarray:
    """把掩码向外扩一圈，避免修复后留下目标边缘的残影。"""
    import cv2
    核 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (像素 * 2 + 1, 像素 * 2 + 1))
    return cv2.dilate(掩码, 核)
