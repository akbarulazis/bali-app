# 🏡 Pilih Basecamp — Bali 11–14 Juli (Airbnb-style)

Website itinerary Bali yang **bisa kamu edit sendiri**, didesain dengan bahasa visual ala **Airbnb** (kanvas putih bersih, aksen Rausch merah, kartu foto-first, rating bintang).

4 kota (Ubud / Kintamani / Bedugul / Tabanan), tiap kota itinerary 4 hari penuh, aktivitas ber-tema (Alam, Chill, Kuliner, Budaya, Foto, Romantis), **97 aktivitas** (5–8 opsi per hari per kota), galeri banyak foto/video/link per aktivitas.

## ✨ Fitur
- **🏡 Pilih basecamp** — pilih 1 kota, dan **🔒 kunci** jadi basecamp; kota lain otomatis disembunyiin biar fokus. Bisa dibuka lagi kapan aja.
- **❤️ Pilihan Kita** — tap ♥ di kartu mana pun → masuk ke panel "Pilihan Kita" (dikelompokkan per kota). Buat shortlist favorit berdua.
- **⭐ Rating bintang** ala Airbnb di tiap kartu & detail.
- **Kartu bisa diklik** → detail lengkap: deskripsi, link cepat (Maps/TikTok/IG), galeri foto, galeri video, daftar link referensi.
- **Banyak media per kartu** — upload/drag foto & video, paste URL, YouTube auto-embed, TikTok/IG jadi link.
- **✏️ Mode Edit** — tambah/ubah/hapus aktivitas & media, semua tersimpan ke SQLite.

## Stack
- **Backend:** FastAPI + SQLite (`bali.db`, auto-seed saat pertama run)
- **Frontend:** Vanilla JS single-page (`static/index.html`), Airbnb design tokens, font Inter
- **Media:** tabel `media` terpisah (banyak per aktivitas); upload ke `uploads/`

## Cara jalanin
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```
Buka **http://localhost:8000**

Buat diakses dari HP (WiFi sama):
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
buka `http://<IP-laptop>:8000` dari HP.

## Struktur folder
```
bali-app/
├── app.py             # FastAPI: activities + media + favorites + settings + upload
├── static/index.html  # frontend SPA (Airbnb style)
├── uploads/           # media upload
├── requirements.txt
├── README.md
└── bali.db            # auto-dibuat
```

## API
Activities: `GET/POST /api/activities`, `GET/PUT/DELETE /api/activities/{id}`
Favorite:   `POST /api/activities/{id}/favorite` (toggle)
Media:      `GET/POST /api/activities/{id}/media`, `DELETE /api/media/{id}`
Settings:   `GET/PUT/DELETE /api/settings/{key}` (dipakai buat `locked_city`)
Upload:     `POST /api/upload` (multipart) → `{url, kind}`

## Reset
Hapus `bali.db`, restart → seed awal balik (rating & favorit ke default).
