# -*- coding: utf-8 -*-
"""
transcriber.py — تحويل الكلام إلى نص مع توقيت لكل كلمة (faster-whisper)
نفس تقنية OpenShorts: word-level timestamps لبناء اللحظات بدقة.
"""
import subprocess

from .renderer import ffbin

_MODEL_CACHE = {}


def extract_audio(video_path: str, audio_path: str):
    """استخراج صوت أحادي 16kHz مناسب لـ Whisper."""
    ff, _ = ffbin()
    subprocess.run(
        [ff, "-y", "-v", "error", "-i", video_path,
         "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", audio_path],
        check=True, timeout=600,
    )
    return audio_path


def probe_language(audio_path: str) -> str:
    """كشف سريع للغة على نموذج tiny (ثوانٍ قليلة) لاختيار النموذج المناسب."""
    model = get_model("tiny")
    _, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
    return (info.language or "en").lower()


def get_model(model_size: str = "base"):
    from faster_whisper import WhisperModel
    if model_size not in _MODEL_CACHE:
        _MODEL_CACHE[model_size] = WhisperModel(
            model_size, device="cpu", compute_type="int8",
            cpu_threads=2,
        )
    return _MODEL_CACHE[model_size]


def transcribe(audio_path: str, model_size: str = "base", cb=None):
    """
    يعيد: (قائمة كلمات [{s,e,t}], اللغة)
    كل كلمة ببداية ونهاية بالثواني.
    """
    model = get_model(model_size)

    # مدة الصوت لشريط التقدم
    _, fp = ffbin()
    dur = 0.0
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=30,
        )
        dur = float(out.stdout.strip() or 0)
    except Exception:
        pass

    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=1,
    )

    words = []
    for seg in segments:
        for w in (seg.words or []):
            t = (w.word or "").strip()
            if not t:
                continue
            words.append({"s": round(w.start, 3), "e": round(w.end, 3), "t": t})
        if cb and dur:
            cb(min(99, round(seg.end / dur * 100)),
               f"تحليل الكلام… {int(seg.end)}ث / {int(dur)}ث")

    lang = (info.language or "en").lower()
    return words, lang
