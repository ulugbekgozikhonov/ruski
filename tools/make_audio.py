"""words.json dan har bir mavzu uchun tinglash audiosini yaratadi.

Har bir so'z uchun tartib (PLAN): rus so'zi -> pauza (eslashga vaqt) -> o'zbekcha ->
rus misol gapi -> uning tarjimasi. Natija: audio/<id>.mp3 va
audio/index.json (sayt qaysi so'z qachon o'qilishini shundan biladi).

O'zgarmagan mavzular qayta yaratilmaydi.

    pip install -r tools/requirements.txt
    python tools/make_audio.py
"""
import array
import asyncio
import hashlib
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
CACHE = Path(__file__).resolve().parent / ".cache"

VOICES = {"ru": ("ru-RU-SvetlanaNeural", "-10%"), "uz": ("uz-UZ-SardorNeural", "+0%")}
SR = 24000  # Hz, mono, 16-bit PCM
# (til, items dagi ustun, keyingi pauza soniyada)
PLAN = [("ru", 0, 1.2), ("uz", 1, 0.8), ("ru", 2, 0.6), ("uz", 3, 1.6)]
VERSION = "5"  # VOICES yoki PLAN o'zgarsa oshiring: hamma audio qayta yaratiladi


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def speakable(text, lang):
    text = text.replace("/", ",")
    if lang == "ru":
        return text.replace("'", "")  # urg'u belgisi faqat ekran uchun
    text = re.sub(r"([oOgG])'", "\\1\u02bb", text)  # o' g' -> oʻ gʻ
    return text.replace("'", "\u02bc")  # tutuq belgisi


async def tts(text, lang):
    voice, rate = VOICES[lang]
    path = CACHE / (hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest() + ".pcm")
    if path.exists():
        return path.read_bytes()
    for attempt in range(6):  # ko'p so'rovda Microsoft vaqtincha 403 qaytaradi
        try:
            mp3 = b""
            async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
                if chunk["type"] == "audio":
                    mp3 += chunk["data"]
            if not mp3:
                raise RuntimeError("bo'sh audio")
            break
        except Exception:
            if attempt == 5:
                raise
            await asyncio.sleep(15 * 2 ** attempt)
    await asyncio.sleep(0.5)
    pcm = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(SR), "pipe:1"],
        input=mp3, capture_output=True, check=True,
    ).stdout
    CACHE.mkdir(exist_ok=True)
    path.write_bytes(pcm)
    return pcm


def trim(pcm, keep=0.06, threshold=400):
    """Klip boshi va oxiridagi uzun jimlikni kesadi (pauzani PLAN o'zi beradi)."""
    a = array.array("h", pcm)
    if not a:
        return pcm
    start = next((i for i, x in enumerate(a) if abs(x) > threshold), 0)
    end = next((i for i in range(len(a) - 1, -1, -1) if abs(a[i]) > threshold), len(a) - 1)
    pad = int(SR * keep)
    return a[max(0, start - pad):min(len(a), end + pad)].tobytes()


# Bluetooth quloqchinlar mutlaq jimlikda "uxlab" qoladi va keyingi so'z boshini yutadi.
# Shuning uchun pauzalar eshitilmaydigan darajadagi (~-62 dB) shovqin bilan to'ldiriladi.
_rnd = random.Random(0)
_HUSH = array.array("h", (_rnd.randint(-25, 25) for _ in range(SR * 3))).tobytes()


def hush(seconds):
    n = 2 * int(SR * seconds)
    return (_HUSH * (n // len(_HUSH) + 1))[:n]


async def build(cat):
    pcm = bytearray()
    marks = []
    now = lambda: round(len(pcm) / (2 * SR), 2)
    pcm += hush(0.3)
    for item in cat["items"]:
        mark = {"ru": item[0], "t": now()}
        for n, (lang, col, pause) in enumerate(PLAN):
            if lang == "uz" and "u" not in mark:
                mark["u"] = now()
            pcm += trim(await tts(speakable(item[col], lang), lang))
            if n == 0:
                mark["w"] = now()
            pcm += hush(pause)
        marks.append(mark)
    mp3 = subprocess.run(
        [ffmpeg(), "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
         "-c:a", "libmp3lame", "-b:a", "48k", "-f", "mp3", "pipe:1"],
        input=bytes(pcm), capture_output=True, check=True,
    ).stdout
    return mp3, marks


def main():
    cats = json.loads((ROOT / "words.json").read_text("utf-8"))
    AUDIO.mkdir(exist_ok=True)
    index_path = AUDIO / "index.json"
    old = json.loads(index_path.read_text("utf-8")) if index_path.exists() else {}
    new = {}
    for cat in cats:
        cid = cat["id"]
        src = hashlib.sha1((VERSION + json.dumps(cat["items"], ensure_ascii=False)).encode()).hexdigest()[:12]
        mp3_path = AUDIO / f"{cid}.mp3"
        if old.get(cid, {}).get("src") == src and mp3_path.exists():
            new[cid] = old[cid]
            print(f"{cid}: o'zgarmagan")
            continue
        mp3, marks = asyncio.run(build(cat))
        mp3_path.write_bytes(mp3)
        version = hashlib.sha1(mp3).hexdigest()[:10]
        new[cid] = {"file": f"audio/{cid}.mp3?v={version}", "src": src, "items": marks}
        print(f"{cid}: {len(marks)} ta so'z, {marks[-1]['t'] / 60:.1f} daqiqa, {len(mp3) // 1024} KB")
    for f in AUDIO.glob("*.mp3"):
        if f.stem not in new:
            f.unlink()
    index_path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")


if __name__ == "__main__":
    main()
