"""Otomatisasi: download Laporan Siap Proses (Jubelio) -> PDF daftar SKU spesial.

Pemakaian:
    python src/main.py                      # download dari Jubelio lalu buat PDF
    python src/main.py --excel file.xlsx    # lewati download, proses file yang ada
    python src/main.py --excel file.xlsx --tanpa-cek-nilai   # tanpa akses API sama sekali

Proses sampai label pengiriman (proses_label.py):
    python src/main.py --label                          # MODE UJI: hanya tampilkan rencana
    python src/main.py --label --sku T01-BSBI-5         # mode uji untuk 1 SKU saja
    python src/main.py --label --jalankan               # proses sungguhan semua SKU spesial
    python src/main.py --label --sku T01-BSBI-5 --jalankan
    python src/main.py --label --tanpa-reguler --jalankan   # SKU spesial saja, tanpa lanjut reguler
    python src/main.py --lanjut PICK-000154839 --jalankan   # lanjutkan picklist yang terhenti
    python src/main.py --lanjut PICK-000157269 --nama KOMBINASI-REGULER-LANTAI2 \
        --subfolder KOMBINASI --sesi 2026-10-06/11 --jalankan
        # nama file/subfolder/folder sesi sama dengan alur asalnya - perintah lengkap ini
        # sudah tercantum di Catatan TERHENTI (riwayat & blok PERHATIAN), tinggal disalin

Dengan "--label --jalankan", PDF BARU dibuat setelah proses selesai, dari jumlah pesanan
yang benar-benar berhasil dipicklist per SKU (bukan daftar kandidat awal).

Picklist sampel (proses_label.py): pesanan channel TikTok Shop ("Shop | Tokopedia") nilainya
0/kosong (kreator/sampel) - TIDAK bagian dari alur "--label --jalankan", dijalankan PALING
PERTAMA di tiap TIPE proses-harian.bat (sebelum urgent). Berdiri sendiri lewat --sampel:
    python src/main.py --sampel                          # MODE UJI: hanya tampilkan rencana
    python src/main.py --sampel --jalankan

Picklist urgent (proses_label.py): TIDAK bagian dari alur "--label --jalankan" (menu 3 di
menu.bat cuma untuk kurir J&T/SPX). 2 skenario: channel Lazada (1 picklist gabungan), dan
kurir GTL/SiCepat (lintas channel - baik dari Tokopedia asli maupun "Shop | Tokopedia"/TikTok,
urgent-nya ditentukan kurir bukan channel), dipecah per LANTAI rak gudang (1/2/3/LAINNYA) sama
pola dengan bagian kombinasi picklist sisa reguler. Berdiri sendiri lewat --urgent (sampai
label PDF juga), boleh dibatasi 1 skenario saja lewat --channel:
    python src/main.py --urgent                          # MODE UJI: hanya tampilkan rencana
    python src/main.py --urgent --channel lazada --jalankan
    python src/main.py --urgent --channel gtl-sicepat --jalankan

Picklist sisa reguler (proses_label.py): pesanan channel TikTok Shop ("Shop | Tokopedia") &
Shopee, kurir J&T/SPX, yang BUKAN bagian SKU spesial hari itu - dipecah 2: (1) 1 SKU 1 qty
yang tidak spesial, (2) kombinasi/multi-baris. Lewat "--label --jalankan" dijalankan otomatis
SETELAH proses SKU spesial (perlu tahu SKU mana yang sudah spesial) - DILEWATI kalau dipakai
bersama --sku (proses cuma sebagian SKU, daftar SKU spesial belum lengkap utk pengecualian).
Bisa juga berdiri sendiri lewat --reguler, boleh dibatasi 1 bagian saja lewat --bagian:
    python src/main.py --reguler                          # MODE UJI: hanya tampilkan rencana
    python src/main.py --reguler --bagian 1qty --jalankan
    python src/main.py --reguler --bagian kombinasi --jalankan

Pemisahan J&T/SPX (dipakai TIPE 2 & TIPE 3 - lihat proses-harian.bat/docs/jadwal-proses.md):
tambahkan --kurir jnt atau --kurir spx ke --label maupun --reguler supaya J&T dan SPX jadi
picklist terpisah saat pembuatan (bukan digabung seperti TIPE 1/TIPE 4). Penentuan SKU
spesial sendiri TETAP menggabung J&T+SPX, --kurir hanya membatasi resi mana yang benar-benar
dipicklist:
    python src/main.py --label --kurir jnt --tanpa-reguler --jalankan
    python src/main.py --reguler --bagian 1qty --kurir spx --jalankan

Mode EVENT (hari 10.10/11.11/12.12 dst, lihat docs/jadwal-proses.md; proses-event.bat): J&T,
SPX Hemat, dan SPX Standard dipisah SEPANJANG HARI. Berdiri sendiri dari alur harian - tanpa
--event, perilaku semua flag di atas TIDAK berubah. J&T dan SPX Hemat: spesial, satuan, kombinasi
(penentuan SKU spesial dihitung PER KURIR, bukan digabung) lewat --event + --kurir jnt|spx-hemat;
SPX Standard: hanya dipecah per lantai (1/2/3/LAINNYA) lewat --spx-standard. Versi Shopee Pagi
(jam pesan s.d. 12:00, folder hasil TERPISAH): --kurir spx-hemat-pagi dan --spx-standard --pagi:
    python src/main.py --label --event --kurir jnt --tanpa-reguler --jalankan
    python src/main.py --reguler --event --kurir spx-hemat --bagian 1qty --jalankan
    python src/main.py --label --event --kurir spx-hemat-pagi --tanpa-reguler --jalankan
    python src/main.py --spx-standard --jalankan
    python src/main.py --spx-standard --pagi --jalankan

Picklist Shopee Pagi (proses_label.py): dijalankan MANUAL 1x sehari (mis. jam 13:00), BUKAN
bagian alur otomatis --label --jalankan. Semua pesanan channel Shopee yang jam pesannya (WIB)
maksimal jam 12 siang hari ini, dipecah per LANTAI rak gudang (1/2/3/LAINNYA) - sama pola
dengan bagian kombinasi picklist sisa reguler/urgent GTL-SiCepat:
    python src/main.py --shopee-pagi                      # MODE UJI: hanya tampilkan rencana
    python src/main.py --shopee-pagi --jalankan

Picklist J&T Resi Siang (proses_label.py): dijalankan MANUAL 1x sehari (mis. jam 15:00), BUKAN
bagian alur otomatis --label --jalankan. Semua pesanan channel TikTok Shop, kurir J&T, yang
jam pesannya (WIB) maksimal jam 15 siang hari ini, dipecah per LANTAI rak gudang (1/2/3/
LAINNYA, sama pola dengan Shopee Pagi di atas) - aturan bisnis J&T: wajib keluar TikTok Shop
paling lambat jam 15.00, lihat docs/jadwal-proses.md:
    python src/main.py --jnt-siang                        # MODE UJI: hanya tampilkan rencana
    python src/main.py --jnt-siang --jalankan

Recheck stok (jubelio.py): cek ulang stok SEMUA pesanan yang berstatus stok kosong (tombol
"Recheck Stok" di web) - pesanan yang stoknya sudah tersedia lagi otomatis kembali ke proses
normal. Dijalankan PALING PERTAMA di tiap TIPE proses-harian.bat (sebelum picklist sampel),
supaya pesanan yang pulih ikut terhitung di langkah-langkah berikutnya:
    python src/main.py --recheck-stok                    # MODE UJI: hanya tampilkan daftar
    python src/main.py --recheck-stok --jalankan

Rekap PICKLIST.xlsx (rekap_master_excel.py): otomatis, tiap picklist langsung ditulis ke
PICKLIST.xlsx di folder sesi label (dari data/template/picklist-form-kosong.xlsx) - tidak ada langkah
atau flag terpisah.

Upload faktur ke IRESIS (iresis.py; dulu manual setelah proses pesanan selesai):
    python src/main.py --upload-iresis                   # MODE UJI: hanya unduh faktur
    python src/main.py --upload-iresis --jalankan [--hari 2] [--hari-pesanan 4]
(mengunggah 2 file berurutan: faktur N hari, lalu pesanan N hari)
"""
import argparse
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

import peringatan_gagal
import peringatan_picklist
import peringatan_resi
import rekap_master_excel
import serah_terima
from proses_label import durasi
from sku_spesial import (baca_excel, buat_pdf, grup_rak_per_pesanan, hitung_sku_spesial,
                         lantai_per_pesanan, rak_dominan_per_sku, resi_kandidat,
                         sku_bundle_per_pesanan)

ROOT = Path(__file__).resolve().parent.parent   # root project, bukan folder src/ ini
FOLDER_DATA = ROOT / "data"       # laporan hasil unduh & riwayat picklist (tidak dikomit); template/ & prototype-desktop/ di dalamnya dikomit
FOLDER_EXCEL = FOLDER_DATA / "laporan-siap-proses"
FOLDER_FAKTUR = FOLDER_DATA / "laporan-faktur"
FOLDER_PDF = FOLDER_DATA / "laporan-sku-spesial"
FOLDER_LOG = ROOT / "logs"
FOLDER_LABEL = ROOT / "label-pengiriman"
FILE_RIWAYAT = FOLDER_DATA / "riwayat_picklist.xlsx"

# Folder sesi aktif di dalam FOLDER_LABEL, mis. "label-pengiriman/2026-09-30/4" (folder
# tanggal berisi subfolder bernomor per sesi). Diisi sekali oleh main() lewat
# folder_label_sesi() sebelum menu mana pun dijalankan, supaya semua pilihan menu.bat (1-7)
# dalam 1x jalan menu.bat menyimpan label ke folder sesi yang sama - baru ganti sesi saat
# menu.bat ditutup & dijalankan ulang (lihat menu.bat: LABEL_SESI_DIR).
FOLDER_LABEL_SESI = FOLDER_LABEL


def sesi_label_baru() -> str:
    """Cari nomor sesi terbesar untuk tanggal hari ini di FOLDER_LABEL/<tanggal>, lalu buat
    folder sesi berikutnya (mis. sudah ada 2026-09-30/1..2026-09-30/3 -> buat 2026-09-30/4)."""
    tanggal = datetime.now().strftime("%Y-%m-%d")
    folder_tanggal = FOLDER_LABEL / tanggal
    folder_tanggal.mkdir(parents=True, exist_ok=True)
    urutan_terbesar = 0
    for item in folder_tanggal.iterdir():
        if item.is_dir() and item.name.isdigit():
            urutan_terbesar = max(urutan_terbesar, int(item.name))
    nama = f"{tanggal}/{urutan_terbesar + 1}"
    (FOLDER_LABEL / nama).mkdir(parents=True, exist_ok=True)
    return nama


def _sesi_valid(teks: str) -> str:
    """Validasi --sesi: harus pola folder sesi `YYYY-MM-DD/N` (lihat sesi_label_baru())."""
    teks = teks.replace("\\", "/").strip("/")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}/\d+", teks):
        raise argparse.ArgumentTypeError(f"format sesi harus YYYY-MM-DD/N, bukan {teks!r}")
    return teks


def folder_label_sesi() -> Path:
    """Folder sesi label aktif: pakai LABEL_SESI_DIR dari environment kalau ada (diset
    sekali oleh menu.bat saat mulai), kalau tidak buat sesi baru (mis. dipanggil langsung
    tanpa menu.bat)."""
    nama = os.environ.get("LABEL_SESI_DIR") or sesi_label_baru()
    folder = FOLDER_LABEL / nama
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def cetak_bermasalah(hasil: list[dict],
                     judul: str = "PERHATIAN: PICKLIST TERHENTI/GAGAL") -> list[dict]:
    """Cetak blok peringatan mencolok untuk baris hasil proses yang Catatan-nya diawali
    GAGAL/TERHENTI (mis. error koneksi saat unduh label, lihat proses_label.lanjutkan_picklist())
    - supaya tidak tenggelam di log yang panjang, sejajar dengan
    peringatan_picklist.cetak()/peringatan_resi.cetak(). Juga dicatat lewat peringatan_gagal
    (lintas proses python, dibaca ulang di rekap_waktu.py) supaya tidak hilang dari rekap akhir
    TIPE proses-harian.bat kalau langkah ini bukan langkah terakhir (lihat insiden 2026-10-06:
    picklist urgent bermasalah tidak muncul di rekap karena ketenggelam langkah berikutnya).
    Mengembalikan baris yang bermasalah (dipakai caller untuk exit code)."""
    bermasalah = [h for h in hasil if str(h.get("Catatan", "")).startswith(("GAGAL", "TERHENTI"))]
    if not bermasalah:
        return bermasalah
    print()
    print("!" * 60)
    print(f"  {judul}")
    print("!" * 60)
    for h in bermasalah:
        pesan = f"{h.get('No Picklist') or h.get('SKU', '-')}: {h.get('Catatan', '')}"
        print(f"  - {pesan}")
        peringatan_gagal.catat(pesan)
    print("!" * 60)
    return bermasalah


def dalam_jam_menu(menu: str) -> bool:
    """Cek apakah jam sekarang ada dalam jendela jam menu proses-harian.bat. Jendela di sini
    cuma SANITY CHECK (soft warning via konfirmasi Y/N, bukan blokir) - tim tetap yang
    menentukan urutan kerja sebenarnya. 4 tipe (lihat docs/jadwal-proses.md untuk urutan
    langkah & alasan bisnis tiap tipe):
      "1"=TIPE 1, gabung J&T+SPX (07.00-12.00 pagi, DAN 16.00-17.00 sore setelah TIPE 4
          selesai; malam/dini hari 17.00-07.00 pakai proses-malam.bat, bukan menu ini)
      "2"=TIPE 2, dipisah + SPX Resi Pagi, dipicu TEPAT jam 13.00 (12.00-13.00 sengaja
          dikosongkan dari jendela menu mana pun = jam istirahat, bukan celah)
      "3"=TIPE 3, dipisah tanpa SPX Resi Pagi (13.00-15.00, setelah TIPE 2 & sebelum TIPE 4)
      "4"=TIPE 4, gabung lagi + J&T Resi Siang, dipicu TEPAT jam 15.00 (15.00-16.00)
    Jendela menu 2/3 (13.00-13.59 vs 13.00-14.59) SENGAJA tumpang tindih - di rentang itu
    dua tipe sama-sama valid dipilih tim, tergantung mana yang sudah/belum dijalankan hari
    itu. TIPE 1 (menu "1") punya 2 jendela (pagi & sore), dicek dengan membandingkan
    jam-dalam-sehari saja (berulang tiap hari, tidak peduli tanggal)."""
    sekarang = datetime.now().hour * 60 + datetime.now().minute
    jendela = {
        "1": [(7 * 60, 12 * 60 - 1), (16 * 60, 17 * 60 - 1)],
        "2": [(13 * 60, 13 * 60 + 59)],
        "3": [(13 * 60, 14 * 60 + 59)],
        "4": [(15 * 60, 15 * 60 + 59)],
        # proses-event.bat pilihan 2 (Shopee Pagi, picklist jam pesan s.d. 12.00): baru masuk
        # akal SETELAH jam 12.00 (semua pesanan s.d. 12.00 sudah masuk), kapan pun sesudahnya
        # sampai sore. Pilihan 1 (sesi biasa) tidak punya jendela - boleh kapan saja.
        "E2": [(12 * 60, 15 * 60 + 59)],
    }
    return any(awal <= sekarang <= akhir for awal, akhir in jendela[menu])


def jam_malam(sekarang: datetime | None = None) -> bool:
    """True kalau jam sekarang 16.00-06.59, yaitu jendela malam TIPE 1 (lihat dalam_jam_menu).
    Di jendela ini langkah urgent Lazada & GTL-SiCepat dilewati (`--urgent --lewati-malam`)."""
    jam = (sekarang or datetime.now()).hour
    return jam >= 16 or jam < 7


TEKS_NON_WAJIB = "NON WAJIB KELUAR"


def menu_mulai_setelah_16(mulai: datetime) -> bool:
    """True kalau menu dimulai 16.01 atau lebih (16.00 pas masih wajib keluar). Dihitung dari
    waktu MENU dimulai (bukan waktu tiap picklist), supaya satu TIPE tidak berisi sebagian
    picklist bertulisan dan sebagian tidak walau langkah terakhirnya selesai lewat 17.00."""
    return mulai.hour * 60 + mulai.minute > 16 * 60


def waktu_menu_mulai() -> datetime:
    """Waktu menu mulai dari env WAKTU_MENU_MULAI (epoch detik; diisi sekali per menu oleh
    proses-harian.bat / jalankan_harian.py); kosong atau tidak valid = sekarang."""
    try:
        return datetime.fromtimestamp(float(os.environ["WAKTU_MENU_MULAI"]))
    except (KeyError, ValueError, OverflowError, OSError):
        return datetime.now()


def atur_catatan_non_wajib(args) -> bool:
    """Aktifkan tulisan NON WAJIB KELUAR di kolom U PICKLIST.xlsx untuk proses ini kalau
    --non-wajib, atau --non-wajib-sore dan menunya dimulai setelah 16.00."""
    aktif = bool(args.non_wajib or (args.non_wajib_sore and menu_mulai_setelah_16(waktu_menu_mulai())))
    rekap_master_excel.atur_catatan_proses(TEKS_NON_WAJIB if aktif else "")
    return aktif


def jam_tanpa_iresis(sekarang: datetime | None = None) -> bool:
    """True kalau jam sekarang 20.00-04.59: semua yang terkait IRESIS (unduh faktur/pesanan
    & upload) dilewati di jendela ini. Bisa dipaksa manual lewat `--upload-iresis --paksa`."""
    jam = (sekarang or datetime.now()).hour
    return jam >= 20 or jam < 5


def muat_env(path: Path) -> None:
    """Baca file .env sederhana (KUNCI=nilai) ke environment."""
    if not path.exists():
        return
    for baris in path.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, nilai = baris.split("=", 1)
        os.environ.setdefault(kunci.strip(), nilai.strip().strip('"').strip("'"))


def siapkan_log() -> logging.Logger:
    FOLDER_LOG.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=[
            logging.FileHandler(FOLDER_LOG / f"run_{datetime.now():%Y-%m}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("sku-spesial")


def login(log: logging.Logger) -> str:
    import jubelio

    email = os.environ.get("JUBELIO_EMAIL")
    password = os.environ.get("JUBELIO_PASSWORD")
    if not email or not password:
        raise SystemExit("JUBELIO_EMAIL / JUBELIO_PASSWORD belum diisi di file .env")
    log.info("Login ke Jubelio sebagai %s", email)
    return jubelio.login(email, password)


def download(log: logging.Logger, token: str) -> Path:
    import jubelio

    log.info("Meminta URL Laporan Siap Proses")
    url = jubelio.ambil_url_laporan(token)
    log.info("Mengunduh Excel")
    return jubelio.unduh_excel(token, url, FOLDER_EXCEL)


def atur_operator(args) -> int:
    """--operator [NAMA] / --tambah-operator NAMA: kelola daftar operator, tanpa menyentuh Jubelio."""
    import operator_aktif
    try:
        if args.tambah_operator:
            operator_aktif.tambah(args.tambah_operator)
            print(f"Operator {operator_aktif.normalkan(args.tambah_operator)} ditambahkan.")
        if args.operator:
            operator_aktif.set_aktif(args.operator)
    except operator_aktif.OperatorError as e:
        print(f"GAGAL: {e}")
        return 1
    d = operator_aktif.info()
    print("Operator aktif:", d["aktif"])
    print("Daftar        :", ", ".join(d["daftar"]))
    return 0


def cek_sinkron() -> int:
    """--cek-sinkron: status kunci serah-terima + file konflik sinkron. 1 kalau ada masalah."""
    print(serah_terima.status())
    d = serah_terima._baca()
    dipegang_lain = (serah_terima._aktif(d, time.time())
                     and d.get("perangkat") != serah_terima.nama_perangkat())
    konflik = serah_terima.laporan_konflik(ROOT)
    print(chr(10).join(konflik) if konflik else "Tidak ada file konflik sinkron.")
    return 1 if konflik or dipegang_lain else 0


def ambil_kunci(log: logging.Logger, args) -> str | None:
    """Ambil kunci serah-terima untuk proses yang mengubah data (--jalankan/--lanjut) dan cetak
    peringatan konflik sinkron. Mode uji tidak mengambil kunci. Return pesan galat kalau ditolak."""
    for baris in serah_terima.laporan_konflik(ROOT):
        log.warning(baris)
    if not (args.jalankan or args.lanjut):
        return None
    galat, peringatan = serah_terima.ambil(" ".join(sys.argv[1:])[:80],
                                           abaikan=args.abaikan_kunci)
    for p in peringatan:
        log.warning(p)
    return galat


def main() -> int:
    """Jalankan _main(), lalu cetak peringatan picklist terlompat/batal & pesanan tanpa resi
    PALING AKHIR supaya tidak tenggelam di log yang panjang."""
    peringatan_picklist.atur_folder(FOLDER_LOG)
    peringatan_resi.atur_folder(FOLDER_LOG)
    peringatan_gagal.atur_folder(FOLDER_LOG)
    serah_terima.atur_folder(FOLDER_LOG)
    try:
        return _main()
    finally:
        serah_terima.lepas()
        import proses_label

        proses_label.tutup_riwayat()
        rekap_master_excel.selesai()
        peringatan_picklist.cetak_sesi()
        peringatan_resi.cetak_sesi()


def _main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", type=Path, help="proses file Excel ini tanpa download")
    ap.add_argument("--tanpa-cek-nilai", action="store_true",
                    help="jangan cek nilai pesanan ke API (pesanan nilai 0 tidak dikeluarkan)")
    ap.add_argument("--label", action="store_true",
                    help="lanjut proses SKU spesial sampai label PDF (tanpa --jalankan = mode uji)")
    ap.add_argument("--tanpa-reguler", action="store_true",
                    help="dipakai bersama --label: lewati picklist sisa reguler otomatis "
                        "setelah SKU spesial selesai (SKU spesial saja)")
    ap.add_argument("--sampel", action="store_true",
                    help="hanya buat picklist sampel (channel TikTok Shop, nilai pesanan "
                        "0/kosong - kreator/sampel) sampai label PDF, tanpa proses lain "
                        "(dijalankan paling pertama di tiap TIPE proses-harian.bat, sebelum "
                        "urgent; tanpa --jalankan = mode uji)")
    ap.add_argument("--urgent", action="store_true",
                    help="hanya buat picklist urgent (channel Lazada, kurir GTL/SiCepat lintas "
                        "channel - GTL/SiCepat dipecah per lantai rak gudang) sampai label "
                        "PDF, tanpa proses SKU spesial (tanpa --jalankan = mode uji)")
    ap.add_argument("--channel", choices=["lazada", "gtl-sicepat"],
                    help="dipakai bersama --urgent: batasi ke 1 skenario saja")
    ap.add_argument("--lewati-malam", action="store_true",
                    help="dipakai bersama --urgent: lewati (tidak memproses apa pun) kalau "
                        "jam sekarang 16.00-06.59 (jendela malam TIPE 1)")
    ap.add_argument("--non-wajib", action="store_true",
                    help="dipakai bersama --label/--reguler: tulis 'NON WAJIB KELUAR' di kolom U "
                        "PICKLIST.xlsx tiap picklist proses ini (TIPE 2/3 langkah SPX, TIPE 4 "
                        "langkah SPX-J&T)")
    ap.add_argument("--non-wajib-sore", action="store_true",
                    help="seperti --non-wajib, tapi hanya kalau menu mulai dijalankan setelah "
                        "16.00 (16.01 dst; jam menu dibaca dari env WAKTU_MENU_MULAI, epoch detik, "
                        "diisi sekali oleh proses-harian.bat/jalankan_harian.py; kosong = sekarang) "
                        "- dipakai TIPE 1 yang juga berjalan pagi 07.00-12.00 (wajib keluar)")
    ap.add_argument("--reguler", action="store_true",
                    help="hanya buat picklist sisa reguler (TikTok Shop & Shopee, bukan SKU "
                        "spesial) sampai label PDF, tanpa proses SKU spesial "
                        "(tanpa --jalankan = mode uji)")
    ap.add_argument("--bagian", choices=["1qty", "kombinasi"],
                    help="dipakai bersama --reguler: batasi ke 1 bagian saja")
    ap.add_argument("--kurir", choices=["jnt", "spx", "spx-hemat", "spx-hemat-pagi"],
                    help="dipakai bersama --label atau --reguler: pisahkan J&T dan SPX jadi "
                        "picklist sendiri-sendiri, bukan digabung (dipakai TIPE 2 & TIPE 3 - "
                        "lihat proses-harian.bat/docs/jadwal-proses.md); tanpa --kurir = J&T "
                        "dan SPX digabung seperti semula (TIPE 1/TIPE 4). spx-hemat & "
                        "spx-hemat-pagi (s.d. jam 12:00, folder hasil terpisah) hanya untuk "
                        "mode event dan WAJIB bersama --event")
    ap.add_argument("--event", action="store_true",
                    help="mode event, dipakai bersama --label atau --reguler dan --kurir jnt|"
                        "spx-hemat|spx-hemat-pagi: penentuan SKU spesial dihitung hanya dari "
                        "kurir itu (bukan J&T+SPX digabung). Tanpa --event perilaku harian")
    ap.add_argument("--spx-standard", action="store_true",
                    help="hanya buat picklist SPX Standard (mode event): semua pesanan SPX "
                        "Standard, TANPA dipisah spesial/satuan/kombinasi, dipecah per lantai "
                        "rak gudang (1/2/3/LAINNYA) sampai label PDF (tanpa --jalankan = mode "
                        "uji)")
    ap.add_argument("--pagi", action="store_true",
                    help="dipakai bersama --spx-standard: versi Shopee Pagi (hanya Shopee, jam "
                        "pesan s.d. 12:00 WIB hari ini, folder hasil SPX_PAGI)")
    ap.add_argument("--shopee-pagi", action="store_true",
                    help="hanya buat picklist Shopee Pagi (channel Shopee, jam pesan s.d. "
                        "12:00 WIB hari ini, dipecah per lantai rak gudang) sampai label PDF "
                        "- dijalankan manual 1x sehari, BUKAN bagian alur otomatis --label "
                        "(tanpa --jalankan = mode uji)")
    ap.add_argument("--jnt-siang", action="store_true",
                    help="hanya buat picklist J&T Resi Siang (channel TikTok Shop, kurir "
                        "J&T, jam pesan s.d. 15:00 WIB hari ini, dipecah per lantai rak "
                        "gudang) sampai label PDF - dijalankan manual 1x sehari, BUKAN "
                        "bagian alur otomatis --label (tanpa --jalankan = mode uji)")
    ap.add_argument("--recheck-stok", action="store_true",
                    help="cek ulang stok untuk SEMUA pesanan yang berstatus stok kosong "
                        "(tombol 'Recheck Stok' di web) - pesanan yang stoknya sudah "
                        "tersedia lagi otomatis kembali diproses normal (dijalankan paling "
                        "pertama di tiap TIPE proses-harian.bat; tanpa --jalankan = mode uji)")
    ap.add_argument("--upload-iresis", action="store_true",
                    help="unduh Excel 'Daftar Penjualan Faktur' terbaru dari Jubelio lalu upload "
                        "ke menu Upload Resi IRESIS (dulu manual, setelah proses pesanan "
                        "selesai) - langkah terakhir tiap TIPE proses-harian.bat; tanpa "
                        "--jalankan = mode uji, hanya unduh & tampilkan rencana")
    ap.add_argument("--paksa", action="store_true",
                    help="dipakai bersama --upload-iresis: tetap jalan walau jam 20.00-04.59 "
                        "(jendela yang biasanya melewati IRESIS)")
    ap.add_argument("--hari", type=int, default=2, metavar="N",
                    help="dipakai bersama --upload-iresis: rentang laporan faktur N hari "
                        "terakhir termasuk hari ini (bawaan 2, seperti kebiasaan tim)")
    ap.add_argument("--hari-pesanan", type=int, default=4, metavar="N",
                    help="dipakai bersama --upload-iresis: rentang laporan PESANAN N hari "
                        "terakhir termasuk hari ini (bawaan 4 = 3 hari ke belakang + hari ini, "
                        "sesuai sniff 07-10-2026)")
    ap.add_argument("--operator", metavar="NAMA", nargs="?", const="",
                    help="ganti operator aktif (nama harus sudah ada di daftar) lalu selesai; "
                        "tanpa NAMA = tampilkan daftar & operator aktif. Operator ini yang ditulis "
                        "di kolom F PICKLIST.xlsx (lihat operator_aktif.py)")
    ap.add_argument("--tambah-operator", metavar="NAMA",
                    help="tambah NAMA ke daftar operator (tidak mengganti operator aktif) lalu selesai")
    ap.add_argument("--cek-sinkron", action="store_true",
                    help="tampilkan status kunci serah-terima antar perangkat & cek file konflik "
                        "sinkron (OneDrive/Google Drive/Syncthing) lalu selesai; exit 1 kalau "
                        "ada konflik atau kunci dipegang perangkat lain (lihat serah_terima.py)")
    ap.add_argument("--abaikan-kunci", action="store_true",
                    help="ambil alih kunci serah-terima yang dipegang perangkat lain (hanya kalau "
                        "yakin perangkat itu sudah berhenti)")
    ap.add_argument("--sku", action="append",
                    help="hanya proses SKU ini (boleh diulang)")
    ap.add_argument("--jalankan", action="store_true",
                    help="benar-benar buat picklist, selesaikan picking, minta resi, cetak label")
    ap.add_argument("--lanjut", metavar="PICK-000xxxxxx",
                    help="lanjutkan picklist yang prosesnya terhenti")
    ap.add_argument("--nama", metavar="LABEL",
                    help="dipakai bersama --lanjut: nama label di nama file PDF & kolom SKU "
                        "riwayat (mis. KOMBINASI-REGULER-LANTAI2, atau SKU-nya utk SKU spesial)")
    ap.add_argument("--tag", metavar="TAG",
                    help="dipakai bersama --lanjut: penanda SKU spesial (SPESIAL/JNT_SPESIAL/"
                        "SPX_SPESIAL/SPXHEMAT_SPESIAL/SPXHEMATPAGI_SPESIAL) - disisipkan di nama file & jadi subfolder")
    ap.add_argument("--subfolder", metavar="SUBFOLDER",
                    help="dipakai bersama --lanjut: subfolder tujuan PDF (URGENT, SATUAN, "
                        "KOMBINASI, JNT_SATUAN, dst)")
    ap.add_argument("--sesi", metavar="YYYY-MM-DD/N", type=_sesi_valid,
                    help="simpan label ke folder sesi ini (mis. 2026-10-06/12, folder sesi "
                        "asal picklist yang terhenti), bukan folder sesi baru")
    args = ap.parse_args()
    if (pesan := pesan_salah_mode_event(args)):
        ap.error(pesan)

    if args.operator is not None or args.tambah_operator:
        return atur_operator(args)

    muat_env(ROOT / ".env")
    if args.cek_sinkron:
        return cek_sinkron()
    log = siapkan_log()
    if (galat := ambil_kunci(log, args)):
        log.error(galat)
        return 1
    if args.upload_iresis and not args.paksa and jam_tanpa_iresis():
        log.info("IRESIS DILEWATI: jam %s masuk jendela 20.00-05.00 (unduh & upload faktur/pesanan "
                 "tidak dijalankan). Paksa manual: --upload-iresis --jalankan --paksa.",
                 datetime.now().strftime("%H.%M"))
        return 0
    if args.upload_iresis:
        # bukan proses picklist - jangan buat folder sesi label baru yang kosong
        return upload_faktur_iresis(log, args)
    if args.urgent and args.lewati_malam and jam_malam():
        # dicek sebelum folder sesi dibuat supaya tidak ada folder sesi kosong (nomor sesi bergeser)
        log.info("Urgent DILEWATI: jam %s masuk jendela malam 16.00-07.00 (Lazada & GTL-SiCepat "
                 "tidak diproses di TIPE 1 sore/malam/dini hari).",
                 datetime.now().strftime("%H.%M"))
        return 0
    global FOLDER_LABEL_SESI
    FOLDER_LABEL_SESI = FOLDER_LABEL / args.sesi if args.sesi else folder_label_sesi()
    FOLDER_LABEL_SESI.mkdir(parents=True, exist_ok=True)
    log.info("Folder sesi label: %s", FOLDER_LABEL_SESI)
    if atur_catatan_non_wajib(args):
        log.info("Catatan kolom U PICKLIST.xlsx: %s", TEKS_NON_WAJIB)
    try:
        if args.lanjut:
            return lanjut_picklist(log, args)
        if args.recheck_stok:
            return recheck_stok_pesanan(log, args)
        if args.sampel:
            return sampel_picklist(log, args)
        if args.spx_standard:
            return spx_standard_picklist(log, args)
        if args.urgent:
            return urgent_picklist(log, args)
        if args.reguler:
            return reguler_picklist(log, args)
        if args.shopee_pagi:
            return shopee_pagi_picklist(log, args)
        if args.jnt_siang:
            return jnt_siang_picklist(log, args)

        waktu, mulai = datetime.now(), time.monotonic()
        perlu_api = not args.excel or not args.tanpa_cek_nilai or args.label
        token = login(log) if perlu_api else None

        proses_sungguhan = args.label and args.jalankan

        excel = args.excel or download(log, token)
        log.info("Excel: %s", excel)
        df = baca_excel(excel)

        nilai = None
        if not args.tanpa_cek_nilai:
            import jubelio
            kandidat = resi_kandidat(df, kurir_hitung(args))
            log.info("Mengambil nilai pesanan dari API untuk %d resi kandidat", len(kandidat))
            nilai = jubelio.ambil_nilai_pesanan(token, kandidat)

        tabel, ringkasan = hitung_sku_spesial(df, nilai, kurir_hitung(args))
        log.info("Baris %d | resi %d | lolos 1 baris %d | qty1 %d | J&T/SPX %d | "
                 "nilai 0 (kreator) %d | lolos nilai %d",
                 ringkasan["total_baris"], ringkasan["total_resi"], ringkasan["resi_1_baris"],
                 ringkasan["resi_1_baris_qty1"], ringkasan["resi_lolos_kurir"],
                 ringkasan["resi_nilai_0"], ringkasan["resi_lolos_nilai"])
        if ringkasan["resi_tanpa_nilai"]:
            log.warning("%d resi kandidat tidak ditemukan nilainya di API "
                        "(dikeluarkan dari hitungan spesial)", ringkasan["resi_tanpa_nilai"])
        log.info("Kandidat (rencana): %d SKU spesial, %d resi spesial",
                 ringkasan["total_sku_spesial"], ringkasan["total_resi_spesial"])
        lama_daftar = time.monotonic() - mulai

        if proses_sungguhan:
            # PDF BELUM dibuat di sini: dibuat proses_label_sku() setelah proses SKU spesial
            # betul-betul jalan, dari jumlah pesanan AKTUAL yang berhasil dipicklist (bisa
            # beda dari kandidat di atas kalau ada yang dilewati/gagal/stok kosong).
            return proses_label_sku(log, token, df, tabel, ringkasan, args, lama_daftar, waktu)

        FOLDER_PDF.mkdir(parents=True, exist_ok=True)
        pdf = FOLDER_PDF / nama_pdf_spesial(waktu, args)
        buat_pdf(tabel, ringkasan, pdf, waktu)
        log.info("SELESAI: %d SKU spesial, %d resi spesial -> %s",
                 ringkasan["total_sku_spesial"], ringkasan["total_resi_spesial"], pdf)
        log.info("Daftar resi spesial (urut rak) dibuat dalam %s", durasi(lama_daftar))

        if args.label:
            return proses_label_sku(log, token, df, tabel, ringkasan, args, lama_daftar, waktu)
        return 0
    except Exception as e:   # noqa: BLE001 - catat semua kegagalan ke log
        log.exception("GAGAL: %s", e)
        return 1


def _lengkapi_fallback_bundle(k, df, grup_dari_excel: dict, lantai_dari_excel: dict) -> tuple[dict, dict]:
    """Lengkapi fallback Excel (grup_rak_per_pesanan()/lantai_per_pesanan(), selalu gagal utk
    SKU bundling - lihat catatan di situ) dengan fallback live API (proses_label.
    grup_rak_bundle_live()/lantai_bundle_live(), lewat master data Jubelio - lihat
    sku_spesial.sku_bundle_per_pesanan()). Live LEBIH DIUTAMAKAN (menang kalau ada hasil),
    Excel tetap jadi fallback terakhir utk kasus lain yang bukan bundling."""
    import proses_label

    sku_bundle = sku_bundle_per_pesanan(df)
    if not sku_bundle:
        return grup_dari_excel, lantai_dari_excel
    grup_live = proses_label.grup_rak_bundle_live(k, sku_bundle, proses_label.GRUP_RAK)
    lantai_live = proses_label.lantai_bundle_live(k, sku_bundle, proses_label.LANTAI_RAK)
    return {**grup_dari_excel, **grup_live}, {**lantai_dari_excel, **lantai_live}


def proses_label_sku(log: logging.Logger, token: str, df, tabel, ringkasan: dict, args,
                     lama_daftar: float, waktu: datetime) -> int:
    import proses_label

    urutan = list(tabel["SKU"])                      # tabel sudah urut No Rak
    if args.sku:
        tidak_ada = [s for s in args.sku if s not in urutan]
        if tidak_ada:
            log.warning("SKU bukan SKU spesial, diabaikan: %s", ", ".join(tidak_ada))
        urutan = [s for s in urutan if s in args.sku]
    resi_per_sku = {s: ringkasan["resi_per_sku"][s] for s in urutan}

    k = proses_label.Klien(token)
    batas = proses_label.batas_untuk_kurir(args.kurir)      # None kecuali spx-hemat-pagi
    rak_per_sku = dict(zip(tabel["SKU"], tabel["No Rak"]))
    # Fallback khusus SKU bundling utk picklist 1qty reguler (lihat proses_reguler()):
    # live API Jubelio selalu melaporkan location_id -1/virtual utk item bundle, padahal kolom
    # Rak di Excel ini tetap berisi rak fisik asli komponennya (ditemukan 03-10-2026).
    rak_dominan_sku = rak_dominan_per_sku(df)
    grup_dari_excel = grup_rak_per_pesanan(df, proses_label.GRUP_RAK, rak_dominan_sku)
    lantai_dari_excel = lantai_per_pesanan(df, proses_label.LANTAI_RAK, rak_dominan_sku)
    grup_dari_excel, lantai_dari_excel = _lengkapi_fallback_bundle(
        k, df, grup_dari_excel, lantai_dari_excel)
    if not args.jalankan:
        if not resi_per_sku:
            log.info("Tidak ada SKU spesial untuk diproses")
            return 0
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana(k, resi_per_sku, rak_per_sku, args.kurir, batas)
        if not args.sku and not args.tanpa_reguler:
            resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values() for no in daftar}
            proses_label.rencana_reguler(k, resi_spesial_semua, kurir=args.kurir,
                                         grup_dari_excel=grup_dari_excel,
                                         lantai_dari_excel=lantai_dari_excel, batas=batas)
        return 0

    # Gelombang bersama: semua picklist (spesial dulu, lalu reguler) dibuat SERIAL di sini, tapi
    # langkah tunggu picking/resi/PDF tiap picklist langsung jalan di latar belakang - picklist
    # reguler tidak perlu menunggu PDF SKU spesial selesai. Urutan pembuatan (dan deteksi nomor
    # picklist terlompat) sama seperti sebelumnya.
    gelombang = proses_label.Gelombang()
    hasil, hasil_reguler, lama_proses = [], [], 0.0
    mulai = time.monotonic()
    try:
        if resi_per_sku:
            log.info("MEMPROSES %d SKU spesial per rak sampai label PDF", len(resi_per_sku))
            hasil = proses_label.proses(k, resi_per_sku, FOLDER_LABEL_SESI, FILE_RIWAYAT,
                                        rak_per_sku, args.kurir, batas, gelombang=gelombang)
        else:
            log.info("Tidak ada SKU spesial untuk diproses")

        if not args.sku and not args.tanpa_reguler:
            # Sisa reguler (TikTok Shop & Shopee, bukan SKU spesial) baru bisa dipisah dengan
            # benar SETELAH tahu daftar SKU spesial hari itu -> dijalankan di sini, bukan sebelum
            # download seperti urgent. Dilewati kalau --sku dipakai (proses cuma sebagian SKU,
            # daftar SKU spesial belum lengkap utk pengecualian), atau --tanpa-reguler (SKU
            # spesial saja).
            resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values()
                                  for no in daftar}
            log.info("MEMPROSES picklist sisa reguler (TikTok Shop & Shopee, bukan SKU spesial)")
            hasil_reguler = proses_label.proses_reguler(
                k, resi_spesial_semua, FILE_RIWAYAT, FOLDER_LABEL_SESI, kurir=args.kurir,
                grup_dari_excel=grup_dari_excel, lantai_dari_excel=lantai_dari_excel,
                batas=batas, gelombang=gelombang)
    finally:
        gelombang.tunggu()      # catat riwayat/PICKLIST.xlsx semua picklist, walau ada error
    lama_proses = time.monotonic() - mulai

    if hasil:
        log.info("RINGKASAN (urut rak):")
        for h in hasil:
            log.info("  %-8s %-14s %-16s pesanan %-3s resi %-3s %-18s %s", h["Rak"], h["SKU"],
                     h.get("No Picklist", "-"), h.get("Total Pesanan", "-"), h.get("Resi Keluar", "-"),
                     h["Durasi"], h.get("Catatan", ""))

    # PDF dibuat SETELAH proses, dari hasil AKTUAL (SKU yang benar-benar berhasil dipicklist),
    # bukan dari daftar kandidat -> total di PDF selalu sama dengan yang benar-benar diproses.
    baris_aktual = [{"No Rak": h["Rak"], "SKU": h["SKU"], "Jumlah Resi": h["Total Pesanan"]}
                    for h in hasil if h.get("No Picklist")]
    tabel_aktual = pd.DataFrame(baris_aktual, columns=["No Rak", "SKU", "Jumlah Resi"])
    ringkasan_aktual = {
        "total_sku_spesial": len(tabel_aktual),
        "total_resi_spesial": int(tabel_aktual["Jumlah Resi"].sum()) if len(tabel_aktual) else 0,
    }
    FOLDER_PDF.mkdir(parents=True, exist_ok=True)
    pdf = FOLDER_PDF / nama_pdf_spesial(waktu, args)
    buat_pdf(tabel_aktual, ringkasan_aktual, pdf, waktu)
    log.info("SELESAI: %d SKU spesial (benar-benar diproses), %d resi -> %s",
             ringkasan_aktual["total_sku_spesial"], ringkasan_aktual["total_resi_spesial"], pdf)

    diproses = [h["detik"] for h in hasil if h.get("No Picklist")]
    log.info("Waktu buat daftar resi spesial : %s", durasi(lama_daftar))
    log.info("Waktu proses %d SKU spesial    : %s (%d dibuat picklist, rata-rata %s per SKU)",
             len(hasil), durasi(lama_proses), len(diproses),
             durasi(sum(diproses) / len(diproses)) if diproses else "-")
    log.info("Total waktu                    : %s", durasi(lama_daftar + lama_proses))
    log.info("Riwayat: %s", FILE_RIWAYAT)
    bermasalah = cetak_bermasalah(hasil + hasil_reguler)
    return 1 if bermasalah else 0


def recheck_stok_pesanan(log: logging.Logger, args) -> int:
    import jubelio

    token = login(log)
    sebelum = jubelio.ambil_stok_kosong(token)
    log.info("%d pesanan berstatus stok kosong saat ini", len(sebelum))
    if not sebelum:
        log.info("Tidak ada pesanan stok kosong untuk di-recheck")
        return 0
    for o in sebelum:
        log.info("  - %s (%s)", o.get("salesorder_no"), o.get("store_name", "-"))

    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        return 0

    jubelio.recheck_stok(token)
    sesudah = jubelio.ambil_stok_kosong(token)
    nomor_sebelum = {o.get("salesorder_no") for o in sebelum}
    nomor_sesudah = {o.get("salesorder_no") for o in sesudah}
    pulih = nomor_sebelum - nomor_sesudah
    log.info("SELESAI recheck stok: %d pesanan kembali normal, %d masih stok kosong",
             len(pulih), len(sesudah))
    for o in sesudah:
        log.info("  - masih stok kosong: %s (%s)", o.get("salesorder_no"), o.get("store_name", "-"))
    return 0


def sampel_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_sampel(k)
        return 0
    hasil = proses_label.proses_sampel(k, FILE_RIWAYAT, FOLDER_LABEL_SESI)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI sampel: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def urgent_picklist(log: logging.Logger, args) -> int:
    import proses_label

    skenario = ([s for s in proses_label.SKENARIO_URGENT if s[0].lower() == args.channel]
               if args.channel else None)
    if args.channel and not skenario:
        raise SystemExit(f"Channel tidak dikenal: {args.channel}")

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_urgent(k, skenario)
        return 0
    hasil = proses_label.proses_urgent(k, FILE_RIWAYAT, FOLDER_LABEL_SESI, skenario)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI urgent: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def reguler_picklist(log: logging.Logger, args) -> int:
    import proses_label

    token = login(log)
    excel = args.excel or download(log, token)
    log.info("Excel: %s", excel)
    df = baca_excel(excel)
    nilai = None
    if not args.tanpa_cek_nilai:
        import jubelio
        kandidat = resi_kandidat(df, kurir_hitung(args))
        log.info("Mengambil nilai pesanan dari API untuk %d resi kandidat", len(kandidat))
        nilai = jubelio.ambil_nilai_pesanan(token, kandidat)
    _, ringkasan = hitung_sku_spesial(df, nilai, kurir_hitung(args))
    resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values() for no in daftar}
    log.info("%d resi SKU spesial hari ini (dikeluarkan dari picklist reguler)",
             len(resi_spesial_semua))
    # Fallback khusus SKU bundling utk picklist 1qty reguler (lihat proses_reguler()):
    # live API Jubelio selalu melaporkan location_id -1/virtual utk item bundle, padahal kolom
    # Rak di Excel ini tetap berisi rak fisik asli komponennya (ditemukan 03-10-2026).
    rak_dominan_sku = rak_dominan_per_sku(df)
    grup_dari_excel = grup_rak_per_pesanan(df, proses_label.GRUP_RAK, rak_dominan_sku)
    lantai_dari_excel = lantai_per_pesanan(df, proses_label.LANTAI_RAK, rak_dominan_sku)

    k = proses_label.Klien(token)
    batas = proses_label.batas_untuk_kurir(args.kurir)      # None kecuali spx-hemat-pagi
    grup_dari_excel, lantai_dari_excel = _lengkapi_fallback_bundle(
        k, df, grup_dari_excel, lantai_dari_excel)
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_reguler(k, resi_spesial_semua, args.bagian, args.kurir,
                                     grup_dari_excel=grup_dari_excel,
                                     lantai_dari_excel=lantai_dari_excel, batas=batas)
        return 0
    hasil = proses_label.proses_reguler(k, resi_spesial_semua, FILE_RIWAYAT, FOLDER_LABEL_SESI,
                                        args.bagian, args.kurir, grup_dari_excel=grup_dari_excel,
                                        lantai_dari_excel=lantai_dari_excel, batas=batas)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI reguler: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


KURIR_MODE_EVENT = ("jnt", "spx-hemat", "spx-hemat-pagi")      # nilai --kurir yang sah dgn --event
KURIR_HANYA_EVENT = ("spx-hemat", "spx-hemat-pagi")            # nilai --kurir yang WAJIB --event


def pesan_salah_mode_event(args) -> str | None:
    """Pesan error kalau kombinasi flag mode event salah, None kalau sah. Dipisah dari argparse
    supaya mudah diuji. SPX Hemat tanpa --event DITOLAK (bukan diam-diam dihitung digabung):
    penentuan SKU spesial per kurir hanya berlaku dengan --event, jadi salah ketik di .bat tidak
    boleh menghasilkan picklist dengan hitungan yang tidak dimaksud."""
    if args.kurir in KURIR_HANYA_EVENT and not args.event:
        return f"--kurir {args.kurir} hanya untuk mode event: tambahkan --event"
    if args.event:
        if not (args.label or args.reguler):
            return "--event dipakai bersama --label atau --reguler"
        if args.kurir not in KURIR_MODE_EVENT:
            return "--event butuh --kurir " + " atau ".join(KURIR_MODE_EVENT)
    if (args.non_wajib or args.non_wajib_sore) and not (args.label or args.reguler):
        return "--non-wajib/--non-wajib-sore dipakai bersama --label atau --reguler"
    if args.pagi and not args.spx_standard:
        return "--pagi hanya dipakai bersama --spx-standard"
    if args.spx_standard and (args.label or args.reguler or args.event):
        return "--spx-standard berdiri sendiri (tidak bersama --label/--reguler/--event)"
    return None


def kurir_hitung(args) -> str | None:
    """Kurir untuk penentuan SKU spesial (sku_spesial.hitung_sku_spesial): HANYA mode event yang
    menghitung per kurir; selain itu None = J&T+SPX digabung seperti semula, APA PUN nilai
    --kurir (TIPE 2/3 harian tetap menggabung)."""
    return args.kurir if getattr(args, "event", False) else None


def nama_pdf_spesial(waktu: datetime, args) -> str:
    """Nama PDF ringkasan SKU spesial. Mode event diberi akhiran kurir supaya hitungan J&T dan
    SPX Hemat (dijalankan berturut-turut, bisa dalam menit yang sama) tidak saling menimpa."""
    akhiran = f"_{args.kurir}" if kurir_hitung(args) else ""
    return f"SKU_Spesial_{waktu:%Y-%m-%d_%H%M}{akhiran}.pdf"


def spx_standard_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_spx_standard(k, args.pagi)
        return 0
    hasil = proses_label.proses_spx_standard(k, FILE_RIWAYAT, FOLDER_LABEL_SESI, args.pagi)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI SPX Standard%s: %d picklist dibuat%s", " (Shopee Pagi)" if args.pagi else "",
             len(hasil) - len(gagal), f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def shopee_pagi_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_shopee_pagi(k)
        return 0
    hasil = proses_label.proses_shopee_pagi(k, FILE_RIWAYAT, FOLDER_LABEL_SESI)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI Shopee Pagi: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def jnt_siang_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_jnt_siang(k)
        return 0
    hasil = proses_label.proses_jnt_siang(k, FILE_RIWAYAT, FOLDER_LABEL_SESI)
    gagal = cetak_bermasalah(hasil)
    log.info("SELESAI J&T Resi Siang: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def lanjut_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        p = k.get(f"sales/picklists/{int(args.lanjut.upper().replace('PICK-', ''))}")
        status = sorted({str(i.get('wms_status')) for i in p['items']})
        log.info("MODE UJI: %s berisi %d pesanan, status %s, is_completed=%s. "
                 "Tambahkan --jalankan untuk melanjutkan.", p["picklist_no"],
                 len({i['salesorder_id'] for i in p['items']}), status, p.get("is_completed"))
        return 0
    baris = proses_label.lanjutkan(k, args.lanjut, FOLDER_LABEL_SESI, FILE_RIWAYAT,
                                   nama=args.nama, tag=args.tag, subfolder=args.subfolder)
    log.info("SELESAI: %s", baris)
    return 0


def upload_faktur_iresis(log: logging.Logger, args) -> int:
    """Langkah UPLOAD IRESIS (akhir tiap TIPE proses-harian.bat): unduh 'Daftar Penjualan
    Faktur' lalu upload ke IRESIS. Kegagalan TIDAK menghentikan TIPE - dicetak mencolok lewat
    cetak_bermasalah() (juga muncul lagi di rekap waktu) dan exit code 1. Mode uji (tanpa
    --jalankan): hanya unduh, upload tidak dilakukan."""
    import iresis
    import jubelio

    username = os.environ.get("IRESIS_USERNAME")
    password = os.environ.get("IRESIS_PASSWORD")
    if args.jalankan and not (username and password):
        log.error("IRESIS_USERNAME / IRESIS_PASSWORD belum diisi di file .env")
        cetak_bermasalah([{"SKU": "UPLOAD IRESIS", "Catatan": "GAGAL: IRESIS_USERNAME/"
                           "IRESIS_PASSWORD belum diisi di .env"}], "PERHATIAN: UPLOAD IRESIS GAGAL")
        return 1
    hari_ini = datetime.now().date()
    laporan = [("Faktur", jubelio.ambil_url_faktur, args.hari, "daftar_penjualan_faktur"),
               ("Pesanan", jubelio.ambil_url_pesanan, getattr(args, "hari_pesanan", 4),
                "daftar_penjualan_pesanan")]
    gagal = False
    upload_ok = False
    token = None
    for nama, ambil_url, hari, awalan in laporan:
        # tiap laporan berdiri sendiri: gagalnya faktur tidak membatalkan upload pesanan
        dari = hari_ini - timedelta(days=max(hari, 1) - 1)
        try:
            token = token or login(log)
            log.info("Meminta URL laporan Daftar Penjualan %s %s s.d. %s", nama, dari, hari_ini)
            url = ambil_url(token, dari, hari_ini)
            file = jubelio.unduh_excel(token, url, FOLDER_FAKTUR, awalan=awalan)
            log.info("%s diunduh: %s", nama, file.name)
            if not args.jalankan:
                log.info("MODE UJI - upload %s ke IRESIS (%s) tidak dilakukan. Tambahkan "
                         "--jalankan untuk upload.", nama.lower(), iresis._url_dasar())
                continue
            log.info("Upload %s ke IRESIS", file.name)
            ringkasan = iresis.unggah(file, username, password)
        except Exception as e:   # noqa: BLE001 - catat semua kegagalan, jangan hentikan TIPE
            log.exception("GAGAL upload %s ke IRESIS: %s", nama.lower(), e)
            cetak_bermasalah([{"SKU": "UPLOAD IRESIS", "Catatan": f"GAGAL ({nama}): {e}"}],
                             "PERHATIAN: UPLOAD IRESIS GAGAL")
            gagal = True
            continue
        log.info("IRESIS (%s): %s", nama.lower(), ringkasan)
        upload_ok = True
    if upload_ok:
        gagal = isi_scan_picklist(log, username, password, args.hari, hari_ini) or gagal
    return 1 if gagal else 0


def isi_scan_picklist(log: logging.Logger, username: str, password: str, hari: int,
                      hari_ini) -> bool:
    """Setelah upload: isi kolom P (SCAN) PICKLIST.xlsx dari laporan Total Picklist IRESIS untuk
    folder sesi `hari` hari terakhir. Mengembalikan True kalau GAGAL (tidak menghentikan TIPE)."""
    import iresis

    dari = hari_ini - timedelta(days=max(hari, 1) - 1)
    try:
        total = iresis.ambil_total_picklist(iresis.login(username, password), dari,
                                            datetime.now())
        berubah = 0
        for h in range(max(hari, 1)):
            folder_tgl = FOLDER_LABEL / str(dari + timedelta(days=h))
            for folder in sorted(folder_tgl.glob("*")) if folder_tgl.is_dir() else []:
                berubah += rekap_master_excel.isi_scan(folder, total)
        log.info("IRESIS: kolom SCAN PICKLIST.xlsx diisi/diperbarui di %d baris (laporan %d "
                 "picklist)", berubah, len(total))
        return False
    except Exception as e:   # noqa: BLE001 - jangan hentikan TIPE
        log.exception("GAGAL mengisi SCAN dari IRESIS: %s", e)
        cetak_bermasalah([{"SKU": "UPLOAD IRESIS", "Catatan": f"GAGAL (isi SCAN picklist): {e}"}],
                         "PERHATIAN: UPLOAD IRESIS GAGAL")
        return True


if __name__ == "__main__":
    sys.exit(main())
