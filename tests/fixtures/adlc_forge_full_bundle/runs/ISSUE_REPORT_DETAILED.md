# ISSUE REPORT (Detailed)

- Generated at: 2026-02-18T21:41:28
- Total: 27
- Passed: 26
- Failed: 0
- Skipped: 1

## Preflight
```json
{
  "entry_suite_gate_exists": false,
  "entry_live_suite_exists": false,
  "suite_entry_skip_reasons": [
    "missing entry: tools/checks/suite_gate.py",
    "missing entry: tests/fixtures/adlc_forge_full_bundle/suites/forge_full_suite.live.yaml"
  ],
  "has_cmake": true,
  "has_cl": false,
  "has_gpp": false,
  "has_clangpp": false,
  "has_cpp_compiler": false,
  "has_qmake": true,
  "has_windeployqt": true,
  "has_qt_tooling": true,
  "has_pytest_qt": true,
  "has_display": false,
  "has_gui_harness": false,
  "has_build_toolchain": false,
  "has_gui_automation": false,
  "optional_gui_smoke": {
    "status": "skip",
    "reason": "missing dependency: Qt/GUI automation | display not available (DISPLAY missing); GUI harness not implemented (tests/gui or tools/checks gui runner missing)",
    "command": "python tools/checks/web_spider_visual_check.py"
  }
}
```

## Case Results

### T01 禁止代码门禁（未授权必须失败）
- Status: **pass**
- Expectation: verify should fail with Code changes allowed hint
- Evidence:
```json
{
  "rc": 1,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks][error] code changes detected but CURRENT.md does not allow code edits.\nAdd and tick the checkbox in meta/tasks/CURRENT.md:\n  - [x] Code changes allowed\nCode changes:\n  - src/main.cpp\n",
  "stderr_tail": "Invoke-ExternalChecked : [verify_repo] FAILED: workflow gate (workflow checks) (exit=1)\nAt D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\\scripts\\verify_repo.ps1:148 \nchar:3\n+   Invoke-ExternalChecked -Label \"workflow gate (workflow checks)\" -Co ...\n+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n    + CategoryInfo          : NotSpecified: (:) [Write-Error], WriteErrorException\n    + FullyQualifiedErrorId : Microsoft.PowerShell.Commands.WriteErrorException,Invoke-ExternalChecked\n \n",
  "diff": "diff --git a/meta/tasks/CURRENT.md b/meta/tasks/CURRENT.md\nindex 191fc07..abf85ae 100644\n--- a/meta/tasks/CURRENT.md\n+++ b/meta/tasks/CURRENT.md\n@@ -8,7 +8,7 @@\n ## Acceptance (must be checkable)\n - [x] DoD written (this file complete)\n - [x] Research logged (if needed): no new third-party runtime dependency planned\n-- [x] Code changes allowed\n+- [ ] Code changes allowed\n - [ ] Added `tools/run_verify.py` with configure/build/ctest/install/smoke sequencing and artifact logs\n - [ ] Added `tools/adlc_gate.py` to fail on missing evidence or non-PASS proof\n - [ ] Added `tools/contrast_proof.py` to diff two proof.json files and write markdown report\ndiff --git a/src/main.cpp b/src/main.cpp\nindex 305b7b1..a5c8996 100644\n--- a/src/main.cpp\n+++ b/src/main.cpp\n@@ -58,3 +58,5 @@ int main(int argc, char *argv[]) {\n         return 3;\n     }\n }\n+\n+// matrix-case-01\n"
}
```

### T02 禁止代码门禁（授权后必须通过）
- Status: **pass**
- Expectation: workflow gate should pass with authorization
- Evidence:
```json
{
  "rc": 0,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks] ok\n[verify_repo] contract checks\n[contract_checks] schema presence ok\n[contract_checks] meta schema_version ok\n[contract_checks] readme links ok\n[contract_checks] unique Graph Spider implementation ok\n[verify_repo] doc index check (sync doc links --check)\n[sync_doc_links] ok\n[verify_repo] tests\n[tests] ok (10 cases)\n[verify_repo] OK\n",
  "stderr_tail": ""
}
```

### T03 只改文档不需要授权（应通过）
- Status: **pass**
- Expectation: doc-only change should not be blocked by workflow gate
- Evidence:
```json
{
  "rc": 0,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks] ok (no code changes)\n[verify_repo] contract checks\n[contract_checks] schema presence ok\n[contract_checks] meta schema_version ok\n[contract_checks] readme links ok\n[contract_checks] unique Graph Spider implementation ok\n[verify_repo] doc index check (sync doc links --check)\n[sync_doc_links] ok\n[verify_repo] tests\n[tests] ok (10 cases)\n[verify_repo] OK\n",
  "stderr_tail": ""
}
```

### T04 缺失契约文件必须失败
- Status: **pass**
- Expectation: verify should fail and mention missing AI contract
- Evidence:
```json
{
  "rc": 1,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks][error] missing required workflow files:\n  - ai_context/00_AI_CONTRACT.md\n",
  "stderr_tail": "Invoke-ExternalChecked : [verify_repo] FAILED: workflow gate (workflow checks) (exit=1)\nAt D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\\scripts\\verify_repo.ps1:148 \nchar:3\n+   Invoke-ExternalChecked -Label \"workflow gate (workflow checks)\" -Co ...\n+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n    + CategoryInfo          : NotSpecified: (:) [Write-Error], WriteErrorException\n    + FullyQualifiedErrorId : Microsoft.PowerShell.Commands.WriteErrorException,Invoke-ExternalChecked\n \n"
}
```

### T05 README 引用不存在文件必须失败
- Status: **pass**
- Expectation: contract check should detect broken README link
- Evidence:
```json
{
  "rc": 1,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks] ok (no code changes)\n[verify_repo] contract checks\n[contract_checks] schema presence ok\n[contract_checks] meta schema_version ok\n",
  "stderr_tail": "[contract_checks] README contains broken local links:\n- README.md:99: broken link 'docs/NOPE.md' -> 'docs/NOPE.md'\nInvoke-ExternalChecked : [verify_repo] FAILED: contract checks (exit=1)\nAt D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\\scripts\\verify_repo.ps1:153 \nchar:3\n+   Invoke-ExternalChecked -Label \"contract checks\" -Command { python s ...\n+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n    + CategoryInfo          : NotSpecified: (:) [Write-Error], WriteErrorException\n    + FullyQualifiedErrorId : Microsoft.PowerShell.Commands.WriteErrorException,Invoke-ExternalChecked\n \n"
}
```

### T06 README 修复断链后必须通过
- Status: **pass**
- Expectation: contract check should pass after link fix
- Evidence:
```json
{
  "rc": 0,
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks] ok (no git diff detected)\n[verify_repo] contract checks\n[contract_checks] schema presence ok\n[contract_checks] meta schema_version ok\n[contract_checks] readme links ok\n[contract_checks] unique Graph Spider implementation ok\n[verify_repo] doc index check (sync doc links --check)\n[sync_doc_links] ok\n[verify_repo] tests\n[tests] ok (10 cases)\n[verify_repo] OK\n",
  "stderr_tail": ""
}
```

### T07 doc link check（无改动应通过）
- Status: **pass**
- Expectation: sync_doc_links --check should pass with no diff
- Evidence:
```json
{
  "rc": 0,
  "stdout_tail": "[sync_doc_links] ok\n",
  "stderr_tail": "",
  "diff_names": ""
}
```

### T08 doc link 同步可预测（产生固定 diff）
- Status: **pass**
- Expectation: sync write should repair tampered README doc-index block, then --check should pass
- Evidence:
```json
{
  "write_rc": 0,
  "check_rc": 0,
  "write_out": "[sync_doc_links] updated: README.md\n",
  "check_out": "[sync_doc_links] ok\n",
  "diff": "",
  "wrote_update": true
}
```

### T09 助手 init-task 生成 CURRENT.md
- Status: **pass**
- Expectation: CURRENT.md should contain acceptance checklist
- Evidence:
```json
{
  "rc": 0,
  "stdout": "[ok] task: meta\\tasks\\20260218-214112-hitbox-fix.md\n[ok] current: meta\\tasks\\CURRENT.md\n",
  "current_head": "# Task — hitbox-fix\n\n## Context\n- Why are we doing this?\n\n## Acceptance (must be checkable)\n- [ ] DoD written (this file complete)\n- [ ] Research logged (if needed): meta/externals/YYYYMMDD-hitbox-fix.md\n- [ ] Code changes allowed\n- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly\n- [ ] `scripts/verify_repo.*` passes\n- [ ] Demo report updated: `meta/reports/LAST.md`\n\n## Plan\n1) Spec-first (docs/spec/meta)\n2) Implement (code if allowed)\n3) Verify (verify_repo)\n4) Record (problem_registry / decision_log if needed)\n5) Demo (LAST.md + TRACE)\n"
}
```

### T10 助手 init-externals 生成外部调研模板
- Status: **pass**
- Expectation: externals file should be generated with template sections
- Evidence:
```json
{
  "rc": 0,
  "stdout": "[ok] externals: meta\\externals\\20260218-cytoscape-layout.md\n",
  "file": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_gate_matrix_sandbox/meta/externals/20260218-cytoscape-layout.md",
  "head": "# Externals Review — cytoscape-layout <topic>\n\n## Goal\n- \n\n## Constraints\n- Offline only?:\n- License constraints?:\n- Must support Windows?:\n- Must be vendorable?:\n\n## Candidates\n### A) <name>\n- Link:\n- License:\n- Activity (last commit / releases):\n- Bundle size / deps:\n- Integration plan (exact files / APIs):\n- Pros:\n- Cons:"
}
```

### T11 助手 print-prompt 输出必须阅读清单
- Status: **pass**
- Expectation: stdout should include required reading/order format blocks
- Evidence:
```json
{
  "rc": 0,
  "stdout": "/adlc_forge_full_bundle/runs/_gate_matrix_sandbox/ai_context/00_AI_CONTRACT.md\n\n# CTCP / SDDAI �� AI Contract (Hard Rules)\n\n���ļ��ǡ����̻�Լ������ڣ��ýű����Ž��� agent ��Ϊ�̶�������\n\n---\n\n## A. Ŀ��̬����Ҫ�ﵽʲô��\n\n��ֻ�ṩһ��Ŀ�꣨Goal����ϵͳ����������\n\n1) �Լ���� �� �Լ��ƽ� �� �Լ����� �� �Լ���¼  \n2) ֻ�ڡ������������/�ṩ��Ϣ��ʱ����  \n3) �����ɻط���ʾ������ʲô��Ϊʲô����θ��֡���֤���\n\n---\n\n## B. �����������/ά����\n\n- ���񵥣�`meta/tasks/CURRENT.md`\n- ���м�¼������Ҫ����`meta/externals/<date>-*.md`\n- ���а���`meta/runs/<timestamp>/`\n  - `PROMPT.md`���� coding agent �����루Ψһ��\n  - `QUESTIONS.md`���������⣨Ψһ��������������\n  - `TRACE.md`��ȫ������־����ʾ��\n- ��ʾ���棺`meta/reports/LAST.md`\n- ������䣺`ai_context/problem_registry.md`\n- ���߼�¼��`ai_context/decision_log.md`\n\n---\n\n## C. ǿ���Ž����� verify_repo ִ�У�\n\n### C1) ��ֹ���루Ĭ�ϣ�\n�� `meta/tasks/CURRENT.md` δ��ѡ `[x] Code changes allowed` ǰ��\n- ������docs/ specs/ meta/ ai_context/ ��\n- ��ֹ��src/ include/ web/ scripts/ tools/ CMakeLists.txt package*.json ��\n\n### C2) Ψһ�������\nֻ�� `scripts/verify_repo.*`��\n\n### C3) �ĵ���������ͬ��\n`scripts/sync_doc_links.py --check` ����ͨ����README �� Doc Index �������һ�£���\n\n---\n\n## D. ���ʲ��ԣ��������أ�\n\n��������������һ���������򲻵����ʣ�\n\n1) ��Ҫ���ṩ��Կ/Ȩ��  \n2) ��Ҫ���ڻ��ⷽ�����İ�  \n3) ȱ�ٹؼ�Լ�������޷�����\n\n���ʱ���д�� `meta/runs/<ts>/QUESTIONS.md`����������\n- ����\n- ��ѡ�� A/B/C�������ף�\n- Ĭ�Ͻ��飨����㲻�أ�ϵͳ����Ĭ�ϼ�����\n\n---\n\n## E. ��ʾ��ʽ�����һ��Ҫ�ܡ�������ʾ����\n\n`meta/reports/LAST.md` �ṹ�̶���\n\n1. Goal\n2. Readlist\n3. Plan\n4. Timeline / Trace pointer\n5. Changes (file list)\n6. Verify (commands + output)\n7. Open questions (if any)\n8. Next steps\n\n\n",
  "stderr": ""
}
```

### T12 Windows build 脚本存在且可执行
- Status: **skip**
- Expectation: requires build toolchain in environment
- Evidence:
```json
{
  "reason": "missing dependency: C++ compiler"
}
```

### T13 verify_repo 是唯一主 gate（覆盖 workflow+contract+doclinks）
- Status: **pass**
- Expectation: verify_repo output should contain expected sequence
- Evidence:
```json
{
  "rc": 0,
  "positions": [
    0,
    231,
    316,
    514
  ],
  "stdout_tail": "[verify_repo] repo root: D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\n[verify_repo] Qt6 SDK not found; skipping C++ build\n[verify_repo] no web frontend detected (web/package.json missing)\n[verify_repo] workflow gate (workflow checks)\n[workflow_checks] ok (no code changes)\n[verify_repo] contract checks\n[contract_checks] schema presence ok\n[contract_checks] meta schema_version ok\n[contract_checks] readme links ok\n[contract_checks] unique Graph Spider implementation ok\n[verify_repo] doc index check (sync doc links --check)\n[sync_doc_links] ok\n[verify_repo] tests\n[tests] ok (10 cases)\n[verify_repo] OK\n",
  "stderr_tail": ""
}
```

### T14 单击选中节点（只测选中态）
- Status: **pass**
- Expectation: single click should select node target
- Evidence:
```json
{
  "hit": {
    "kind": "node",
    "id": "a",
    "dist": 1.4142135623730951,
    "reason": "node_hit"
  },
  "state": {
    "selected_kind": "node",
    "selected_id": "a",
    "last_click_target": {
      "kind": "node",
      "id": "a"
    },
    "last_click_count": 1
  }
}
```

### T15 二次点击钻取（只测 drilldown）
- Status: **pass**
- Expectation: double click on node should emit drilldown action
- Evidence:
```json
{
  "transition": {
    "action": "drilldown",
    "target_id": "c",
    "reason": "double_click_node"
  }
}
```

### T16 Ctrl+点击打开文件（只测 open-file 动作）
- Status: **pass**
- Expectation: ctrl+click file node should request open_file(path)
- Evidence:
```json
{
  "action": {
    "action": "open_file",
    "path": "src/main.cpp",
    "reason": "ctrl_click_file_node"
  }
}
```

### T17 滚轮缩放（只测 zoom）
- Status: **pass**
- Expectation: zoom_update should follow exp wheel formula with clamp
- Evidence:
```json
{
  "new_scale": 0.8057353018734796,
  "expected": 0.8057353018734796,
  "params": {
    "zoom_k": 0.0018,
    "min_scale": 0.18,
    "max_scale": 5.0
  }
}
```

### T18 节点命中优先级（只测 node>edge）
- Status: **pass**
- Expectation: when node and edge both hit, node should win
- Evidence:
```json
{
  "hit": {
    "kind": "node",
    "id": "c",
    "dist": 1.0,
    "reason": "node_hit"
  },
  "params": {
    "node_radius_px": 8.0,
    "edge_radius_px": 5.0,
    "node_priority": true,
    "distance_metric": "pixel_to_world"
  }
}
```

### T19 边命中半径（只测 edge hitbox）
- Status: **pass**
- Expectation: edge hit should be inside/at threshold and miss outside threshold
- Evidence:
```json
{
  "near": {
    "kind": "edge",
    "id": "e_ab",
    "dist": 4.0,
    "reason": "edge_hit"
  },
  "mid": {
    "kind": "edge",
    "id": "e_ab",
    "dist": 5.0,
    "reason": "edge_hit"
  },
  "far": {
    "kind": "none",
    "id": null,
    "dist": null,
    "reason": "miss"
  },
  "params": {
    "node_radius_px": 0.0,
    "edge_radius_px": 5.0,
    "node_priority": true,
    "distance_metric": "pixel_to_world"
  }
}
```

### T20 缩放后命中一致（只测 hitbox 随 scale）
- Status: **pass**
- Expectation: pixel_to_world rule: higher scale shrinks world-space hit radius
- Evidence:
```json
{
  "scale_1": {
    "kind": "edge",
    "id": "e_ab",
    "dist": 3.0,
    "reason": "edge_hit"
  },
  "scale_2": {
    "kind": "none",
    "id": null,
    "dist": null,
    "reason": "miss"
  },
  "params": {
    "node_radius_px": 0.0,
    "edge_radius_px": 4.0,
    "node_priority": true,
    "distance_metric": "pixel_to_world"
  }
}
```

### T22 SimLab S01 init task
- Status: **pass**
- Expectation: S01_init_task should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S01_init_task",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S01_init_task/TRACE.md",
  "bundle": "",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T23 SimLab S02 doc-first gate
- Status: **pass**
- Expectation: S02_doc_first_gate should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S02_doc_first_gate",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S02_doc_first_gate/TRACE.md",
  "bundle": "",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T24 SimLab S03 doc index check
- Status: **pass**
- Expectation: S03_doc_index_check should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S03_doc_index_check",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S03_doc_index_check/TRACE.md",
  "bundle": "",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T25 SimLab S04 assistant --force
- Status: **pass**
- Expectation: S04_assistant_force should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S04_assistant_force",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S04_assistant_force/TRACE.md",
  "bundle": "",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T26 SimLab S05 run artifacts
- Status: **pass**
- Expectation: S05_run_artifacts should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S05_run_artifacts",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S05_run_artifacts/TRACE.md",
  "bundle": "",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T27 SimLab S06 failure bundle
- Status: **pass**
- Expectation: S06_failure_bundle should pass in headless environment
- Evidence:
```json
{
  "scenario_id": "S06_failure_bundle",
  "status": "pass",
  "trace": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S06_failure_bundle/TRACE.md",
  "bundle": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113/S06_failure_bundle/failure_bundle.zip",
  "run_dir": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-214113",
  "simlab_summary_path": "D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_suite_summary.json"
}
```

### T21 clean zip 不包含临时文件
- Status: **pass**
- Expectation: zip should exclude _tmp_patch.py/patch_debug.txt/*.bak
- Evidence:
```json
{
  "rc": 0,
  "stdout": "[ok] wrote D:\\.c_projects\\adc\\ctcp\\tests\\fixtures\\adlc_forge_full_bundle\\runs\\_gate_matrix_sandbox\\dist\\clean_repo_matrix.zip\n",
  "stderr": "",
  "zip_exists": true,
  "contains_bad": false
}
```
