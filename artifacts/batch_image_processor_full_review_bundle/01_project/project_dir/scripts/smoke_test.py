from __future__ import annotations

import importlib.util
import io
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _load_app_module():
    spec = importlib.util.spec_from_file_location("batch_image_processor_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _png_bytes(color: str, size: tuple[int, int]) -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    buf.seek(0)
    return buf


def main() -> int:
    app_module = _load_app_module()
    app = app_module.create_app()
    client = app.test_client()
    data = {
        "resize_mode": "fixed",
        "width": "900",
        "height": "600",
        "keep_aspect": "1",
        "scale_percent": "80",
        "output_format": "jpg",
        "quality": "78",
        "rename_rule": "prefix",
        "prefix": "catalog_",
        "images": [
            (_png_bytes("#cc6644", (1400, 900)), "alpha.png"),
            (_png_bytes("#3366aa", (1200, 1200)), "beta.png"),
            (_png_bytes("#44aa66", (1600, 1000)), "gamma.png"),
        ],
    }
    response = client.post("/process", data=data, content_type="multipart/form-data")
    text = response.get_data(as_text=True)
    assert response.status_code == 200, response.status_code
    assert "下载全部 ZIP" in text
    job_match = re.search(r"/download-zip/([a-z0-9]+)", text)
    assert job_match, text[:500]
    job_id = job_match.group(1)
    job = app_module.get_job(job_id)
    assert job is not None
    assert int(job.get("success_count", 0)) == 3, job
    processed_dir = app_module.PROCESSED_DIR / job_id
    outputs = sorted(path for path in processed_dir.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".png"})
    assert len(outputs) == 3, outputs
    assert any(path.suffix.lower() == ".zip" for path in processed_dir.iterdir()), list(processed_dir.iterdir())
    zip_response = client.get(f"/download-zip/{job_id}")
    assert zip_response.status_code == 200
    assert len(zip_response.data) > 100
    print(f"SMOKE PASS job={job_id} outputs={len(outputs)-1} zip_bytes={len(zip_response.data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
