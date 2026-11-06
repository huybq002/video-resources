"""Tự gán giọng cho nhân vật theo tên (flow tự động không có bước chọn tay).

- Đoán giới tính từ tên/xưng hô (ông, bà, chị, Thị, Văn, Ngọc...).
- Nhân vật khác nhau luôn nhận giọng khác nhau (chỉ dùng lại khi hết giọng cùng giới).
- Tên trung tính (An, Minh...) được cân bằng nam/nữ theo thứ tự xuất hiện.
- Giọng người dùng đã chọn tay giữ nguyên và không bị cấp cho nhân vật khác.
"""
from __future__ import annotations

import re
import unicodedata

# Thứ tự = ưu tiên (giọng đọc rõ, dễ nghe xếp trước).
VIENEU_VOICES: dict[str, dict[str, list[str]]] = {
    "v3turbo": {
        "female": ["Ngọc Huyền", "Mai Anh", "Thùy Dung", "Trúc Ly", "Quỳnh Anh", "Đoan Trang",
                   "Ngọc Trân", "Mỹ Duyên", "Ngọc Linh", "Thục Đoan", "Kim Thanh"],
        "male": ["Hải Đăng", "Quang Sơn", "Minh Đức", "Quốc Tuấn", "Thái Sơn", "Minh Triết",
                 "Đức Trí", "Phạm Tuyên", "Xuân Vĩnh", "Thanh Bình", "Adam"],
    },
    "v3nano": {
        "female": ["Mai Anh", "Ái Hân", "Mỹ Duyên", "Trúc Ly"],
        "male": ["Adam", "Đức Trí", "Hữu Quân", "Anh Khôi", "Minh Quân", "Mạnh Dũng"],
    },
}

EDGE_GENDER: dict[str, str] = {
    "en-US-JennyNeural": "female", "en-US-AriaNeural": "female", "en-US-MichelleNeural": "female",
    "en-GB-SoniaNeural": "female", "en-GB-LibbyNeural": "female", "en-AU-NatashaNeural": "female",
    "en-US-GuyNeural": "male", "en-US-EricNeural": "male", "en-US-ChristopherNeural": "male",
    "en-US-RogerNeural": "male", "en-GB-RyanNeural": "male", "en-AU-WilliamNeural": "male",
    "ja-JP-NanamiNeural": "female", "ja-JP-KeitaNeural": "male",
    "zh-CN-XiaoxiaoNeural": "female", "zh-CN-YunxiNeural": "male",
    "ko-KR-SunHiNeural": "female", "ko-KR-InJoonNeural": "male",
}

# Xưng hô đứng đầu tên → quyết định mạnh.
_FEMALE_TITLE = {"bà", "cô", "chị", "mẹ", "má", "dì", "mợ", "thím", "nàng", "bé gái", "em gái", "nữ",
                 "mrs", "ms", "miss", "madam", "she", "girl", "woman", "mother", "mom"}
_MALE_TITLE = {"ông", "anh", "chú", "cậu", "bố", "ba", "cha", "thầy", "nam", "bé trai", "em trai",
               "mr", "sir", "he", "boy", "man", "father", "dad"}
# Tên đệm / tên riêng thiên về một giới.
_FEMALE_NAME = {"thị", "thùy", "thuỳ", "ngọc", "lan", "hoa", "hương", "trang", "linh", "phương", "thảo",
                "mai", "huyền", "trân", "duyên", "hạnh", "thu", "hà", "loan", "nga", "yến", "vy", "uyên",
                "nhi", "ly", "trúc", "quỳnh", "diệp", "châu", "giang", "oanh", "lụa", "my", "ái",
                "hân", "trinh", "hồng", "liên", "nhung", "sương", "tuyết", "ngân",
                # English
                "mary", "anna", "emma", "olivia", "sophia", "lily", "kate", "katie", "sarah", "lisa", "jane",
                "alice", "emily", "grace", "linda", "susan", "maria", "rose", "julia", "lucy", "amy", "anne",
                "ella", "chloe", "sally", "betty", "helen", "laura", "jenny", "jessica", "nancy", "ruby"}
_MALE_NAME = {"văn", "đức", "hùng", "dũng", "quân", "khôi", "sơn", "tuấn", "bình", "hải", "đăng", "long",
              "nam", "thành", "trung", "hiếu", "phúc", "khang", "huy", "quang", "cường", "đạt", "toàn",
              "thắng", "hoàng", "kiên", "lộc", "nghĩa", "phong", "tài", "vinh", "bảo", "khoa",
              # English
              "john", "tom", "david", "james", "mike", "michael", "peter", "paul", "jack", "bob", "henry",
              "george", "harry", "ben", "tim", "steve", "mark", "luke", "adam", "eric", "daniel", "jim",
              "joe", "bill", "frank", "charlie", "oliver", "william", "robert", "richard", "thomas"}


def _norm(name: str) -> str:
    return unicodedata.normalize("NFC", name).strip().lower()


def guess_gender(name: str) -> str | None:
    """'female' | 'male' | None (trung tính/không rõ)."""
    n = _norm(name)
    if not n:
        return None
    # Gợi ý tường minh trong ngoặc: "An (nữ)", "Minh [male]"
    hint = re.search(r"[(\[]\s*([^)\]]+?)\s*[)\]]", n)
    if hint:
        h = hint.group(1)
        if h in ("nữ", "female", "f", "girl"):
            return "female"
        if h in ("nam", "male", "m", "boy"):
            return "male"
        n = re.sub(r"[(\[].*?[)\]]", "", n).strip()
    tokens = re.findall(r"[\w'-]+", n)
    if not tokens:
        return None
    two = " ".join(tokens[:2])
    if tokens[0] in _FEMALE_TITLE or two in _FEMALE_TITLE:
        return "female"
    if tokens[0] in _MALE_TITLE or two in _MALE_TITLE:
        return "male"
    female = sum(t in _FEMALE_NAME for t in tokens)
    male = sum(t in _MALE_NAME for t in tokens)
    if female > male:
        return "female"
    if male > female:
        return "male"
    return None


def _pools(mode: str, language: str) -> dict[str, list[str]]:
    if language and language != "vi":
        from .tts import EDGE_VOICES

        pools: dict[str, list[str]] = {"female": [], "male": []}
        for voice in EDGE_VOICES.get(language, []):
            pools.setdefault(EDGE_GENDER.get(voice["id"], "female"), []).append(voice["id"])
        return pools
    return {k: list(v) for k, v in VIENEU_VOICES.get(mode, VIENEU_VOICES["v3turbo"]).items()}


def assign_voices(
    speakers: list[str],
    explicit: dict[str, str] | None = None,
    *,
    mode: str = "v3turbo",
    language: str = "vi",
) -> dict[str, str]:
    """Trả về map nhân vật → giọng; giữ nguyên lựa chọn tay trong ``explicit``."""
    voices = {k: v for k, v in (explicit or {}).items() if v}
    pools = _pools(mode, language)
    taken = {v for v in voices.values()}
    counts = {"female": 0, "male": 0}
    for name, voice in voices.items():
        for gender, pool in pools.items():
            if voice in pool and name:
                counts[gender] += 1

    def pick(gender: str) -> str | None:
        pool = pools.get(gender) or []
        if not pool:
            return None
        free = [v for v in pool if v not in taken]
        if free:
            return free[0]
        # Hết giọng cùng giới: mượn giọng giới kia chưa dùng trước khi lặp lại.
        other = [v for g, p in pools.items() if g != gender for v in p if v not in taken]
        if other:
            return other[0]
        return min(pool, key=lambda v: sum(1 for x in voices.values() if x == v))

    named = [s for s in dict.fromkeys(speakers) if s and s not in voices]
    # Nhân vật rõ giới tính chọn trước để nhân vật trung tính cân bằng quanh họ.
    known = [(s, guess_gender(s)) for s in named]
    for name, gender in known:
        if gender:
            voice = pick(gender)
            if voice:
                voices[name] = voice
                taken.add(voice)
                counts[gender] += 1
    for name, gender in known:
        if gender:
            continue
        target = "male" if counts["male"] <= counts["female"] else "female"
        voice = pick(target)
        if voice:
            voices[name] = voice
            taken.add(voice)
            counts[target] += 1
    return voices
