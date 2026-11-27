"""words.json dan har bir mavzu uchun tinglash audiosini yaratadi.

Har bir so'z uchun tartib (PLAN): rus so'zi -> pauza (eslashga vaqt) -> o'zbekcha ->
rus misol gapi -> uning tarjimasi. Natija: audio/<id>.mp3 va
audio/index.json (sayt qaysi so'z qachon o'qilishini shundan biladi).

Takrorlash rejimi (audio/<id>-t.mp3): har bir ruscha klipdan keyin uning
uzunligiga yarasha pauza — tinglovchi shu vaqtda ovoz chiqarib qaytaradi.

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
import time
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
CACHE = Path(__file__).resolve().parent / ".cache"

VOICES = {"ru": ("ru-RU-SvetlanaNeural", "-10%"), "uz": ("uz-UZ-SardorNeural", "+0%")}
SR = 24000  # Hz, mono, 16-bit PCM
REPEAT = "repeat"  # pauza = klip uzunligi * 1.2 + 1 soniya (qaytarib aytishga)
# (til, items dagi ustun, keyingi pauza soniyada)
MODES = {
    "": [("ru", 0, 1.2), ("uz", 1, 0.8), ("ru", 2, 0.6), ("uz", 3, 1.6)],
    "-t": [("ru", 0, REPEAT), ("uz", 1, 0.8), ("ru", 2, REPEAT), ("uz", 3, 1.6)],
}
VERSION = "5"  # VOICES yoki MODES o'zgarsa oshiring: hamma audio qayta yaratiladi


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def speakable(text, lang):
    text = text.replace("/", ",")
    # "…" (bo'sh joy belgisi) ovozda kerak emas; ", …" bilan tugagan matnga TTS audio qaytarmaydi
    text = re.sub(r"\s*…\s*", " ", text).strip(" ,")
    text = re.sub(r"\s+([?!.,])", r"\1", text)
    if lang == "ru":
        return text.replace("'", "")  # urg'u belgisi faqat ekran uchun
    text = re.sub(r"\s*\(ayol:[^)]*\)", "", text)  # "(ayol: согласна)" — faqat ekran uchun
    text = re.sub(r"([oOgG])'", "\\1\u02bb", text)  # o' g' -> oʻ gʻ
    return text.replace("'", "\u02bc")  # tutuq belgisi


def decode(mp3):
    return subprocess.run(
        [ffmpeg(), "-v", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(SR), "pipe:1"],
        input=mp3, capture_output=True, check=True,
    ).stdout


def too_short(pcm, text):
    """Matn uzunligiga nisbatan g'ayritabiiy qisqa — xizmat audioni chala qaytargan."""
    return len(pcm) / (2 * SR) < 0.15 + 0.03 * len(text)


async def tts(text, lang):
    """Klipning PCM'i; Microsoft bir necha urinishda ham bermasa — None."""
    voice, rate = VOICES[lang]
    path = CACHE / (hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest() + ".pcm")
    if path.exists():
        return path.read_bytes()
    base = int(rate.rstrip("%"))
    best = None  # eng uzun (eng to'liq) javob
    for attempt in range(10):
        # Xizmat ba'zan bo'sh yoki chala javob qaytaradi (tasodifan, matnga bog'liq emas):
        # tezlikni ±1–3% o'zgartirib qayta so'raymiz — eshitganda farqi sezilmaydi.
        shift = (0, 1, -1, 2, -2, 3, -3)[attempt % 7]
        mp3 = b""
        try:
            async for chunk in edge_tts.Communicate(text, voice, rate=f"{base + shift:+d}%").stream():
                if chunk["type"] == "audio":
                    mp3 += chunk["data"]
        except edge_tts.exceptions.NoAudioReceived:
            mp3 = b""
        except Exception:  # ko'p so'rovda Microsoft vaqtincha 403 qaytaradi
            await asyncio.sleep(min(15 * 2 ** attempt, 240))
            continue
        if mp3:
            pcm = decode(mp3)
            if best is None or len(pcm) > len(best):
                best = pcm
            if not too_short(trim(pcm), text):
                break
            print(f"  ? chala audio, qayta so'raladi ({lang}): {text}")
        await asyncio.sleep(3 + attempt)
    if best is None:
        print(f"  ! TTS ishlamadi ({lang}): {text}")
        return None
    pcm = best
    await asyncio.sleep(0.8)
    if too_short(trim(pcm), text):
        print(f"  ! audio chala ({lang}): {text}")
        return pcm  # keshga yozilmaydi: keyingi urinishda qayta so'raladi
    CACHE.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")  # run to'xtatilsa chala fayl keshga tushmasin
    tmp.write_bytes(pcm)
    tmp.replace(path)
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


async def build(cat, plan):
    """(mp3, marks, to'liqmi). O'qilmagan klip o'rnida qisqa pauza qoladi."""
    pcm = bytearray()
    marks = []
    complete = True
    now = lambda: round(len(pcm) / (2 * SR), 2)
    pcm += hush(0.3)
    for item in cat["items"]:
        mark = {"ru": item[0], "t": now()}
        for n, (lang, col, pause) in enumerate(plan):
            if lang == "uz" and "u" not in mark:
                mark["u"] = now()
            text = speakable(item[col], lang)
            raw = await tts(text, lang)
            clip = trim(raw) if raw is not None else hush(0.5)
            if raw is None or too_short(clip, text):
                complete = False
            pcm += clip
            if pause == REPEAT:
                pause = len(clip) / (2 * SR) * 1.2 + 1.0
            if n == 0:
                mark["w"] = now()
            pcm += hush(pause)
        marks.append(mark)
    mp3 = subprocess.run(
        [ffmpeg(), "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
         "-c:a", "libmp3lame", "-b:a", "48k", "-f", "mp3", "pipe:1"],
        input=bytes(pcm), capture_output=True, check=True,
    ).stdout
    return mp3, marks, complete


def main():
    cats = json.loads((ROOT / "words.json").read_text("utf-8"))
    AUDIO.mkdir(exist_ok=True)
    index_path = AUDIO / "index.json"
    old = json.loads(index_path.read_text("utf-8")) if index_path.exists() else {}
    new = {}
    todo = []
    for cat, suffix in [(c, m) for c in cats for m in MODES]:
        cid = cat["id"] + suffix
        src = hashlib.sha1((VERSION + suffix + json.dumps(cat["items"], ensure_ascii=False)).encode()).hexdigest()[:12]
        if old.get(cid, {}).get("src") == src and (AUDIO / f"{cid}.mp3").exists():
            new[cid] = old[cid]
            print(f"{cid}: o'zgarmagan")
        else:
            todo.append((cat, suffix, cid, src))
    # O'qilmay qolgan klip bo'lsa, mavzu bir ozdan keyin qayta yig'iladi (tayyor kliplar keshda).
    # Baribir to'liq chiqmasa, audio saqlanadi, lekin src belgilanmaydi — keyingi ishga tushishda qayta urinadi.
    for round_ in range(3):
        if round_:
            print(f"{len(todo)} ta mavzu to'liq emas — 60 soniyadan keyin qayta urinish")
            time.sleep(60)
        left = []
        for cat, suffix, cid, src in todo:
            mp3, marks, complete = asyncio.run(build(cat, MODES[suffix]))
            mp3_path = AUDIO / f"{cid}.mp3"
            mp3_path.write_bytes(mp3)
            version = hashlib.sha1(mp3).hexdigest()[:10]
            new[cid] = {"file": f"audio/{cid}.mp3?v={version}", "src": src if complete else "partial", "items": marks}
            print(f"{cid}: {len(marks)} ta so'z, {marks[-1]['t'] / 60:.1f} daqiqa, {len(mp3) // 1024} KB"
                  + ("" if complete else " — TO'LIQ EMAS"))
            if not complete:
                left.append((cat, suffix, cid, src))
        todo = left
        if not todo:
            break
    for f in AUDIO.glob("*.mp3"):
        if f.stem not in new:
            f.unlink()
    index_path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")


if __name__ == "__main__":
    main()
