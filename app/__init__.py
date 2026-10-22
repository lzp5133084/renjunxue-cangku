# -*- coding: utf-8 -*-
"""包初始化：统一设置模型缓存目录与国内镜像（先于任何第三方库导入执行）。"""
import os

_项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 模型缓存放项目 models 目录（实际经目录联接存在大容量盘）
os.environ.setdefault("HF_HOME", os.path.join(_项目根, "models"))
os.environ.setdefault("TORCH_HOME", os.path.join(_项目根, "models"))
# 国内 HuggingFace 镜像，模型下载更快更稳
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
