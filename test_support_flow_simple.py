#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试从客服到生成项目的完整流程 - 简化版"""
import sys
import subprocess
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"

def send_message(message: str, chat_id: str = "test_user_001", step_num: int = 0):
    """发送消息到客服机器人"""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {message[:50]}...")
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
            errors='replace',  # 替换无法解码的字符
            timeout=60
        )

        print(f"Return code: {result.returncode}")

        if result.stdout:
            # 保存输出到文件
            output_file = ARTIFACTS / f"test_step_{step_num}_output.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            print(f"Output saved to: {output_file}")
            print(f"Output preview: {result.stdout[:200]}...")

        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}...")

        # 检查session state
        check_session_state(step_num)

        time.sleep(1)  # 等待文件写入完成

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("TIMEOUT!")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_session_state(step_num: int):
    """检查session state文件"""
    session_file = ARTIFACTS / "support_session_state.json"

    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 保存完整的session state
            output_file = ARTIFACTS / f"test_step_{step_num}_session.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"Session state saved to: {output_file}")

            # 打印关键信息
            if 'task_summary' in data:
                print(f"  task_summary: {data['task_summary'][:100] if data['task_summary'] else 'None'}...")
            if 'bound_run_id' in data:
                print(f"  bound_run_id: {data['bound_run_id']}")
            if 'frontdesk_state' in data:
                fs = data['frontdesk_state']
                if isinstance(fs, dict):
                    print(f"  frontdesk_state.state: {fs.get('state', 'N/A')}")
                    print(f"  frontdesk_state.current_goal: {str(fs.get('current_goal', ''))[:80]}...")

        except Exception as e:
            print(f"Failed to read session state: {e}")
    else:
        print("Session state file not found")

def main():
    print("Testing support bot flow: from greeting to project generation")
    print(f"Artifacts dir: {ARTIFACTS}")

    # Test 1: Greeting
    print("\n" + "="*60)
    print("TEST 1: Send greeting")
    print("="*60)
    send_message("你好", step_num=1)

    # Test 2: Project request
    print("\n" + "="*60)
    print("TEST 2: Request project")
    print("="*60)
    send_message("我想做一个简单的剧情推理游戏，有剧情分支", step_num=2)

    # Test 3: Add details
    print("\n" + "="*60)
    print("TEST 3: Add project details")
    print("="*60)
    send_message("优先速度，先做出第一版", step_num=3)

    # Test 4: Check status
    print("\n" + "="*60)
    print("TEST 4: Check status")
    print("="*60)
    send_message("进度怎么样了？", step_num=4)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print(f"\nCheck artifacts directory for detailed outputs: {ARTIFACTS}")
    print("Files to review:")
    print("  - test_step_*_output.txt (bot replies)")
    print("  - test_step_*_session.json (session states)")

if __name__ == "__main__":
    main()
