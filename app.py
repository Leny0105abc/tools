from flask import Flask, render_template, request, send_file, jsonify, after_this_request
from pathlib import Path
from werkzeug.utils import secure_filename
import subprocess
import uuid
import shutil
import re

import msoffcrypto

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".xlsb"}

def unique_path(directory: Path, filename: str) -> Path:
    safe = secure_filename(filename) or "file"
    return directory / f"{uuid.uuid4().hex}_{safe}"

def cleanup_later(*paths):
    @after_this_request
    def remove_files(response):
        for p in paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
        return response

def ffmpeg_exists():
    return shutil.which("ffmpeg") is not None

def ytdlp_exists():
    return shutil.which("yt-dlp") is not None

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def status():
    return jsonify({"ffmpeg": ffmpeg_exists(), "yt_dlp": ytdlp_exists()})

@app.post("/api/youtube-to-mp4")
def youtube_to_mp4():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    confirm = bool(data.get("confirmRights"))

    if not url:
        return jsonify({"error": "Please enter a YouTube URL."}), 400
    if not confirm:
        return jsonify({"error": "Please confirm that you own the video or have permission to download it."}), 400
    if not re.match(r"^https?://", url, re.I):
        return jsonify({"error": "Please enter a valid URL beginning with http:// or https://."}), 400
    if not ytdlp_exists():
        return jsonify({"error": "yt-dlp is not installed on the server. Install it with: pip install yt-dlp"}), 500
    if not ffmpeg_exists():
        return jsonify({"error": "FFmpeg is not installed or not available in PATH."}), 500

    job_id = uuid.uuid4().hex
    template = str(OUTPUT_DIR / f"{job_id}_%(title).80s.%(ext)s")
    cmd = ["yt-dlp","--no-playlist","--restrict-filenames","--merge-output-format","mp4","-f","bv*+ba/b","-o",template,url]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Download timed out."}), 504
    except Exception as e:
        return jsonify({"error": f"Unable to start downloader: {e}"}), 500

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "Download failed.").strip()
        return jsonify({"error": msg[-1200:]}), 400

    matches = sorted(OUTPUT_DIR.glob(f"{job_id}_*.mp4")) or sorted(OUTPUT_DIR.glob(f"{job_id}_*"))
    if not matches:
        return jsonify({"error": "The video was processed but no output file was found."}), 500

    out = matches[0]
    cleanup_later(out)
    return send_file(out, as_attachment=True, download_name=out.name.split("_", 1)[-1])

@app.post("/api/mp4-to-mp3")
def mp4_to_mp3():
    if "file" not in request.files:
        return jsonify({"error": "Please upload a video file."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Please choose a file."}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"error": "Unsupported video format."}), 400
    if not ffmpeg_exists():
        return jsonify({"error": "FFmpeg is not installed or not available in PATH."}), 500

    src = unique_path(UPLOAD_DIR, f.filename)
    out = OUTPUT_DIR / f"{uuid.uuid4().hex}_{Path(secure_filename(f.filename)).stem}.mp3"
    f.save(src)

    cmd = ["ffmpeg","-y","-i",str(src),"-vn","-codec:a","libmp3lame","-q:a","2",str(out)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        src.unlink(missing_ok=True)
        return jsonify({"error": "Conversion timed out."}), 504

    if proc.returncode != 0 or not out.exists():
        src.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        msg = (proc.stderr or "Conversion failed.").strip()
        return jsonify({"error": msg[-1200:]}), 400

    cleanup_later(src, out)
    return send_file(out, as_attachment=True, download_name=f"{Path(f.filename).stem}.mp3")

@app.post("/api/unlock-excel")
def unlock_excel():
    if "file" not in request.files:
        return jsonify({"error": "Please upload an Excel file."}), 400

    f = request.files["file"]
    password = request.form.get("password", "")
    if not f.filename:
        return jsonify({"error": "Please choose an Excel file."}), 400
    if not password:
        return jsonify({"error": "Enter the current workbook password."}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXCEL_EXTENSIONS:
        return jsonify({"error": "Please upload a supported Excel file (.xlsx, .xlsm, .xls, .xlsb)."}), 400

    src = unique_path(UPLOAD_DIR, f.filename)
    out_name = f"{Path(secure_filename(f.filename)).stem}_unlocked{ext}"
    out = OUTPUT_DIR / f"{uuid.uuid4().hex}_{out_name}"
    f.save(src)

    try:
        with open(src, "rb") as encrypted:
            office = msoffcrypto.OfficeFile(encrypted)
            office.load_key(password=password)
            with open(out, "wb") as decrypted:
                office.decrypt(decrypted)
    except Exception:
        src.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        return jsonify({"error": "Could not unlock the workbook. Check that the file is encrypted and that the password is correct."}), 400

    cleanup_later(src, out)
    return send_file(out, as_attachment=True, download_name=out_name)

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "File is too large. Maximum upload size is 500 MB."}), 413

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
