"""Tayyor audioni tekshiradi: har bir so'zning 4 ta klipi (rus so'zi, tarjima, misol, misol
tarjimasi) o'z joyida ovozli va matn uzunligiga yarasha uzunlikdami. Klip chegaralari
index.json dan (t, w, u, s). Bo'laklarni pauza bo'yicha sanash ishonchsiz: dialoglardagi tire
("— Как дела? — Хорошо") joyida ovozning o'zi ~1 s pauza qiladi.

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

WIN = m.SR // 100   # 10 ms
MIN_RATIO = 0.02    # klipdagi ovozli soniya / harf; normal ~0.06, tushib qolgan klip ~0


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
        louds = []
        for ch in a["chunks"]:
            x = array.array("h", m.decode((m.ROOT / ch["file"].split("?")[0]).read_bytes()))
            louds.append([max(map(abs, x[i:i + WIN])) > 400 for i in range(0, len(x) - WIN, WIN)])
        for k, mark in enumerate(a["items"]):
            loud = louds[mark["c"]]
            nxt = a["items"][k + 1] if k + 1 < len(a["items"]) else None
            start, end = round(mark["t"] * 100), (round(nxt["t"] * 100) if nxt and nxt["c"] == mark["c"] else len(loud))
            it = cat["items"][k]
            names = ("rus so'zi", "tarjima", "misol", "misol tarjimasi")
            if "s" not in mark:
                print(f"{cid}: eski format (klip chegaralari yo'q) — VERSION oshirib qayta yarating")
                break
            bounds = [start, round(mark["w"] * 100), round(mark["u"] * 100)] + [round(x * 100) for x in mark["s"]] + [end]
            spans = [(bounds[0], bounds[1]), (bounds[2], bounds[3]), (bounds[3], bounds[4]), (bounds[4], bounds[5])]
            msg = None
            for name, (lo, hi), (lang, col) in zip(names, spans, (("ru", 0), ("uz", 1), ("ru", 2), ("uz", 3))):
                text = m.speakable(it[col], lang)
                voiced = sum(loud[lo:hi]) / 100
                if voiced < max(0.1, MIN_RATIO * len(text)):
                    msg = f"{name} ovozsiz yoki chala ({voiced:.2f}s, «{text}»)"
                    break
            if msg:
                bad += 1
                print(f"{cid} #{k + 1} {m.speakable(it[0], 'ru')}: {msg}")
        print(f"{cid}: tekshirildi ({len(a['items'])})")
    print("Muammoli so'zlar:", bad)


if __name__ == "__main__":
    main()
