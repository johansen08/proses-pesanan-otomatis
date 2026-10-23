"""SATU-SATUNYA sumber definisi alur menu Harian/Event/Malam: daftar langkah (nama -> flag
`main.py`), isi tiap TIPE, aturan flag tambahan (`--lewati-malam`, `--non-wajib*`), dan teks
menu konsol. Dipakai bersama oleh `menu_konsol.py` (dipanggil semua `bat\\proses-*.bat`) dan
`jalankan_harian.py` (menu Harian di UI) - ubah langkah/urutan/flag HANYA di sini.

Dulu daftar ini ditulis ulang di 6 file .bat + KATALOG UI; satu salah ketik atau file .bat
berakhiran LF pernah menjalankan langkah TIPE lain SUNGGUHAN (insiden 2026-10-01). Sekarang
.bat hanya peluncur tipis. Preset di data/prototype-desktop/index.html (JS) masih salinan
terpisah - dikunci tests/test_alur.py supaya tidak menyimpang dari sini.

Modul ini murni data + fungsi kecil: tanpa I/O, tanpa import berat.
"""
from __future__ import annotations

# Langkah pembuka yang sama di menu harian dan event.
_LANGKAH_DASAR: list[tuple[str, list[str]]] = [
    ("Recheck stok", ["--recheck-stok"]),
    ("Sampel TikTok (nilai 0)", ["--sampel"]),
    ("Urgent Lazada", ["--urgent", "--channel", "lazada"]),
    ("Spesial GTL & SiCepat", ["--urgent", "--channel", "gtl-sicepat-spesial"]),
    ("Urgent GTL & SiCepat", ["--urgent", "--channel", "gtl-sicepat"]),
    ("Urgent JNE & LEX", ["--urgent", "--channel", "jne-lex"]),
]

# (nama langkah di UI/konsol, flag main.py tanpa --jalankan). Urutan = urutan eksekusi.
KATALOG: list[tuple[str, list[str]]] = [
    *_LANGKAH_DASAR,
    ("SPX ≤ 12.00 (Resi Pagi)", ["--shopee-pagi"]),
    ("J&T ≤ 15.00 (Resi Siang)", ["--jnt-siang"]),
    ("SPX-J&T Spesial", ["--label", "--tanpa-reguler"]),
    ("SPX-J&T 1 qty reguler", ["--reguler", "--bagian", "1qty"]),
    ("SPX-J&T Kombinasi", ["--reguler", "--bagian", "kombinasi"]),
    ("J&T Spesial", ["--label", "--kurir", "jnt", "--tanpa-reguler"]),
    ("J&T 1 qty reguler", ["--reguler", "--bagian", "1qty", "--kurir", "jnt"]),
    ("J&T Kombinasi", ["--reguler", "--bagian", "kombinasi", "--kurir", "jnt"]),
    ("SPX Spesial", ["--label", "--kurir", "spx", "--tanpa-reguler"]),
    ("SPX 1 qty reguler", ["--reguler", "--bagian", "1qty", "--kurir", "spx"]),
    ("SPX Kombinasi", ["--reguler", "--bagian", "kombinasi", "--kurir", "spx"]),
    ("Upload faktur & pesanan ke IRESIS", ["--upload-iresis"]),
]

# Menu EVENT (10.10/11.11/12.12 dst): J&T, SPX Hemat, SPX Standard dipisah seharian (`--event`).
# Nama langkah dipisah dari KATALOG karena nama yang sama ("J&T Spesial") punya flag berbeda.
KATALOG_EVENT: list[tuple[str, list[str]]] = [
    *_LANGKAH_DASAR,
    ("J&T ≤ 15.00 (Resi Siang)", ["--jnt-siang"]),
    ("SPX Standard Pagi ≤ 12.00 (per lantai)", ["--spx-standard", "--pagi"]),
    ("SPX Hemat Pagi Spesial", ["--label", "--event", "--kurir", "spx-hemat-pagi", "--tanpa-reguler"]),
    ("SPX Hemat Pagi 1 qty reguler", ["--reguler", "--event", "--kurir", "spx-hemat-pagi", "--bagian", "1qty"]),
    ("SPX Hemat Pagi Kombinasi", ["--reguler", "--event", "--kurir", "spx-hemat-pagi", "--bagian", "kombinasi"]),
    ("J&T Spesial", ["--label", "--event", "--kurir", "jnt", "--tanpa-reguler"]),
    ("J&T 1 qty reguler", ["--reguler", "--event", "--kurir", "jnt", "--bagian", "1qty"]),
    ("J&T Kombinasi", ["--reguler", "--event", "--kurir", "jnt", "--bagian", "kombinasi"]),
    ("J&T NDD Spesial", ["--label", "--event", "--kurir", "jnt-ndd", "--tanpa-reguler"]),
    ("J&T NDD 1 qty reguler", ["--reguler", "--event", "--kurir", "jnt-ndd", "--bagian", "1qty"]),
    ("J&T NDD Kombinasi", ["--reguler", "--event", "--kurir", "jnt-ndd", "--bagian", "kombinasi"]),
    ("SPX Hemat Spesial", ["--label", "--event", "--kurir", "spx-hemat", "--tanpa-reguler"]),
    ("SPX Hemat 1 qty reguler", ["--reguler", "--event", "--kurir", "spx-hemat", "--bagian", "1qty"]),
    ("SPX Hemat Kombinasi", ["--reguler", "--event", "--kurir", "spx-hemat", "--bagian", "kombinasi"]),
    ("SPX Standard (per lantai)", ["--spx-standard"]),
    ("Upload faktur & pesanan ke IRESIS", ["--upload-iresis"]),
]
FLAG = dict(KATALOG)
FLAG_EVENT = dict(KATALOG_EVENT)

JUDUL_EVENT = {"EVENT - TIPE 1", "EVENT - TIPE 2", "EVENT - TIPE 3", "EVENT - TIPE 4",
               "EVENT - MALAM", "EVENT - KUSTOM"}
JUDUL_VALID = {"TIPE 1", "TIPE 2", "TIPE 3", "TIPE 4", "MALAM", "KUSTOM"} | JUDUL_EVENT
# Urgent `--lewati-malam`: sesi biasa (TIPE 1/KUSTOM; event: TIPE 1/3/4) memakainya; TIPE 2
# (Shopee Pagi/pilihan 2 event) dan MALAM tidak.
JUDUL_LEWATI_MALAM = {"TIPE 1", "KUSTOM", "EVENT - TIPE 1", "EVENT - TIPE 3", "EVENT - TIPE 4",
                      "EVENT - KUSTOM"}
LANGKAH_IRESIS = "Upload faktur & pesanan ke IRESIS"
JUDUL_TANPA_IRESIS = {"MALAM", "EVENT - MALAM"}   # IRESIS hanya di jaringan lokal kantor
# Kunci jendela jam untuk main.dalam_jam_menu() (peringatan Y/N di menu konsol, UI /api/harian/info).
MENU_JAM = {"TIPE 1": "1", "TIPE 2": "2", "TIPE 3": "3", "TIPE 4": "4",
            "EVENT - TIPE 1": "1", "EVENT - TIPE 2": "2", "EVENT - TIPE 3": "3", "EVENT - TIPE 4": "4"}

# Tulisan NON WAJIB KELUAR di kolom U PICKLIST.xlsx (lihat docs/jadwal-proses.md): langkah SPX
# dipisah di TIPE 2/3 dan langkah SPX-J&T gabungan di TIPE 4 selalu (`--non-wajib`); langkah
# gabungan TIPE 1 hanya kalau menu dimulai setelah 16.00 (`--non-wajib-sore`). Event, MALAM,
# KUSTOM tidak.
NON_WAJIB_SPX_DIPISAH = {"SPX Spesial", "SPX 1 qty reguler", "SPX Kombinasi"}
NON_WAJIB_SPX_GABUNG = {"SPX-J&T Spesial", "SPX-J&T 1 qty reguler", "SPX-J&T Kombinasi"}


def flag_non_wajib(judul: str, nama_langkah: str) -> str | None:
    if judul in ("TIPE 2", "TIPE 3") and nama_langkah in NON_WAJIB_SPX_DIPISAH:
        return "--non-wajib"
    if judul == "TIPE 4" and nama_langkah in NON_WAJIB_SPX_GABUNG:
        return "--non-wajib"
    if judul == "TIPE 1" and nama_langkah in NON_WAJIB_SPX_GABUNG:
        return "--non-wajib-sore"
    return None


# ----------------------------------------------------------------------------- isi tiap TIPE
_PERSIAPAN = ["Recheck stok", "Sampel TikTok (nilai 0)"]
_URGENT = ["Urgent Lazada", "Spesial GTL & SiCepat", "Urgent GTL & SiCepat", "Urgent JNE & LEX"]
_GABUNG = ["SPX-J&T Spesial", "SPX-J&T 1 qty reguler", "SPX-J&T Kombinasi"]
_JNT = ["J&T Spesial", "J&T 1 qty reguler", "J&T Kombinasi"]
_SPX = ["SPX Spesial", "SPX 1 qty reguler", "SPX Kombinasi"]
_SIANG = "J&T ≤ 15.00 (Resi Siang)"
_E_PAGI = ["SPX Standard Pagi ≤ 12.00 (per lantai)", "SPX Hemat Pagi Spesial",
           "SPX Hemat Pagi 1 qty reguler", "SPX Hemat Pagi Kombinasi"]
_E_SEHARIAN = [*_JNT, "J&T NDD Spesial", "J&T NDD 1 qty reguler", "J&T NDD Kombinasi",
               "SPX Hemat Spesial", "SPX Hemat 1 qty reguler", "SPX Hemat Kombinasi",
               "SPX Standard (per lantai)"]
_IRESIS = [LANGKAH_IRESIS]

# Isi preset tiap judul (himpunan; urutan eksekusi selalu mengikuti KATALOG/KATALOG_EVENT).
PRESET: dict[str, list[str]] = {
    "TIPE 1": [*_PERSIAPAN, *_URGENT, *_GABUNG, *_IRESIS],
    "TIPE 2": [*_PERSIAPAN, *_URGENT, "SPX ≤ 12.00 (Resi Pagi)", *_JNT, *_SPX, *_IRESIS],
    "TIPE 3": [*_PERSIAPAN, *_URGENT, *_JNT, *_SPX, *_IRESIS],
    "TIPE 4": [*_PERSIAPAN, *_URGENT, _SIANG, *_GABUNG, *_IRESIS],
    "MALAM": [*_URGENT, *_GABUNG],
    "EVENT - TIPE 1": [*_PERSIAPAN, *_URGENT, *_E_SEHARIAN, *_IRESIS],
    "EVENT - TIPE 2": [*_PERSIAPAN, *_URGENT, *_E_PAGI, *_E_SEHARIAN, *_IRESIS],
    "EVENT - TIPE 3": [*_PERSIAPAN, *_URGENT, *_E_SEHARIAN, *_IRESIS],
    "EVENT - TIPE 4": [*_PERSIAPAN, *_URGENT, _SIANG, *_E_SEHARIAN, *_IRESIS],
    "EVENT - MALAM": [*_URGENT, *_E_SEHARIAN],
}

# Teks menu konsol. `menu` = baris di daftar pilihan; `jam` = teks peringatan di luar jam;
# `catatan` = tambahan di kalimat PERHATIAN. Urutan = nomor pilihan 1..N.
MENU_HARIAN: list[tuple[str, str, str, str]] = [
    ("TIPE 1", "GABUNG JNT+SPX                           (07.00-12.00 / 16.00-17.00)",
     "TIPE 1 (07.00-12.00 / 16.00-17.00)", ""),
    ("TIPE 2", "DIPISAH + SPX RESI <= 12.00              (TEPAT JAM 13.00)",
     "TIPE 2 (TEPAT JAM 13.00)", "SPX RESI PAGI cuma 1x sehari."),
    ("TIPE 3", "DIPISAH, TANPA SPX RESI PAGI             (13.00-15.00)",
     "TIPE 3 (13.00-15.00)", ""),
    ("TIPE 4", "GABUNG JNT+SPX LAGI + JNT RESI <= 15.00  (TEPAT JAM 15.00)",
     "TIPE 4 (TEPAT JAM 15.00)", "J&T RESI SIANG cuma 1x sehari."),
]
MENU_EVENT: list[tuple[str, str, str, str]] = [
    ("EVENT - TIPE 1", "EVENT - TIPE 1 (07.00-12.00 / 16.00-17.00)",
     "EVENT - TIPE 1 (07.00-12.00 / 16.00-17.00)", ""),
    ("EVENT - TIPE 2", "EVENT - TIPE 2 (TEPAT JAM 13.00, + SHOPEE PAGI <= 12.00)",
     "EVENT - TIPE 2 (tepat 13.00)", "SHOPEE PAGI cuma 1x sehari."),
    ("EVENT - TIPE 3", "EVENT - TIPE 3 (13.00-15.00)", "EVENT - TIPE 3 (13.00-15.00)", ""),
    ("EVENT - TIPE 4", "EVENT - TIPE 4 (TEPAT JAM 15.00, + J&T RESI SIANG <= 15.00)",
     "EVENT - TIPE 4 (tepat 15.00)", ""),
    ("EVENT - MALAM", "EVENT - MALAM  (URGENT + J&T / J&T NDD / SPX HEMAT / SPX STANDARD dipisah)",
     "", ""),
]


def langkah_urut(judul: str, daftar: list[str]) -> list[str]:
    """`daftar` nama langkah diurutkan mengikuti katalog judul itu (bukan urutan kiriman)."""
    katalog = KATALOG_EVENT if judul in JUDUL_EVENT else KATALOG
    pilih = set(daftar)
    return [nama for nama, _ in katalog if nama in pilih]


def susun_argumen(judul: str, nama_langkah: str, uji: bool = False) -> list[str]:
    """Argumen `main.py` (tanpa python & path skrip) untuk satu langkah. `uji`: tanpa
    `--jalankan` (mode uji = read-only, hanya menampilkan rencana)."""
    flag = list((FLAG_EVENT if judul in JUDUL_EVENT else FLAG)[nama_langkah])
    argumen = list(flag)
    if not uji:
        argumen.append("--jalankan")
    if judul in JUDUL_LEWATI_MALAM and flag[:1] == ["--urgent"]:
        argumen.append("--lewati-malam")
    if (nw := flag_non_wajib(judul, nama_langkah)):
        argumen.append(nw)
    return argumen
