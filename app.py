# -*- coding: utf-8 -*-
"""
ReelsForge 🎬🔥 — خادم الويب
أعطه رابط يوتيوب ➜ يعيد ريلزات 9:16 فيروسية مع عناوين وهاشتاغات جاهزة.
التشغيل:  python3 app.py   ثم افتح  http://localhost:8000
"""
import os
import re
import json
import uuid
import time
import shutil
import threading

from flask import Flask, request, jsonify, send_from_directory, send_file

from pipeline import run_pipeline, downloader

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUTS = os.path.join(BASE, "outputs")
os.makedirs(OUTPUTS, exist_ok=True)

app = Flask(__name__, static_folder="static")

JOBS = {}                 # job_id -> حالة المهمة
LOCK = threading.Lock()
WORK_SEM = threading.Semaphore(1)   # معالِج واحد في كل مرة (2 أنوية فقط)

YT_PAT = re.compile(
    r"(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)[\w\-]{6,}", re.I)


def _cleanup_old(keep=8):
    try:
        dirs = [os.path.join(OUTPUTS, d) for d in os.listdir(OUTPUTS)
                if os.path.isdir(os.path.join(OUTPUTS, d))]
        dirs.sort(key=lambda p: os.path.getmtime(p))
        while len(dirs) > keep:
            shutil.rmtree(dirs.pop(0), ignore_errors=True)
    except Exception:
        pass


def _worker(job_id, url, num_clips, clip_len, model):
    job = JOBS[job_id]
    jobdir = os.path.join(OUTPUTS, job_id)
    with WORK_SEM:
        job["state"] = "running"
        try:
            def cb(stage, pct, msg):
                job["stage"] = stage
                job["progress"] = int(pct)
                job["message"] = msg
                job["log"].append(msg)
                if len(job["log"]) > 60:
                    job["log"] = job["log"][-60:]

            result = run_pipeline(
                url, jobdir,
                num_clips=num_clips, clip_len=clip_len,
                whisper_model=model, cb=cb,
            )
            with open(os.path.join(jobdir, "results.json"), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=1)
            job["result"] = result
            job["state"] = "done"
            job["progress"] = 100
            job["message"] = "🎉 اكتمل التحويل!"
        except Exception as e:
            err = str(e)
            if "Sign in" in err or "confirm" in err or "bot" in err.lower():
                msg = "يوتيوب يمنع تحميل هذا الفيديو آلياً (يتطلب تحققاً). جرّب فيديو آخر."
            elif "unsupported URL" in err or "not a valid URL" in err:
                msg = "الرابط غير مدعوم. تأكد أنه رابط يوتيوب صحيح."
            elif "Video unavailable" in err or "Private video" in err:
                msg = "الفيديو غير متاح (محذوف أو خاص)."
            elif "age" in err.lower():
                msg = "الفيديو مقيّد بالعمر ولا يمكن تحميله آلياً."
            else:
                msg = f"حدث خطأ أثناء المعالجة: {err[:300]}"
            job["state"] = "error"
            job["message"] = msg
            job["log"].append(msg)


@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE, "static"), "index.html")


@app.post("/api/jobs")
def create_job():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    if not YT_PAT.search(url):
        return jsonify({"error": "الرابط غير صالح — أدخل رابط يوتيوب صحيحاً"}), 400
    num = max(1, min(6, int(data.get("num_clips", 3))))
    clen = max(15, min(60, int(data.get("clip_len", 30))))
    model = data.get("model", "auto")
    if model not in ("tiny", "base", "small", "auto"):
        model = "auto"

    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {
        "state": "queued", "stage": "queued", "progress": 0,
        "message": "في قائمة الانتظار…", "log": [], "result": None,
        "created": time.time(),
        "params": {"url": url, "num_clips": num, "clip_len": clen, "model": model},
    }
    _cleanup_old()
    t = threading.Thread(target=_worker, args=(job_id, url, num, clen, model),
                         daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "المهمة غير موجودة"}), 404
    out = {
        "state": job["state"], "stage": job["stage"],
        "progress": job["progress"], "message": job["message"],
        "log": job["log"][-8:],
    }
    if job["state"] == "done" and job["result"]:
        out["result"] = job["result"]
    return jsonify(out)


@app.get("/media/<job_id>/<path:fname>")
def media(job_id, fname):
    safe = re.sub(r"[^a-zA-Z0-9_\.\-]", "", job_id)
    return send_from_directory(os.path.join(OUTPUTS, safe), fname)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "jobs": len(JOBS),
                    "busy": any(j["state"] == "running" for j in JOBS.values())})


if __name__ == "__main__":
    port = int(os.environ.get("PORT",
                              "7860" if os.environ.get("SPACE_ID") else "8000"))
    try:
        from waitress import serve
        print(f"⚡ خادم إنتاج (waitress) يعمل على 0.0.0.0:{port} — وضع 24/7", flush=True)
        serve(app, host="0.0.0.0", port=port, threads=6, channel_timeout=300)
    except ImportError:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
