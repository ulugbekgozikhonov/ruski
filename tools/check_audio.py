"""Tayyor audioni tekshiradi: har bir so'zda 4 ta ovoz bo'lagi (so'z, tarjima, misol,
misol tarjimasi) bormi va hech biri g'ayritabiiy qisqa (chala) emasmi.

    python tools/check_audio.py            # hamma mavzular
    python tools/check_audio.py kafe oila  # faqat shular
"""
import array
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_audio as m  # noqa: E402

WIN = m.SR // 100  # 10 ms
GAP = 45           # 0.45 s dan uzun jimlik — bo'laklar orasidagi pauza (eng qisqasi 0.6 s)


def segments(loud, start, end):
    segs, cur, gap = [], None, 0
    for j in range(start, end):
        if loud[j]:
            if cur is None:
                cur = [j, j]
            cur[1], gap = j, 0
        elif cur is not None:
            gap += 1
            if gap > GAP:
                segs.append(cur)
                cur = None
    if cur:
        segs.append(cur)
    return segs


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    words = {c["id"]: c for c in json.loads((m.ROOT / "words.json").read_text("utf-8"))}
    index = json.loads((m.AUDIO / "index.json").read_text("utf-8"))
    only = set(sys.argv[1:])
    bad = 0
    for cid, a in index.items():
        if only and cid not in only and cid.removesuffix("-t") not in only:
            continue
        cat = words.get(cid.removesuffix("-t"))
        if cat is None:
            continue
        if a["src"] == "partial":
            print(f"{cid}: TO'LIQ EMAS (keyingi run to'ldiradi)")
        x = array.array("h", m.decode((m.AUDIO / f"{cid}.mp3").read_bytes()))
        loud = [max(map(abs, x[i:i + WIN])) > 400 for i in range(0, len(x) - WIN, WIN)]
        for k, mark in enumerate(a["items"]):
            end = round(a["items"][k + 1]["t"] * 100) if k + 1 < len(a["items"]) else len(loud)
            segs = segments(loud, round(mark["t"] * 100), end)
            it = cat["items"][k]
            texts = [m.speakable(it[c], lang) for lang, c in (("ru", 0), ("uz", 1), ("ru", 2), ("uz", 3))]
            durs = [(b - s + 1) / 100 for s, b in segs]
            msg = None
            if len(segs) != 4:
                msg = f"{len(segs)} ta ovoz bo'lagi, 4 ta bo'lishi kerak {durs}"
            else:
                for d, t in zip(durs, texts):
                    if d < 0.15 + 0.03 * len(t):
                        msg = f"chala: {d:.2f}s «{t}»"
                        break
            if msg:
                bad += 1
                print(f"{cid} #{k + 1} {m.speakable(it[0], 'ru')}: {msg}")
        print(f"{cid}: tekshirildi ({len(a['items'])})")
    print("Muammoli so'zlar:", bad)


if __name__ == "__main__":
    main()
