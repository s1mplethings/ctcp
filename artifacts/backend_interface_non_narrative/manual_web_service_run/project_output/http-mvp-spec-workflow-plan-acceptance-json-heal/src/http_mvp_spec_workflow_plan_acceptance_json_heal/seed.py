from __future__ import annotations
import json

DEFAULT_PROJECT_INTENT = json.loads(r'''{
  "goal_summary": "生成一个本地 HTTP 服务 MVP",
  "target_user": "内部项目发起人",
  "problem_to_solve": "把模糊项目目标转成结构化 spec/workflow/acceptance JSON 响应",
  "mvp_scope": [
    "提供 health 路径",
    "提供 generate 路径",
    "导出 spec、workflow、acceptance 结果"
  ],
  "required_inputs": [
    "用户目标"
  ],
  "required_outputs": [
    "service contract",
    "sample response",
    "acceptance report"
  ],
  "hard_constraints": [
    "delivery_shape=web_first"
  ],
  "assumptions": [
    "先做本地可运行的 JSON 服务 MVP"
  ],
  "open_questions": [],
  "acceptance_criteria": [
    "health 路径可用",
    "generate 路径返回结构化 JSON",
    "README 可指导启动"
  ]
}''')
DEFAULT_PROJECT_SPEC = json.loads(r'''{
  "schema_version": "ctcp-project-spec-v1",
  "goal_summary": "生成一个本地 HTTP 服务 MVP",
  "target_user": "内部项目发起人",
  "problem_to_solve": "把模糊项目目标转成结构化 spec/workflow/acceptance JSON 响应",
  "mvp_scope": [
    "提供 health 路径",
    "提供 generate 路径",
    "导出 spec、workflow、acceptance 结果"
  ],
  "required_inputs": [
    "用户目标"
  ],
  "required_outputs": [
    "service contract",
    "sample response",
    "acceptance report"
  ],
  "hard_constraints": [
    "delivery_shape=web_first"
  ],
  "assumptions": [
    "先做本地可运行的 JSON 服务 MVP"
  ],
  "open_questions": [],
  "acceptance_criteria": [
    "health 路径可用",
    "generate 路径返回结构化 JSON",
    "README 可指导启动"
  ],
  "constraint_snapshot": {
    "delivery_shape": "web_first"
  }
}''')
