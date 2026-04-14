from __future__ import annotations

import argparse
import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, Response, flash, redirect, render_template, request, send_file, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
UPLOADS_DIR = ARTIFACTS_DIR / "uploads"
PROCESSED_DIR = ARTIFACTS_DIR / "processed"
JOB_INDEX_PATH = ARTIFACTS_DIR / "jobs.json"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_SETTINGS = {
    "resize_mode": "fixed",
    "width": "1200",
    "height": "1200",
    "keep_aspect": "1",
    "scale_percent": "75",
    "output_format": "jpg",
    "quality": "82",
    "rename_rule": "prefix",
    "prefix": "batch_",
}

@dataclass
class JobFile:
    original_name: str
    stored_name: str
    processed_name: str
    output_format: str
    original_size: tuple[int, int]
    processed_size: tuple[int, int]
    original_bytes: int
    processed_bytes: int
    error: str = ""


def ensure_dirs() -> None:
    for path in (ARTIFACTS_DIR, UPLOADS_DIR, PROCESSED_DIR):
        path.mkdir(parents=True, exist_ok=True)
    if not JOB_INDEX_PATH.exists():
        JOB_INDEX_PATH.write_text("{}\n", encoding="utf-8")


def load_jobs() -> dict[str, Any]:
    ensure_dirs()
    try:
        data = json.loads(JOB_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def save_jobs(data: dict[str, Any]) -> None:
    ensure_dirs()
    JOB_INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def sanitize_prefix(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw or "").strip())
    return value[:40] or "batch"


def normalize_quality(raw: str) -> int:
    try:
        value = int(raw)
    except Exception:
        value = 82
    return min(95, max(30, value))


def normalize_dimension(raw: str, fallback: int) -> int:
    try:
        value = int(raw)
    except Exception:
        value = fallback
    return min(4000, max(1, value))


def normalize_scale(raw: str) -> int:
    try:
        value = int(raw)
    except Exception:
        value = 100
    return min(400, max(5, value))


def output_extension(fmt: str) -> str:
    return ".png" if fmt.lower() == "png" else ".jpg"


def build_output_name(*, original_name: str, index: int, rename_rule: str, prefix: str, ext: str) -> str:
    stem = secure_filename(Path(original_name).stem) or f"image_{index:02d}"
    if rename_rule == "preserve":
        target = stem
    elif rename_rule == "sequence":
        target = f"{stem}_{index:02d}"
    else:
        target = f"{prefix}{stem}"
    return f"{target}{ext}"


def transform_image(img: Image.Image, settings: dict[str, str]) -> Image.Image:
    mode = settings.get("resize_mode", "fixed")
    if mode == "ratio":
        scale_percent = normalize_scale(settings.get("scale_percent", "100"))
        w, h = img.size
        new_size = (max(1, int(w * scale_percent / 100)), max(1, int(h * scale_percent / 100)))
        return img.resize(new_size, Image.Resampling.LANCZOS)
    width = normalize_dimension(settings.get("width", "1200"), 1200)
    height = normalize_dimension(settings.get("height", "1200"), 1200)
    keep_aspect = settings.get("keep_aspect", "1") == "1"
    if keep_aspect:
        copy = img.copy()
        copy.thumbnail((width, height), Image.Resampling.LANCZOS)
        return copy
    return img.resize((width, height), Image.Resampling.LANCZOS)


def save_processed_image(img: Image.Image, path: Path, fmt: str, quality: int) -> None:
    if fmt == "png":
        img.save(path, format="PNG", optimize=True)
        return
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(path, format="JPEG", quality=quality, optimize=True)


def process_files(files: list[Any], form: dict[str, str]) -> tuple[str, dict[str, Any]]:
    ensure_dirs()
    job_id = uuid4().hex[:12]
    upload_dir = UPLOADS_DIR / job_id
    processed_dir = PROCESSED_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_fmt = "png" if str(form.get("output_format", "jpg")).lower() == "png" else "jpg"
    quality = normalize_quality(str(form.get("quality", "82")))
    rename_rule = str(form.get("rename_rule", "prefix")).strip().lower()
    prefix = sanitize_prefix(str(form.get("prefix", "batch_")))
    normalized = {
        "resize_mode": str(form.get("resize_mode", "fixed")),
        "width": str(normalize_dimension(str(form.get("width", "1200")), 1200)),
        "height": str(normalize_dimension(str(form.get("height", "1200")), 1200)),
        "keep_aspect": "1" if str(form.get("keep_aspect", "1")) == "1" else "0",
        "scale_percent": str(normalize_scale(str(form.get("scale_percent", "75")))),
        "output_format": output_fmt,
        "quality": str(quality),
        "rename_rule": rename_rule if rename_rule in {"preserve", "prefix", "sequence"} else "prefix",
        "prefix": prefix,
    }
    results: list[dict[str, Any]] = []
    successful_paths: list[Path] = []
    for idx, file_storage in enumerate(files, start=1):
        original_name = secure_filename(file_storage.filename or f"image_{idx:02d}.png")
        if not original_name or not allowed_file(original_name):
            results.append(asdict(JobFile(file_storage.filename or f"image_{idx:02d}", "", "", output_fmt, (0, 0), (0, 0), 0, 0, "unsupported file type")))
            continue
        stored_name = f"{idx:02d}_{original_name}"
        source_path = upload_dir / stored_name
        file_storage.save(source_path)
        try:
            with Image.open(source_path) as img:
                img.load()
                original_size = img.size
                transformed = transform_image(img, normalized)
                processed_name = build_output_name(original_name=original_name, index=idx, rename_rule=normalized["rename_rule"], prefix=prefix, ext=output_extension(output_fmt))
                target_path = processed_dir / processed_name
                save_processed_image(transformed, target_path, output_fmt, quality)
                successful_paths.append(target_path)
                results.append(asdict(JobFile(original_name, stored_name, processed_name, output_fmt, original_size, transformed.size, source_path.stat().st_size, target_path.stat().st_size)))
        except UnidentifiedImageError:
            results.append(asdict(JobFile(original_name, stored_name, "", output_fmt, (0, 0), (0, 0), source_path.stat().st_size if source_path.exists() else 0, 0, "invalid image content")))
        except Exception as exc:
            results.append(asdict(JobFile(original_name, stored_name, "", output_fmt, (0, 0), (0, 0), source_path.stat().st_size if source_path.exists() else 0, 0, str(exc))))
    zip_path = processed_dir / f"{job_id}_batch.zip"
    if successful_paths:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in successful_paths:
                zf.write(path, arcname=path.name)
    jobs = load_jobs()
    jobs[job_id] = {
        "job_id": job_id,
        "settings": normalized,
        "results": results,
        "success_count": sum(1 for item in results if not item.get("error")),
        "error_count": sum(1 for item in results if item.get("error")),
        "zip_name": zip_path.name if zip_path.exists() else "",
    }
    save_jobs(jobs)
    return job_id, jobs[job_id]


def get_job(job_id: str) -> dict[str, Any] | None:
    jobs = load_jobs()
    job = jobs.get(job_id)
    return job if isinstance(job, dict) else None


def file_path(job_id: str, filename: str, kind: str) -> Path:
    safe_name = secure_filename(filename)
    root = UPLOADS_DIR if kind == "original" else PROCESSED_DIR
    return (root / job_id / safe_name).resolve()


def create_app() -> Flask:
    ensure_dirs()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = "batch-image-processor-local"

    @app.get("/")
    def index() -> str:
        return render_template("index.html", settings=DEFAULT_SETTINGS, job=None, current_job_id="")

    @app.post("/process")
    def process() -> Response | str:
        files = request.files.getlist("images")
        valid_files = [item for item in files if item and item.filename]
        if not valid_files:
            flash("请至少上传一张 jpg/jpeg/png 图片。", "error")
            return redirect(url_for("index"))
        try:
            job_id, job = process_files(valid_files, request.form.to_dict())
        except Exception as exc:
            flash(f"处理失败：{exc}", "error")
            return redirect(url_for("index"))
        if int(job.get("success_count", 0)) <= 0:
            flash("没有成功处理任何图片，请检查输入格式。", "error")
        else:
            flash(f"处理完成：成功 {job['success_count']} 张，失败 {job['error_count']} 张。", "success")
        return render_template("index.html", settings=job["settings"], job=job, current_job_id=job_id)

    @app.get("/download/<job_id>/<filename>")
    def download(job_id: str, filename: str) -> Response:
        path = file_path(job_id, filename, "processed")
        if not path.exists():
            return Response("file not found", status=404)
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.get("/download-zip/<job_id>")
    def download_zip(job_id: str) -> Response:
        job = get_job(job_id)
        if not job:
            return Response("job not found", status=404)
        zip_name = str(job.get("zip_name", "")).strip()
        path = (PROCESSED_DIR / job_id / zip_name).resolve()
        if not zip_name or not path.exists():
            return Response("zip not found", status=404)
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.get("/preview/<kind>/<job_id>/<filename>")
    def preview(kind: str, job_id: str, filename: str) -> Response:
        if kind not in {"original", "processed"}:
            return Response("invalid preview kind", status=400)
        path = file_path(job_id, filename, kind)
        if not path.exists():
            return Response("preview not found", status=404)
        return send_file(path)

    return app


def run_server(host: str, port: int) -> int:
    app = create_app()
    app.run(host=host, port=port, debug=False)
    return 0


def self_check() -> int:
    ensure_dirs()
    print("Batch Image Processor is ready. Run `python app.py --serve` to launch the web UI.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch Image Processor")
    parser.add_argument("--serve", action="store_true", help="Run the local web server")
    parser.add_argument("--host", default=os.environ.get("BIP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BIP_PORT", "5085")))
    args = parser.parse_args(argv)
    if args.serve:
        return run_server(args.host, args.port)
    return self_check()


if __name__ == "__main__":
    raise SystemExit(main())
