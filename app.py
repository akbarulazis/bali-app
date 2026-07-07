"""
Pilih Basecamp Bali — editable itinerary app (v2: multi-media + clickable cards)
Run:  pip install -r requirements.txt
      uvicorn app:app --reload
Open: http://localhost:8000
"""
import os
import sqlite3
import shutil
import uuid
from contextlib import contextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DATA_DIR, "bali.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Pilih Basecamp Bali API")


# ---------------------------------------------------------------- DB helpers
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            day INTEGER NOT NULL,
            theme TEXT NOT NULL,
            title TEXT NOT NULL,
            time_label TEXT DEFAULT '',
            energy INTEGER DEFAULT 1,
            skip_flag INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            maps_query TEXT DEFAULT '',
            tiktok_query TEXT DEFAULT '',
            ig_tag TEXT DEFAULT '',
            rating REAL DEFAULT 0,
            favorite INTEGER DEFAULT 0,
            sort INTEGER DEFAULT 0
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            kind TEXT NOT NULL,          -- photo | video | link
            url TEXT NOT NULL,
            caption TEXT DEFAULT '',
            sort INTEGER DEFAULT 0,
            FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
        )""")
        n = conn.execute("SELECT COUNT(*) c FROM activities").fetchone()["c"]
        if n == 0:
            seed(conn)


def seed(conn):
    # (city, day, theme, title, time, energy, skip, desc, maps, tiktok, ig)
    S = [
        # ============================ UBUD ============================
        ("ubud",1,"kuliner","Lunch pinggir sawah — Bebek Tepi Sawah","Siang",1,0,
         "Welcome lunch: bebek goreng legendaris di gazebo menghadap sawah. Turun mobil, duduk, makan, senyum.",
         "Bebek Tepi Sawah Ubud","bebek tepi sawah ubud","bebektepisawah"),
        ("ubud",1,"kuliner","Sari Organik — menu sehat di tengah sawah","Siang",1,0,
         "Alternatif kalau perut masih sensitif pasca operasi: makanan organik ringan dengan view sawah Ubud.",
         "Sari Organik Ubud","sari organik ubud","sariorganik"),
        ("ubud",1,"chill","Couple spa + flower bath — Sang Spa","Sore",1,0,
         "Berendam air hangat penuh kelopak kamboja. Terapis di-brief dulu soal operasi — treatment gentle, area bekas operasi tidak disentuh.",
         "Sang Spa Ubud","sang spa ubud flower bath","flowerbathbali"),
        ("ubud",1,"chill","Sound healing — Pyramids of Chi","Sore",1,0,
         "Tiduran di dalam piramida sambil 'dimandikan' suara gong & singing bowl. Nol tenaga, tidur ternyenyak seumur hidup.",
         "Pyramids of Chi Ubud","pyramids of chi ubud","pyramidsofchi"),
        ("ubud",1,"romantis","Candlelight dinner di Bridges Bali","Malam",1,0,
         "Restoran romantis di atas jurang Sungai Campuhan, lampu temaram & suara sungai. Reservasi meja tepi tebing buat malam pertama yang berkesan.",
         "Bridges Bali Restaurant Ubud","bridges bali ubud","bridgesbali"),
        ("ubud",1,"chill","Foot massage pinggir jalan Ubud","Malam",1,0,
         "Rp 60–100rb per jam, ada di tiap sudut Ubud. Simple tapi nagih — penutup hari pertama yang sempurna.",
         "foot massage Ubud","foot massage ubud",""),
        ("ubud",2,"chill","Jungle pool club — Jungle Fish","Pagi–Sore",1,0,
         "Infinity pool menggantung di atas jurang hutan. Daybed + makanan + seharian cuma pindah posisi rebahan. Nyemplung opsional (cek luka operasi dulu).",
         "Jungle Fish Ubud","jungle fish ubud","junglefishbali"),
        ("ubud",2,"foto","Cretya Ubud — kolam 3 tingkat viral","Pagi–Sore",1,0,
         "Pool club paling viral di TikTok: kolam bertingkat menghadap sawah Tegallalang. Rame tapi kontennya juara.",
         "Cretya Ubud","cretya ubud","cretyaubud"),
        ("ubud",2,"chill","Ubud Sunset Pool — hidden gem murah","Siang–Sore",1,0,
         "Kolam kecil santai ±Rp 20rb, makanan murah & enak, jauh dari keramaian. Buat yang anti rame-rame club.",
         "Ubud Sunset Pool","ubud sunset pool",""),
        ("ubud",2,"kuliner","Kopi santai di Ubud Coffee Roastery","Pagi",1,0,
         "Flat white terbaik di Ubud + almond croissant juara, WiFi kencang, lantai dua yang adem. Buat mulai hari pelan-pelan.",
         "Ubud Coffee Roastery","ubud coffee roastery","ubudcoffeeroastery"),
        ("ubud",2,"alam","Sunset kelapa muda di tebing Tegallalang","Sore",1,0,
         "Terasering terkenal itu — dinikmati dari café pinggir tebing, tanpa trekking turun. Sama cantiknya, nol keringat.",
         "Tegallalang Rice Terrace","tegallalang rice terrace","tegallalang"),
        ("ubud",2,"alam","Campuhan Ridge Walk","Pagi",3,1,
         "Cantik banget tapi 2 km jalan kaki + tanjakan. Simpan untuk trip berikutnya saat sudah 100% pulih.",
         "Campuhan Ridge Walk","campuhan ridge walk","campuhanridgewalk"),
        ("ubud",3,"budaya","Ubud Palace + Pura Taman Saraswati","Pagi",2,0,
         "Istana kerajaan Ubud (gratis) lalu jalan pelan 3 menit ke pura kolam teratai. Dua-duanya datar, total 20–30 menit santai.",
         "Ubud Palace","ubud palace saraswati","ubudpalace"),
        ("ubud",3,"budaya","Museum ARMA — seni + taman adem","Pagi",2,0,
         "Museum seni Bali dengan taman tropis luas, banyak bangku & jalur teduh. Bisa se-lambat apapun.",
         "ARMA Museum Ubud","arma museum ubud","armamuseum"),
        ("ubud",3,"romantis","Kelas pottery berdua (sambil duduk!)","Siang",1,0,
         "Bikin mug tanah liat berdua ala film Ghost — seluruh kelas sambil duduk, hasilnya jadi kenang-kenangan trip pemulihan ini.",
         "pottery class Ubud","pottery class ubud","potteryubud"),
        ("ubud",3,"foto","Pura Gunung Kawi Sebatu — pura air tersembunyi","Siang",2,0,
         "Alternatif Tirta Empul yang jauh lebih sepi: kolam mata air jernih, taman lumut, koi. Adem, tenang, dan foto-fotonya estetik banget.",
         "Gunung Kawi Sebatu Temple","gunung kawi sebatu","gunungkawisebatu"),
        ("ubud",3,"budaya","Nonton tari Legong malam di Ubud Palace","Malam ±19.30",1,0,
         "Tari Bali tradisional + gamelan live di halaman istana. Kamu duduk sejam, penarinya yang capek.",
         "Ubud Palace Legong Dance","legong dance ubud","legongdance"),
        ("ubud",4,"kuliner","Slow brunch — Clear Café / Ubud Coffee Roastery","Pagi",1,0,
         "Bangun tanpa alarm, sarapan lama (croissant almond-nya juara), lalu meluncur ke bandara ±1,5 jam.",
         "Clear Cafe Ubud","clear cafe ubud","ubudcafe"),
        ("ubud",4,"foto","Oleh-oleh + foto terakhir Jalan Kajeng","Siang",2,0,
         "Gang tenang dengan sawah kecil & galeri seni — foto penutup yang kalem sebelum pulang.",
         "Jalan Kajeng Ubud","jalan kajeng ubud","ubud"),
        ("ubud",4,"chill","Foot massage terakhir sebelum pesawat","Siang",1,0,
         "Satu jam dipijat sebelum duduk lama di pesawat. Ritual penutup wajib.",
         "massage Ubud","massage ubud",""),

        # ============================ KINTAMANI ============================
        ("kintamani",1,"kuliner","Lunch pertama depan Batur — Pahdi","Siang",1,0,
         "Coffee shop specialty terbesar di Asia Tenggara — masuk pakai lift dari pinggir jalan. Indoor luas, elegan, hangat.",
         "Pahdi Specialty Coffee Kintamani","pahdi kintamani","pahdi"),
        ("kintamani",1,"romantis","Check-in cabin + sunset dari balkon sendiri","Sore–Malam",1,0,
         "Selimutan, teh hangat, nonton matahari tenggelam di belakang Batur dari kamar. Nol tenaga, maksimal romantis.",
         "Batur Cabins Kintamani","kintamani cabin glamping","kintamanibali"),
        ("kintamani",1,"chill","Ngeteh sore di Blue Mountains","Sore",1,0,
         "Café klasik dengan panorama 180° dari Batur sampai danau — kursi didesain biar nggak perlu nengok-nengok.",
         "Blue Mountains Bali Kintamani","blue mountains kintamani",""),
        ("kintamani",1,"kuliner","Makan malam hangat — Kintamani Eatery","Malam",1,0,
         "Pilihan resto hangat buat malam pertama yang dingin: sup, nasi goreng, teh jahe. Dekat area penginapan cabin.",
         "Kintamani restaurant Penelokan","kintamani dinner",""),
        ("kintamani",2,"kuliner","Brunch viral — AKASA Specialty Coffee","Pagi",1,0,
         "Café paling viral Kintamani & beneran sesuai hype. Roasting Arabika Kintamani sendiri, semua kursi menghadap Batur. Pesan Batur Tea biar anget.",
         "AKASA Specialty Coffee Kintamani","akasa kintamani","akasa_specialtycoffee"),
        ("kintamani",2,"foto","Hammock di atas awan — Montana del Café","Siang",1,0,
         "Café putih ala Santorini dengan jaring hammock menggantung di atas kaldera — foto ikonik FYP itu di sini.",
         "Montana del Cafe Kintamani","montana del cafe","montanadelcafe"),
        ("kintamani",2,"foto","Balkon cermin bundar — El Lago","Siang",1,0,
         "Spot foto paling terkenal kedua di Kintamani. Datang weekday ±jam 11 biar sepi.",
         "El Lago Kintamani","el lago kintamani","ellagobali"),
        ("kintamani",2,"chill","Paperhills — pool club di gunung","Pagi–Sore",1,0,
         "Café + kolam kecil estetik, musik chill, buka dari 5.30 pagi buat sunrise dari kursi yang nyaman.",
         "Paperhills Kintamani","paperhills kintamani","paperhills"),
        ("kintamani",2,"chill","Olympus Coffee — Yunani rasa Bali","Sore",1,0,
         "Dua lantai balkon menghadap Batur, lebih sepi dari tetangganya. Buat yang mau view tanpa antri foto.",
         "Olympus Coffee Kintamani","olympus coffee kintamani",""),
        ("kintamani",2,"kuliner","Lunch Thai & kopi di Lunamoon","Siang",1,0,
         "Café moody dengan proteksi angin terbaik di rim — kalau hari lagi berangin, kaca indoornya bikin view tetap jernih tanpa kedinginan.",
         "Lunamoon Kintamani","lunamoon kintamani","lunamoonkintamani"),
        ("kintamani",3,"budaya","Desa Penglipuran — desa terbersih di dunia","Pagi",2,0,
         "±30 menit dari Kintamani. Satu jalan batu lurus & datar, rumah bambu tradisional, warga nawarin loloh cemcem. Tiap beberapa meter ada tempat duduk.",
         "Desa Penglipuran Bangli","desa penglipuran","penglipuran"),
        ("kintamani",3,"alam","Petik stroberi — La Fresa","Siang",2,0,
         "Petik stroberi berdua: lucu buat konten, manis buat camilan di mobil. Kebunnya kecil, sisanya duduk.",
         "La Fresa Kintamani","la fresa kintamani","lafresakintamani"),
        ("kintamani",3,"kuliner","Mujair nyat-nyat pinggir Danau Batur","Siang",1,0,
         "Turun ke Desa Kedisan buat ikan mujair khas Batur di warung pinggir danau. Otentik & murah.",
         "warung mujair nyat nyat Kedisan Kintamani","mujair nyat nyat kintamani",""),
        ("kintamani",3,"romantis","Toya Devasya hot springs","Sore",1,1,
         "Berendam air panas alami pinggir danau — romantis maksimal, TAPI berendam biasanya belum boleh sebelum luka operasi sembuh total. Cek dokter dulu.",
         "Toya Devasya Kintamani","toya devasya","toyadevasya"),
        ("kintamani",3,"foto","Sunset di Pinggan Village viewpoint","Sore",2,0,
         "Desa di atas awan yang lagi viral — lautan awan di bawah kaki menjelang sore. Butuh jalan sedikit, tapi pemandangannya juara.",
         "Pinggan Village Kintamani","pinggan village","pingganvillage"),
        ("kintamani",3,"alam","Jeep tour lava hitam Batur","Pagi",3,1,
         "Keren, tapi guncangannya lumayan — kurang aman untuk badan yang lagi pemulihan. Wishlist trip berikutnya.",
         "Black Lava Jeep Tour Batur","black lava jeep batur","mountbatur"),
        ("kintamani",4,"romantis","Sunrise Batur — dari balkon, bukan puncak","Pagi",1,0,
         "Orang lain bangun jam 2 & mendaki 2 jam. Kita buka gorden jam 6, selimutan, kopi. Sama mataharinya, beda perjuangannya.",
         "Mount Batur viewpoint Penelokan","sunrise kintamani","mountbatur"),
        ("kintamani",4,"kuliner","Sarapan sunrise di Paperhills","Pagi (buka 5.30)",1,0,
         "Kalau mau sunrise yang lebih 'acara' — pindah duduk 10 menit dari cabin, sarapan hangat menghadap gunung.",
         "Paperhills Kintamani","paperhills sunrise","paperhills"),
        ("kintamani",4,"chill","Teh hangat terakhir depan gunung","Pagi",1,0,
         "Sebelum turun ke bandara: teh & pisang goreng di warung pinggir jalan menghadap Batur. Perpisahan yang manis.",
         "warung Penelokan Kintamani","kintamani warung view",""),

        # ============================ BEDUGUL ============================
        ("bedugul",1,"kuliner","Lunch rumah kaca — Rumah Gemuk","Siang",1,0,
         "Disambut makan hangat di restoran viral berbentuk rumah kaca. Kamu makan di dalam kaca sementara kabut lewat di luar jendela.",
         "Rumah Gemuk Bedugul","rumah gemuk bedugul","rumahgemuk"),
        ("bedugul",1,"budaya","Golden hour di Pura Ulun Danu Beratan","Sore",2,0,
         "Pura yang seolah mengapung di danau — yang di uang Rp 50.000 itu. Sore cahayanya lembut & pengunjung mulai pulang.",
         "Pura Ulun Danu Beratan","ulun danu beratan","ulundanuberatan"),
        ("bedugul",1,"chill","Ngopi hangat di café danau","Sore",1,0,
         "De Danau Lake View & sejenisnya: dinding kaca, view danau + gunung, cokelat panas. Penutup hari pertama.",
         "De Danau Lake View Restaurant Bedugul","cafe bedugul lake view","bedugul"),
        ("bedugul",1,"chill","Sore di Danau Buyan yang sunyi","Sore",2,0,
         "Danau kembar yang jauh lebih sepi dari Beratan — dermaga kayu, kabut, hampir nggak ada turis. Buat yang cari hening beneran.",
         "Danau Buyan Bedugul","danau buyan","danaubuyan"),
        ("bedugul",2,"foto","Foto wajib di Handara Gate","Pagi",1,0,
         "Gerbang paling terkenal di Instagram — gapura megah berlatar gunung berkabut, persis pinggir jalan, 10 menit dari penginapan.",
         "Handara Gate Bali","handara gate","handaragate"),
        ("bedugul",2,"foto","Wanagiri Hidden Hills — di atas dua danau","Siang",1,0,
         "Sarang bambu & dek kayu menghadap Danau Buyan & Tamblingan. Pilih yang duduk cantik; ayunan ekstrem biar aku yang coba.",
         "Wanagiri Hidden Hills","wanagiri hidden hills","wanagirihiddenhills"),
        ("bedugul",2,"alam","Bali Farm House — kasih makan alpaca","Siang",2,0,
         "Farm bergaya Eropa dekat Handara Gate: alpaca, kelinci, jalur rapi & pendek. Gemas maksimal.",
         "Bali Farm House Buleleng","bali farm house","balifarmhouse"),
        ("bedugul",2,"alam","Petik stroberi + jagung bakar sore","Sore",2,0,
         "Petik sendiri + milkshake stroberi segar, lalu jagung bakar & bandrek hangat di pinggir danau sambil lihat kabut turun.",
         "strawberry farm Bedugul","strawberry picking bedugul","bedugul"),
        ("bedugul",2,"kuliner","Secret Garden Village — workshop kopi","Sore",1,0,
         "Tur singkat bikin kopi/sabun alami + café view lembah. Semua sambil duduk.",
         "Secret Garden Village Bedugul","secret garden village bedugul","secretgardenvillage"),
        ("bedugul",2,"budaya","Pura Ulun Danu dari sisi taman belakang","Pagi",2,0,
         "Sisi taman yang jarang dikunjungi turis — lebih sepi, angle foto pura beda, dan banyak bangku buat duduk santai.",
         "Ulun Danu Beratan garden","ulun danu garden","ulundanuberatan"),
        ("bedugul",3,"romantis","Naik perahu berdua di Danau Beratan","Pagi",1,0,
         "Jukung (dengan pengemudi) atau pedal boat angsa, lewat depan pura dari sisi air. Pagi airnya tenang & kadang masih berkabut.",
         "Danau Beratan Bedugul","danau beratan perahu","danauberatan"),
        ("bedugul",3,"alam","Kebun Raya Bedugul — piknik dari mobil","Siang",1,0,
         "Kebun raya terbesar di Bali (157 ha) dan mobil boleh keliling di dalam. Piknik dari bagasi di bawah hutan pinus.",
         "Kebun Raya Bedugul","kebun raya bedugul","kebunrayabali"),
        ("bedugul",3,"alam","The Blooms Garden — taman bunga hits","Siang",2,0,
         "Taman bunga warna-warni yang lagi naik daun. Jalan setapak rapi, banyak spot duduk & foto.",
         "The Blooms Garden Bedugul","blooms garden bedugul","thebloomsgarden"),
        ("bedugul",3,"kuliner","Makan siang serba stroberi di Strawberry Hill","Siang",1,0,
         "Resto klasik Bedugul dengan menu serba stroberi — pancake, jus, sampai fondue. Hangat, cozy, dan manis (literally).",
         "Strawberry Hill Bedugul","strawberry hill bedugul","strawberryhillbali"),
        ("bedugul",3,"alam","Bali Treetop Adventure","Siang",3,1,
         "Flying fox & panjat-panjat di Kebun Raya. Seru, tapi bukan untuk badan yang lagi pemulihan.",
         "Bali Treetop Adventure Park","bali treetop adventure","balitreetop"),
        ("bedugul",4,"kuliner","Belanja Pasar Candi Kuning","Pagi",1,0,
         "Stroberi, markisa & vanili buat oleh-oleh — bisa belanja dari pinggir mobil. 5 menit dari Ulun Danu.",
         "Pasar Candi Kuning Bedugul","pasar candi kuning","bedugul"),
        ("bedugul",4,"budaya","Mampir Taman Ayun di rute pulang","Siang",2,0,
         "Pura kerajaan bertaman datar & rapi — situs UNESCO, pas di jalur pulang ke bandara, 30–40 menit cukup.",
         "Pura Taman Ayun Mengwi","taman ayun","tamanayun"),
        ("bedugul",4,"foto","Foto kabut terakhir di Twin Lakes viewpoint","Pagi",1,0,
         "Viewpoint dua danau (Buyan & Tamblingan) di pinggir jalan pulang. Berhenti sebentar, foto, lanjut turun. Nol effort.",
         "Twin Lakes viewpoint Wanagiri","twin lakes bali","twinlakesbali"),

        # ============================ TABANAN ============================
        ("tabanan",1,"alam","Sore pertama di Pantai Kedungu","Sore",1,0,
         "Jam 12 mendarat, jam 1 rebahan di kamar (bandara cuma ±45 menit!). Sorenya pantai pasir hitam yang masih sepi — kelapa muda, tikar, ombak.",
         "Pantai Kedungu Tabanan","kedungu beach","kedungubeach"),
        ("tabanan",1,"chill","Leyeh-leyeh di resort + sunset balkon","Sore",1,0,
         "Hari pertama nggak wajib ke mana-mana: kolam resort + sunset dari balkon juga sah.",
         "resort Tanah Lot Tabanan","resort tanah lot","tanahlotbali"),
        ("tabanan",1,"kuliner","Dinner seafood pinggir laut","Malam",1,0,
         "Resto tebing area Tanah Lot dengan suara ombak. Pilih yang paling dekat resort biar hemat tenaga.",
         "seafood restaurant Tanah Lot","seafood tanah lot","tanahlot"),
        ("tabanan",1,"foto","Sunset pertama di Tanah Lot (tanpa turun ke batu)","Sore",2,0,
         "Kalau mendaratnya sore, langsung ke Tanah Lot buat sunset pertama dari café tebing. Pemanasan sebelum yang utama di hari terakhir.",
         "Tanah Lot Tabanan","tanah lot sunset","tanahlot"),
        ("tabanan",2,"alam","Jatiluwih — lunch menghadap 400 ha sawah","Pagi–Siang",1,0,
         "Terasering terluas di Bali, sistem subak UNESCO, kaki Gunung Batukaru yang sejuk. Lunch lama di resto pinggir sawah + nasi merah lokal. Trekking 100% opsional.",
         "Jatiluwih Rice Terrace","jatiluwih","jatiluwih"),
        ("tabanan",2,"budaya","Pura Luhur Batukaru — pura tua di hutan","Siang",2,0,
         "Salah satu pura tertua & tersakral di Bali, sepi turis, di tengah hutan tropis yang tenang. Dekat Jatiluwih.",
         "Pura Luhur Batukaru","pura luhur batukaru","batukaru"),
        ("tabanan",2,"alam","Leke Leke Waterfall","Siang",3,1,
         "Air terjun tercantik di Tabanan, tapi ±20 menit jalan lewat hutan & tangga. Wishlist saat sudah pulih.",
         "Leke Leke Waterfall","leke leke waterfall","lekelekewaterfall"),
        ("tabanan",2,"chill","Ngopi valley view di Secret Garden Village","Sore",1,0,
         "Dalam perjalanan pulang dari Jatiluwih: café dengan view lembah hijau + tur singkat bikin kopi. Semua sambil duduk.",
         "Secret Garden Village Bedugul","secret garden village","secretgardenvillage"),
        ("tabanan",3,"budaya","Pura Taman Ayun — taman kerajaan Mengwi","Pagi",2,0,
         "Pura kerajaan abad 17 dikelilingi kolam & taman UNESCO. Jalur rata sempurna, rindang, dan damai. Cocok jalan pelan sambil gandengan.",
         "Pura Taman Ayun Mengwi","taman ayun","tamanayun"),
        ("tabanan",3,"chill","Spa couple sore di resort","Sore",1,0,
         "Briefing yang sama ke terapis: gentle, hindari area operasi. Lalu mandi sore & siap-siap dinner.",
         "spa resort Tanah Lot Tabanan","spa tabanan",""),
        ("tabanan",3,"alam","Pantai Balian — pasir hitam eksotis","Siang",2,0,
         "Pantai hitam yang lebih liar & artsy, favorit surfer tapi tetap tenang. Buat yang mau suasana beda.",
         "Pantai Balian Tabanan","balian beach","balianbeach"),
        ("tabanan",3,"romantis","Piknik sunset di Pantai Yeh Gangga","Sore",2,0,
         "Pantai hitam luas yang hampir selalu sepi, ada formasi karang unik. Gelar tikar, bawa camilan, nikmatin matahari turun berdua.",
         "Pantai Yeh Gangga Tabanan","yeh gangga beach","yehganggabeach"),
        ("tabanan",4,"romantis","Tanah Lot — penutup dari café tebing","Sore",2,0,
         "Pura ikonik di atas karang tengah laut. View terbaik dari café di atas tebing — nggak perlu turun ke batu. Golden hour, lalu bandara ±45 menit.",
         "Tanah Lot Tabanan","tanah lot sunset","tanahlot"),
        ("tabanan",4,"chill","Pagi santai + packing pelan","Pagi",1,0,
         "Sarapan lama, berenang pelan kalau boleh, packing tanpa drama. Hari terakhir itu buat napas.",
         "resort Tanah Lot","morning tabanan",""),
        ("tabanan",4,"kuliner","Brunch terakhir view laut","Siang",1,0,
         "Satu meja, dua kopi, laut. Ritual penutup sebelum flight — dan bandaranya deket, jadi nggak ada drama ngejar pesawat.",
         "beach cafe Kedungu Tabanan","cafe tabanan","tanahlotbali"),

        # ================= BATCH 3 (makin banyak makin asik) =================
        # ---- UBUD ----
        ("ubud",1,"chill","Welcome drink di infinity pool penginapan","Sore",1,0,
         "Begitu check-in, langsung nyemplung pelan (kalau boleh) atau duduk di tepi kolam dengan mocktail. Jet lag hilang, mood naik.",
         "Ubud infinity pool hotel","ubud pool villa","ubudvilla"),
        ("ubud",2,"kuliner","Makan siang sehat di Zest Ubud","Siang",1,0,
         "Restoran plant-based dengan view lembah yang bikin melongo. Menu ringan, cocok buat perut yang lagi pemulihan.",
         "Zest Ubud","zest ubud","zestubud"),
        ("ubud",2,"romantis","Floating breakfast di villa","Pagi",1,0,
         "Sarapan mengapung di kolam pribadi — croissant, buah, kopi, di atas nampan kayu. Konten wajib, dan sarapannya beneran enak.",
         "floating breakfast Ubud villa","floating breakfast ubud","floatingbreakfast"),
        ("ubud",3,"budaya","Tirta Empul — pura pemandian suci","Pagi",2,0,
         "Pura mata air suci untuk ritual melukat (pembersihan). Kamu bisa cuma menyaksikan dari tepi tanpa ikut berendam — tetap khusyuk & indah.",
         "Tirta Empul Temple","tirta empul","tirtaempul"),
        ("ubud",3,"kuliner","Kopi luwak tasting di kebun kopi","Siang",1,0,
         "Duduk di gazebo kebun, cicip 12+ jenis kopi & teh gratis, plus pemandangan terasering. Santai, teduh, dan edukatif.",
         "coffee plantation Ubud tegallalang","kopi luwak ubud","balicoffee"),
        ("ubud",3,"foto","Bali Swing / rumah pohon Tegallalang","Siang",2,1,
         "Ayunan raksasa & sarang burung di atas jurang. Kamu foto dari deck yang aman aja ya, ayunannya biar aku. Ada tangga jadi santai-santai.",
         "Bali Swing Tegallalang","bali swing","baliswing"),
        ("ubud",4,"chill","Yoga gentle pagi (opsional) di The Yoga Barn","Pagi",2,0,
         "Kalau badan udah enakan, kelas restorative yoga yang super lembut — banyak posisi berbaring. Kalau belum, skip santai.",
         "The Yoga Barn Ubud","yoga barn ubud","theyogabarn"),
        # ---- KINTAMANI ----
        ("kintamani",1,"foto","Mampir Pura Tegeh Koripan / Pura Puncak Penulisan","Sore",2,1,
         "Pura tertinggi di Bali dengan tangga panjang — pemandangannya luar biasa TAPI banyak anak tangga. Cek tenaga dulu; ada opsi lihat dari bawah.",
         "Pura Puncak Penulisan Kintamani","pura penulisan","kintamani"),
        ("kintamani",2,"kuliner","Makan siang buffet view Batur — Grand Puncak Sari","Siang",1,0,
         "Restoran buffet klasik Kintamani dengan barisan meja menghadap gunung & danau. Turis-y tapi view-nya nggak bohong.",
         "Grand Puncak Sari Kintamani","kintamani buffet restaurant",""),
        ("kintamani",2,"chill","Coffee tasting di kebun kopi Kintamani","Sore",1,0,
         "Kintamani = asal Arabika Bali. Duduk di kebun, cicip single-origin lokal fresh dari sumbernya. Sejuk & wangi kopi.",
         "Kintamani coffee plantation tasting","kintamani coffee farm","kintamanicoffee"),
        ("kintamani",3,"alam","Perahu pelan di Danau Batur (Kedisan)","Siang",2,0,
         "Sewa perahu tenang menyusuri danau kawah — air biru, dikelilingi tebing kaldera. Lebih adem & privat dari trekking.",
         "Danau Batur Kedisan boat","lake batur boat","lakebatur"),
        ("kintamani",3,"budaya","Desa Trunyan (nyebrang danau)","Siang",3,1,
         "Desa Bali Aga kuno dengan tradisi unik. Menarik secara budaya TAPI perlu nyebrang perahu agak lama — skip kalau lagi capek.",
         "Trunyan Village Kintamani","trunyan village","trunyan"),
        ("kintamani",4,"foto","Berhenti foto di Kintamani Puncak Sari viewpoint","Pagi",1,0,
         "Satu stop foto terakhir menghadap kaldera sebelum jalan turun. Cepat, cakep, nol effort.",
         "Kintamani viewpoint Penelokan","kintamani viewpoint","kintamani"),
        # ---- BEDUGUL ----
        ("bedugul",1,"kuliner","Sup & ikan bakar hangat di warung danau","Malam",1,0,
         "Malam Bedugul dingin — warung ikan bakar + sup panas pinggir Danau Beratan jadi penyelamat. Sederhana tapi ngangenin.",
         "warung ikan bakar Bedugul","bedugul dinner",""),
        ("bedugul",2,"alam","Air Terjun Banyumala (twin waterfall)","Siang",3,1,
         "Air terjun kembar tercantik di area ini. Turunnya lumayan (tangga & jalur), jadi masuk daftar 'nanti pas udah kuat'. Foto dari atas juga udah bagus.",
         "Banyumala Twin Waterfall","banyumala waterfall","banyumala"),
        ("bedugul",2,"foto","Bukit Campuhan / Bukit Teletubbies Bedugul","Sore",2,0,
         "Bukit hijau bergelombang yang lucu banget buat foto. Bisa dinikmati dari pinggir tanpa mendaki jauh.",
         "Bukit Teletubbies Bedugul","bukit teletubbies bali","bukitteletubbies"),
        ("bedugul",3,"chill","Piknik teh sore di tepi Danau Tamblingan","Sore",2,0,
         "Danau paling tenang & spiritual dari tiga danau kembar. Nyaris tanpa turis, cocok buat duduk diam berdua ditemani teh hangat.",
         "Danau Tamblingan","danau tamblingan","danautamblingan"),
        ("bedugul",3,"kuliner","Makan siang di Billy Terrace Cafe","Siang",1,0,
         "Café bertingkat menghadap kebun & gunung, menu Indonesia komplit, porsi ramah. Hangat dan santai.",
         "Billy Terrace Cafe Bedugul","billy terrace bedugul",""),
        ("bedugul",4,"foto","Foto pagi di kabun stroberi sebelum turun","Pagi",1,0,
         "Satu sesi foto manis di kebun stroberi berkabut, beli selai & jus buat oleh-oleh, lalu jalan pulang.",
         "strawberry farm Bedugul","bedugul strawberry","bedugul"),
        # ---- TABANAN ----
        ("tabanan",1,"kuliner","Kelapa muda & jagung bakar di pinggir pantai","Sore",1,0,
         "Ritual sore Tabanan: duduk di warung pantai, kelapa muda dingin + jagung bakar manis pedas, sambil lihat ombak. Murah, bahagia.",
         "warung pantai Kedungu Tabanan","kedungu beach warung",""),
        ("tabanan",2,"budaya","Jatiluwih — spot subak & pura kecil","Siang",2,0,
         "Selain foto sawah, ada pura-pura kecil & saluran subak yang bisa dilihat dari jalur datar. Budaya + alam sekaligus.",
         "Jatiluwih subak temple","jatiluwih subak","jatiluwih"),
        ("tabanan",2,"chill","Kopi pinggir sawah di Billy's / warung Jatiluwih","Sore",1,0,
         "Sehabis lunch, pindah ke warung kopi dengan kursi menghadap terasering. Diam, ngopi, dengerin angin. Itu aja.",
         "cafe Jatiluwih rice terrace","jatiluwih cafe","jatiluwih"),
        ("tabanan",3,"alam","Taman Kupu-Kupu Bali (butterfly park)","Siang",2,0,
         "Taman kupu-kupu terbesar di Asia — jalur datar & teduh, kupu-kupu warna-warni ke mana-mana. Gemas dan santai.",
         "Bali Butterfly Park Tabanan","bali butterfly park","balibutterflypark"),
        ("tabanan",3,"kuliner","Seafood sunset di Pantai Nyanyi/Nyayi","Sore",2,0,
         "Pantai sepi bersebelahan dengan Tanah Lot, ada resto seafood tepi laut. Sunset tanpa keramaian, ikan bakar fresh.",
         "Pantai Nyanyi Tabanan","pantai nyanyi","pantainyanyi"),
        ("tabanan",4,"foto","Sesi foto pagi di sawah dekat resort","Pagi",1,0,
         "Sebelum ke Tanah Lot & bandara, jalan pelan ke pematang sawah dekat penginapan buat foto pagi yang tenang.",
         "rice field Tabanan","tabanan rice field","tabanan"),
    ]
    for i, row in enumerate(S):
        # deterministic pleasant rating between 4.62 and 4.97 based on title hash
        h = sum(ord(c) for c in row[3])
        rating = round(4.62 + (h % 36) / 100.0, 2)
        conn.execute(
            """INSERT INTO activities
               (city, day, theme, title, time_label, energy, skip_flag, description,
                maps_query, tiktok_query, ig_tag, rating, favorite, sort)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (*row, rating, 0, i),
        )


init_db()


# ---------------------------------------------------------------- models
class ActivityIn(BaseModel):
    city: str
    day: int
    theme: str
    title: str
    time_label: Optional[str] = ""
    energy: Optional[int] = 1
    skip_flag: Optional[int] = 0
    description: Optional[str] = ""
    maps_query: Optional[str] = ""
    tiktok_query: Optional[str] = ""
    ig_tag: Optional[str] = ""
    rating: Optional[float] = 0
    favorite: Optional[int] = 0
    sort: Optional[int] = 0


class MediaIn(BaseModel):
    kind: str            # photo | video | link
    url: str
    caption: Optional[str] = ""
    sort: Optional[int] = 0


def media_for(conn, aid):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM media WHERE activity_id=? ORDER BY sort, id", (aid,)).fetchall()]


# ---------------------------------------------------------------- activities API
@app.get("/api/activities")
def list_activities(city: Optional[str] = None):
    q = "SELECT * FROM activities"
    args = []
    if city:
        q += " WHERE city = ?"
        args.append(city)
    q += " ORDER BY day, sort, id"
    with db() as conn:
        rows = [dict(r) for r in conn.execute(q, args).fetchall()]
        for r in rows:
            r["media"] = media_for(conn, r["id"])
        return rows


@app.get("/api/activities/{aid}")
def get_activity(aid: int):
    with db() as conn:
        r = conn.execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()
        if not r:
            raise HTTPException(404, "Not found")
        d = dict(r)
        d["media"] = media_for(conn, aid)
        return d


@app.post("/api/activities")
def create_activity(a: ActivityIn):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO activities
               (city, day, theme, title, time_label, energy, skip_flag, description,
                maps_query, tiktok_query, ig_tag, rating, favorite, sort)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (a.city, a.day, a.theme, a.title, a.time_label, a.energy, a.skip_flag,
             a.description, a.maps_query, a.tiktok_query, a.ig_tag,
             a.rating or 0, a.favorite or 0, a.sort),
        )
        return {"id": cur.lastrowid}


@app.put("/api/activities/{aid}")
def update_activity(aid: int, a: ActivityIn):
    with db() as conn:
        r = conn.execute(
            """UPDATE activities SET city=?, day=?, theme=?, title=?, time_label=?,
               energy=?, skip_flag=?, description=?, maps_query=?, tiktok_query=?,
               ig_tag=?, rating=?, favorite=?, sort=? WHERE id=?""",
            (a.city, a.day, a.theme, a.title, a.time_label, a.energy, a.skip_flag,
             a.description, a.maps_query, a.tiktok_query, a.ig_tag,
             a.rating or 0, a.favorite or 0, a.sort, aid),
        )
        if r.rowcount == 0:
            raise HTTPException(404, "Activity not found")
        return {"ok": True}


@app.post("/api/activities/{aid}/favorite")
def toggle_favorite(aid: int):
    with db() as conn:
        r = conn.execute("SELECT favorite FROM activities WHERE id=?", (aid,)).fetchone()
        if not r:
            raise HTTPException(404, "Activity not found")
        newval = 0 if r["favorite"] else 1
        conn.execute("UPDATE activities SET favorite=? WHERE id=?", (newval, aid))
        return {"favorite": newval}


@app.delete("/api/activities/{aid}")
def delete_activity(aid: int):
    with db() as conn:
        r = conn.execute("DELETE FROM activities WHERE id=?", (aid,))
        if r.rowcount == 0:
            raise HTTPException(404, "Activity not found")
        return {"ok": True}


# ---------------------------------------------------------------- media API
@app.get("/api/activities/{aid}/media")
def list_media(aid: int):
    with db() as conn:
        return media_for(conn, aid)


@app.post("/api/activities/{aid}/media")
def add_media(aid: int, m: MediaIn):
    with db() as conn:
        a = conn.execute("SELECT id FROM activities WHERE id=?", (aid,)).fetchone()
        if not a:
            raise HTTPException(404, "Activity not found")
        nxt = conn.execute("SELECT COALESCE(MAX(sort),0)+1 s FROM media WHERE activity_id=?",
                           (aid,)).fetchone()["s"]
        cur = conn.execute(
            "INSERT INTO media (activity_id, kind, url, caption, sort) VALUES (?,?,?,?,?)",
            (aid, m.kind, m.url, m.caption, m.sort or nxt),
        )
        return {"id": cur.lastrowid}


@app.delete("/api/media/{mid}")
def delete_media(mid: int):
    with db() as conn:
        r = conn.execute("DELETE FROM media WHERE id=?", (mid,))
        if r.rowcount == 0:
            raise HTTPException(404, "Media not found")
        return {"ok": True}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov"}
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not allowed")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOAD_DIR, name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    kind = "video" if ext in {".mp4", ".webm", ".mov"} else "photo"
    return {"url": f"/uploads/{name}", "kind": kind}


# ---------------------------------------------------------------- settings API
class SettingIn(BaseModel):
    value: str


@app.get("/api/settings/{key}")
def get_setting(key: str):
    with db() as conn:
        r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return {"key": key, "value": r["value"] if r else None}


@app.put("/api/settings/{key}")
def set_setting(key: str, s: SettingIn):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, s.value),
        )
        return {"ok": True, "key": key, "value": s.value}


@app.delete("/api/settings/{key}")
def del_setting(key: str):
    with db() as conn:
        conn.execute("DELETE FROM settings WHERE key=?", (key,))
        return {"ok": True}


# ---------------------------------------------------------------- static
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
