#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析测试结果并保存为JSON"""
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
    results = {
        "steps": [],
        "final_session": None,
        "analysis": {}
    }

    # 读取每个步骤的输出
    for i in range(1, 5):
        step_data = {
            "step_num": i,
            "output": None,
            "output_encoding": None,
            "session": None
        }

        # 读取输出
        output_file = ARTIFACTS / f"test_step_{i}_output.txt"
        if output_file.exists():
            content, encoding = read_file(output_file)
            step_data["output"] = content
            step_data["output_encoding"] = encoding

        # 读取session state
        session_file = ARTIFACTS / f"test_step_{i}_session.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    step_data["session"] = json.load(f)
            except Exception as e:
                step_data["session_error"] = str(e)

        results["steps"].append(step_data)

    # 检查support_session_state.json
    session_file = ARTIFACTS / "support_session_state.json"
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                results["final_session"] = json.load(f)
        except Exception as e:
            results["final_session_error"] = str(e)

    # 分析
    if results["final_session"]:
        fs = results["final_session"]
        results["analysis"] = {
            "task_summary": fs.get("task_summary", ""),
            "bound_run_id": fs.get("bound_run_id", ""),
            "has_active_project": bool(fs.get("bound_run_id", "")),
        }

        if "frontdesk_state" in fs:
            fds = fs["frontdesk_state"]
            results["analysis"]["frontdesk_state"] = {
                "state": fds.get("state", ""),
                "current_goal": fds.get("current_goal", ""),
                "active_task_id": fds.get("active_task_id", ""),
                "state_reason": fds.get("state_reason", ""),
                "interrupt_kind": fds.get("interrupt_kind", ""),
            }

    # 保存结果
    output_file = ARTIFACTS / "test_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return str(output_file)

if __name__ == "__main__":
    output = main()
    print(output)
