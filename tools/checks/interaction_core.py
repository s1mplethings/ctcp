#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any


def _dist_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    qx = ax + t * abx
    qy = ay + t * aby
    return math.hypot(px - qx, py - qy)


def _radius_in_world(px_radius: float, scale: float, metric: str) -> float:
    if metric == "pixel_to_world":
        safe_scale = max(scale, 1e-9)
        return px_radius / safe_scale
    return px_radius


def hit_test(graph: dict[str, Any], point: dict[str, float], scale: float, params: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    point_x = float(point["x"])
    point_y = float(point["y"])

    metric = str(params.get("distance_metric", "pixel_to_world"))
    node_radius_px = float(params.get("node_radius_px", 10.0))
    edge_radius_px = float(params.get("edge_radius_px", 6.0))
    node_priority = bool(params.get("node_priority", True))

    node_pad = _radius_in_world(node_radius_px, scale, metric)
    edge_hit_radius = _radius_in_world(edge_radius_px, scale, metric)

    node_by_id: dict[str, dict[str, Any]] = {str(n.get("id")): n for n in nodes if "id" in n}

    best_node_id: str | None = None
    best_node_dist = float("inf")
    for n in nodes:
        nx = float(n.get("x", 0.0))
        ny = float(n.get("y", 0.0))
        nr = float(n.get("r", 0.0))
        d = math.hypot(point_x - nx, point_y - ny)
        if d <= nr + node_pad and d < best_node_dist:
            best_node_dist = d
            best_node_id = str(n.get("id"))

    best_edge_id: str | None = None
    best_edge_dist = float("inf")
    for e in edges:
        eid = str(e.get("id", ""))
        polyline = e.get("polyline")
        points: list[tuple[float, float]] = []
        if isinstance(polyline, list) and len(polyline) >= 2:
            for p in polyline:
                if isinstance(p, dict) and "x" in p and "y" in p:
                    points.append((float(p["x"]), float(p["y"])))
        if len(points) < 2:
            src = node_by_id.get(str(e.get("src", e.get("source", ""))))
            dst = node_by_id.get(str(e.get("dst", e.get("target", ""))))
            if not src or not dst:
                continue
            points = [
                (float(src.get("x", 0.0)), float(src.get("y", 0.0))),
                (float(dst.get("x", 0.0)), float(dst.get("y", 0.0))),
            ]

        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            d = _dist_point_to_segment(point_x, point_y, ax, ay, bx, by)
            if d <= edge_hit_radius and d < best_edge_dist:
                best_edge_dist = d
                best_edge_id = eid

    node_hit = best_node_id is not None
    edge_hit = best_edge_id is not None
    if node_hit and (node_priority or not edge_hit):
        return {"kind": "node", "id": best_node_id, "dist": best_node_dist, "reason": "node_hit"}
    if edge_hit:
        return {"kind": "edge", "id": best_edge_id, "dist": best_edge_dist, "reason": "edge_hit"}
    return {"kind": "none", "id": None, "dist": None, "reason": "miss"}


def selection_update(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    new_state = dict(state)
    if event.get("type") != "click":
        return new_state

    target = event.get("target") or {}
    kind = target.get("kind")
    target_id = target.get("id")
    click_count = int(event.get("click_count", 1))

    if kind in {"node", "edge"} and target_id is not None:
        new_state["selected_kind"] = kind
        new_state["selected_id"] = str(target_id)
    else:
        new_state["selected_kind"] = None
        new_state["selected_id"] = None

    new_state["last_click_target"] = {
        "kind": kind if kind in {"node", "edge"} else "none",
        "id": None if target_id is None else str(target_id),
    }
    new_state["last_click_count"] = click_count
    return new_state


def drilldown_transition(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    _ = state
    if event.get("type") != "click":
        return {"action": "none", "target_id": None, "reason": "not_click"}
    target = event.get("target") or {}
    if int(event.get("click_count", 1)) >= 2 and target.get("kind") == "node" and target.get("id") is not None:
        return {"action": "drilldown", "target_id": str(target["id"]), "reason": "double_click_node"}
    return {"action": "none", "target_id": None, "reason": "condition_not_met"}


def ctrl_click_action(event: dict[str, Any], node_metadata: dict[str, Any]) -> dict[str, Any]:
    target = event.get("target") or {}
    modifiers = event.get("modifiers") or {}
    if target.get("kind") != "node":
        return {"action": "none", "path": None, "reason": "target_not_node"}
    if not bool(modifiers.get("ctrl", False)):
        return {"action": "none", "path": None, "reason": "ctrl_not_pressed"}

    node_id = str(target.get("id", ""))
    meta = node_metadata.get(node_id) or {}
    path = meta.get("path")
    is_file = bool(meta.get("is_file", False))
    if not is_file and isinstance(path, str):
        is_file = not path.endswith("/")

    if path and is_file:
        return {"action": "open_file", "path": str(path), "reason": "ctrl_click_file_node"}
    return {"action": "none", "path": None, "reason": "missing_file_path"}


def zoom_update(scale: float, wheel_delta: float, params: dict[str, Any]) -> float:
    zoom_k = float(params.get("zoom_k", 0.0018))
    min_scale = float(params.get("min_scale", 0.18))
    max_scale = float(params.get("max_scale", 5.0))
    factor = math.exp(-float(wheel_delta) * zoom_k)
    return max(min_scale, min(max_scale, float(scale) * factor))

