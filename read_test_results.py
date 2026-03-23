#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取测试结果"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"

def read_file(fpath):
    """读取文件，尝试多种编码"""
    for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16']:
        try:
            with open(fpath, 'r', encoding=encoding) as f:
                return f.read(), encoding
        except:
            continue
    return None, None

def main():
    print("="*60)
    print("测试结果分析")
    print("="*60)

    # 读取每个步骤的输出
    for i in range(1, 5):
        print(f"\n{'='*60}")
        print(f"步骤 {i}")
        print(f"{'='*60}")

        # 读取输出
        output_file = ARTIFACTS / f"test_step_{i}_output.txt"
        if output_file.exists():
            content, encoding = read_file(output_file)
            if content:
                print(f"\n机器人回复 (编码: {encoding}):")
                print(content)
            else:
                print(f"\n无法读取输出文件")
        else:
            print(f"\n输出文件不存在: {output_file}")

        # 读取session state
        session_file = ARTIFACTS / f"test_step_{i}_session.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"\nSession State:")
                print(f"  task_summary: {data.get('task_summary', 'N/A')}")
                print(f"  bound_run_id: {data.get('bound_run_id', 'N/A')}")
                if 'frontdesk_state' in data:
                    fs = data['frontdesk_state']
                    print(f"  frontdesk_state.state: {fs.get('state', 'N/A')}")
                    print(f"  frontdesk_state.current_goal: {fs.get('current_goal', 'N/A')}")
                    print(f"  frontdesk_state.state_reason: {fs.get('state_reason', 'N/A')}")
            except Exception as e:
                print(f"\n无法读取session state: {e}")
        else:
            print(f"\nSession state文件不存在: {session_file}")

    # 检查support_session_state.json
    print(f"\n{'='*60}")
    print("检查 support_session_state.json")
    print(f"{'='*60}")

    session_file = ARTIFACTS / "support_session_state.json"
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"\n最终 Session State:")
            print(f"  task_summary: {data.get('task_summary', 'N/A')}")
            print(f"  bound_run_id: {data.get('bound_run_id', 'N/A')}")
            if 'frontdesk_state' in data:
                fs = data['frontdesk_state']
                print(f"  frontdesk_state.state: {fs.get('state', 'N/A')}")
                print(f"  frontdesk_state.current_goal: {fs.get('current_goal', 'N/A')}")
                print(f"  frontdesk_state.state_reason: {fs.get('state_reason', 'N/A')}")
                print(f"  frontdesk_state.active_task_id: {fs.get('active_task_id', 'N/A')}")
        except Exception as e:
            print(f"\n无法读取: {e}")
    else:
        print(f"\n文件不存在")

if __name__ == "__main__":
    main()
