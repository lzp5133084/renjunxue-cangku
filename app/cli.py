# -*- coding: utf-8 -*-
"""命令行入口（V0.1 验证用）：
python -m app.cli 图片模式 --图 input/test.jpg --命令 "消除 女人" --输出 output/结果.png
python -m app.cli 视频模式 --视频 input/test.mp4 --命令 "消除 女人" --输出 output/结果.mp4
"""
import argparse
import os
import sys

# 允许用 python app/cli.py 直接跑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline import 消除图片, 消除视频


def main():
    解析器 = argparse.ArgumentParser(description="AI 消除命令行")
    解析器.add_argument("模式", choices=["图片模式", "视频模式"])
    解析器.add_argument("--图", dest="图片路径")
    解析器.add_argument("--视频", dest="视频路径")
    解析器.add_argument("--命令", required=True, help='如 "消除 女人"')
    解析器.add_argument("--输出", required=True)
    参数 = 解析器.parse_args()

    if 参数.模式 == "图片模式":
        结果 = 消除图片(参数.图片路径, 参数.输出, 参数.命令)
        print(f"掩码覆盖率：{结果['掩码覆盖率']:.2%} → {结果['输出']}")
    else:
        结果 = 消除视频(
            参数.视频路径, 参数.输出, 参数.命令,
            进度回调=lambda 当前, 总数, 阶段: print(f"\r{阶段}", end="", flush=True),
            日志回调=print,
        )
        print(f"\n完成：{结果['输出']}（共 {结果['总帧数']} 帧）")


if __name__ == "__main__":
    main()
