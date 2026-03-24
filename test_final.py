#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终测试 - 在干净的工作区下测试完整流程"""
import sys
import subprocess
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent

def send_message(message: str, chat_id: str = "test_user_003"):
    """发送消息到客服机器人"""
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "ctcp_support_bot.py"),
        "--stdin",
        "--chat-id", chat_id
    ]

    result = subprocess.run(
        cmd,
        input=message.encode('utf-8'),
        capture_output=True,
        timeout=60
    )

    if result.stdout:
        output = result.stdout.decode('utf-8', errors='replace')
        print(f"Bot reply: {output[:200]}...")

    return result.returncode == 0

def get_session_dir(chat_id: str) -> Path:
    """获取session目录"""
    result = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, 'scripts'); from ctcp_support_bot import session_run_dir; print(session_run_dir('{chat_id}'))"],
        capture_output=True,
        text=True,
        cwd=ROOT
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None

def check_status(chat_id: str):
    """检查项目状态"""
    session_dir = get_session_dir(chat_id)
    if not session_dir:
        print("Failed to get session directory")
        return

    session_file = session_dir / "artifacts" / "support_session_state.json"
    if session_file.exists():
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n{'='*60}")
        print("Session State:")
        print(f"{'='*60}")
        print(f"  bound_run_id: {data.get('bound_run_id', 'N/A')}")
        print(f"  task_summary: {data.get('task_summary', 'N/A')}")

        if data.get('bound_run_id'):
            run_dir = Path(data.get('bound_run_dir', ''))
            if run_dir.exists():
                run_json = run_dir / "RUN.json"
                if run_json.exists():
                    with open(run_json, 'r', encoding='utf-8') as f:
                        run_data = json.load(f)
                    print(f"\nProject Status:")
                    print(f"  status: {run_data.get('status', 'N/A')}")
                    print(f"  blocked_reason: {run_data.get('blocked_reason', 'N/A')[:200]}...")

def main():
    chat_id = "test_user_003"

    print("="*60)
    print("最终测试：在干净的工作区下测试完整流程")
    print("="*60)

    print("\n步骤1: 发送问候")
    send_message("你好", chat_id)
    time.sleep(1)

    print("\n步骤2: 提出项目需求")
    send_message("我想做一个简单的视觉小说游戏，有剧情分支", chat_id)
    time.sleep(2)
    check_status(chat_id)

    print("\n步骤3: 补充细节")
    send_message("优先速度，先做出第一版", chat_id)
    time.sleep(2)
    check_status(chat_id)

    print("\n步骤4: 查询状态")
    send_message("进度怎么样了？", chat_id)
    time.sleep(1)
    check_status(chat_id)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
