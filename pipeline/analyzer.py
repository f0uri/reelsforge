# -*- coding: utf-8 -*-
"""
analyzer.py — محرك الذكاء الفيروسي 🧠
مستوحى من "Virality-Aware Highlight Selection" في AI-Youtube-Shorts-Generator:
تسجيل نقاط لكل نافذة زمنية بناءً على: الخطافات، الأسئلة، الأرقام،
العاطفة، إيقاع الكلام، وبدايات الجمل — بدون أي مفاتيح API.
"""
import re
import unicodedata

# ---------------------------------------------------------------- قوائم اللغة
AR_HOOK_PHRASES = [
    "لن تصدق", "لا تفوت", "هل تعلم", "لا تفعل", "توقف عن", "انتبه من",
    "احذر من", "أهم شيء", "السر في", "سر نجاح", "أكبر خطأ", "أخطاء شائعة",
    "طريقة سهلة", "طريقة بسيطة", "في ثواني", "بسرعة البرق", "مثل المحترفين",
    "لا أحد يخبرك", "ما لا تعرفه", "الحقيقة وراء", "قصة حقيقية", "تجربة حقيقية",
    "أقسم لك", "تخيل معي", "صدق أو لا تصدق", "شيء لا يصدق", "مستحيل أن",
]
AR_HOOK_WORDS = [
    "سر", "أسرار", "السر", "مفاجأة", "صدمة", "مذهل", "خطير", "مهم",
    "الحقيقة", "خدعة", "حيلة", "طريقة", "كيف", "لماذا", "أفضل", "أسوأ",
    "أغرب", "أجمل", "أخطر", "قصة", "تجربة", "جرب", "انتبه", "احذر",
    "خطأ", "أخطاء", "نصيحة", "نصائح", "فكرة", "عبقري", "مجانا", "مجاني",
    "الآن", "بسرعة", "بسيط", "سهل", "صعب", "مستحيل", "ربح", "خسارة",
    "ثروة", "نجاح", "فشل", "غني", "فقير", "مشهور", "كارثة", "إنجاز",
]
EN_HOOK_PHRASES = [
    "you won't believe", "don't do this", "stop doing", "the secret to",
    "biggest mistake", "how to", "nobody tells you", "what they don't",
    "the truth about", "here's why", "watch this", "wait for it",
    "this changed everything", "game changer", "mind blowing",
]
EN_HOOK_WORDS = [
    "secret", "secrets", "shocking", "amazing", "insane", "crazy",
    "mistake", "mistakes", "truth", "hack", "hacks", "trick", "tips",
    "best", "worst", "never", "always", "why", "how", "story", "try",
    "stop", "warning", "dangerous", "free", "now", "fast", "easy",
    "impossible", "success", "failure", "rich", "poor", "viral",
]
AR_EMOTION = [
    "حب", "حبيب", "كره", "خوف", "خايف", "سعادة", "سعيد", "حزن", "حزين",
    "غضب", "ضحك", "ضحكت", "مضحك", "مبكي", "رائع", "جميل", "فظيع",
    "رهيب", "مجنون", "خيالي", "كارثة", "فخور", "فخر", "ألم", "دموع",
    "بكيت", "قلبي", "حلمي", "حلم", "موت", "حياة", "أمل", "يأس",
]
EN_EMOTION = [
    "love", "hate", "fear", "scared", "happy", "sad", "angry", "laugh",
    "funny", "crying", "beautiful", "terrible", "horrible", "awesome",
    "incredible", "unbelievable", "disaster", "proud", "pain", "tears",
    "dream", "hope", "life", "death", "heart",
]
AR_QUESTION = ["هل", "لماذا", "كيف", "ماذا", "متى", "أين", "من هو", "من هي", "ليش", "واش"]
EN_QUESTION = ["why", "how", "what", "when", "where", "who", "which"]

AR_NUM_WORDS = ["واحد", "اثنين", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة",
                "ثمانية", "تسعة", "عشرة", "مئة", "ألف", "مليون", "بالمئة", "في المئة"]
EN_NUM_WORDS = ["one", "two", "three", "four", "five", "six", "seven",
                "eight", "nine", "ten", "hundred", "thousand", "million", "percent"]

AR_STOP = set("""في من على إلى عن مع هذا هذه ذلك تلك الذي التي الذين ما لا لن نعم
قد لقد كم كان تكون يكون كانت هذاك كما وأنه بأنه وأنه يا أيها أيها عند غير أي كل
بعض منذ فقط أيضا جدا هنا هناك الآن اليوم أمس غد ليس ليست ليسوا ثم أو لكن إذا حتى
لأن بين بعد قبل خلال أثناء حول فوق تحت هو هي أنا أنت نحن هم هن أن إن إلى علي عليه
عليها معه معها معهم لهم لها منه منها فيهم بها به لها له وهو وهي وكانت وكان ولم ولما يعني شيء شي والله
بس ايش وش هيك كتير مرة ثاني أول حتى لو انا انت هو هي ان انا انتم
الا كنت تكون تحب تريد يجب يمكن لذلك لان مما فيما عليكم اليكم
تعالى تعالي سبحانه عز وجل صلى عليه وسلم
""".split())
_AR_STOP_RAW = AR_STOP
EN_STOP = set("""the a an and or but if then so of in on at to for from by with about
into over under again further once here there when where why how all any both each
few more most other some such no nor not only own same than too very can will just
should now is are was were be been being have has had do does did i you he she it we
they what which who whom this that these those my your his her its our their
""".split())

# ------------------------------------------------------- بنوك هاشتاجات جاهزة
VIRAL_TAGS = {
    "ar": ["#ريلز", "#اكسبلور", "#فايرل", "#ترند", "#فيروسي", "#شورتس",
           "#يوتيوب_شورتس", "#تيك_توك", "#مقطع_قصير", "#اكسبلورر"],
    "en": ["#reels", "#viral", "#fyp", "#foryou", "#explore", "#trending",
           "#shorts", "#youtubeshorts", "#tiktok", "#reelitfeelit"],
}
CATEGORY_TAGS = {
    "طبخ": (["طبخ", "وصفة", "وصفات", "طعام", "أكل", "مطبخ", "حلويات", "كيك", "طهي",
            "recipe", "food", "cooking", "kitchen", "cake"], ["#طبخ", "#وصفات", "#food"]),
    "رياضة": (["كرة", "مباراة", "هدف", "لاعب", "تدريب", "جيم", "تمرين", "رياضة",
              "فريق", "بطولة", "football", "soccer", "gym", "workout", "sport"],
             ["#رياضة", "#كرة_القدم", "#sports"]),
    "تقنية": (["تطبيق", "تطبيقات", "هاتف", "آيفون", "اندرويد", "ذكاء", "اصطناعي",
              "برمجة", "حاسوب", "تكنولوجيا", "موقع", "خوارزمية", "app", "phone",
              "ai", "tech", "coding", "software"], ["#تقنية", "#تكنولوجيا", "#tech"]),
    "مال وأعمال": (["مال", "استثمار", "ربح", "بيزنس", "تسويق", "مشروع", "تجارة",
                   "أرباح", "راتب", "بيع", "شراء", "عمل", "وظيفة", "money",
                   "invest", "business", "marketing", "startup"],
                  ["#ريادة_أعمال", "#مال", "#business"]),
    "صحة": (["صحة", "تغذية", "نوم", "فيتامين", "مرض", "علاج", "طبيب", "دواء",
            "رجيم", "حمية", "health", "sleep", "diet", "doctor", "fitness"],
           ["#صحة", "#صحتك", "#health"]),
    "إسلاميات": (["الله", "قرآن", "القرآن", "إسلام", "صلاة", "دعاء", "نبي",
                "الرسول", "سنة", "حديث", "جنة", "ايات", "سورة"],
               ["#إسلاميات", "#قرآن", "#دين"]),
    "سفر": (["سفر", "رحلة", "سياحة", "مطار", "طائرة", "فندق", "بلد", "مدينة",
            "travel", "trip", "tourism", "vacation"], ["#سفر", "#سياحة", "#travel"]),
    "تعليم": (["تعلم", "درس", "شرح", "دورة", "معلومة", "معلومات", "دراسة",
              "جامعة", "مدرسة", "learn", "study", "lesson", "tutorial", "facts"],
             ["#تعلم", "#معلومات", "#education"]),
    "ترفيه": (["مضحك", "ضحك", "نكتة", "مقالب", "تحدي", "لعبة", "فيلم", "مسلسل",
              "اغنية", "فن", "مشاهير", "funny", "meme", "challenge", "movie",
              "music", "celebrity"], ["#ترفيه", "#مضحك", "#fun"]),
    "تطوير الذات": (["نجاح", "تطوير", "ذات", "تحفيز", "طاقة", "عادة", "عادات",
                   "هدف", "أهداف", "انضباط", "ثقة", "motivation", "success",
                   "mindset", "habits", "discipline"], ["#تطوير_الذات", "#تحفيز", "#motivation"]),
}

AR_LETTERS = re.compile(r"[\u0621-\u064A\u0671-\u06D5]")
PUNCT = ".!?؟…。"


# ----------------------------------------------------------------- أدوات عامة
def detect_lang(text: str) -> str:
    ar = len(AR_LETTERS.findall(text))
    tot = max(1, len(re.findall(r"\w", text, re.UNICODE)))
    return "ar" if ar / tot > 0.35 else "en"


def normalize_ar(tok: str) -> str:
    tok = unicodedata.normalize("NFC", tok)
    tok = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", tok)  # تشكيل + تطويل
    tok = tok.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    tok = tok.replace("ى", "ي")
    return tok


def tokenize(text: str):
    return [t for t in re.findall(r"[\w\u0621-\u064A\u0671-\u06D5]{2,}", text, re.UNICODE)]


# تطبيع قوائم الإيقاف العربية حتى تطابق طريقة تطبيع الكلمات المستخرجة
AR_STOP = {normalize_ar(w) for w in _AR_STOP_RAW}


# ----------------------------------------------------------------- تسجيل النقاط
def _count_hits(text: str, phrases, words_lst):
    score = 0.0
    low = text.lower()
    for p in phrases:
        score += low.count(p) * 2.5
    for w in words_lst:
        score += low.count(w) * 1.2
    return score


def score_window(window_words, lang):
    """يحسب درجة الفيروسية (0-100) لنافذة من الكلمات."""
    text = " ".join(w["t"] for w in window_words)
    n = max(1, len(window_words))
    dur = max(1.0, window_words[-1]["e"] - window_words[0]["s"])

    if lang == "ar":
        hooks, emotion, question, num_words = AR_HOOK_PHRASES + AR_HOOK_WORDS, AR_EMOTION, AR_QUESTION, AR_NUM_WORDS
        stop = AR_STOP
        en_hooks = en_emo = en_q = en_num = []
    else:
        hooks, emotion, question, num_words = EN_HOOK_PHRASES + EN_HOOK_WORDS, EN_EMOTION, EN_QUESTION, EN_NUM_WORDS
        stop = EN_STOP
        ar_all = []

    low = text.lower()
    if lang == "ar":
        hook_s = _count_hits(text, AR_HOOK_PHRASES, AR_HOOK_WORDS)
        emo_s = _count_hits(text, [], AR_EMOTION)
        q_s = sum(low.count(q) for q in AR_QUESTION) + text.count("؟") + text.count("?")
        num_s = len(re.findall(r"\d+", text)) + sum(low.count(x) for x in AR_NUM_WORDS)
    else:
        hook_s = _count_hits(text, EN_HOOK_PHRASES, EN_HOOK_WORDS)
        emo_s = _count_hits(text, [], EN_EMOTION)
        q_s = sum(low.count(q) for q in EN_QUESTION) + text.count("?")
        num_s = len(re.findall(r"\d+", text)) + sum(low.count(x) for x in EN_NUM_WORDS)

    # إيقاع الكلام (كلمات/ثانية) — الإيقاع الحيوي يجذب الانتباه
    wps = n / dur
    rate_s = 1.0 if 1.8 <= wps <= 4.2 else (0.5 if 1.0 <= wps <= 5.5 else 0.15)

    # عقوبة الصمت الطويل داخل المقطع
    max_gap = 0.0
    for i in range(1, len(window_words)):
        gap = window_words[i]["s"] - window_words[i - 1]["e"]
        if gap > max_gap:
            max_gap = gap
    silence_pen = min(25, max(0, (max_gap - 1.6)) * 18)

    # كثافة الكلمات المهمة نسبة لطول المقطع
    density = min(1.0, (hook_s + emo_s) / max(1, n / 12))

    score = (
        34 * min(1.0, hook_s / 3.5)
        + 14 * min(1.0, q_s / 2.0)
        + 10 * min(1.0, num_s / 2.0)
        + 14 * min(1.0, emo_s / 2.0)
        + 14 * rate_s
        + 14 * density
    )
    score = max(3.0, min(99.0, score - silence_pen))

    parts = {
        "hook": hook_s, "question": q_s, "number": num_s,
        "emotion": emo_s, "rate": rate_s, "gap": max_gap, "wps": wps,
    }
    return round(score, 1), parts


def reason_from_parts(parts, lang):
    """يشرح للمشاهد لماذا اخترنا هذه اللحظة."""
    norm = {
        "hook": parts.get("hook", 0) / 3.5,
        "question": parts.get("question", 0) / 2,
        "number": parts.get("number", 0) / 2,
        "emotion": parts.get("emotion", 0) / 2,
        "rate": parts.get("rate", 0),
    }
    best = max(norm, key=norm.get)
    ar = {
        "hook": "🪝 خطاف قوي يشد الانتباه من أول ثانية",
        "question": "❓ سؤال يثير الفضول ويجبر على المتابعة",
        "number": "🔢 أرقام وحقائق قابلة للمشاركة والحفظ",
        "emotion": "❤️ شحنة عاطفية عالية تحفّز التفاعل والتعليقات",
        "rate": "⚡ إيقاع كلام سريع وحيوي يمنع الملل",
    }
    en = {
        "hook": "🪝 Strong hook that grabs attention instantly",
        "question": "❓ A curiosity-triggering question",
        "number": "🔢 Shareable numbers & facts",
        "emotion": "❤️ High emotional charge drives engagement",
        "rate": "⚡ Fast-paced delivery keeps viewers watching",
    }
    return (ar if lang == "ar" else en)[best]


# ----------------------------------------------------------------- اختيار اللحظات
def _boundaries(words):
    """يعيد قائمة فواصل الجمل (مؤشر كلمة + نوع)."""
    b = [0]
    for i in range(len(words) - 1):
        gap = words[i + 1]["s"] - words[i]["e"]
        ends = words[i]["t"] and words[i]["t"][-1] in PUNCT
        if gap > 0.7 or ends:
            b.append(i + 1)
    return b


def find_moments(words, lang, num_clips=3, target_len=30):
    """
    يبحث عن أفضل اللحظات الفيروسية بنوافذ منزلقة مسجّلة النقاط،
    ثم يزيل التكرار ويوسّع كل نافذة لأقرب جملة كاملة.
    """
    if len(words) < 6:
        return []

    min_len = max(8.0, target_len * 0.45)
    max_len = target_len * 1.6

    avg_wps = len(words) / max(1.0, words[-1]["e"] - words[0]["s"])
    stride = max(2, int(avg_wps * 3.5))  # خطوة ≈ 3.5 ثانية

    candidates = []
    i = 0
    while i < len(words):
        start_t = words[i]["s"]
        j = i
        while j < len(words) and words[j]["e"] - start_t < target_len:
            j += 1
        j = max(j, i + 3)
        j = min(j, len(words))
        window = words[i:j]
        dur = window[-1]["e"] - start_t
        if dur >= min_len:
            score, parts = score_window(window, lang)
            candidates.append({
                "i": i, "j": j, "start": start_t, "end": window[-1]["e"],
                "score": score, "parts": parts,
                "text": " ".join(w["t"] for w in window),
            })
        i += stride

    if not candidates:
        return []

    candidates.sort(key=lambda c: c["score"], reverse=True)

    # إزالة التداخل: لا نأخذ مقطعين متداخلين بأكثر من 35%
    picked = []
    for c in candidates:
        ok = True
        for p in picked:
            inter = min(c["end"], p["end"]) - max(c["start"], p["start"])
            if inter > 0.10 * min(c["end"] - c["start"], p["end"] - p["start"]):
                ok = False
                break
        if ok:
            picked.append(c)
        if len(picked) >= num_clips:
            break

    # توسيع لأقرب جملة كاملة
    bounds = _boundaries(words)
    for c in picked:
        # البداية: أقرب فاصل جملة قبل البداية (خلال 4 ثوانٍ)
        for b in reversed(bounds):
            if b <= c["i"] and words[b]["s"] >= c["start"] - 4.0:
                c["i"] = b
                c["start"] = words[b]["s"]
                break
        # النهاية: أقرب فاصل جملة بعد النهاية (خلال 4 ثوانٍ)
        for b in bounds:
            if b >= c["j"] and b < len(words) and words[b]["s"] <= c["end"] + 4.0:
                c["end"] = words[min(b, len(words) - 1)]["s"] if b < len(words) else c["end"]
                c["j"] = b
                break
        c["start"] = max(0.0, c["start"] - 0.25)
        c["end"] = min(words[-1]["e"] + 0.35, c["end"] + 0.25)
        if c["end"] - c["start"] > max_len:
            c["end"] = c["start"] + max_len
        c["reason"] = reason_from_parts(c["parts"], lang)

    # بعد التوسيع: نزيل أي تداخل ناتج عن التمدد لجملة كاملة
    picked.sort(key=lambda c: c["start"])
    fixed, min_gap = [], 0.3
    for c in picked:
        if fixed and c["start"] < fixed[-1]["end"] + min_gap:
            c["start"] = fixed[-1]["end"] + min_gap
        if c["end"] - c["start"] >= min_len * 0.7:
            fixed.append(c)
    picked = fixed

    picked.sort(key=lambda c: c["start"])
    return picked


# ----------------------------------------------------------------- العناوين
def _sentences(text):
    parts = re.split(r"(?<=[.!?؟…])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 8:
            out.append(p)
    return out or ([text.strip()] if text.strip() else [])


def make_title(moment_text, video_title, lang):
    """يولّد عنواناً جذاباً + بديلين من نص اللحظة."""
    hooks = (AR_HOOK_PHRASES + AR_HOOK_WORDS) if lang == "ar" else (EN_HOOK_PHRASES + EN_HOOK_WORDS)
    sents = _sentences(moment_text)

    def sent_score(s):
        low = s.lower()
        sc = sum(2.5 if h in low else 0 for h in hooks)
        sc += 6 if ("؟" in s or "?" in s) else 0
        sc += 4 if re.search(r"\d", s) else 0
        # خصم للجمل التي تبدأ بحرف عطف فتبدو مبتورة
        if s and s[0] in "وفث":
            sc -= 5
        # نفضل العناوين بطول معقول
        L = len(s)
        sc += 3 if 25 <= L <= 110 else (1 if L < 25 else -2)
        return sc

    ranked = sorted(sents, key=sent_score, reverse=True)

    def clean(s):
        s = re.sub(r"^[،,.\-–\s]+|[.،,]+$", "", s).strip()
        if len(s) > 100:
            cut = s[:97].rsplit(" ", 1)[0]
            s = cut + "…"
        return s

    titles = []
    for s in ranked:
        t = clean(s)
        if t and t not in titles:
            titles.append(t)
        if len(titles) >= 3:
            break
    if not titles:
        titles = [(video_title or "أقوى لحظة في الفيديو")[:100]]

    emoji = "🔥" if lang == "ar" else "🔥"
    main = f"{emoji} {titles[0]}"
    return main, titles[1:3]


# ----------------------------------------------------------------- الهاشتاغات
def make_hashtags(moment_text, video_title, lang, count=12):
    """
    يبني هاشتاجات ذكية: كلمات مفتاحية من النص + تصنيف الموضوع
    + هاشتاجات الانتشار العام — بنفس لغة الفيديو.
    """
    text = f"{moment_text} {video_title or ''}"
    stop = AR_STOP if lang == "ar" else EN_STOP
    hot = set((AR_HOOK_WORDS + AR_EMOTION) if lang == "ar" else (EN_HOOK_WORDS + EN_EMOTION))

    freq = {}
    for tok in tokenize(text):
        key = normalize_ar(tok) if lang == "ar" else tok.lower()
        if key in stop or len(key) < 2:
            continue
        freq[key] = freq.get(key, 0) + (2.0 if key in hot else 1.0)

    keywords = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    tags = []
    for k, _ in keywords:
        tag = "#" + k.replace(" ", "_")
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break

    # هاشتاجات تصنيف الموضوع
    kw_set = set(k for k, _ in keywords[:10])
    cats_added = 0
    for cat, (triggers, cat_tags) in CATEGORY_TAGS.items():
        if cats_added >= 2:
            break
        if any(normalize_ar(t) in kw_set or t in kw_set for t in triggers):
            for t in cat_tags:
                if t not in tags:
                    tags.append(t)
                    cats_added += 1
                    break

    # هاشتاجات الانتشار
    for t in VIRAL_TAGS[lang]:
        if len(tags) >= count:
            break
        if t not in tags:
            tags.append(t)

    return tags[:count]


def build_package(moment, video_title, lang):
    """يحزم اللحظة: عنوان + بدائل + هاشتاجات + وصف جاهز للنشر."""
    title, alternates = make_title(moment.get("text", ""), video_title, lang)
    hashtags = make_hashtags(moment.get("text", ""), video_title, lang)
    caption = f"{title}\n\n{' '.join(hashtags)}"
    return {
        "title": title,
        "alternates": alternates,
        "hashtags": hashtags,
        "caption": caption,
    }
