"""Cetak bulk label pengiriman (SPESIAL/GTL-SICEPAT/SATUAN/KOMBINASI) dari folder sesi
label-pengiriman TERBARU.

Program ini TIDAK membuat label baru - cuma mencari file PDF yang SUDAH ada di
subfolder terkait jenis yang dipilih lewat --jenis (lihat JENIS_LABEL):
  --jenis spesial    -> subfolder SPESIAL/JNT_SPESIAL/SPX_SPESIAL (Alur 1, SKU
                        spesial - lihat TAG_SPESIAL & _tag_spesial() di
                        proses_label.py), HANYA file bertanda `_SPESIAL_` yang ikut
                        (mis. PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf).
  --jenis gtl-sicepat -> subfolder URGENT (Alur 2), HANYA file GTL-SiCepat yang ikut (nama
                        file mengandung `_GTL-SICEPAT`, mis. GTL-SICEPAT-LANTAI1). Label
                        Lazada di subfolder yang sama TIDAK ikut dicetak bulk (dicetak
                        manual, lihat docs/analisa-alur-cetak-label.md bagian 6).
  --jenis satuan     -> subfolder SATUAN/JNT_SATUAN/SPX_SATUAN (Alur 3 bagian "1qty"),
                        SEMUA PDF ikut (mis. 1QTY-REGULER-2A).
  --jenis kombinasi  -> subfolder KOMBINASI/JNT_KOMBINASI/SPX_KOMBINASI (Alur 3
                        bagian "kombinasi"), SEMUA PDF ikut (mis.
                        KOMBINASI-REGULER-LANTAI2).
  --jenis spesial-jnt / spesial-spx / satuan-jnt / satuan-spx / kombinasi-jnt /
  kombinasi-spx -> sama dengan tiga jenis di atas, tapi HANYA subfolder kurir itu
                        (JNT_SPESIAL, SPX_SATUAN, dst - hasil --kurir jnt/spx, TIPE 2 & 3).
  --jenis spx-pagi   -> subfolder SPX_PAGI (--shopee-pagi), SEMUA PDF ikut (SHOPEE-PAGI-LANTAI*).
  --jenis jnt-siang  -> subfolder JNT_SIANG (--jnt-siang), SEMUA PDF ikut (JNT-SIANG-LANTAI*).
Semua jenis dicetak BERURUT (nomor PICK terkecil dulu, nomor diekstrak dari awal nama
file - lihat POLA_SPESIAL/POLA_PICK) ke printer pilihan lewat SumatraPDF (-print-to,
-silent).

Sebelum mencetak (alur folder sesi, bukan `--ulang`), nomor PICK label yang ditemukan dicek
berurut atau tidak (lihat cari_nomor_terlompat()) - kalau ada nomor yang hilang di tengah
(mis. ada PICK 621, 622, lalu lompat ke 700), program BERHENTI dan tanya konfirmasi dulu
sebelum lanjut cetak, supaya user bisa cek dulu apakah ada label yang belum masuk folder ini
(masih dibuat, gagal, atau ketinggalan di folder sesi lain) - pertanyaan ini tetap muncul
meski pakai --tanpa-konfirmasi.

Pemakaian (lihat juga cetak-label-spesial.bat/cetak-label-gtl-sicepat.bat/
cetak-label-satuan.bat/cetak-label-kombinasi.bat, masing-masing isinya cuma
memanggil ini dengan --jenis tetap):
    .venv\\Scripts\\python.exe src\\print_spesial.py --jenis spesial
        # cari folder sesi terbaru, tampilkan daftar printer, pilih, konfirmasi, cetak
    .venv\\Scripts\\python.exe src\\print_spesial.py --jenis gtl-sicepat --folder label-pengiriman/2026-10-01/3
        # pakai folder sesi tertentu, bukan yang terbaru
    .venv\\Scripts\\python.exe src\\print_spesial.py --jenis satuan --tanpa-konfirmasi
        # lewati tanya Y/N sebelum mulai cetak (tetap tanya pilih printer)
    .venv\\Scripts\\python.exe src\\print_spesial.py --jenis kombinasi --ulang logs\\gagal_cetak_2026-10-01_153000.txt
        # cetak ULANG hanya file dari daftar gagal sebelumnya (lihat bagian "gagal" di bawah)

Perlu SumatraPDF terinstall (gratis, https://www.sumatrapdfreader.org/) - lokasi
SumatraPDF.exe dicari otomatis di PATH & lokasi install umum (lihat cari_sumatra()),
atau diset manual lewat environment variable SUMATRA_PDF_PATH.

Kertas habis / printer bermasalah di tengah proses: program memantau antrian cetak
Windows (PrintManagement - Get-PrintJob) setelah tiap file dikirim. Kalau job itu
ditandai bermasalah (mis. "PaperOut", "Error", "UserIntervention", "Offline"), program
BERHENTI SEJENAK di file itu dan menunggu user memperbaikinya (isi ulang kertas, dst)
lalu tekan ENTER - BUKAN lanjut ke file berikutnya dulu, supaya urutan cetak tetap benar
dan tidak ada file yang terlewat diam-diam. User juga bisa ketik "lewati" untuk
melewati 1 file itu saja (dicatat sebagai gagal, lihat di bawah).
CATATAN KETERBATASAN: pemantauan ini bergantung pada driver printer melaporkan status
ke Windows Print Spooler. Printer tertentu (umumnya printer label/thermal yang mencetak
langsung tanpa melapor balik) mungkin TIDAK melaporkan status ini sama sekali - kalau
begitu program tidak akan tahu kertas habis sampai dicek fisik sendiri. Daftar
berhasil/gagal (lihat di bawah) tetap berguna sebagai jaring pengaman untuk kasus itu.

Setiap file yang diproses (berhasil maupun gagal/dilewati) dicatat jelas ke log
(logs/cetak_YYYY-MM.log, sama seperti run_YYYY-MM.log main.py) DAN ke layar. Setelah
semua file selesai diproses, kalau ada yang gagal: daftar nama filenya disimpan ke
logs/gagal_cetak_<waktu>.txt, dan program langsung menawarkan untuk mencetak ULANG
hanya file yang gagal itu saja (bukan mengulang dari awal) - baik langsung (Y/N) maupun
belakangan lewat --ulang.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from proses_label import (KURIR_LABEL_FILE, SUBFOLDER_JNT_SIANG, SUBFOLDER_KOMBINASI,
                           SUBFOLDER_SATUAN, SUBFOLDER_SPX_PAGI, SUBFOLDER_URGENT,
                           TAG_SPESIAL)

ROOT = Path(__file__).resolve().parent.parent   # root project, bukan folder src/ ini
FOLDER_LABEL = ROOT / "label-pengiriman"
FOLDER_LOG = ROOT / "logs"
# Daftar path label yang SUDAH berhasil dicetak (1 path absolut per baris, ditambah tiap file
# sukses). Cetak berikutnya melewati file di daftar ini supaya tidak tercetak dobel waktu
# folder sesi dipakai bersama beberapa TIPE; --cetak-ulang-semua mengabaikannya.
FILE_SUDAH_DICETAK = FOLDER_LOG / "sudah_dicetak.txt"

POLA_TANGGAL_SESI = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Penanda SPESIAL ini dibuat proses_label.py (lihat TAG_SPESIAL & _tag_spesial()) - HANYA
# alur SKU spesial yang menyisipkannya di nama file, jadi cukup cari pola ini saja. Kalau
# --kurir jnt/spx dipakai saat proses, tag-nya disisipi awalan JNT_/SPX_ (lihat
# _tag_spesial()) - pola ini menerima dengan atau tanpa awalan itu.
POLA_SPESIAL = re.compile(
    rf"^PICK-0*(\d+)_(?:(?:{'|'.join(KURIR_LABEL_FILE.values())})_)?SPESIAL_.*\.pdf$",
    re.IGNORECASE)
# Subfolder tempat label SPESIAL disimpan: tanpa --kurir di folder `SPESIAL`, dengan
# --kurir jnt/spx di folder `JNT_SPESIAL`/`SPX_SPESIAL` (lihat _tag_spesial()) - dicari
# semuanya supaya label dari ketiga kemungkinan tetap ketemu dan tercetak.
SUBFOLDER_SPESIAL = [TAG_SPESIAL] + [f"{v}_{TAG_SPESIAL}" for v in KURIR_LABEL_FILE.values()]

# Pola generik untuk jenis selain `spesial`: label gtl-sicepat/satuan/kombinasi TIDAK
# punya tag unik di nama file (variatif: GTL-SiCepat-LANTAI1, 1QTY-REGULER-2A,
# KOMBINASI-REGULER-LANTAI2, dst - lihat proses_label.py), jadi keanggotaan "ikut dicetak
# jenis ini" ditentukan LOKASI SUBFOLDER (lihat JENIS_LABEL & daftar_label() di bawah),
# ditambah FILTER_NAMA untuk subfolder yang dipakai bersama - pola ini cuma dipakai
# mengekstrak nomor PICK di awal nama file (selalu ada di semua label, lihat _nama_file()
# di proses_label.py) untuk urutan cetak & deteksi nomor terlompat.
POLA_PICK = re.compile(r"^PICK-0*(\d+)_.*\.pdf$", re.IGNORECASE)
# Subfolder URGENT dipakai bersama Lazada & GTL-SiCepat, tapi cetak bulk hanya GTL-SiCepat
# (nama file memuat nama skenarionya, lihat SKENARIO_URGENT di proses_label.py).
FILTER_NAMA = {"gtl-sicepat": re.compile(r"^PICK-\d+_GTL-SICEPAT", re.IGNORECASE)}

# Jenis label yang didukung cetak bulk -> daftar subfolder yang dicari & digabung
# di dalam folder sesi (lihat SUBFOLDER_URGENT/SUBFOLDER_SATUAN/SUBFOLDER_KOMBINASI
# & TAG_SPESIAL di proses_label.py). "gtl-sicepat" SENGAJA tanpa varian kurir -
# proses_urgent() di proses_label.py memanggil subfolder=SUBFOLDER_URGENT polos,
# tidak lewat _gabung_kurir(), jadi tidak ada JNT_URGENT/SPX_URGENT.
JENIS_LABEL: dict[str, list[str]] = {
    "spesial": SUBFOLDER_SPESIAL,
    "gtl-sicepat": [SUBFOLDER_URGENT],
    "satuan": [SUBFOLDER_SATUAN] + [f"{v}_{SUBFOLDER_SATUAN}"
                                     for v in KURIR_LABEL_FILE.values()],
    "kombinasi": [SUBFOLDER_KOMBINASI] + [f"{v}_{SUBFOLDER_KOMBINASI}"
                                           for v in KURIR_LABEL_FILE.values()],
    # Varian per kurir (TIPE 2 & 3, kurir dipisah): HANYA subfolder kurir itu, supaya J&T dan
    # SPX bisa dicetak terpisah (printer/rak/kurir pickup berbeda). Jenis tanpa akhiran kurir
    # di atas tetap menggabung semuanya.
    **{f"{dasar}-{kode}": [f"{KURIR_LABEL_FILE[kode]}_{sub}"]
       for dasar, sub in (("spesial", TAG_SPESIAL), ("satuan", SUBFOLDER_SATUAN),
                          ("kombinasi", SUBFOLDER_KOMBINASI))
       for kode in KURIR_LABEL_FILE},
    "spx-pagi": [SUBFOLDER_SPX_PAGI],      # Shopee Pagi (--shopee-pagi), SEMUA PDF ikut
    "jnt-siang": [SUBFOLDER_JNT_SIANG],    # J&T Resi Siang (--jnt-siang), SEMUA PDF ikut
}

LOKASI_SUMATRA_UMUM = [
    r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
]

JEDA_ANTAR_CETAK_S = 0.5   # jeda antar print job, supaya spooler tidak kebanjiran
TIMEOUT_SUMATRA_S = 120    # batas tunggu SumatraPDF mengirim 1 dokumen ke spooler
TIMEOUT_POWERSHELL_S = 20

# Status job (Get-PrintJob -> JobStatus, dari PrintManagement module) yang dianggap
# "printer butuh perhatian user" - job tidak akan maju sendiri sampai masalahnya
# diperbaiki fisik (isi kertas, buka pintu, dst). "Paused" sengaja TIDAK dimasukkan
# sendirian (banyak printer sebentar "Paused" normal saat baru menerima job).
STATUS_JOB_BERMASALAH = ("PaperOut", "Error", "UserIntervention", "Offline", "Blocked_DevQ")
STATUS_JOB_SELESAI = ("Complete", "Printed", "Deleted")

log = logging.getLogger("cetak-spesial")


class CetakError(RuntimeError):
    pass


def siapkan_log() -> logging.Logger:
    FOLDER_LOG.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(FOLDER_LOG / f"cetak_{datetime.now():%Y-%m}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log


# ============================================================== 1. cari file
def folder_sesi_terbaru(folder_label: Path = FOLDER_LABEL) -> Path:
    """Folder sesi (mis. `label-pengiriman/2026-10-01/3`) TERBARU: dibandingkan dari
    tanggal lalu nomor urut sesi di namanya (sejalan dengan sesi_label_baru() di
    main.py yang membuatnya), BUKAN dari waktu modifikasi file/folder."""
    terbaik: tuple | None = None
    for folder_tanggal in folder_label.iterdir() if folder_label.is_dir() else []:
        if not folder_tanggal.is_dir() or not POLA_TANGGAL_SESI.match(folder_tanggal.name):
            continue
        for item in folder_tanggal.iterdir():
            if not item.is_dir() or not item.name.isdigit():
                continue
            kunci = (folder_tanggal.name, int(item.name))
            if terbaik is None or kunci > terbaik[0]:
                terbaik = (kunci, item)
    if terbaik is None:
        raise CetakError(f"Tidak ada folder sesi (YYYY-MM-DD/N) di {folder_label}")
    return terbaik[1]


def daftar_label(folder_sesi: Path, jenis: str, saring_nama: bool = True) -> list[Path]:
    """PDF label jenis `jenis` (salah satu key JENIS_LABEL) di subfolder-subfolder
    terkait folder_sesi (lihat JENIS_LABEL), digabung lalu diurutkan dari nomor PICK
    terkecil (urutan dibuat), BUKAN diurutkan abjad nama file apa adanya. Untuk jenis
    `spesial`, nama file juga divalidasi mengandung tag SPESIAL (POLA_SPESIAL) - untuk
    jenis lain, SEMUA *.pdf di subfolder ikut (POLA_PICK hanya mengekstrak nomor PICK,
    lihat catatan di atas POLA_PICK), kecuali jenis di FILTER_NAMA (subfolder dipakai
    bersama) yang disaring lagi lewat nama file. `saring_nama=False` melewati saringan itu -
    dipakai cek nomor terlompat, karena nomor PICK jenis lain di subfolder yang sama (mis.
    Lazada) bukan nomor yang hilang. Kosong (bukan error) kalau belum ada subfolder
    sama sekali."""
    pola = POLA_SPESIAL if jenis.startswith("spesial") else POLA_PICK
    filter_nama = FILTER_NAMA.get(jenis) if saring_nama else None
    berlabel = []
    for nama_folder in JENIS_LABEL[jenis]:
        folder = folder_sesi / nama_folder
        if not folder.is_dir():
            continue
        for f in folder.iterdir():
            if f.is_file() and (filter_nama is None or filter_nama.match(f.name)):
                cocok = pola.match(f.name)
                if cocok:
                    berlabel.append((int(cocok.group(1)), f))
    berlabel.sort(key=lambda x: x[0])
    return [f for _, f in berlabel]


def baca_sudah_dicetak(file_catatan: Path | None = None) -> set[str]:
    """Path (string absolut, hasil resolve()) label yang sudah tercatat berhasil dicetak."""
    file_catatan = file_catatan or FILE_SUDAH_DICETAK
    if not file_catatan.is_file():
        return set()
    return {b.strip() for b in file_catatan.read_text(encoding="utf-8").splitlines() if b.strip()}


def catat_sudah_dicetak(file: Path, file_catatan: Path | None = None) -> None:
    file_catatan = file_catatan or FILE_SUDAH_DICETAK
    file_catatan.parent.mkdir(exist_ok=True)
    with open(file_catatan, "a", encoding="utf-8") as f:
        f.write(str(file.resolve()) + "\n")


def saring_belum_dicetak(file_pdf: list[Path],
                         sudah: set[str]) -> tuple[list[Path], list[Path]]:
    """Pisahkan `file_pdf` (urutan dipertahankan) jadi (belum dicetak, sudah dicetak)."""
    belum, lewat = [], []
    for f in file_pdf:
        (lewat if str(f.resolve()) in sudah else belum).append(f)
    return belum, lewat


def nomor_pick_sesi(folder_sesi: Path) -> set[int]:
    """SEMUA nomor PICK yang ada di folder sesi (root & semua subfolder, jenis apa pun).
    Dipakai cari_nomor_terlompat(): nomor yang tidak ada di daftar satu jenis tapi ada di
    jenis/kurir lain di sesi yang sama BUKAN nomor hilang (nomor PICK dipakai bersama J&T,
    SPX, spesial, reguler, dst)."""
    nomor = set()
    for f in folder_sesi.rglob("*.pdf"):
        cocok = POLA_PICK.match(f.name)
        if cocok:
            nomor.add(int(cocok.group(1)))
    return nomor


def cari_nomor_terlompat(file_pdf: list[Path], jenis: str,
                         nomor_ada: set[int] | None = None) -> list[int]:
    """Cari nomor PICK yang terlompat (hilang) di antara nomor PICK terkecil dan
    terbesar pada `file_pdf` (hasil daftar_label(), sudah urut naik) - tanda
    kemungkinan ada label yang tidak ikut tercetak/tersalin ke folder ini. `jenis`
    menentukan pola ekstraksi nomor PICK (sama seperti daftar_label()). `nomor_ada`: nomor
    PICK yang ada di tempat lain di sesi yang sama (lihat nomor_pick_sesi()) - tidak dihitung
    hilang. Return list
    nomor yang hilang, urut naik (kosong kalau berurut sempurna atau <2 file)."""
    pola = POLA_SPESIAL if jenis.startswith("spesial") else POLA_PICK
    nomor = []
    for f in file_pdf:
        cocok = pola.match(f.name)
        if cocok:
            nomor.append(int(cocok.group(1)))
    if len(nomor) < 2:
        return []
    lengkap = set(range(nomor[0], nomor[-1] + 1))
    return sorted(lengkap - set(nomor) - (nomor_ada or set()))


# ============================================================== 2. SumatraPDF & printer
def cari_sumatra() -> Path:
    manual = os.environ.get("SUMATRA_PDF_PATH")
    if manual:
        p = Path(manual)
        if p.is_file():
            return p
        raise CetakError(f"SUMATRA_PDF_PATH diset tapi file tidak ditemukan: {manual}")
    ditemukan = shutil.which("SumatraPDF.exe") or shutil.which("SumatraPDF")
    if ditemukan:
        return Path(ditemukan)
    for lokasi in LOKASI_SUMATRA_UMUM:
        p = Path(os.path.expandvars(lokasi))
        if p.is_file():
            return p
    raise CetakError(
        "SumatraPDF.exe tidak ditemukan. Install dari https://www.sumatrapdfreader.org/ "
        "atau set environment variable SUMATRA_PDF_PATH ke lokasi SumatraPDF.exe.")


def _ps(perintah: str, timeout: float = TIMEOUT_POWERSHELL_S) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", perintah],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


def _esc_ps(s: str) -> str:
    return s.replace("'", "''")


def daftar_printer() -> list[str]:
    """Daftar nama printer yang terhubung ke komputer ini (lewat PowerShell Get-Printer)."""
    out = _ps("Get-Printer | Select-Object -ExpandProperty Name")
    nama = [baris.strip() for baris in out.splitlines() if baris.strip()]
    if not nama:
        raise CetakError("Tidak ada printer terhubung ke komputer ini (Get-Printer kosong).")
    return nama


def pilih_printer(daftar: list[str]) -> str:
    print()
    print("Printer yang terhubung:")
    for i, nama in enumerate(daftar, 1):
        print(f"  {i}. {nama}")
    while True:
        pilih = input(f"Pilih printer (1-{len(daftar)}): ").strip()
        if pilih.isdigit() and 1 <= int(pilih) <= len(daftar):
            return daftar[int(pilih) - 1]
        print("Pilihan tidak valid, coba lagi.")


def dukungan_pemantauan_job() -> bool:
    """Cek sekali di awal apakah cmdlet Get-PrintJob (modul PrintManagement) tersedia di
    komputer ini - dipakai untuk deteksi kertas habis/printer bermasalah. Kalau tidak ada,
    program tetap jalan TANPA pemantauan (lihat catatan keterbatasan di docstring atas)."""
    out = _ps("if (Get-Command Get-PrintJob -ErrorAction SilentlyContinue) { 'ADA' } else { 'TIDAK' }")
    return "ADA" in out


# ============================================================== 3. cetak + pantau antrian
def _job_ids(printer: str) -> set[str]:
    out = _ps(f"Get-PrintJob -PrinterName '{_esc_ps(printer)}' -ErrorAction SilentlyContinue "
             "| Select-Object -ExpandProperty Id")
    return {baris.strip() for baris in out.splitlines() if baris.strip()}


def _job_status(printer: str, job_id: str) -> str | None:
    out = _ps(f"(Get-PrintJob -PrinterName '{_esc_ps(printer)}' -ID {job_id} "
             "-ErrorAction SilentlyContinue).JobStatus")
    out = out.strip()
    return out or None


def _tunggu_job_bersih(printer: str, job_id: str, nama_file: str) -> bool:
    """Pantau 1 print job sampai selesai/hilang dari antrian. True = lanjut normal
    (selesai atau tidak ada masalah), False = user pilih "lewati" file ini karena
    printer tetap bermasalah (dicatat sebagai gagal oleh pemanggil)."""
    pernah_bermasalah = False
    while True:
        status = _job_status(printer, job_id)
        if status is None:
            return True   # job sudah tidak ada di antrian -> selesai dicetak
        if any(k in status for k in STATUS_JOB_SELESAI):
            return True
        if not any(k in status for k in STATUS_JOB_BERMASALAH):
            time.sleep(1)
            continue
        if not pernah_bermasalah:
            log.warning('Printer "%s" bermasalah saat mencetak %s (status job: %s)',
                       printer, nama_file, status)
            pernah_bermasalah = True
        print()
        print(f'!!! PRINTER BERMASALAH ({status}) saat mencetak: {nama_file}')
        print("    Perbaiki printer (isi kertas / buka yang macet, dst), lalu tekan ENTER untuk melanjutkan")
        print('    (ketik "lewati" lalu ENTER untuk melewati file ini saja dan lanjut ke berikutnya)')
        aksi = input("> ").strip().lower()
        if aksi == "lewati":
            log.warning('File %s DILEWATI manual oleh user (status job terakhir: %s)', nama_file, status)
            return False


def cetak(sumatra: Path, printer: str, file: Path, pantau: bool) -> bool:
    """Kirim 1 file ke printer lewat SumatraPDF. True = berhasil, False = dilewati
    manual oleh user karena printer bermasalah berkelanjutan (lihat _tunggu_job_bersih).
    Melempar CetakError kalau SumatraPDF sendiri gagal (mis. file rusak/printer tidak
    valid) - beda dengan "bermasalah di tengah jalan" yang ditangani _tunggu_job_bersih."""
    sebelum = _job_ids(printer) if pantau else set()
    r = subprocess.run(
        [str(sumatra), "-print-to", printer, "-silent", "-exit-when-done", str(file)],
        capture_output=True, text=True, timeout=TIMEOUT_SUMATRA_S)
    if r.returncode != 0:
        raise CetakError(f"SumatraPDF gagal (kode {r.returncode}): "
                         f"{r.stderr.strip() or r.stdout.strip()}")
    if not pantau:
        return True
    baru = _job_ids(printer) - sebelum
    if not baru:
        return True   # keburu selesai sebelum sempat dicek -> anggap sukses
    return _tunggu_job_bersih(printer, next(iter(baru)), file.name)


def cetak_semua(sumatra: Path, printer: str, file_pdf: list[Path],
                pantau: bool) -> tuple[list[Path], list[Path]]:
    """Cetak `file_pdf` berurut. Setiap hasil (berhasil/gagal) dicatat jelas ke log.
    Return (berhasil, gagal) - urutan tetap dipertahankan."""
    berhasil, gagal = [], []
    for i, f in enumerate(file_pdf, 1):
        print(f"[{i}/{len(file_pdf)}] Mencetak {f.name} ...")
        mulai = time.monotonic()
        try:
            ok = cetak(sumatra, printer, f, pantau)
        except CetakError as e:
            log.error("GAGAL cetak %s: %s", f.name, e)
            gagal.append(f)
            continue
        durasi = time.monotonic() - mulai
        if ok:
            log.info("OK cetak %s (%.1f detik)", f.name, durasi)
            catat_sudah_dicetak(f)
            berhasil.append(f)
        else:
            log.warning("DILEWATI %s (printer bermasalah, dipilih lewati oleh user)", f.name)
            gagal.append(f)
        time.sleep(JEDA_ANTAR_CETAK_S)
    return berhasil, gagal


# ============================================================== 4. daftar gagal (resume)
def simpan_daftar_gagal(gagal: list[Path]) -> Path:
    FOLDER_LOG.mkdir(exist_ok=True)
    tujuan = FOLDER_LOG / f"gagal_cetak_{datetime.now():%Y-%m-%d_%H%M%S}.txt"
    tujuan.write_text("\n".join(str(f.resolve()) for f in gagal) + "\n", encoding="utf-8")
    return tujuan


def baca_daftar_ulang(file_daftar: Path) -> list[Path]:
    if not file_daftar.is_file():
        raise CetakError(f"File daftar tidak ditemukan: {file_daftar}")
    hasil = []
    for baris in file_daftar.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris:
            continue
        p = Path(baris)
        if not p.is_file():
            log.warning("Dilewati dari daftar ulang (file tidak ada lagi): %s", p)
            continue
        hasil.append(p)
    if not hasil:
        raise CetakError(f"Tidak ada file valid di daftar: {file_daftar}")
    return hasil


# ============================================================== main
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cetak bulk label dari folder sesi label-pengiriman terbaru "
                    "(SPESIAL/GTL-SICEPAT/SATUAN/KOMBINASI)")
    ap.add_argument("--jenis", required=True, choices=sorted(JENIS_LABEL),
                    help="Jenis label yang dicetak bulk")
    ap.add_argument("--folder", type=Path,
                    help="Folder sesi label-pengiriman tertentu (default: paling baru)")
    ap.add_argument("--tanpa-konfirmasi", action="store_true",
                    help="Tanpa tanya Y/N sebelum mulai cetak (tetap tanya pilih printer; "
                         "tetap tanya juga kalau ada nomor PICK terlompat, lihat "
                         "cari_nomor_terlompat())")
    ap.add_argument("--cetak-ulang-semua", action="store_true",
                    help="Cetak juga label yang sudah tercatat tercetak (logs/sudah_dicetak.txt)")
    ap.add_argument("--ulang", type=Path,
                    help="Cetak ULANG hanya file dari daftar gagal sebelumnya "
                         "(logs/gagal_cetak_*.txt), lewati pencarian folder sesi")
    args = ap.parse_args()

    siapkan_log()
    try:
        if args.ulang:
            file_pdf = baca_daftar_ulang(args.ulang)
            log.info("Cetak ULANG %d file dari daftar %s", len(file_pdf), args.ulang)
        else:
            folder = args.folder or folder_sesi_terbaru()
            log.info("Folder sesi: %s", folder)
            file_pdf = daftar_label(folder, args.jenis)
            if not file_pdf:
                log.info("Tidak ada label %s di folder ini.", args.jenis.upper())
                return 0
            if not args.cetak_ulang_semua:
                file_pdf, sudah_tercetak = saring_belum_dicetak(file_pdf, baca_sudah_dicetak())
                if sudah_tercetak:
                    log.info("%d label %s dilewati karena sudah tercetak (pakai "
                             "--cetak-ulang-semua untuk mencetak ulang).",
                             len(sudah_tercetak), args.jenis.upper())
                if not file_pdf:
                    log.info("Semua label %s di folder ini sudah tercetak.", args.jenis.upper())
                    return 0
            log.info("Ditemukan %d label %s (urut cetak):", len(file_pdf), args.jenis.upper())
            for f in file_pdf:
                log.info("  %s", f.name)

            terlompat = cari_nomor_terlompat(
                daftar_label(folder, args.jenis, saring_nama=False), args.jenis,
                nomor_pick_sesi(folder))
            if terlompat:
                log.warning("Nomor PICK TERLOMPAT di folder sesi ini (%d nomor): %s",
                           len(terlompat), ", ".join(str(n) for n in terlompat))
                print()
                print(f"!!! PERINGATAN: ada {len(terlompat)} nomor PICK yang terlompat/hilang "
                     "di antara label folder sesi ini "
                     "(nomor yang ada di jenis/kurir lain sudah tidak dihitung):")
                print("    " + ", ".join(str(n) for n in terlompat))
                print("    Kemungkinan ada label yang belum masuk folder ini (mis. masih dibuat, "
                     "gagal, atau beda folder sesi) - cek dulu sebelum lanjut.")
                lanjut = input("Tetap lanjut cetak yang ADA sekarang? (Y/N): ").strip().lower()
                if lanjut != "y":
                    log.info("Dibatalkan oleh user (nomor PICK terlompat).")
                    return 0

        sumatra = cari_sumatra()
        printer = pilih_printer(daftar_printer())
        log.info("Printer dipilih: %s", printer)

        pantau = dukungan_pemantauan_job()
        if not pantau:
            log.warning("Get-PrintJob tidak tersedia di komputer ini - deteksi otomatis "
                       "kertas habis/printer bermasalah DIMATIKAN untuk sesi ini.")

        if not args.tanpa_konfirmasi:
            yakin = input(f'Cetak {len(file_pdf)} label ke "{printer}"? (Y/N): ').strip().lower()
            if yakin != "y":
                log.info("Dibatalkan oleh user.")
                return 0

        berhasil, gagal = cetak_semua(sumatra, printer, file_pdf, pantau)
        log.info("Selesai: %d berhasil, %d gagal dari %d total.",
                 len(berhasil), len(gagal), len(file_pdf))

        if not gagal:
            print(f"\nSelesai, {len(berhasil)} label berhasil dicetak.")
            return 0

        file_daftar_gagal = simpan_daftar_gagal(gagal)
        print(f"\n=== {len(gagal)} FILE GAGAL/DILEWATI SAAT CETAK ===")
        for f in gagal:
            print(f"  {f.name}")
        print(f"Daftar disimpan di: {file_daftar_gagal}")
        print("Rekomendasi: cetak ULANG hanya file yang gagal ini lewat:")
        print(f'  cetak-label-spesial.bat --ulang "{file_daftar_gagal}"')

        if args.tanpa_konfirmasi:
            return 1
        ulang_sekarang = input("Cetak ulang SEKARANG juga? (Y/N): ").strip().lower()
        if ulang_sekarang != "y":
            return 1

        sisa = gagal
        while sisa:
            log.info("Mencoba ulang %d file yang gagal ...", len(sisa))
            berhasil_ulang, sisa = cetak_semua(sumatra, printer, sisa, pantau)
            if not sisa:
                break
            file_daftar_gagal = simpan_daftar_gagal(sisa)
            print(f"\nMasih ada {len(sisa)} gagal, daftar disimpan di: {file_daftar_gagal}")
            lagi = input("Coba ulang lagi sekarang? (Y/N): ").strip().lower()
            if lagi != "y":
                print("Rekomendasi: jalankan ulang berikut setelah masalah diperbaiki:")
                print(f'  cetak-label-spesial.bat --ulang "{file_daftar_gagal}"')
                return 1
        log.info("Semua file berhasil dicetak setelah diulang.")
        print("\nSemua file berhasil dicetak setelah diulang.")
        return 0
    except CetakError as e:
        log.error("ERROR: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
