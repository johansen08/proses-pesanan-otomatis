"""Cetak bulk label pengiriman SPESIAL dari folder sesi label-pengiriman TERBARU.

Program ini TIDAK membuat label baru - cuma mencari file PDF yang SUDAH ada di folder
sesi label-pengiriman/YYYY-MM-DD/N (dibuat proses_label.py alur SKU spesial, lihat
TAG_SPESIAL di situ), menyaring yang namanya mengandung penanda `_SPESIAL_`
(mis. PICK-000155621_SPESIAL_TRC1_2026-10-01_080302.pdf), lalu mencetaknya BERURUT
(diurutkan dari nomor PICK terkecil - urutan dibuat, bukan abjad nama file) ke printer
pilihan lewat SumatraPDF (-print-to, -silent).

Sebelum mencetak (alur folder sesi, bukan `--ulang`), nomor PICK label yang ditemukan dicek
berurut atau tidak (lihat cari_nomor_terlompat()) - kalau ada nomor yang hilang di tengah
(mis. ada PICK 621, 622, lalu lompat ke 700), program BERHENTI dan tanya konfirmasi dulu
sebelum lanjut cetak, supaya user bisa cek dulu apakah ada label yang belum masuk folder ini
(masih dibuat, gagal, atau ketinggalan di folder sesi lain) - pertanyaan ini tetap muncul
meski pakai --tanpa-konfirmasi.

Pemakaian:
    .venv\\Scripts\\python.exe src\\print_spesial.py
        # cari folder sesi terbaru, tampilkan daftar printer, pilih, konfirmasi, cetak
    .venv\\Scripts\\python.exe src\\print_spesial.py --folder label-pengiriman/2026-10-01/3
        # pakai folder sesi tertentu, bukan yang terbaru
    .venv\\Scripts\\python.exe src\\print_spesial.py --tanpa-konfirmasi
        # lewati tanya Y/N sebelum mulai cetak (tetap tanya pilih printer)
    .venv\\Scripts\\python.exe src\\print_spesial.py --ulang logs\\gagal_cetak_2026-10-01_153000.txt
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

ROOT = Path(__file__).resolve().parent.parent   # root project, bukan folder src/ ini
FOLDER_LABEL = ROOT / "label-pengiriman"
FOLDER_LOG = ROOT / "logs"

POLA_TANGGAL_SESI = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Penanda SPESIAL ini dibuat proses_label.py (lihat TAG_SPESIAL) - HANYA alur SKU
# spesial yang menyisipkannya di nama file, jadi cukup cari pola ini saja.
POLA_SPESIAL = re.compile(r"^PICK-0*(\d+)_SPESIAL_.*\.pdf$", re.IGNORECASE)

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


def daftar_label_spesial(folder_sesi: Path) -> list[Path]:
    """PDF label SPESIAL di `folder_sesi`, diurutkan dari nomor PICK terkecil (urutan
    dibuat), BUKAN diurutkan abjad nama file apa adanya."""
    berlabel = []
    for f in folder_sesi.iterdir():
        if f.is_file():
            cocok = POLA_SPESIAL.match(f.name)
            if cocok:
                berlabel.append((int(cocok.group(1)), f))
    berlabel.sort(key=lambda x: x[0])
    return [f for _, f in berlabel]


def cari_nomor_terlompat(file_pdf: list[Path]) -> list[int]:
    """Cari nomor PICK yang terlompat (hilang) di antara nomor PICK terkecil dan
    terbesar pada `file_pdf` (hasil daftar_label_spesial, sudah urut naik) - tanda
    kemungkinan ada label yang tidak ikut tercetak/tersalin ke folder ini. Return
    list nomor yang hilang, urut naik (kosong kalau berurut sempurna atau <2 file)."""
    nomor = []
    for f in file_pdf:
        cocok = POLA_SPESIAL.match(f.name)
        if cocok:
            nomor.append(int(cocok.group(1)))
    if len(nomor) < 2:
        return []
    lengkap = set(range(nomor[0], nomor[-1] + 1))
    return sorted(lengkap - set(nomor))


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
        description="Cetak bulk label SPESIAL dari folder sesi label-pengiriman terbaru")
    ap.add_argument("--folder", type=Path,
                    help="Folder sesi label-pengiriman tertentu (default: paling baru)")
    ap.add_argument("--tanpa-konfirmasi", action="store_true",
                    help="Tanpa tanya Y/N sebelum mulai cetak (tetap tanya pilih printer; "
                         "tetap tanya juga kalau ada nomor PICK terlompat, lihat "
                         "cari_nomor_terlompat())")
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
            file_pdf = daftar_label_spesial(folder)
            if not file_pdf:
                log.info("Tidak ada label SPESIAL di folder ini.")
                return 0
            log.info("Ditemukan %d label SPESIAL (urut cetak):", len(file_pdf))
            for f in file_pdf:
                log.info("  %s", f.name)

            terlompat = cari_nomor_terlompat(file_pdf)
            if terlompat:
                log.warning("Nomor PICK TERLOMPAT di folder sesi ini (%d nomor): %s",
                           len(terlompat), ", ".join(str(n) for n in terlompat))
                print()
                print(f"!!! PERINGATAN: ada {len(terlompat)} nomor PICK yang terlompat/hilang "
                     "di antara label SPESIAL folder ini:")
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
