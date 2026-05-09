from __future__ import annotations

import re


def semantic_project_slug(text: str) -> str:
    source = str(text or "").strip().lower()
    tokens: list[str] = []
    rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("voice", ("voice", "speech", "语音", "说话", "口述")),
        ("assistant", ("assistant", "助理", "助手")),
        ("mobile", ("mobile", "phone", "手机")),
        ("pc", ("电脑", "computer", "pc")),
        ("web", ("web", "browser", "网页", "浏览器", "http")),
        ("whitelist", ("whitelist", "白名单")),
        ("control", ("control", "remote", "操控", "控制", "连接")),
    )
    for token, markers in rules:
        if any(marker in source for marker in markers):
            tokens.append(token)
    if "voice" in tokens and ("assistant" in tokens or ("control" in tokens and ("mobile" in tokens or "pc" in tokens))):
        return "voice-assistant"
    ascii_words = re.findall(r"[a-z0-9]+", source)
    weak_artifact_words = {
        "api",
        "app",
        "browser",
        "docs",
        "http",
        "local",
        "project",
        "readme",
        "script",
        "scripts",
        "service",
        "test",
        "tests",
        "ui",
        "web",
    }
    meaningful_ascii = [word for word in ascii_words if word not in weak_artifact_words]
    if tokens and not meaningful_ascii:
        return "-".join(dict.fromkeys(tokens[:4]))
    value = re.sub(r"[^a-z0-9_-]+", "-", source)
    value = re.sub(r"-+", "-", value).strip("-")
    if value and tokens and all(part in weak_artifact_words for part in value.replace("_", "-").split("-") if part):
        return "-".join(dict.fromkeys(tokens[:4]))
    return value or "goal"
