# Rus tili — so'zlar

Rus tili so'zlarini yo'lda tinglab yodlash uchun sayt: https://ulugbekgozikhonov.github.io/ruski/

- **🎧 Tinglash** — mavzuni to'xtovsiz o'qiydi: rus so'zi → pauza → o'zbekcha → rus misol gapi → gap tarjimasi.
  Tinglash paytida ekran o'chmaydi; saytdan chiqilsa (boshqa ilova, ekran qulfi) to'xtaydi.
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
- Urg'u: urg'uli unlidan keyin `'` qo'ying — `ба'бушка` saytda `ба́бушка` bo'lib chiqadi.
- `id` — lotin harflarida, takrorlanmasin (audio fayl nomi shundan).

Push qilingach GitHub Actions audioni o'zi yaratadi (1–3 daqiqa). Shu orada sayt telefon ovozidan foydalanadi.

Qo'lda yaratish:

```bash
pip install -r tools/requirements.txt
python tools/make_audio.py
```
