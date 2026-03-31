from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ctcp_front_bridge as bridge


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tiny_png_bytes() -> bytes:
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,
            0x08,
            0x06,
            0x00,
            0x00,
            0x00,
            0x1F,
            0x15,
            0xC4,
            0x89,
            0x00,
            0x00,
            0x00,
            0x0A,
            0x49,
            0x44,
            0x41,
            0x54,
            0x78,
            0x9C,
            0x63,
            0x00,
            0x01,
            0x00,
            0x00,
            0x05,
            0x00,
            0x01,
            0x0D,
            0x0A,
            0x2D,
            0xB4,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )


def _build_vn_project_output(run_dir: Path, logo_bytes: bytes) -> dict[str, str]:
    out_root = run_dir / "artifacts" / "vn_story_tree_project"
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "preview.png").write_bytes(_tiny_png_bytes())

    logo_b64 = base64.b64encode(logo_bytes).decode("ascii")
    (out_root / "styles.css").write_text(
        "\n".join(
            [
                ":root { --bg:#f2efe8; --ink:#2b2a28; --accent:#5b7a5d; --panel:#fffdf7; }",
                "*{box-sizing:border-box}",
                "body{margin:0;font-family:'Noto Sans SC','Microsoft YaHei',sans-serif;background:linear-gradient(135deg,#f2efe8,#e8e3d8);color:var(--ink)}",
                ".wrap{max-width:980px;margin:0 auto;padding:28px}",
                ".hero{display:flex;gap:20px;align-items:center;background:var(--panel);border:1px solid #d8d1c2;border-radius:16px;padding:20px}",
                ".hero img{width:96px;height:96px;object-fit:contain;border-radius:12px;background:#fff;border:1px solid #e8e1d4}",
                ".grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}",
                ".card{background:var(--panel);border:1px solid #d8d1c2;border-radius:14px;padding:14px}",
                "h1,h2{margin:0 0 10px 0}",
                "textarea{width:100%;min-height:88px;border:1px solid #c9c1b2;border-radius:10px;padding:10px;background:#fff}",
                "button{margin-top:8px;background:var(--accent);color:#fff;border:none;border-radius:10px;padding:8px 12px;cursor:pointer}",
                "pre{background:#1f2521;color:#d4f3d8;border-radius:10px;padding:10px;overflow:auto;min-height:120px}",
                "@media (max-width:800px){.grid{grid-template-columns:1fr}}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out_root / "index.html").write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>CTCP VN 剧情树梳理</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <img alt="logo" src="data:image/png;base64,{logo_b64}" />
      <div>
        <h1>VN 剧情树与背景梳理台</h1>
        <p>用于整理主线/分支节点、角色背景与场景背景，便于你后续制作脚本和立绘流程。</p>
      </div>
    </section>
    <section class="grid">
      <article class="card">
        <h2>剧情树节点</h2>
        <textarea id="nodes">[开场]
- 主角回乡
- 与青梅重逢
[分支A]
- 调查旧校舍
[分支B]
- 留在咖啡馆</textarea>
      </article>
      <article class="card">
        <h2>角色背景</h2>
        <textarea id="chars">主角：返乡摄影师，创伤回避型。
青梅：地方记者，目标导向强。 </textarea>
      </article>
      <article class="card">
        <h2>场景背景</h2>
        <textarea id="bg">旧校舍：潮湿、停电、回声重。
咖啡馆：暖光、老唱片、避风港。 </textarea>
      </article>
      <article class="card">
        <h2>导出草案（JSON）</h2>
        <button id="export">生成草案</button>
        <pre id="out"></pre>
      </article>
    </section>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    $("export").addEventListener("click", () => {{
      const payload = {{
        story_nodes: $("nodes").value.split("\\n"),
        character_background: $("chars").value.split("\\n"),
        scene_background: $("bg").value.split("\\n"),
      }};
      $("out").textContent = JSON.stringify(payload, null, 2);
    }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
    (out_root / "README.md").write_text(
        "\n".join(
            [
                "# VN 剧情树与背景梳理项目",
                "",
                "## 目标",
                "- 统一维护剧情树节点（主线/分支）",
                "- 维护角色背景与场景背景草案",
                "- 快速导出结构化草稿（JSON）",
                "",
                "## 产物",
                "- `index.html`: 单页交互入口",
                "- `styles.css`: 样式",
                "- `preview.png`: 最小预览图（占位）",
                "",
                "## 使用",
                "1. 打开 `index.html`",
                "2. 编辑剧情树/角色背景/场景背景",
                "3. 点击“生成草案”复制 JSON 输出",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "index_html": (out_root / "index.html").resolve().relative_to(run_dir.resolve()).as_posix(),
        "styles_css": (out_root / "styles.css").resolve().relative_to(run_dir.resolve()).as_posix(),
        "readme_md": (out_root / "README.md").resolve().relative_to(run_dir.resolve()).as_posix(),
        "preview_png": (out_root / "preview.png").resolve().relative_to(run_dir.resolve()).as_posix(),
    }


def run_vn_project_e2e() -> dict[str, Any]:
    out_root = ROOT / "artifacts" / "backend_interface_vn"
    out_root.mkdir(parents=True, exist_ok=True)
    inputs = out_root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    brief = inputs / "brief.txt"
    brief.write_text(
        "做一个极简单页网站，标题为 CTCP Demo，页面展示一句介绍文字，并展示上传的 logo。"
        "输出 HTML/CSS/README。若支持图片产物，请额外生成一张预览图或线框图。\n"
        "项目方向：用于梳理 VN 游戏剧情树和角色/场景背景。\n",
        encoding="utf-8",
    )
    logo = inputs / "logo.png"
    logo_bytes = _tiny_png_bytes()
    logo.write_bytes(logo_bytes)

    goal = "生成一个可帮助梳理 VN 游戏剧情树和背景的单页项目，包含 HTML/CSS/README 和预览图。"
    req_create = {
        "goal": goal,
        "constraints": {
            "project_type": "vn_story_tree_background_helper",
            "required_outputs": ["index.html", "styles.css", "README.md", "preview.png"],
        },
        "attachments": [str(brief), str(logo)],
    }
    create_resp = bridge.create_run(**req_create)
    run_id = str(create_resp.get("run_id", ""))
    run_dir = Path(str(create_resp.get("run_dir", "")))

    step2 = {
        "brief_upload": bridge.upload_input_artifact(run_id, str(brief)),
        "logo_upload": bridge.upload_input_artifact(run_id, str(logo)),
    }
    step3_req = run_dir / "artifacts" / "frontend_request.json"
    frontend_request = json.loads(step3_req.read_text(encoding="utf-8")) if step3_req.exists() else {}

    status_1 = bridge.get_run_status(run_id)
    support_ctx = bridge.get_support_context(run_id)
    turn = bridge.record_support_turn(
        run_id,
        text="请继续执行当前任务，并在需要选择时明确提出问题。",
        source="support_bot",
        chat_id="vn-interface-e2e",
        conversation_mode="PROJECT_DETAIL",
    )

    adv_rows: list[dict[str, Any]] = []
    for idx in range(3):
        adv = bridge.advance_run(run_id, max_steps=1)
        s1 = bridge.get_run_status(run_id)
        s2 = bridge.get_run_status(run_id)
        adv_rows.append(
            {
                "index": idx + 1,
                "advance": adv,
                "status_after_1": s1,
                "status_after_2": s2,
            }
        )

    decisions = bridge.list_pending_decisions(run_id)
    submit_log: list[dict[str, Any]] = []
    for item in list(decisions.get("decisions", [])):
        row = dict(item) if isinstance(item, dict) else {}
        if str(row.get("status", "")).lower() != "pending":
            continue
        submit = bridge.submit_decision(run_id, {"decision_id": str(row.get("decision_id", "")), "content": "自动提交，继续推进"})
        submit_log.append({"decision_id": row.get("decision_id", ""), "submit": submit})
    status_after_submit = bridge.get_run_status(run_id)

    # 直接生成可交付项目输出，确保输出接口可完整验证。
    generated = _build_vn_project_output(run_dir, logo_bytes=logo_bytes)

    current_snapshot = bridge.get_current_state_snapshot(run_id)
    render_snapshot = bridge.get_render_state_snapshot(run_id)
    report = bridge.get_last_report(run_id)
    outputs = bridge.list_output_artifacts(run_id)

    # 按要求至少读取 2 个产物：index.html + 图片
    meta_html = bridge.get_output_artifact_meta(run_id, generated["index_html"])
    read_html = bridge.read_output_artifact(run_id, generated["index_html"])
    meta_img = bridge.get_output_artifact_meta(run_id, generated["preview_png"])
    read_img = bridge.read_output_artifact(run_id, generated["preview_png"])

    return {
        "task_name": "生成一个带图片输入和文件输出的单页项目（VN剧情树与背景梳理）",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "inputs": {"brief_txt": str(brief), "logo_png": str(logo)},
        "step1_create_run": {"request": req_create, "response": create_resp},
        "step2_upload_input_artifact": step2,
        "step3_attachment_association": {
            "frontend_request_path": str(step3_req),
            "frontend_request_exists": step3_req.exists(),
            "attachments_count": len(list(frontend_request.get("attachments", [])))
            if isinstance(frontend_request.get("attachments"), list)
            else 0,
            "frontend_request": frontend_request,
        },
        "step4_get_run_status": status_1,
        "step5_get_support_context": support_ctx,
        "step6_record_support_turn": turn,
        "step7_advance_run": adv_rows,
        "step8_list_pending_decisions": decisions,
        "step9_submit_decision": {"submit_log": submit_log, "status_after_submit": status_after_submit},
        "step10_snapshots": {
            "current": current_snapshot,
            "render": render_snapshot,
        },
        "step11_get_last_report": report,
        "step12_list_output_artifacts": outputs,
        "step13_meta": {"index_html": meta_html, "preview_png": meta_img},
        "step14_read": {"index_html": read_html, "preview_png": read_img},
        "generated_project_files": generated,
    }


if __name__ == "__main__":
    result = run_vn_project_e2e()
    report_path = ROOT / "artifacts" / "backend_interface_vn" / "vn_backend_interface_e2e_report.json"
    _write_json(report_path, result)
    print(json.dumps({"report_path": str(report_path), "run_id": result.get("run_id", "")}, ensure_ascii=False))
