from __future__ import annotations

import json
from typing import Any

from tools.providers.project_generation_provenance_writer import provenance_json


def prefixed_files(project_root: str, files: dict[str, str]) -> dict[str, str]:
    root = str(project_root).strip().rstrip("/")
    return {f"{root}/{str(path).strip().lstrip('/')}": content for path, content in files.items()}


def static_asset_files(*, index_html: str, app_js: str, styles_css: str) -> dict[str, str]:
    return {
        "static/index.html": index_html,
        "static/app.js": app_js,
        "static/styles.css": styles_css,
    }


def standard_support_files(
    *,
    project_id: str,
    workflow_doc_rel: str,
    provenance: dict[str, Any],
    core_notes: str,
    workflow_notes: str,
    project_archetype: str = "concrete_fast_path",
) -> dict[str, str]:
    generation_mode = str(provenance.get("generation_mode", "concrete_fast_path"))
    return {
        "scripts/verify_repo.ps1": "$ErrorActionPreference = 'Stop'\npython -m unittest discover -v\n",
        "docs/00_CORE.md": core_notes,
        workflow_doc_rel: workflow_notes,
        "meta/manifest.json": json.dumps(
            {
                "schema_version": "ctcp-generated-project-manifest-v1",
                "project_id": project_id,
                "project_archetype": project_archetype,
                "generation_mode": generation_mode,
                "mainline": ["new-run", "status", "advance", "analysis", "source_generation", "project_output"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "provenance.json": provenance_json(provenance),
    }
