#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试从客服到生成项目的完整流程"""
import sys
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"

def send_message(message: str, chat_id: str = "test_user_001"):
    """发送消息到客服机器人"""
    print(f"\n{'='*60}")
    print(f"发送消息: {message}")
    print(f"{'='*60}")

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "ctcp_support_bot.py"),
        "--stdin",
        "--chat-id", chat_id
    ]

    try:
        result = subprocess.run(
            cmd,
            input=message,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=60
        )

        print(f"\n返回码: {result.returncode}")
        if result.stdout:
            print(f"\n回复:\n{result.stdout}")
        if result.stderr:
            print(f"\n错误:\n{result.stderr}")

        # 检查生成的文件
        check_artifacts()

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("超时!")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def check_artifacts():
    """检查生成的artifact文件"""
    print(f"\n{'='*60}")
    print("检查生成的文件:")
    print(f"{'='*60}")

    files_to_check = [
        "support_session_state.json",
        "support_reply.json",
        "support_inbox.jsonl",
    ]

    for fname in files_to_check:
        fpath = ARTIFACTS / fname
        if fpath.exists():
            print(f"\n✓ {fname} 存在")
            try:
                if fname.endswith('.json'):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  内容预览: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
            except Exception as e:
                print(f"  读取失败: {e}")
        else:
            print(f"\n✗ {fname} 不存在")

def main():
    print("开始测试从客服到生成项目的流程")

    # 测试1: 问候语
    print("\n\n" + "="*60)
    print("测试 1: 发送问候语")
    print("="*60)
    send_message("你好")

    input("\n按回车继续下一步...")

    # 测试2: 提出项目需求
    print("\n\n" + "="*60)
    print("测试 2: 提出项目需求")
    print("="*60)
    send_message("我想做一个简单的剧情推理游戏，有剧情分支")

    input("\n按回车继续下一步...")

    # 测试3: 补充细节
    print("\n\n" + "="*60)
    print("测试 3: 补充项目细节")
    print("="*60)
    send_message("优先速度，先做出第一版")

    input("\n按回车继续下一步...")

    # 测试4: 查询状态
    print("\n\n" + "="*60)
    print("测试 4: 查询项目状态")
    print("="*60)
    send_message("进度怎么样了？")

    print("\n\n测试完成!")

if __name__ == "__main__":
    main()
