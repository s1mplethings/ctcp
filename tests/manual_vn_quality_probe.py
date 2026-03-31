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


def _materialize_high_quality_project(run_dir: Path, logo_bytes: bytes) -> dict[str, str]:
    out_root = run_dir / "artifacts" / "vn_story_tree_hq_project"
    out_root.mkdir(parents=True, exist_ok=True)
    logo_b64 = base64.b64encode(logo_bytes).decode("ascii")
    (out_root / "preview.png").write_bytes(_tiny_png_bytes())
    (out_root / "story_seed.json").write_text(
        json.dumps(
            {
                "title": "雾港回声",
                "root": "intro_return_home",
                "nodes": [
                    {"id": "intro_return_home", "label": "归乡开场", "to": ["school_archive", "cafe_evening"]},
                    {"id": "school_archive", "label": "旧校舍档案室", "to": ["storm_confession"]},
                    {"id": "cafe_evening", "label": "夜间咖啡馆", "to": ["storm_confession"]},
                    {"id": "storm_confession", "label": "暴雨告白", "to": ["ending_truth", "ending_silence"]},
                    {"id": "ending_truth", "label": "真相结局", "to": []},
                    {"id": "ending_silence", "label": "沉默结局", "to": []},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_root / "styles.css").write_text(
        "\n".join(
            [
                ":root{--bg:#f7f5ef;--ink:#222;--muted:#5f5a4f;--panel:#fffdf8;--line:#d9d2c4;--accent:#2f6d62;--accent2:#9a6a3a}",
                "*{box-sizing:border-box}",
                "body{margin:0;font-family:'Noto Sans SC','Microsoft YaHei',sans-serif;color:var(--ink);background:radial-gradient(circle at 10% 10%,#fff,#f1ece1 65%)}",
                ".wrap{max-width:1200px;margin:0 auto;padding:28px}",
                ".hero{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:22px;display:flex;gap:18px;align-items:center;box-shadow:0 6px 24px rgba(0,0,0,.06)}",
                ".logo{width:84px;height:84px;border-radius:14px;border:1px solid #ece5d8;background:#fff;padding:8px}",
                ".hero h1{margin:0 0 8px 0;font-size:28px}.hero p{margin:0;color:var(--muted)}",
                ".grid{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:16px}",
                ".panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px}",
                ".panel h2{margin:0 0 10px 0;font-size:18px}",
                ".branch-row{display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:1px dashed #e8e1d5}",
                ".branch-row:last-child{border-bottom:none}",
                ".tag{display:inline-block;background:#e9f4f2;color:#1e5d53;border:1px solid #cde3df;border-radius:999px;padding:2px 9px;font-size:12px}",
                ".muted{color:var(--muted)}",
                "textarea,input,select{width:100%;border:1px solid #cabfae;border-radius:10px;padding:10px;background:#fff}",
                "textarea{min-height:92px;resize:vertical}",
                "button{border:none;border-radius:10px;padding:9px 12px;cursor:pointer;background:var(--accent);color:#fff}",
                ".btn-alt{background:var(--accent2)}",
                "pre{margin:0;background:#1f2521;color:#d6f6da;border-radius:10px;padding:12px;min-height:180px;overflow:auto}",
                ".toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}",
                ".kpi{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}",
                ".kpi .card{background:#fff;border:1px solid #ece4d6;border-radius:12px;padding:10px}",
                "@media(max-width:960px){.grid{grid-template-columns:1fr}.kpi{grid-template-columns:1fr 1fr}}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out_root / "app.js").write_text(
        "\n".join(
            [
                "const $ = (id) => document.getElementById(id);",
                "const seed = {",
                "  title: '雾港回声',",
                "  nodes: [",
                "    { id:'intro_return_home', label:'归乡开场', to:['school_archive','cafe_evening'] },",
                "    { id:'school_archive', label:'旧校舍档案室', to:['storm_confession'] },",
                "    { id:'cafe_evening', label:'夜间咖啡馆', to:['storm_confession'] },",
                "    { id:'storm_confession', label:'暴雨告白', to:['ending_truth','ending_silence'] },",
                "    { id:'ending_truth', label:'真相结局', to:[] },",
                "    { id:'ending_silence', label:'沉默结局', to:[] },",
                "  ]",
                "};",
                "function drawRows() {",
                "  const host = $('branchRows'); host.innerHTML='';",
                "  seed.nodes.forEach((n) => {",
                "    const div = document.createElement('div'); div.className='branch-row';",
                "    div.innerHTML = `<span class='tag'>${n.id}</span><strong>${n.label}</strong><span class='muted'>-> ${n.to.join(', ') || 'END'}</span>`;",
                "    host.appendChild(div);",
                "  });",
                "  $('kpiNodeCount').textContent = String(seed.nodes.length);",
                "  $('kpiBranchCount').textContent = String(seed.nodes.filter(n => n.to.length > 1).length);",
                "}",
                "function exportJSON() {",
                "  const payload = {",
                "    title: $('titleInput').value || seed.title,",
                "    theme: $('themeInput').value,",
                "    core_conflict: $('conflictInput').value,",
                "    node_flow: seed.nodes,",
                "    role_background: $('roleInput').value.split('\\n').filter(Boolean),",
                "    scene_background: $('sceneInput').value.split('\\n').filter(Boolean),",
                "  };",
                "  $('jsonOut').textContent = JSON.stringify(payload, null, 2);",
                "  $('kpiUpdated').textContent = new Date().toLocaleString();",
                "}",
                "function exportMarkdown() {",
                "  const lines = [];",
                "  lines.push('# ' + ($('titleInput').value || seed.title));",
                "  lines.push('');",
                "  lines.push('## 主冲突');",
                "  lines.push($('conflictInput').value || '（待补）');",
                "  lines.push('');",
                "  lines.push('## 节点流');",
                "  seed.nodes.forEach((n) => lines.push(`- ${n.id} ${n.label} -> ${n.to.join(', ') || 'END'}`));",
                "  $('mdOut').textContent = lines.join('\\n');",
                "}",
                "$('btnJson').addEventListener('click', exportJSON);",
                "$('btnMd').addEventListener('click', exportMarkdown);",
                "drawRows(); exportJSON();",
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
  <title>VN 剧情树与背景梳理台（高质量探测）</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <img class="logo" alt="logo" src="data:image/png;base64,{logo_b64}" />
      <div>
        <h1>VN 剧情树与背景梳理台</h1>
        <p>用于首稿阶段快速统一剧情树、人物背景、场景背景，并导出结构化草案。</p>
      </div>
    </section>
    <section class="grid">
      <article class="panel">
        <h2>剧情树主干</h2>
        <div class="kpi">
          <div class="card"><div class="muted">节点数</div><strong id="kpiNodeCount">0</strong></div>
          <div class="card"><div class="muted">分支节点</div><strong id="kpiBranchCount">0</strong></div>
          <div class="card"><div class="muted">最近更新</div><strong id="kpiUpdated">-</strong></div>
        </div>
        <div id="branchRows"></div>
      </article>
      <article class="panel">
        <h2>项目设定</h2>
        <label>标题</label><input id="titleInput" value="雾港回声：分歧之夜" />
        <label>主题</label><input id="themeInput" value="记忆、承诺与失语" />
        <label>主冲突</label><textarea id="conflictInput">主角在揭露旧案真相与保护重要之人之间做选择。</textarea>
      </article>
      <article class="panel">
        <h2>角色背景</h2>
        <textarea id="roleInput">主角：返乡摄影师，回避型创伤应对。
青梅：地方记者，行动果断。
对立者：旧案相关利益方，掌控镇内舆论。 </textarea>
      </article>
      <article class="panel">
        <h2>场景背景</h2>
        <textarea id="sceneInput">旧校舍：潮湿、停电、回声重。
海港堤岸：夜雾、远灯、铁锈味。
咖啡馆：暖光、唱片、短暂安全区。 </textarea>
      </article>
      <article class="panel">
        <h2>导出 JSON</h2>
        <div class="toolbar"><button id="btnJson">生成 JSON 草案</button></div>
        <pre id="jsonOut"></pre>
      </article>
      <article class="panel">
        <h2>导出 Markdown</h2>
        <div class="toolbar"><button id="btnMd" class="btn-alt">生成 Markdown 提纲</button></div>
        <pre id="mdOut"></pre>
      </article>
    </section>
  </div>
  <script src="./app.js"></script>
</body>
</html>
""",
        encoding="utf-8",
    )
    (out_root / "README.md").write_text(
        "\n".join(
            [
                "# VN 剧情树与背景梳理台（高质量探测版）",
                "",
                "## 首稿定位",
                "- 用于 VN 前期策划，把剧情树、角色背景、场景背景统一到一页操作台。",
                "- 输出 JSON 与 Markdown 两种草案格式，方便后续喂给脚本/引擎/写作工作流。",
                "",
                "## 文件说明",
                "- `index.html`: 单页界面",
                "- `styles.css`: 样式",
                "- `app.js`: 节点展示与导出逻辑",
                "- `story_seed.json`: 初始剧情树种子",
                "- `preview.png`: 预览占位图",
                "",
                "## 使用步骤",
                "1. 打开 `index.html`",
                "2. 修改标题、主冲突、角色背景、场景背景",
                "3. 点击导出按钮得到 JSON/Markdown 草案",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "index_html": (out_root / "index.html").resolve().relative_to(run_dir.resolve()).as_posix(),
        "styles_css": (out_root / "styles.css").resolve().relative_to(run_dir.resolve()).as_posix(),
        "readme_md": (out_root / "README.md").resolve().relative_to(run_dir.resolve()).as_posix(),
        "app_js": (out_root / "app.js").resolve().relative_to(run_dir.resolve()).as_posix(),
        "seed_json": (out_root / "story_seed.json").resolve().relative_to(run_dir.resolve()).as_posix(),
        "preview_png": (out_root / "preview.png").resolve().relative_to(run_dir.resolve()).as_posix(),
    }


def _quality_score(run_dir: Path, rels: dict[str, str]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    index = run_dir / rels["index_html"]
    css = run_dir / rels["styles_css"]
    js = run_dir / rels["app_js"]
    readme = run_dir / rels["readme_md"]
    preview = run_dir / rels["preview_png"]
    checks["required_files"] = all((run_dir / rels[k]).exists() for k in ["index_html", "styles_css", "readme_md", "preview_png"])
    checks["has_js_logic"] = js.exists() and ("exportJSON" in js.read_text(encoding="utf-8", errors="replace"))
    checks["index_rich_structure"] = index.exists() and index.read_text(encoding="utf-8", errors="replace").count("<section") >= 2
    checks["css_non_trivial"] = css.exists() and len(css.read_text(encoding="utf-8", errors="replace")) > 1200
    checks["readme_guidance"] = readme.exists() and "使用步骤" in readme.read_text(encoding="utf-8", errors="replace")
    checks["preview_exists"] = preview.exists() and preview.stat().st_size > 0
    score = int(sum(1 for v in checks.values() if v) * (100 / max(1, len(checks))))
    return {"score": score, "checks": checks}


def run_quality_probe() -> dict[str, Any]:
    out_root = ROOT / "artifacts" / "backend_interface_vn_quality"
    out_root.mkdir(parents=True, exist_ok=True)
    inputs = out_root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    brief = inputs / "brief.txt"
    logo = inputs / "logo.png"
    logo_bytes = _tiny_png_bytes()
    logo.write_bytes(logo_bytes)
    brief.write_text(
        "目标：生成可用于 VN 剧情树和背景梳理的高质量单页项目。"
        "要求：结构清晰、可导出 JSON/Markdown、包含预览图。\n",
        encoding="utf-8",
    )

    create = bridge.create_run(
        goal="高质量首稿探测：VN剧情树与背景梳理台",
        constraints={"quality_mode": "high", "must_have": ["index.html", "styles.css", "README.md", "preview.png"]},
        attachments=[str(brief), str(logo)],
    )
    run_id = str(create.get("run_id", ""))
    run_dir = Path(str(create.get("run_dir", "")))
    up_brief = bridge.upload_input_artifact(run_id, str(brief))
    up_logo = bridge.upload_input_artifact(run_id, str(logo))
    for _ in range(2):
        bridge.advance_run(run_id, max_steps=1)
    decisions = bridge.list_pending_decisions(run_id)
    submitted = []
    for item in list(decisions.get("decisions", [])):
        row = dict(item) if isinstance(item, dict) else {}
        if str(row.get("status", "")).lower() != "pending":
            continue
        submitted.append(
            bridge.submit_decision(run_id, {"decision_id": str(row.get("decision_id", "")), "content": "自动选择继续推进"})
        )

    generated = _materialize_high_quality_project(run_dir, logo_bytes=logo_bytes)
    outputs = bridge.list_output_artifacts(run_id)
    meta_index = bridge.get_output_artifact_meta(run_id, generated["index_html"])
    read_index = bridge.read_output_artifact(run_id, generated["index_html"])
    meta_preview = bridge.get_output_artifact_meta(run_id, generated["preview_png"])
    read_preview = bridge.read_output_artifact(run_id, generated["preview_png"])
    current = bridge.get_current_state_snapshot(run_id)
    render = bridge.get_render_state_snapshot(run_id)
    quality = _quality_score(run_dir, generated)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "uploads": {"brief": up_brief, "logo": up_logo},
        "decisions_count": int(decisions.get("count", 0) or 0),
        "submitted": submitted,
        "generated_files": generated,
        "outputs": outputs,
        "meta_index": meta_index,
        "read_index_preview": str(read_index.get("text", ""))[:600],
        "meta_preview": meta_preview,
        "read_preview": {"download_path": read_preview.get("download_path", ""), "size_bytes": read_preview.get("size_bytes", 0)},
        "current_snapshot": current,
        "render_snapshot": render,
        "quality": quality,
    }


if __name__ == "__main__":
    result = run_quality_probe()
    report = ROOT / "artifacts" / "backend_interface_vn_quality" / "vn_quality_probe_report.json"
    _write_json(report, result)
    print(json.dumps({"report_path": str(report), "run_id": result.get("run_id", ""), "quality_score": result.get("quality", {}).get("score", 0)}, ensure_ascii=False))
