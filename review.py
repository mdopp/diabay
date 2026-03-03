"""
Flask review server for DiaBay.
Serves a single-page review UI for inspecting and correcting processed slides.
"""
import json
import logging
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock, Timer

from PIL import Image, ImageFile
from flask import Flask, render_template, send_from_directory, request, jsonify

ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)


def create_app(output_dir: Path) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    app.config["OUTPUT_DIR"] = output_dir

    _manifest_lock = Lock()

    def _manifest_path():
        return Path(app.config["OUTPUT_DIR"]) / "manifest.json"

    def _load_manifest():
        mp = _manifest_path()
        if mp.exists():
            text = mp.read_text()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                obj, _ = json.JSONDecoder().raw_decode(text)
                return obj
        return {"images": {}}

    def _save_manifest(manifest):
        mp = _manifest_path()
        tmp = mp.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, indent=2))
        for attempt in range(5):
            try:
                tmp.replace(mp)
                return
            except OSError:
                time.sleep(0.1 * (attempt + 1))
        # Last resort: direct write
        mp.write_text(json.dumps(manifest, indent=2))
        tmp.unlink(missing_ok=True)

    @app.route("/")
    def index():
        manifest = _load_manifest()
        return render_template("review.html", manifest=manifest)

    @app.route("/images/<path:filepath>")
    def serve_image(filepath):
        return send_from_directory(str(app.config["OUTPUT_DIR"]), filepath)

    # PIL transpose constants: ROTATE_90 = CCW 90°, ROTATE_270 = CW 90°
    _PIL_ROTATE = {
        90: Image.Transpose.ROTATE_270,    # CW 90°
        180: Image.Transpose.ROTATE_180,
        270: Image.Transpose.ROTATE_90,    # CCW 90°
    }

    def _rotate_one(stem, new_rotation, current_rotation, out):
        """Rotate a single enhanced JPEG + regenerate thumbnail."""
        delta = (new_rotation - current_rotation) % 360
        enhanced_path = out / "enhanced" / f"{stem}.jpg"
        if not enhanced_path.exists():
            return stem, {"error": "enhanced file not found"}

        try:
            img = Image.open(str(enhanced_path))
        except Exception:
            return stem, {"error": "read failed"}

        if delta in _PIL_ROTATE:
            img = img.transpose(_PIL_ROTATE[delta])

        img.save(str(enhanced_path), quality=95)

        thumb = img.copy()
        thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)
        thumb.save(str(out / "thumbs" / f"{stem}.jpg"), quality=80)

        return stem, {"status": "updated"}

    @app.route("/api/apply", methods=["POST"])
    def apply_corrections():
        """Rotate existing enhanced JPEGs — no re-enhancement needed."""
        data = request.get_json()
        corrections = data.get("corrections", {})
        out = Path(app.config["OUTPUT_DIR"])

        with _manifest_lock:
            manifest = _load_manifest()
            results = {}
            futures = []

            with ThreadPoolExecutor() as pool:
                for stem, new_rotation in corrections.items():
                    if stem not in manifest["images"]:
                        results[stem] = {"error": "not found"}
                        continue
                    current_rotation = manifest["images"][stem].get("rotation", 0)
                    if current_rotation == new_rotation:
                        results[stem] = {"status": "unchanged"}
                        continue
                    futures.append((stem, new_rotation,
                                    pool.submit(_rotate_one, stem, new_rotation, current_rotation, out)))

                for stem, new_rotation, fut in futures:
                    s, result = fut.result()
                    results[s] = result
                    if result.get("status") == "updated":
                        manifest["images"][s]["rotation"] = new_rotation

            _save_manifest(manifest)
        return jsonify({"ok": True, "results": results})

    return app


def start_review_server(output_dir: Path, port: int = 5555):
    app = create_app(output_dir)
    Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    print(f"Review server running at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
