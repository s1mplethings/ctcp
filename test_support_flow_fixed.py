#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试从客服到生成项目的完整流程 - 修复编码问题"""
import sys
import subprocess
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"

def send_message(message: str, chat_id: str = "test_user_002", step_num: int = 0):
    """发送消息到客服机器人 - 修复编码问题"""
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
        # 关键修复：使用bytes模式，确保UTF-8编码正确传递
        result = subprocess.run(
            cmd,
            input=message.encode('utf-8'),  # 编码为UTF-8 bytes
            capture_output=True,
            timeout=60
        )

        print(f"Return code: {result.returncode}")

        # 解码输出
        if result.stdout:
            try:
                output_text = result.stdout.decode('utf-8', errors='replace')
                output_file = ARTIFACTS / f"test_step_{step_num}_output.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"Output saved to: {output_file}")
                print(f"Output preview: {output_text[:200]}...")
            except Exception as e:
                print(f"Failed to decode output: {e}")

        if result.stderr:
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
                print(f"Stderr: {stderr_text[:200]}...")
            except:
                pass

        time.sleep(1)
        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("TIMEOUT!")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_session_dir(chat_id: str) -> Path:
    """获取session目录"""
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, 'scripts'); from ctcp_support_bot import session_run_dir; print(session_run_dir('{chat_id}'))"],
            capture_output=True,
            text=True,
            cwd=ROOT
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except:
        pass
    return None

def check_session_state(chat_id: str, step_num: int):
    """检查session state"""
    session_dir = get_session_dir(chat_id)
    if not session_dir:
        print("Failed to get session directory")
        return

    session_file = session_dir / "artifacts" / "support_session_state.json"
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 保存session state
            output_file = ARTIFACTS / f"test_step_{step_num}_session.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"Session state saved to: {output_file}")
            print(f"  task_summary: {data.get('task_summary', 'N/A')[:80]}")
            print(f"  bound_run_id: {data.get('bound_run_id', 'N/A')}")

            if 'frontdesk_state' in data:
                fs = data['frontdesk_state']
                print(f"  frontdesk_state.state: {fs.get('state', 'N/A')}")
                print(f"  frontdesk_state.current_goal: {str(fs.get('current_goal', ''))[:60]}...")
                print(f"  frontdesk_state.state_reason: {fs.get('state_reason', 'N/A')}")

        except Exception as e:
            print(f"Failed to read session state: {e}")
    else:
        print("Session state file not found")

def main():
    chat_id = "test_user_002"  # 使用新的chat_id避免旧数据干扰

    print("Testing support bot flow with FIXED encoding")
    print(f"Chat ID: {chat_id}")

    session_dir = get_session_dir(chat_id)
    if session_dir:
        print(f"Session directory: {session_dir}")

    # Test 1: Greeting
    print("\n" + "="*60)
    print("TEST 1: Send greeting")
    print("="*60)
    send_message("你好", chat_id=chat_id, step_num=1)
    check_session_state(chat_id, 1)

    # Test 2: Project request
    print("\n" + "="*60)
    print("TEST 2: Request project")
    print("="*60)
    send_message("我想做一个简单的视觉小说游戏，有剧情分支", chat_id=chat_id, step_num=2)
    check_session_state(chat_id, 2)

    # Test 3: Add details
    print("\n" + "="*60)
    print("TEST 3: Add project details")
    print("="*60)
    send_message("优先速度，先做出第一版", chat_id=chat_id, step_num=3)
    check_session_state(chat_id, 3)

    # Test 4: Check status
    print("\n" + "="*60)
    print("TEST 4: Check status")
    print("="*60)
    send_message("进度怎么样了？", chat_id=chat_id, step_num=4)
    check_session_state(chat_id, 4)

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print(f"\nSession directory: {session_dir}")
    print(f"Artifacts directory: {ARTIFACTS}")

if __name__ == "__main__":
    main()
