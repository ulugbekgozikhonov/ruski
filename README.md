# Rus tili — so'zlar

Rus tili so'zlarini yo'lda tinglab yodlash uchun sayt: https://ulugbekgozikhonov.github.io/ruski/

O'quv reja (darslar, grammatika, kunlik tartib): [REJA.md](REJA.md)

- **🎧 Tinglash** — mavzuni to'xtovsiz o'qiydi: rus so'zi → pauza → o'zbekcha → rus misol gapi → gap tarjimasi.
  Tinglash paytida ekran o'chmaydi; saytdan chiqilsa (boshqa ilova, ekran qulfi) to'xtaydi.
- **🗣 Takrorlash** — har bir ruscha gapdan keyin uning uzunligiga yarasha pauza: shu vaqtda ovoz chiqarib qaytarasan.
- **👁 Tarjimani yashirish** — o'zingni tekshirish uchun. Tinglash paytida tarjima o'qilganda o'zi ochiladi.
- Telefonda brauzer menyusidan **"Bosh ekranga qo'shish"**: ilova kabi ochiladi va internetsiz ishlaydi.

## Yangi so'z yoki mavzu qo'shish

`words.json` ni tahrirlang (GitHub saytida ham bo'ladi):

```json
{"id": "transport", "icon": "🚌", "uz": "Transport", "ru": "Транспорт", "items": [
  ["авто'бус", "avtobus", "Я еду на автобусе.", "Men avtobusda ketyapman."]
]}
```

- `items`: `[rus so'zi, tarjima, rus gapi, gap tarjimasi]`
- Ixtiyoriy: `"g": "Gaplashish"` — bosh sahifadagi bo'lim (bo'lmasa "So'zlar"), `"dars": 1` — o'quv rejadagi dars raqami.
- Urg'u: urg'uli unlidan keyin `'` qo'ying — `ба'бушка` saytda `ба́бушка` bo'lib chiqadi.
- `id` — lotin harflarida, takrorlanmasin (audio fayl nomi shundan).

Push qilingach GitHub Actions audioni o'zi yaratadi (oddiy va takrorlash rejimi uchun ikkita fayl; yangi mavzu bo'lsa 10–20 daqiqa). Shu orada sayt telefon ovozidan foydalanadi.

Qo'lda yaratish:

```bash
pip install -r tools/requirements.txt
python tools/make_audio.py
```
