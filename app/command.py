# -*- coding: utf-8 -*-
"""中文命令解析：把「消除 女人」这类大白话指令翻译成检测模型能懂的英文提示词。"""
import re

# 动作词：用户可能用的各种说法
消除动词 = ("消除", "删除", "去掉", "移除", "擦除", "去除", "抹掉", "清楚")

# 内置目标词典：中文目标 → 英文提示词（GroundingDINO 只认英文）
# 用户可在此补充更多目标
目标词典 = {
    "女人": "woman",
    "男人": "man",
    "人": "person",
    "路人": "person",
    "行人": "person",
    "人群": "people",
    "猫": "cat",
    "狗": "dog",
    "鸟": "bird",
    "车": "car",
    "汽车": "car",
    "帽子": "hat",
    "头发": "hair",
    "眼镜": "glasses",
    "口罩": "mask",
    "文字": "text",
    "字幕": "subtitle",
    "水印": "watermark",
    "标志": "logo",
    "logo": "logo",
    "商标": "logo",
    "广告牌": "billboard",
    "桌子": "table",
    "椅子": "chair",
}


class 命令解析结果:
    def __init__(self, 动作: str, 目标中文: str, 目标英文: str, 未识别词: list):
        self.动作 = 动作
        self.目标中文 = 目标中文
        self.目标英文 = 目标英文  # 形如 "woman. hat." 的 GroundingDINO 提示串
        self.未识别词 = 未识别词  # 词典里没有的词，交给界面提示用户


def 解析命令(文本: str) -> 命令解析结果:
    """解析中文命令，返回动作与目标提示词。

    支持写法：「消除 女人」「删除女人和帽子」「去掉 女人, LOGO」。
    """
    文本 = 文本.strip()
    if not 文本:
        raise ValueError("命令不能为空，例如：消除 女人")

    动作 = None
    for v in 消除动词:
        if 文本.startswith(v):
            动作 = v
            剩余 = 文本[len(v):]
            break
    else:
        # 没有动作词时，默认按「消除」处理，整句都当目标
        动作 = "消除"
        剩余 = 文本

    # 按分隔符与连词切出多个目标
    词块 = [w for w in re.split(r"[，,、\s]+|和|与|以及", 剩余) if w]

    英文列表, 未识别, 中文列表 = [], [], []
    for 词 in 词块:
        词小写 = 词.lower()
        if 词 in 目标词典:
            英文列表.append(目标词典[词])
            中文列表.append(词)
        elif 词小写 in 目标词典:
            英文列表.append(目标词典[词小写])
            中文列表.append(词)
        elif re.fullmatch(r"[a-zA-Z\-\s]+", 词):
            # 用户直接输了英文，原样采用
            英文列表.append(词小写)
            中文列表.append(词)
        else:
            未识别.append(词)

    if not 英文列表 and not 未识别:
        raise ValueError("没有识别到要消除的目标，例如：消除 女人")

    # GroundingDINO 的提示串格式：类别之间用「. 」分隔
    提示串 = ". ".join(dict.fromkeys(英文列表))
    if 提示串:
        提示串 += "."

    return 命令解析结果(动作, "、".join(中文列表), 提示串, 未识别)


if __name__ == "__main__":
    # 简单自测
    for 样例 in ["消除 女人", "删除女人和帽子", "去掉 水印, 文字", "消除 女人 LOGO"]:
        r = 解析命令(样例)
        print(f"{样例} → 动作:{r.动作} 目标:{r.目标中文} 提示:{r.目标英文} 未识别:{r.未识别词}")
