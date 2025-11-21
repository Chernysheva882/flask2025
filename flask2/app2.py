from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
import hashlib
import json
from datetime import datetime
import mimetypes

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(APP_DIR, "uploads")
DB_PATH = os.path.join(APP_DIR, "db.json")
TMP_DIR = os.path.join(APP_DIR, "tmp")
BLACKLIST_EXT = {".exe", ".sh", ".php", ".js", ".bat", ".cmd"}

os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "replace-with-secure-random-secret"

def load_db():
    if not os.path.exists(DB_PATH):
        return {"files": []}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def md5_of_file(path, chunk_size=8192):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def ext_allowed(filename):
    return os.path.splitext(filename.lower())[1] not in BLACKLIST_EXT

def storage_path_for_uuid(uhex, ext):
    a = uhex[0:2]
    b = uhex[2:4]
    d = os.path.join(UPLOAD_ROOT, a, b)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{uhex}{ext}")

@app.route("/")
def index():
    db = load_db()
    files = sorted(db.get("files", []), key=lambda x: x.get("upload_time"), reverse=True)
    return render_template("index2.html", files=files)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for("index"))
    f = request.files["file"]
    if f.filename == "":
        flash("Файл не выбран", "error")
        return redirect(url_for("index"))

    orig = secure_filename(f.filename)
    if not ext_allowed(orig):
        flash(f"Запрещённое расширение: {os.path.splitext(orig)[1]}", "error")
        return redirect(url_for("index"))

    tmp_name = os.path.join(TMP_DIR, uuid.uuid4().hex)
    f.save(tmp_name)

    try:
        file_md5 = md5_of_file(tmp_name)
        db = load_db()
        if any(item["md5"] == file_md5 for item in db.get("files", [])):
            os.remove(tmp_name)
            flash("Файл уже загружен (дубликат по MD5)", "error")
            return redirect(url_for("index"))

        uhex = uuid.uuid4().hex
        ext = os.path.splitext(orig)[1].lower()
        dest = storage_path_for_uuid(uhex, ext)
        os.replace(tmp_name, dest)

        entry = {
            "uuid_name": f"{uhex}{ext}",
            "uuid_hex": uhex,
            "original_name": orig,
            "upload_time": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            "path": os.path.relpath(dest, APP_DIR).replace("\\", "/"),
            "ext": ext,
            "md5": file_md5,
        }

        db.setdefault("files", []).append(entry)
        save_db(db)

        flash("Файл успешно загружен", "success")
        return redirect(url_for("index"))
    except Exception as e:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass
        flash(f"Ошибка при загрузке: {e}", "error")
        return redirect(url_for("index"))

@app.route("/uploads/<path:relpath>")
def uploaded_file(relpath):
    full = os.path.join(APP_DIR, relpath)
    if not os.path.exists(full):
        return "Файл не найден", 404
    directory = os.path.dirname(full)
    filename = os.path.basename(full)
    return send_from_directory(directory, filename, as_attachment=False)
if __name__ == "__main__":
    app.run(debug=True)
