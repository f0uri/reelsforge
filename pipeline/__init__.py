# -*- coding: utf-8 -*-
"""
ReelsForge — الأنابيب الكاملة: رابط يوتيوب ➜ ريلزات فيروسية جاهزة للنشر
"""
import os
import json
import time

from . import downloader, transcriber, analyzer, renderer


def _bootstrap_env():
    """يضمن وجود ffmpeg على PATH وخطوط عربية حتى في بيئات بدون حزم نظام (HF)."""
    renderer.ensure_ffmpeg_on_path()
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    if not os.path.isdir(fonts_dir):
        return
    import shutil
    has_ar = True
    if shutil.which("fc-list"):
        try:
            r = subprocess.run(["fc-list", ":lang=ar"], capture_output=True,
                               text=True, timeout=20)
            has_ar = bool(r.stdout.strip())
        except Exception:
            has_ar = True
    else:
        has_ar = False
    if has_ar:
        return
    conf = "/tmp/rf_fonts.conf"
    try:
        with open(conf, "w") as f:
            f.write('<?xml version="1.0"?>\n'
                    '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                    '<fontconfig>\n'
                    f'<dir>{fonts_dir}</dir>\n'
                    '<cachedir>/tmp/rf_fc_cache</cachedir>\n'
                    '</fontconfig>\n')
        os.environ["FONTCONFIG_FILE"] = conf
    except Exception:
        pass


import subprocess  # noqa: E402  (يستخدم في _bootstrap_env)


def run_pipeline(url, jobdir, num_clips=3, clip_len=30, whisper_model="base",
                 max_minutes=25, cb=None):
    """
    ينفّذ الخط الكامل ويعيد قائمة الريلزات الجاهزة.
    cb(stage, percent, message)
    """
    _bootstrap_env()
    jobdir = os.path.abspath(jobdir)
    os.makedirs(jobdir, exist_ok=True)

    def emit(stage, pct, msg):
        if cb:
            cb(stage, pct, msg)

    # 1) التحميل -------------------------------------------------
    emit("download", 2, "جارٍ جلب معلومات الفيديو…")
    info = downloader.get_video_info(url)
    src = os.path.join(jobdir, "source.mp4")
    emit("download", 5, f"تحميل: {info['title'][:60]}")
    downloader.download_video(
        url, src, max_minutes=max_minutes,
        cb=lambda p, m: emit("download", 5 + p * 0.2, m),
    )
    video_dur = downloader.ffprobe_duration(src)
    emit("download", 25, "اكتمل التحميل ✅")

    # لو الفيديو قصير جداً نأخذه كله كريل واحد
    if video_dur and video_dur <= clip_len * 1.5:
        num_clips = 1

    # 2) الصوت ---------------------------------------------------
    emit("audio", 27, "استخراج الصوت…")
    audio = transcriber.extract_audio(src, os.path.join(jobdir, "audio.wav"))
    emit("audio", 30, "تم استخراج الصوت ✅")

    # 3) التفريغ الصوتي -------------------------------------------
    if whisper_model == "auto":
        probe = transcriber.probe_language(audio)
        order = ["tiny", "base", "small"]
        cap = os.environ.get("RF_MAX_MODEL", "small")  # للخوادم المجانية محدودة الرام
        whisper_model = "small" if probe == "ar" else "base"
        if order.index(whisper_model) > order.index(cap):
            whisper_model = cap
        emit("transcribe", 30.5, f"كشف تلقائي: اللغة {probe} ➜ نموذج {whisper_model}")
    emit("transcribe", 31, f"تحويل الكلام إلى نص (نموذج {whisper_model})…")
    words, whisper_lang = transcriber.transcribe(
        audio, model_size=whisper_model,
        cb=lambda p, m: emit("transcribe", 31 + p * 0.24, m),
    )
    lang = analyzer.detect_lang(" ".join(w["t"] for w in words[:300])) \
        if words else (whisper_lang if whisper_lang in ("ar", "en") else "en")
    emit("transcribe", 55, f"تم التفريغ: {len(words)} كلمة، اللغة: {lang} ✅")
    with open(os.path.join(jobdir, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump({"language": lang, "words": words}, f, ensure_ascii=False)

    # 4) التحليل الفيروسي ------------------------------------------
    emit("analyze", 57, "البحث عن اللحظات الفيروسية… 🧠")
    moments = analyzer.find_moments(words, lang, num_clips=num_clips,
                                    target_len=clip_len)

    # خطة بديلة لو ما في كلام كافٍ (فيديو موسيقي/بصري): نقاط متباعدة من الفيديو
    if not moments and video_dur > 8:
        n = max(1, num_clips)
        step = video_dur / (n + 1)
        for k in range(n):
            s = max(0, step * (k + 1) - clip_len / 2)
            moments.append({
                "start": s, "end": min(video_dur, s + clip_len),
                "score": 55.0, "text": "",
                "reason": "🎵 لحظة بصرية مميزة (الفيديو بدون كلام كافٍ)",
            })
    emit("analyze", 64, f"تم اختيار {len(moments)} لحظات واعدة 🎯")

    # 5) المونتاج --------------------------------------------------
    results = []
    n = max(1, len(moments))
    for idx, m in enumerate(moments):
        base = 66 + (idx / n) * 30
        emit("render", base, f"مونتاج الريل {idx+1}/{n}… ✂️")
        name = f"reel_{idx+1:02d}"
        clip_words = [w for w in words
                      if w["e"] > m["start"] and w["s"] < m["end"]]
        subs_name = None
        if clip_words:
            ass_path = os.path.join(jobdir, f"{name}.ass")
            if renderer.build_ass(clip_words, m["start"], m["end"], lang, ass_path):
                subs_name = f"{name}.ass"

        out_mp4 = os.path.join(jobdir, f"{name}.mp4")
        renderer.render_clip(src, m["start"], m["end"], out_mp4, subs_name, jobdir)
        poster = os.path.join(jobdir, f"{name}.jpg")
        renderer.make_poster(out_mp4, poster)

        pkg = analyzer.build_package(m, info.get("title", ""), lang)
        dur = m["end"] - m["start"]
        results.append({
            "file": f"{name}.mp4",
            "poster": f"{name}.jpg",
            "start": round(m["start"], 1),
            "end": round(m["end"], 1),
            "duration": round(dur, 1),
            "score": round(m.get("score", 50), 1),
            "reason": m.get("reason", ""),
            "transcript": m.get("text", "")[:400],
            **pkg,
        })
        emit("render", 66 + ((idx + 1) / n) * 30, f"ريل {idx+1} جاهز ✅")

    emit("done", 100, "🎉 كل الريلزات جاهزة!")
    return {
        "video": info,
        "language": lang,
        "source_duration": round(video_dur, 1),
        "clips": results,
    }
