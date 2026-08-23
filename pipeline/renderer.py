# -*- coding: utf-8 -*-
"""
renderer.py — المونتاج الآلي 🎬
قص + تحويل إلى 9:16 (خلفية ضبابية سينمائية) + حرق ترجمة متحركة
بأسلوب الريلزات الفيروسية (الكلمة النشطة تتلوّن) + صورة مصغرة.
"""
import os
import re
import json
import shutil
import subprocess

TARGET_W, TARGET_H = 1080, 1920

_FF_CACHE = {}


def ffbin():
    """يعيد مساري ffmpeg/ffprobe — نظام أولاً، وإلا النسخة الثابتة (HF)."""
    if _FF_CACHE:
        return _FF_CACHE["ff"], _FF_CACHE["fp"]
    ff = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    fp = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if not ff:
        try:
            import static_ffmpeg
            ff, fp = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        except Exception:
            ff, fp = "ffmpeg", "ffprobe"
    _FF_CACHE["ff"], _FF_CACHE["fp"] = ff, fp
    return ff, fp


def ensure_ffmpeg_on_path():
    ff, fp = ffbin()
    d = os.path.dirname(ff)
    if d and d not in os.environ.get("PATH", ""):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    return ff, fp


def probe_video(path):
    _, fp = ffbin()
    out = subprocess.run(
        [fp, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-of", "json", path],
        capture_output=True, text=True, timeout=30,
    )
    st = json.loads(out.stdout)["streams"][0]
    num, _, den = (st.get("r_frame_rate") or "30/1").partition("/")
    fps = 30.0
    try:
        fps = float(num) / max(1, float(den))
    except Exception:
        pass
    has_audio = False
    out2 = subprocess.run(
        [fp, "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv", path],
        capture_output=True, text=True, timeout=30,
    )
    has_audio = bool(out2.stdout.strip())
    return st["width"], st["height"], min(fps, 30.0), has_audio


# ----------------------------------------------------------------- الترجمة (ASS)
def _ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _esc(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def build_ass(words, start, end, lang, out_path):
    """
    يبني ملف ترجمة: كلمات اللحظة مجمّعة في أسطر قصيرة،
    والكلمة النشطة تتلوّن بالأصفر الذهبي (أسلوب SubMagic).
    """
    font = "KacstOne" if lang == "ar" else "DejaVu Sans"
    fontsize = 84

    # تجميع الكلمات في أسطر (≤ 4 كلمات أو ≤ 30 حرف)
    chunks = []
    cur = []
    clen = 0
    for w in words:
        if w["e"] <= start or w["s"] >= end:
            continue
        cur.append(w)
        clen += len(w["t"]) + 1
        if len(cur) >= 4 or clen >= 30:
            chunks.append(cur)
            cur, clen = [], 0
    if cur:
        chunks.append(cur)

    lines = []
    for ch in chunks:
        ch_start = max(start, ch[0]["s"])
        ch_end = min(end, ch[-1]["e"] + 0.15)
        for idx, w in enumerate(ch):
            a = max(ch_start, w["s"])
            b = ch[idx + 1]["s"] if idx + 1 < len(ch) else ch_end
            b = min(b, ch_end)
            if b - a < 0.05:
                continue
            a -= start   # أوقات نسبية من بداية المقطع
            b -= start
            parts = []
            for k, ww in enumerate(ch):
                t = _esc(ww["t"])
                if k == idx:
                    parts.append(r"{\c&H00C8FF&}" + t + r"{\c&HFFFFFF&}")
                else:
                    parts.append(t)
            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Sub,,0,0,0,,{text}"
            )

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {TARGET_W}
PlayResY: {TARGET_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},{fontsize},&H00FFFFFF,&H00FFFFFF,&H00151515,&H96000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(lines))
        f.write("\n")
    return bool(lines)


# ----------------------------------------------------------------- الفلاتر
def _video_filter(src_w, src_h, subs_name):
    src_ratio = src_w / src_h
    tgt_ratio = TARGET_W / TARGET_H

    if abs(src_ratio - tgt_ratio) < 0.02:
        chain = (f"[0:v]scale={TARGET_W}:{TARGET_H}:"
                 f"force_original_aspect_ratio=decrease,"
                 f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2")
    else:
        fg_scale = (f"scale={TARGET_W}:-2" if src_ratio > tgt_ratio
                    else f"scale=-2:{TARGET_H}")
        chain = (
            "[0:v]split=2[bgsrc][fgsrc];"
            f"[bgsrc]scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W}:{TARGET_H},gblur=sigma=26,eq=brightness=-0.09:saturation=1.15[bg];"
            f"[fgsrc]{fg_scale}[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto"
        )
    if subs_name:
        chain += f",ass={subs_name}"
    chain += ",setsar=1[vout]"
    return chain


def render_clip(src_video, start, end, out_mp4, subs_name, jobdir):
    """يقص اللحظة ويحوّلها لريل 9:16 مع الترجمة والصوت المحسّن."""
    w, h, fps, has_audio = probe_video(src_video)
    dur = max(0.5, end - start)
    flt = _video_filter(w, h, subs_name)

    ff, _ = ffbin()
    cmd = [
        ff, "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src_video,
        "-filter_complex", flt,
        "-map", "[vout]",
    ]
    if has_audio:
        cmd += ["-map", "0:a:0?", "-af", "dynaudnorm=f=180:g=12",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-r", str(int(round(fps)) or 30),
        "-movflags", "+faststart",
        out_mp4,
    ]
    r = subprocess.run(cmd, cwd=jobdir, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg render: {r.stderr[-600:]}")
    return out_mp4


def make_poster(clip_path, poster_path):
    """صورة مصغرة من منتصف الريل."""
    ff, fp = ffbin()
    dur = 0.0
    try:
        out = subprocess.run(
            [fp, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", clip_path],
            capture_output=True, text=True, timeout=30,
        )
        dur = float(out.stdout.strip() or 0)
    except Exception:
        pass
    subprocess.run(
        [ff, "-y", "-v", "error", "-ss", f"{max(0.1, dur/2):.2f}",
         "-i", clip_path, "-frames:v", "1", "-q:v", "4", poster_path],
        timeout=120,
    )
    return poster_path
