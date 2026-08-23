# -*- coding: utf-8 -*-
"""
downloader.py — جلب الفيديو من يوتيوب عبر yt-dlp
مستوحى من: AI-Youtube-Shorts-Generator و OpenShorts
"""
import os
import json
import subprocess

import yt_dlp


def is_youtube_url(url: str) -> bool:
    return bool(re_search(url)) if False else _yt_match(url)


def _yt_match(url: str) -> bool:
    import re
    pat = re.compile(
        r"(youtube\.com/(watch\?v=|shorts/|live/|embed/)|youtu\.be/)[\w\-]{6,}", re.I
    )
    return bool(pat.search(url or ""))


def get_video_info(url: str) -> dict:
    """يجلب عنوان ومدة وصورة الفيديو بدون تحميل."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "id": info.get("id", ""),
        "title": (info.get("title") or "فيديو بدون عنوان").strip(),
        "duration": int(info.get("duration") or 0),
        "channel": info.get("uploader") or info.get("channel") or "",
        "thumbnail": info.get("thumbnail") or "",
    }


def download_video(url: str, out_path: str, max_minutes: int = 25, cb=None) -> dict:
    """
    يحمّل الفيديو بدقة مناسبة (720p تكفي للريلز وتوفر الوقت).
    cb(percent, message) -> None
    """
    def hook(d):
        if cb and d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            pct = round(done / total * 100, 1) if total else 0
            speed = d.get("speed")
            sp = f"{speed/1024/1024:.1f} MB/s" if speed else ""
            cb(pct, f"جارٍ التحميل {pct}% {sp}")

    ydl_opts = {
        "format": (
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
            "best[height<=720][ext=mp4]/best[height<=720]/best"
        ),
        "outtmpl": out_path,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 25,
        "retries": 3,
        "progress_hooks": [hook],
    }

    # لو الفيديو طويل نأخذ أول جزء فقط (مثل ميزة تقسيم الفيديوهات الطويلة في الأدوات الكبيرة)
    try:
        info = get_video_info(url)
    except Exception:
        info = {"title": "", "duration": 0}

    if info.get("duration") and info["duration"] > max_minutes * 60:
        ydl_opts["download_sections"] = f"*0:00-{max_minutes}:00"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    if not os.path.exists(out_path):
        # أحياناً يكون الامتداد مختلف بعد الدمج
        alt = os.path.splitext(out_path)[0] + ".mp4"
        if os.path.exists(alt):
            out_path = alt
        else:
            raise RuntimeError("فشل التحميل: الملف غير موجود")

    dur = ffprobe_duration(out_path)
    return {"path": out_path, "duration": dur, "title": info.get("title", "")}


def ffprobe_duration(path: str) -> float:
    from .renderer import ffbin
    _, fp = ffbin()
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return 0.0
