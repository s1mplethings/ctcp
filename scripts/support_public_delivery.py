from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

DEFAULT_PUBLIC_DELIVERY_MODE = "telegram_live"
VIRTUAL_PUBLIC_DELIVERY_MODE = "e2e_virtual_delivery"
VIRTUAL_SENT_REL_DIR = Path("artifacts") / "support_exports" / "virtual_delivery" / "sent"


def resolve_public_delivery_mode(config: dict[str, Any] | None) -> str:
    if isinstance(config, dict):
        public_delivery = config.get("public_delivery", {})
        if isinstance(public_delivery, dict):
            mode = str(public_delivery.get("mode", "")).strip().lower()
            if mode:
                return mode
    return DEFAULT_PUBLIC_DELIVERY_MODE


def build_public_delivery_transport(*, config: dict[str, Any] | None, run_dir: Path, live_transport: Any) -> Any:
    mode = resolve_public_delivery_mode(config)
    if mode == VIRTUAL_PUBLIC_DELIVERY_MODE:
        return VirtualDeliveryTransport(run_dir=run_dir, mode=mode)
    return live_transport


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class VirtualDeliveryTransport:
    def __init__(self, *, run_dir: Path, mode: str = VIRTUAL_PUBLIC_DELIVERY_MODE) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.mode = mode

    def _deliver(self, *, delivery_type: str, chat_id: int, file_path: Path, caption: str = "") -> dict[str, Any]:
        source = Path(file_path).resolve()
        target_dir = self.run_dir / VIRTUAL_SENT_REL_DIR / ("documents" if delivery_type == "document" else "photos")
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = (target_dir / source.name).resolve()
        shutil.copy2(source, target_path)
        return {
            "transport": "virtual_delivery",
            "delivery_mode": self.mode,
            "delivered_path": str(target_path),
            "source_path": str(source),
            "chat_id": int(chat_id),
            "bytes": int(target_path.stat().st_size),
            "sha256": _sha256(target_path),
            "caption": str(caption or ""),
        }

    def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> dict[str, Any]:
        return self._deliver(delivery_type="document", chat_id=chat_id, file_path=file_path, caption=caption)

    def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> dict[str, Any]:
        return self._deliver(delivery_type="photo", chat_id=chat_id, file_path=file_path, caption=caption)


def auto_emit_virtual_delivery_for_ready_run(
    *,
    run_dir: Path,
    project_context: dict[str, Any] | None,
    public_delivery_mode: str = VIRTUAL_PUBLIC_DELIVERY_MODE,
) -> dict[str, Any]:
    from frontend.delivery_reply_actions import evaluate_delivery_completion, evaluate_overall_completion, evaluate_product_completion, inject_ready_delivery_actions
    from scripts.delivery_replay_validator import run_delivery_replay_check
    from scripts import ctcp_support_bot as support_bot

    manifest_path = (Path(run_dir).resolve() / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).resolve()
    if manifest_path.exists():
        existing = support_bot.read_json_doc(manifest_path)
        if isinstance(existing, dict):
            completion_gate = dict(existing.get("completion_gate", {})) if isinstance(existing.get("completion_gate", {}), dict) else {}
            overall_completion = dict(existing.get("overall_completion", {})) if isinstance(existing.get("overall_completion", {}), dict) else {}
            if bool(completion_gate.get("passed", False)) and bool(completion_gate.get("cold_replay_passed", False)) and bool(overall_completion.get("passed", False)):
                return {
                    "status": "existing",
                    "manifest_path": str(manifest_path),
                    "actions": list(existing.get("requested_actions", [])) if isinstance(existing.get("requested_actions", []), list) else [],
                    "delivery_state": {},
                    "plan": existing,
                    "completion_gate": completion_gate,
                    "delivery_completion": dict(existing.get("delivery_completion", {})) if isinstance(existing.get("delivery_completion", {}), dict) else completion_gate,
                    "product_completion": dict(existing.get("product_completion", {})) if isinstance(existing.get("product_completion", {}), dict) else evaluate_product_completion(existing.get("project_manifest")),
                    "overall_completion": overall_completion,
                }

    effective_context = dict(project_context) if isinstance(project_context, dict) else {}
    status_doc = dict(effective_context.get("status", {})) if isinstance(effective_context.get("status", {}), dict) else {}
    status_doc.setdefault("run_status", "pass")
    status_doc.setdefault("verify_result", "PASS")
    status_doc.setdefault("needs_user_decision", False)
    status_doc.setdefault("decisions_needed_count", 0)
    gate_doc = dict(status_doc.get("gate", {})) if isinstance(status_doc.get("gate", {}), dict) else {}
    gate_doc.setdefault("state", "pass")
    gate_doc.setdefault("owner", "")
    gate_doc.setdefault("reason", "")
    status_doc["gate"] = gate_doc
    effective_context["status"] = status_doc
    effective_context.setdefault("run_id", Path(run_dir).name)
    effective_context.setdefault("run_dir", str(run_dir))
    manifest_doc = support_bot.read_json_doc(Path(run_dir) / "artifacts" / "project_manifest.json")
    if isinstance(manifest_doc, dict) and not isinstance(effective_context.get("project_manifest"), dict):
        effective_context["project_manifest"] = manifest_doc

    session_state = {
        "bound_run_id": str(effective_context.get("run_id", "")).strip() or Path(run_dir).name,
        "bound_run_dir": str(run_dir),
    }
    delivery_state = support_bot.collect_public_delivery_state(
        session_state=session_state,
        project_context=effective_context,
        source=public_delivery_mode,
        support_run_dir=Path(run_dir),
    )
    actions = inject_ready_delivery_actions(
        actions=[],
        project_context=effective_context,
        delivery_state=delivery_state,
        source_hint=public_delivery_mode,
    )
    if not actions:
        return {
            "status": "skipped",
            "reason": "delivery artifacts not ready",
            "manifest_path": str(manifest_path),
            "actions": [],
            "delivery_state": delivery_state,
            "plan": {},
            "completion_gate": evaluate_delivery_completion([], {}, manifest_path=str(manifest_path), require_existing_files=True),
            "delivery_completion": evaluate_delivery_completion([], {}, manifest_path=str(manifest_path), require_existing_files=True),
            "product_completion": evaluate_product_completion(effective_context.get("project_manifest")),
            "overall_completion": evaluate_overall_completion(
                delivery_completion=evaluate_delivery_completion([], {}, manifest_path=str(manifest_path), require_existing_files=True),
                project_manifest=effective_context.get("project_manifest"),
            ),
        }

    config = {
        **support_bot.default_support_dispatch_config(),
        "public_delivery": {"mode": public_delivery_mode},
    }
    transport = build_public_delivery_transport(config=config, run_dir=Path(run_dir), live_transport=object())
    plan = support_bot.emit_public_delivery(
        transport,
        chat_id=0,
        run_dir=Path(run_dir),
        actions=actions,
        delivery_state=delivery_state,
    )
    plan = finalize_public_delivery_manifest(
        run_dir=Path(run_dir),
        actions=actions,
        plan=plan,
        replay_runner=run_delivery_replay_check,
    )
    completion_gate = dict(plan.get("completion_gate", {})) if isinstance(plan.get("completion_gate", {}), dict) else {}
    return {
        "status": "emitted" if bool(completion_gate.get("passed", False)) else "failed",
        "manifest_path": str(manifest_path),
        "actions": actions,
        "delivery_state": delivery_state,
        "plan": plan,
        "completion_gate": completion_gate,
        "delivery_completion": dict(plan.get("delivery_completion", {})) if isinstance(plan.get("delivery_completion", {}), dict) else completion_gate,
        "product_completion": dict(plan.get("product_completion", {})) if isinstance(plan.get("product_completion", {}), dict) else evaluate_product_completion(effective_context.get("project_manifest")),
        "overall_completion": dict(plan.get("overall_completion", {})) if isinstance(plan.get("overall_completion", {}), dict) else evaluate_overall_completion(delivery_completion=completion_gate, project_manifest=effective_context.get("project_manifest")),
    }


def auto_close_public_delivery_after_verify_pass(run_dir: Path) -> dict[str, Any]:
    return auto_emit_virtual_delivery_for_ready_run(
        run_dir=run_dir,
        project_context={
            "run_id": Path(run_dir).name,
            "run_dir": str(run_dir),
            "status": {
                "run_status": "pass",
                "verify_result": "PASS",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "pass", "owner": "", "reason": ""},
            },
        },
    )


def finalize_public_delivery_manifest(
    *,
    run_dir: Path,
    actions: list[dict[str, Any]] | None,
    plan: dict[str, Any] | None,
    replay_runner: Any | None = None,
) -> dict[str, Any]:
    from frontend.delivery_reply_actions import evaluate_delivery_completion, evaluate_overall_completion, evaluate_product_completion
    from scripts import ctcp_support_bot as support_bot
    from scripts.delivery_replay_validator import run_delivery_replay_check

    manifest_path = (Path(run_dir).resolve() / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).resolve()
    updated = dict(plan) if isinstance(plan, dict) else {}
    if not isinstance(updated.get("manifest_path"), str) or not str(updated.get("manifest_path", "")).strip():
        updated["manifest_path"] = str(manifest_path)
    document_path = str(dict(evaluate_delivery_completion(actions, updated, manifest_path=str(manifest_path), require_existing_files=True)).get("selected_document", "")).strip()
    replay_doc: dict[str, Any] = {}
    if document_path:
        replay_root = (Path(run_dir).resolve() / "artifacts" / "delivery_replay").resolve()
        runner = replay_runner or run_delivery_replay_check
        replay_doc = dict(runner(package_path=document_path, output_root=replay_root))
        replay_doc["report_path"] = str((replay_root / "replay_artifacts" / "replay_report.json").resolve())
    updated["replay_report"] = replay_doc
    delivery_completion = evaluate_delivery_completion(
        actions,
        updated,
        manifest_path=str(manifest_path),
        require_existing_files=True,
        require_cold_replay=True,
    )
    updated["completion_gate"] = delivery_completion
    updated["delivery_completion"] = delivery_completion
    project_manifest = support_bot.read_json_doc(Path(run_dir) / "artifacts" / "project_manifest.json")
    updated["product_completion"] = evaluate_product_completion(project_manifest)
    updated["overall_completion"] = evaluate_overall_completion(
        delivery_completion=delivery_completion,
        project_manifest=project_manifest,
    )
    support_bot.write_json(manifest_path, updated)
    return updated
