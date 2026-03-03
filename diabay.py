#!/usr/bin/env python3
"""
DiaBay — Scanned slide optimizer CLI.

Usage:
    python diabay.py /path/to/scans              # Process all TIFFs
    python diabay.py /path/to/scans -r           # Include subdirectories
    python diabay.py /path/to/scans --review     # Open review page
    python diabay.py /path/to/output --export    # Export high-res JPEGs
"""
import argparse
import collections
import json
import logging
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Lock

import cv2
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except AttributeError:
    os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import numpy as np
from rich.color import Color
from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.style import Style
from rich.text import Text

from rename import get_timestamp_name
from orient import detect_orientation, apply_rotation
from enhance import enhance_image

console = Console()
logger = logging.getLogger("diabay")

SUPPORTED_EXTENSIONS = {".tif", ".tiff", ".TIF", ".TIFF"}

# Review server request log (shared between Flask thread and display)
_review_logs = collections.deque(maxlen=200)
_review_log_lock = Lock()


class _LiveDisplay:
    """Combined live display: URL + preview + progress bar + log panel."""

    def __init__(self, progress, review_url):
        self.progress = progress
        self.review_url = review_url
        self.preview = None
        self.show_all_logs = False

    def __rich_console__(self, console, options):
        yield Text.assemble(("Review: ", "dim"), (self.review_url, "bold cyan"))
        if self.preview is not None:
            yield self.preview
        yield self.progress
        with _review_log_lock:
            total = len(_review_logs)
            lines = list(_review_logs) if self.show_all_logs else list(_review_logs)[-4:]
        content = "\n".join(lines) if lines else "[dim]Waiting for requests...[/dim]"
        hint = ""
        if total > 4:
            hint = " | Ctrl+O: collapse" if self.show_all_logs else " | Ctrl+O: show all"
        yield Panel(
            content, title="[bold]Review Server[/bold]",
            subtitle=f"[dim]{total} requests{hint}[/dim]",
            border_style="dim blue", padding=(0, 1),
        )


class _LogDisplay:
    """Post-processing display: log panel only."""

    def __init__(self, review_url):
        self.review_url = review_url
        self.show_all_logs = False

    def __rich_console__(self, console, options):
        with _review_log_lock:
            total = len(_review_logs)
            lines = list(_review_logs) if self.show_all_logs else list(_review_logs)[-4:]
        content = "\n".join(lines) if lines else "[dim]Waiting for requests...[/dim]"
        hint = ""
        if total > 4:
            hint = " | Ctrl+O: collapse" if self.show_all_logs else " | Ctrl+O: show all"
        yield Panel(
            content,
            title=f"[bold]Review Server[/bold] — {self.review_url}",
            subtitle=f"[dim]{total} requests{hint} | Ctrl+C: exit[/dim]",
            border_style="blue", padding=(0, 1),
        )


def render_preview(img: np.ndarray, display: _LiveDisplay):
    """Build half-block preview and update the live display (replaced in-place)."""
    term_h = console.size.height
    term_w = console.size.width
    # Reserve: URL(1) + progress(1) + log panel(6) + padding(2) = 10 lines
    max_h = max(5, term_h - 10)
    max_w = min(120, term_w - 2)

    h, w = img.shape[:2]
    scale = min(max_w / w, (max_h * 2) / h)
    width = max(1, int(w * scale))
    new_h = max(2, int(h * scale) // 2 * 2)
    small = cv2.resize(img, (width, new_h), interpolation=cv2.INTER_AREA)
    small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    text = Text()
    for y in range(0, new_h, 2):
        for x in range(width):
            top = tuple(small[y, x])
            bot = tuple(small[y + 1, x]) if y + 1 < new_h else top
            text.append("\u2580", style=Style(color=Color.from_rgb(*top), bgcolor=Color.from_rgb(*bot)))
        if y + 2 < new_h:
            text.append("\n")
    display.preview = text


def sanitize_prefix(name: str) -> str:
    """Sanitize a directory name for use as filename prefix."""
    s = re.sub(r'[^\w\-]', '_', name)
    s = re.sub(r'_+', '_', s).strip('_')
    return s


def find_tiffs(input_dir: Path, recursive: bool) -> list[tuple[Path, str]]:
    """
    Find TIFF files. Returns list of (path, prefix) tuples.
    prefix is empty for top-level files, or the sanitized subdirectory name.
    """
    results = []

    if recursive:
        subdirs = sorted(d for d in input_dir.iterdir() if d.is_dir() and not d.name.startswith('.'))
        with console.status("Scanning directories...") as status:
            status.update("Scanning top-level files...")
            for p in sorted(input_dir.iterdir()):
                if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
                    results.append((p, ""))

            for i, subdir in enumerate(subdirs, 1):
                status.update(f"Scanning [{i}/{len(subdirs)}] {subdir.name}")
                for p in sorted(subdir.rglob("*")):
                    if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
                        rel = p.parent.relative_to(input_dir)
                        parts_prefix = sanitize_prefix("_".join(rel.parts))
                        results.append((p, parts_prefix))
    else:
        with console.status("Scanning for TIFFs..."):
            for p in sorted(input_dir.iterdir()):
                if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
                    results.append((p, ""))

    return results


def load_manifest(output_dir: Path) -> dict:
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        text = manifest_path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Handle truncated/extra data from interrupted writes on slow mounts
            obj, _ = json.JSONDecoder().raw_decode(text)
            logger.warning("Manifest had trailing data — loaded first valid JSON object")
            return obj
    return {"images": {}}


def save_manifest(output_dir: Path, manifest: dict):
    manifest_path = output_dir / "manifest.json"
    tmp_path = manifest_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(manifest, indent=2))
    tmp_path.replace(manifest_path)


def make_thumbnail(img, thumb_path: Path, size: int = 320):
    h, w = img.shape[:2]
    scale = size / max(h, w)
    thumb = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])


def _copy_file(src: Path, dst: Path):
    """Copy file with manual byte copy (avoids sendfile failures on drvfs)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        while chunk := fsrc.read(1024 * 1024):
            fdst.write(chunk)


def _is_remote_path(path: Path) -> bool:
    """Check if a path is on a slow mount (drvfs/NTFS, NFS, etc.)."""
    s = str(path.resolve())
    return s.startswith("/mnt/") or s.startswith("/media/")


class OutputWriter:
    """
    Writes files to the final output directory in a background thread.
    If output is on a slow mount, processing happens in a local temp dir
    and files are copied out in parallel.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.use_local = _is_remote_path(output_dir)
        self._queue: Queue = Queue()
        self._errors: list = []
        self._worker: Thread | None = None
        self._pending = 0

        if self.use_local:
            self._tmpdir = tempfile.mkdtemp(prefix="diabay_")
            self.local_dir = Path(self._tmpdir)
            console.print(f"Using local temp: [bold]{self.local_dir}[/bold] (async copy to {output_dir})")
            self._worker = Thread(target=self._copy_loop, daemon=True)
            self._worker.start()
        else:
            self.local_dir = output_dir

    def get_work_dir(self) -> Path:
        """Return the directory to write processed files to (local or final)."""
        return self.local_dir

    def queue_copy(self, local_path: Path, final_path: Path):
        """Queue a file to be copied from local temp to final output."""
        if self.use_local:
            self._pending += 1
            self._queue.put((local_path, final_path))
        # If not using local temp, files are already in the right place

    def _copy_loop(self):
        """Background worker that copies files to the final output."""
        while True:
            try:
                item = self._queue.get(timeout=1)
            except Empty:
                continue
            if item is None:  # Shutdown signal
                break
            local_path, final_path = item
            try:
                _copy_file(local_path, final_path)
                # Clean up local temp file after successful copy
                local_path.unlink(missing_ok=True)
            except Exception as e:
                self._errors.append((str(final_path), str(e)))
            finally:
                self._pending -= 1
                self._queue.task_done()

    def finish(self):
        """Wait for all pending copies and clean up."""
        if self.use_local:
            self._queue.join()  # Wait for all copies to finish
            self._queue.put(None)  # Shutdown signal
            self._worker.join()
            # Clean up empty temp dir
            try:
                os.rmdir(self._tmpdir)
            except OSError:
                pass
        return self._errors


def _start_review_background(output_dir: Path, port: int = 5555):
    """Start the review server as a background daemon thread."""
    from review import create_app
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app(output_dir)

    @app.after_request
    def _log_request(response):
        from flask import request as req
        ts = time.strftime("%H:%M:%S")
        with _review_log_lock:
            _review_logs.append(f"[dim]{ts}[/dim]  {req.method:4s} {req.path:30s} {response.status_code}")
        return response

    Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()
    return port


def process(input_dir: Path, output_dir: Path, preset: str, quality: int,
            skip_rename: bool, skip_orient: bool, skip_enhance: bool,
            recursive: bool, use_ai: bool = True):
    tiffs = find_tiffs(input_dir, recursive)
    if not tiffs:
        console.print(f"[red]No TIFF files found in {input_dir}{'  (use -r for subdirectories)' if not recursive else ''}[/red]")
        sys.exit(1)

    if recursive:
        dirs = set(p.parent for p, _ in tiffs)
        console.print(f"Found [bold]{len(tiffs)}[/bold] TIFF files across [bold]{len(dirs)}[/bold] directories")
    else:
        console.print(f"Found [bold]{len(tiffs)}[/bold] TIFF files in {input_dir}")

    console.print(f"Output: [bold]{output_dir.resolve()}[/bold]")

    # Ensure final output dirs exist
    for sub in ["enhanced", "thumbs"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)

    # Start review server in background
    review_port = _start_review_background(output_dir)
    review_url = f"http://localhost:{review_port}"

    writer = OutputWriter(output_dir)
    work_dir = writer.get_work_dir()

    # Create local work subdirs
    enhanced_dir = work_dir / "enhanced"
    thumbs_dir = work_dir / "thumbs"
    for d in [enhanced_dir, thumbs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(output_dir)

    # Build set of already-processed files for resume support
    already_done = set()
    for info in manifest["images"].values():
        already_done.add((info.get("original", ""), info.get("source_dir", "")))

    skipped = 0
    errors = []
    start_time = time.time()
    img_times = []

    STEPS = 4  # load, enhance, orient, save

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("| {task.fields[stats]}"),
        TimeElapsedColumn(),
    )
    display = _LiveDisplay(progress, review_url)
    task = progress.add_task("Starting...", total=STEPS, stats=f"0/{len(tiffs)}")
    done_count = 0

    with Live(display, console=console, auto_refresh=False) as live:
        for tiff, prefix in tiffs:
            label = f"{prefix}/{tiff.name}" if prefix else tiff.name

            # Skip if already processed
            if (tiff.name, str(tiff.parent)) in already_done:
                skipped += 1
                done_count += 1
                progress.update(task, stats=f"{done_count}/{len(tiffs)} ({skipped} skipped)")
                live.refresh()
                continue

            progress.update(task, description=f"{label}", completed=0)
            live.refresh()
            img_start = time.time()
            try:
                # Step 1: Build output stem name + load image
                if skip_rename:
                    stem = tiff.stem
                    if prefix:
                        stem = f"{prefix}_{stem}"
                else:
                    ts_name = get_timestamp_name(tiff)
                    stem = f"{prefix}_{ts_name}" if prefix else ts_name
                    if stem in manifest["images"]:
                        for i in range(1, 100):
                            candidate = f"{stem}_{i:02d}"
                            if candidate not in manifest["images"]:
                                stem = candidate
                                break

                img = cv2.imread(str(tiff), cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise RuntimeError(f"Failed to read {tiff}")
                progress.update(task, completed=1)
                live.refresh()

                # Step 2: Enhance (before rotation — clearer image for detection)
                if skip_enhance:
                    enhanced_img = img
                    used_preset = "none"
                    quality_score = 0.0
                    faces = 0
                    accelerator = "none"
                else:
                    result = enhance_image(img, preset, use_accelerator=use_ai)
                    enhanced_img = result.image
                    used_preset = result.preset
                    quality_score = result.quality_score
                    faces = result.faces_detected
                    accelerator = result.accelerator
                progress.update(task, completed=2)
                live.refresh()

                # Step 3: Detect rotation on enhanced image (faces are clearer now)
                if skip_orient:
                    rotation = 0
                else:
                    from orient import detect_orientation_faces
                    rotation = detect_orientation_faces(enhanced_img) or 0
                    if rotation != 0:
                        enhanced_img = apply_rotation(enhanced_img, rotation)
                progress.update(task, completed=3)
                render_preview(enhanced_img, display)
                live.refresh()

                # Step 4: Save enhanced JPEG + thumbnail
                enhanced_path = enhanced_dir / f"{stem}.jpg"
                cv2.imwrite(str(enhanced_path), enhanced_img, [cv2.IMWRITE_JPEG_QUALITY, quality])

                thumb_path = thumbs_dir / f"{stem}.jpg"
                make_thumbnail(enhanced_img, thumb_path)

                if writer.use_local:
                    writer.queue_copy(enhanced_path, output_dir / "enhanced" / f"{stem}.jpg")
                    writer.queue_copy(thumb_path, output_dir / "thumbs" / f"{stem}.jpg")

                manifest["images"][stem] = {
                    "original": tiff.name,
                    "source_dir": str(tiff.parent),
                    "prefix": prefix,
                    "rotation": rotation,
                    "preset": used_preset,
                    "quality_score": round(quality_score, 1),
                    "faces_detected": faces,
                    "accelerator": accelerator,
                }
                save_manifest(output_dir, manifest)

            except Exception as e:
                logger.error(f"Error processing {label}: {e}")
                errors.append((label, str(e)))

            done_count += 1
            img_times.append(time.time() - img_start)
            avg = sum(img_times) / len(img_times)
            remaining = (len(tiffs) - done_count) * avg
            mins, secs = divmod(int(remaining), 60)
            eta = f"{mins}m{secs:02d}s" if mins else f"{secs}s"
            progress.update(task, completed=STEPS,
                            stats=f"{done_count}/{len(tiffs)} | {avg:.1f}s/img | ETA {eta}")
            live.refresh()

    # Wait for background copies to finish
    if writer.use_local:
        console.print("Waiting for file copies to finish...")
    copy_errors = writer.finish()
    errors.extend(copy_errors)

    elapsed = time.time() - start_time
    processed = len(tiffs) - len(errors) - skipped
    console.print()
    summary = f"[bold green]Done![/bold green] {processed}/{len(tiffs)} images processed in {elapsed:.1f}s"
    if skipped:
        summary += f" ({skipped} skipped, already done)"
    console.print(summary)
    if errors:
        console.print(f"[bold red]{len(errors)} errors:[/bold red]")
        for name, err in errors:
            console.print(f"  {name}: {err}")

    # Keep review server alive with log panel
    log_display = _LogDisplay(review_url)
    try:
        import termios, tty, select
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            with Live(log_display, console=console, refresh_per_second=1):
                while True:
                    if select.select([sys.stdin], [], [], 0.5)[0]:
                        ch = sys.stdin.read(1)
                        if ch == '\x0f':  # Ctrl+O
                            log_display.show_all_logs = not log_display.show_all_logs
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (ImportError, OSError):
        # Fallback: no keyboard handling
        console.print(f"\nReview: [bold]{review_url}[/bold] — Ctrl+C to exit")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def _cv2_rotate(img, rotation):
    """Rotate image using cv2 (works on any bit depth)."""
    _CV2_ROTATE = {
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }
    if rotation in _CV2_ROTATE:
        return cv2.rotate(img, _CV2_ROTATE[rotation])
    return img


def export(output_dir: Path, force: bool = False):
    """Export high-res images from original TIFFs.

    Produces two versions per image:
      - highres/<stem>.jpg  — 8-bit JPEG, quality 98, 4:4:4 chroma
      - highres_jxl/<stem>.jxl — 16-bit JPEG XL, lossless

    Recovers the correct rotation by comparing the enhanced JPEG to the
    original TIFF (dimension check + pixel comparison).  One TIFF read per image.
    """
    from PIL import Image
    from enhance import convert_16bit_to_8bit
    try:
        import imagecodecs
        has_jxl = True
    except ImportError:
        has_jxl = False
        console.print("[yellow]imagecodecs not installed — skipping JXL export (pip install imagecodecs)[/yellow]")

    manifest = load_manifest(output_dir)
    if not manifest["images"]:
        console.print("[red]No images in manifest. Run processing first.[/red]")
        sys.exit(1)

    highres_dir = output_dir / "highres"
    jxl_dir = output_dir / "highres_jxl"
    enhanced_dir = output_dir / "enhanced"
    highres_dir.mkdir(parents=True, exist_ok=True)
    if has_jxl:
        jxl_dir.mkdir(parents=True, exist_ok=True)

    _PIL_ROTATE = {
        90: Image.Transpose.ROTATE_270,
        180: Image.Transpose.ROTATE_180,
        270: Image.Transpose.ROTATE_90,
    }

    entries = list(manifest["images"].items())
    skipped = 0
    recovered = 0
    errors = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("| {task.fields[stats]}"),
        TimeElapsedColumn(),
    )
    task = progress.add_task("Exporting...", total=len(entries), stats=f"0/{len(entries)}")

    with Live(progress, console=console, auto_refresh=True):
        for i, (stem, info) in enumerate(entries):
            progress.update(task, description=f"{stem}")
            orig_img_8bit = None
            try:
                original_path = Path(info["source_dir"]) / info["original"]
                enhanced_path = enhanced_dir / f"{stem}.jpg"
                jpg_path = highres_dir / f"{stem}.jpg"
                jxl_path = jxl_dir / f"{stem}.jxl" if has_jxl else None

                # --- Recover rotation from enhanced JPEG ---
                rotation = info.get("rotation", 0)
                if enhanced_path.exists():
                    enh_img = cv2.imread(str(enhanced_path), cv2.IMREAD_COLOR)
                    if enh_img is not None:
                        eh, ew = enh_img.shape[:2]

                        with Image.open(str(original_path)) as orig_pil:
                            ow, oh = orig_pil.size

                        # Dimension check: narrow to {0,180} or {90,270}
                        if ow == oh:
                            candidates = [0, 90, 180, 270]
                        elif (ew > eh) == (ow > oh):
                            candidates = [0, 180]
                        else:
                            candidates = [90, 270]

                        if len(candidates) == 1:
                            rotation = candidates[0]
                        else:
                            # Pixel comparison: load original, try candidates
                            orig_img_8bit = convert_16bit_to_8bit(
                                cv2.imread(str(original_path), cv2.IMREAD_UNCHANGED))
                            thumb_size = 64
                            enh_small = cv2.resize(enh_img, (thumb_size, thumb_size))

                            best_rotation = candidates[0]
                            best_diff = float("inf")
                            for angle in candidates:
                                rotated = apply_rotation(orig_img_8bit, angle) if angle != 0 else orig_img_8bit
                                rotated_small = cv2.resize(rotated, (thumb_size, thumb_size))
                                diff = np.mean(np.abs(enh_small.astype(float) - rotated_small.astype(float)))
                                if diff < best_diff:
                                    best_diff = diff
                                    best_rotation = angle
                            rotation = best_rotation

                        if rotation != info.get("rotation", 0):
                            info["rotation"] = rotation
                            recovered += 1
                            save_manifest(output_dir, manifest)

                # --- Skip if all outputs already exist with correct rotation ---
                need_jpg = force or not jpg_path.exists()
                need_jxl = has_jxl and (force or not jxl_path.exists())
                if not need_jpg and not need_jxl:
                    # Check existing JPG rotation matches
                    with Image.open(str(jpg_path)) as existing:
                        ex_w, ex_h = existing.size
                    with Image.open(str(original_path)) as orig_pil:
                        ow, oh = orig_pil.size
                    if rotation in (90, 270):
                        expected_landscape = oh > ow
                    else:
                        expected_landscape = ow > oh
                    if expected_landscape == (ex_w > ex_h):
                        skipped += 1
                        progress.update(task, advance=1, stats=f"{i+1}/{len(entries)} ({skipped} skipped)")
                        continue

                # --- Load original TIFF (once) ---
                raw_img = cv2.imread(str(original_path), cv2.IMREAD_UNCHANGED)
                if raw_img is None:
                    raise RuntimeError(f"Failed to read {original_path}")

                # --- JXL: 16-bit lossless, rotate with cv2 ---
                if need_jxl:
                    jxl_img = _cv2_rotate(raw_img, rotation)
                    # Convert BGR → RGB for JXL
                    jxl_img = cv2.cvtColor(jxl_img, cv2.COLOR_BGR2RGB)
                    jxl_data = imagecodecs.jpegxl_encode(jxl_img, lossless=True)
                    jxl_path.write_bytes(jxl_data)

                # --- JPG: 8-bit, quality 98, rotate with PIL ---
                if need_jpg or force:
                    if orig_img_8bit is None:
                        orig_img_8bit = convert_16bit_to_8bit(raw_img)
                    rgb = cv2.cvtColor(orig_img_8bit, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb)
                    if rotation in _PIL_ROTATE:
                        pil_img = pil_img.transpose(_PIL_ROTATE[rotation])
                    pil_img.save(str(jpg_path), "JPEG", quality=98, subsampling=0)

            except Exception as e:
                logger.error(f"Error exporting {stem}: {e}")
                errors.append((stem, str(e)))

            progress.update(task, advance=1, stats=f"{i+1}/{len(entries)} ({skipped} skipped)")

    processed = len(entries) - len(errors) - skipped
    dirs = str(highres_dir)
    if has_jxl:
        dirs += f" + {jxl_dir}"
    summary = f"[bold green]Done![/bold green] {processed} exported to {dirs}"
    if recovered:
        summary += f" ({recovered} rotations recovered)"
    if skipped:
        summary += f" ({skipped} skipped, unchanged)"
    console.print(summary)
    if errors:
        console.print(f"[bold red]{len(errors)} errors:[/bold red]")
        for name, err in errors:
            console.print(f"  {name}: {err}")


def main():
    parser = argparse.ArgumentParser(
        description="DiaBay — Scanned slide optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python diabay.py /path/to/scans\n"
               "  python diabay.py /path/to/scans -r -o /mnt/e/output\n"
               "  python diabay.py --review /mnt/e/output\n",
    )
    parser.add_argument("input_dir", type=Path, help="Folder with scanned TIFFs (or output dir with --review)")
    parser.add_argument("-o", "--output", type=Path, default=Path("./output"), help="Output folder (default: ./output)")
    parser.add_argument("-r", "--recursive", action="store_true", help="Include subdirectories (prefix dir name to filenames)")
    parser.add_argument("--preset", choices=["auto", "gentle", "balanced", "aggressive"], default="auto",
                        help="Enhancement preset (default: auto)")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality 1-100 (default: 95)")
    parser.add_argument("--review", action="store_true", help="Start review server instead of processing")
    parser.add_argument("--export", action="store_true", help="Export high-res JPEGs from original TIFFs (no enhancement)")
    parser.add_argument("--force", action="store_true", help="Re-export all images (ignore resume cache)")
    parser.add_argument("--skip-rename", action="store_true", help="Skip renaming step")
    parser.add_argument("--skip-orient", action="store_true", help="Skip orientation detection")
    parser.add_argument("--skip-enhance", action="store_true", help="Skip enhancement step")
    parser.add_argument("--no-ai", action="store_true", help="CLAHE only, skip OpenVINO/Real-ESRGAN")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )

    if args.review:
        from review import start_review_server
        start_review_server(args.input_dir)
    elif args.export:
        export(args.input_dir, force=args.force)
    else:
        if not args.input_dir.is_dir():
            console.print(f"[red]Not a directory: {args.input_dir}[/red]")
            sys.exit(1)
        process(args.input_dir, args.output, args.preset, args.quality,
                args.skip_rename, args.skip_orient, args.skip_enhance,
                args.recursive, use_ai=not args.no_ai)


if __name__ == "__main__":
    main()
