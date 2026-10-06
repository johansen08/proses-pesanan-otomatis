"""Catat tiap picklist ke PICKLIST.xlsx - SALINAN kerja program dari file master "PICK LIST -
EXCEL 2022 - 2024 - MASTER - TERBARU NEW.xlsx" yang tetap dijalankan MANUAL oleh tim (lihat
CLAUDE.md). Program TIDAK PERNAH menulis ke file master langsung - tim verifikasi dulu isi
PICKLIST.xlsx, baru copy manual ke master kalau sudah sesuai. Kalau PICKLIST.xlsx belum ada
(baru, atau sudah dihapus tim setelah selesai verifikasi), dibuat dari master supaya ikut
format, formula (kolom B/E/Q/W di sheet "HARI INI" - JANGAN disentuh), dan baris yang sudah
di-pre-fill OPR/TANGGAL ke depan.

Kolom yang diisi (lihat verifikasi struktur file master, 06-10-2026): F=operator (konstan
"PUTRI"), G=tanggal, H=jam (desimal gaya "HH.MM", mis. 18.53 = jam 18:53, BUKAN pecahan jam
sungguhan), L=nomor picklist (angka saja, font biru tebal sudah bawaan template), M=Total
Pesanan, N=Resi Keluar, T=label alur (sama seperti kolom "SKU" di riwayat_picklist.xlsx, apa
adanya - lihat proses_label.KOLOM_RIWAYAT), U=daftar no pesanan yang belum dapat resi (dari
field "Tanpa Resi", lihat lanjutkan_picklist()).

Picklist yang terlompat/batal (lihat peringatan_picklist.ambil_nomor_hilang()) ditulis sebagai
baris tersendiri SEBELUM baris picklist yang baru, T="PICKLIST CANCEL", lalu seluruh kolom
B:U (bukan A) di-fill kuning solid - meniru pola manual yang sudah ada di file master (row 29,
05-10-2026).

ANTREAN, bukan tulis langsung (insiden 2026-10-06): sheet "HARI INI" berisi ~51 ribu baris,
sehingga load_workbook() ~48 detik + save ~67 detik = ~2 menit per proses python. Dulu
workbook dibuka & disimpan di TIAP proses (= tiap langkah proses-harian.bat & tiap --lanjut),
jadi satu TIPE 2/3 menghabiskan ~15-20 menit cuma untuk Excel, dan penyimpanan 67 detik yang
terputus (proses dihentikan/2 proses menyimpan bersamaan) pernah merusak file ("File is not a
zip file"). Sekarang:
- catat() cuma menambah 1 baris JSON ke antrean logs/NAMA_ANTRIAN (instan, tanpa buka Excel);
- terapkan() - dipanggil SEKALI di akhir tiap TIPE lewat `main.py --tulis-excel --jalankan`
  (langkah "TULIS PICKLIST.XLSX" proses-harian.bat), atau manual - membuka PICKLIST.xlsx
  sekali, menulis SEMUA antrean berurutan, lalu menyimpannya ATOMIK (tulis ke file sementara
  NAMA_SEMENTARA, baru os.replace ke PICKLIST.xlsx) supaya file lama tetap utuh kalau
  penyimpanan terputus. Kalau gagal (PICKLIST.xlsx sedang dibuka di Excel, rusak, dst),
  antrean TIDAK dibuang - disimpan di logs/NAMA_TERTUNDA dan dicoba lagi di terapkan()
  berikutnya, plus dicatat lewat peringatan_gagal supaya muncul di rekap akhir TIPE.
Waktu (kolom G/H) diambil dari field "Waktu" tiap baris antrean (saat picklist diproses),
bukan saat terapkan() berjalan. terapkan() tidak dikunci antar-proses - jangan jalankan
--tulis-excel di 2 jendela bersamaan.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading
import time
from datetime import date, datetime
from pathlib import Path

import peringatan_gagal

log = logging.getLogger("sku-spesial")

NAMA_MASTER = "PICK LIST - EXCEL 2022 - 2024 - MASTER - TERBARU NEW.xlsx"
NAMA_SALINAN = "PICKLIST.xlsx"
NAMA_SEMENTARA = "PICKLIST.xlsx.menulis"         # lihat _simpan()
NAMA_ANTRIAN = "antrian_picklist_excel.jsonl"     # di logs/ - baris baru dari catat()
NAMA_TERTUNDA = "antrian_picklist_excel_tertunda.jsonl"   # sudah diambil terapkan(), belum tersimpan
NAMA_KLAIM = "antrian_picklist_excel_klaim.jsonl"         # sementara, lihat _pindahkan_ke_tertunda()
SHEET = "HARI INI"
OPERATOR = "PUTRI"
BARIS_DATA_AWAL = 6
KOLOM_F_OPR, KOLOM_G_TGL, KOLOM_H_JAM = 6, 7, 8
KOLOM_L_PICKLIST, KOLOM_M_LOLOS, KOLOM_N_PRINT = 12, 13, 14
KOLOM_T_JENIS, KOLOM_U_CATATAN = 20, 21
KOLOM_FILL_AWAL, KOLOM_FILL_AKHIR = 2, 21      # B..U - lihat baris kuning "PICKLIST CANCEL"
WARNA_KUNING = "FFFFFF00"      # ARGB (alpha FF) - samakan dgn baris kuning manual di master
TEKS_TERLOMPAT = "PICKLIST CANCEL"
# field baris riwayat yang dipakai _tulis_baris() - hanya ini yang disimpan di antrean
KOLOM_ANTRIAN = ("Waktu", "No Picklist", "Total Pesanan", "Resi Keluar", "SKU", "Tanpa Resi",
                 "Catatan")
MAKS_COBA_GANTI_FILE = 5        # os.replace gagal (PermissionError) kalau file sedang dibuka
JEDA_COBA_GANTI_FILE_S = 1

_root: Path | None = None
_wb = None
_ws = None
_baris_cari_mulai = BARIS_DATA_AWAL   # cache per workbook - hindari scan ulang dari atas tiap baris
_lock_antrian = threading.Lock()
_jumlah_dicatat = 0                   # baris yang masuk antrean dari proses ini (cetak_sesi())
_sudah_peringatan_master = False


def atur_root(root: Path) -> None:
    """Dipanggil sekali oleh main.py dengan ROOT project (tempat master & salinan berada;
    antrean di ROOT/logs). Tanpa ini (mis. di test proses_label) catat() tidak berbuat apa-apa."""
    global _root, _wb, _ws, _baris_cari_mulai, _jumlah_dicatat, _sudah_peringatan_master
    _root = root
    _wb = _ws = None
    _baris_cari_mulai = BARIS_DATA_AWAL
    _jumlah_dicatat = 0
    _sudah_peringatan_master = False


def _file_master() -> Path:
    return _root / NAMA_MASTER


def _file_salinan() -> Path:
    return _root / NAMA_SALINAN


def _file_log(nama: str) -> Path:
    return _root / "logs" / nama


# ============================================================== antrean
def catat(baris_riwayat: dict, nomor_terlompat: list[int] | None = None) -> None:
    """Panggil di titik yang sama dengan proses_label.catat_riwayat() - 1 baris
    riwayat_picklist.xlsx = 1 baris PICKLIST.xlsx. `nomor_terlompat`: hasil
    peringatan_picklist.ambil_nomor_hilang() diambil SEGERA setelah picklist ini dibuat
    (sebelum picklist berikutnya dibuat) - tiap nomor dapat baris kuning tersendiri sebelum
    baris picklist ini. Cuma masuk antrean - baru ditulis ke PICKLIST.xlsx oleh terapkan()."""
    global _jumlah_dicatat, _sudah_peringatan_master
    if "No Picklist" not in baris_riwayat or _angka_picklist(baris_riwayat["No Picklist"]) is None:
        return
    if _root is None:
        return
    try:
        if not _file_salinan().exists() and not _file_master().exists():
            if not _sudah_peringatan_master:
                log.warning("  %s tidak ditemukan - %s tidak dibuat, lewati rekap master excel",
                           NAMA_MASTER, NAMA_SALINAN)
                _sudah_peringatan_master = True
            return
        baris = {kol: baris_riwayat[kol] for kol in KOLOM_ANTRIAN
                 if baris_riwayat.get(kol) is not None}
        if not baris.get("Waktu"):
            baris["Waktu"] = datetime.now().strftime("%d-%m-%Y %H:%M")
        teks = json.dumps({"baris": baris, "nomor_terlompat": list(nomor_terlompat or [])},
                          ensure_ascii=False, default=str)
        with _lock_antrian:
            file = _file_log(NAMA_ANTRIAN)
            file.parent.mkdir(parents=True, exist_ok=True)
            with open(file, "a", encoding="utf-8") as f:
                f.write(teks + "\n")
            _jumlah_dicatat += 1
    except Exception as e:     # noqa: BLE001 - jangan sampai proses picklist utama gagal
        log.warning("  Gagal catat %s ke antrean %s: %s", baris_riwayat.get("No Picklist"),
                   NAMA_SALINAN, e)


def _baca_entri(file: Path) -> list[dict]:
    if not file.exists():
        return []
    hasil = []
    for no, teks in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        if not teks.strip():
            continue
        try:
            hasil.append(json.loads(teks))
        except ValueError:
            log.warning("  Baris %d %s rusak, dilewati: %s", no, file.name, teks[:120])
    return hasil


def jumlah_antrian() -> int:
    """Jumlah picklist yang belum tertulis ke PICKLIST.xlsx (antrean baru + yang tertunda)."""
    if _root is None:
        return 0
    return sum(len(_baca_entri(_file_log(n))) for n in (NAMA_TERTUNDA, NAMA_KLAIM, NAMA_ANTRIAN))


def cetak_sesi() -> None:
    """Dipanggil main.py di akhir tiap proses: info kalau proses ini menambah antrean."""
    if _jumlah_dicatat:
        log.info("%d picklist masuk antrean %s (total antre %d) - ditulis sekaligus di langkah "
                 "TULIS PICKLIST.XLSX akhir TIPE proses-harian.bat, atau manual: "
                 "jalankan.bat --tulis-excel --jalankan", _jumlah_dicatat, NAMA_SALINAN,
                 jumlah_antrian())


def _ganti_file(asal: Path, tujuan: Path) -> None:
    """os.replace dengan coba ulang singkat - di Windows gagal (PermissionError) selama file
    asal/tujuan sedang dibuka proses lain (catat() yang sedang menulis, Excel, dst)."""
    for coba in range(1, MAKS_COBA_GANTI_FILE + 1):
        try:
            os.replace(asal, tujuan)
            return
        except PermissionError:
            if coba == MAKS_COBA_GANTI_FILE:
                raise
            time.sleep(JEDA_COBA_GANTI_FILE_S)


def _tambahkan_ke(asal: Path, tujuan: Path) -> None:
    with open(tujuan, "a", encoding="utf-8") as f:
        f.write(asal.read_text(encoding="utf-8"))
    asal.unlink()


def _pindahkan_ke_tertunda() -> None:
    """Pindahkan antrean baru ke NAMA_TERTUNDA (urutan tetap: yang tertunda lebih dulu).
    Antrean di-os.replace dulu (atomik) supaya catat() dari proses lain yang berjalan
    bersamaan langsung menulis ke file antrean BARU, bukan ke baris yang sedang diambil."""
    antrian, tertunda, klaim = (_file_log(NAMA_ANTRIAN), _file_log(NAMA_TERTUNDA),
                                _file_log(NAMA_KLAIM))
    if klaim.exists():                  # sisa terapkan() sebelumnya yang terputus
        _tambahkan_ke(klaim, tertunda)
    if not antrian.exists():
        return
    if tertunda.exists():
        _ganti_file(antrian, klaim)
        _tambahkan_ke(klaim, tertunda)
    else:
        _ganti_file(antrian, tertunda)


def _sedang_dibuka(file: Path) -> bool:
    """Excel mengunci file yang sedang dibuka (tidak bisa dibuka untuk ditulis) - dicek
    SEBELUM load_workbook() ~48 detik yang pasti sia-sia karena penyimpanannya nanti gagal."""
    try:
        with open(file, "r+b"):
            return False
    except PermissionError:
        return True


def _tunda(jumlah: int, alasan: str) -> None:
    pesan = (f"{jumlah} picklist belum tertulis ke {NAMA_SALINAN}: {alasan}. Antrean TETAP "
             f"disimpan (logs/{NAMA_TERTUNDA}) & otomatis dicoba lagi di langkah TULIS "
             f"PICKLIST.XLSX berikutnya, atau manual: jalankan.bat --tulis-excel --jalankan")
    log.warning("  %s", pesan)
    peringatan_gagal.catat(pesan)


def terapkan() -> int:
    """Tulis SEMUA antrean ke PICKLIST.xlsx sekaligus (1x buka, 1x simpan atomik), lalu
    kosongkan antrean. Mengembalikan jumlah picklist yang ditulis (0 kalau antrean kosong
    atau gagal - kalau gagal antrean tidak dibuang, lihat _tunda())."""
    global _wb, _ws
    if _root is None:
        return 0
    try:
        _pindahkan_ke_tertunda()
    except OSError as e:
        log.warning("  Antrean %s gagal diambil (dicoba lagi lain kali): %s", NAMA_ANTRIAN, e)
    tertunda = _file_log(NAMA_TERTUNDA)
    entri = _baca_entri(tertunda)
    if not entri:
        tertunda.unlink(missing_ok=True)
        return 0
    salinan = _file_salinan()
    if salinan.exists() and _sedang_dibuka(salinan):
        _tunda(len(entri), f"{NAMA_SALINAN} sedang dibuka (tutup dulu di Excel)")
        return 0
    _buka()
    if _ws is None:
        _tunda(len(entri), f"{NAMA_SALINAN} gagal dibuka (lihat log; kalau file rusak, ganti "
                           f"nama/hapus {NAMA_SALINAN} - akan dibuat ulang dari master)")
        return 0
    try:
        for e in entri:
            _tulis_baris(e.get("baris") or {}, e.get("nomor_terlompat"))
        if not _simpan():
            _tunda(len(entri), f"{NAMA_SALINAN} gagal disimpan (sedang dibuka di Excel?)")
            return 0
    finally:
        _wb = _ws = None
    tertunda.unlink(missing_ok=True)
    log.info("  %d picklist ditulis ke %s", len(entri), NAMA_SALINAN)
    return len(entri)


# ============================================================== workbook
def _buka() -> None:
    global _wb, _ws, _baris_cari_mulai
    if _wb is not None or _root is None:
        return
    from openpyxl import load_workbook

    salinan = _file_salinan()
    if not salinan.exists():
        master = _file_master()
        if not master.exists():
            log.warning("  %s tidak ditemukan - %s tidak dibuat, lewati rekap master excel",
                       master.name, NAMA_SALINAN)
            return
        shutil.copy2(master, salinan)
        log.info("  %s dibuat dari %s", salinan.name, master.name)
    try:
        wb = load_workbook(salinan)
    except Exception as e:     # noqa: BLE001 - jangan sampai proses picklist utama gagal
        log.warning("  Gagal buka %s: %s", NAMA_SALINAN, e)
        return
    if SHEET not in wb.sheetnames:
        log.warning("  Sheet %s tidak ada di %s - lewati rekap master excel", SHEET, NAMA_SALINAN)
        return
    _wb, _ws = wb, wb[SHEET]
    _baris_cari_mulai = BARIS_DATA_AWAL


def _simpan() -> bool:
    """Simpan ke NAMA_SEMENTARA dulu, baru os.replace ke PICKLIST.xlsx: kalau penyimpanan
    (~67 detik) terputus, PICKLIST.xlsx lama tetap utuh (dulu langsung ditimpa -> pernah
    rusak "File is not a zip file", insiden 2026-10-06)."""
    tujuan = _file_salinan()
    sementara = tujuan.with_name(NAMA_SEMENTARA)
    try:
        _wb.save(sementara)
        _ganti_file(sementara, tujuan)
        return True
    except OSError as e:
        log.warning("  Gagal simpan %s: %s", NAMA_SALINAN, e)
        return False
    finally:
        sementara.unlink(missing_ok=True)


def _angka_picklist(no: str) -> int | None:
    m = re.fullmatch(r"PICK-0*(\d+)", str(no).strip().upper())
    return int(m.group(1)) if m else None


def _jam_desimal(waktu: datetime) -> float:
    return float(f"{waktu.hour}.{waktu.minute:02d}")


def _cari_baris(tanggal: date) -> int:
    """Baris pertama (mulai _baris_cari_mulai) yang tanggalnya (G) = `tanggal` dan No Picklist
    (L) masih kosong - baris hari ini biasanya sudah di-pre-fill OPR/TANGGAL ke depan oleh tim.
    Kalau tidak ketemu (salinan baru/belum ada pre-fill hari ini), pakai baris benar-benar
    kosong pertama setelah data terakhir dan isi sendiri F/G-nya."""
    global _baris_cari_mulai
    r = _baris_cari_mulai
    while True:
        g, l, f = (_ws.cell(r, KOLOM_G_TGL).value, _ws.cell(r, KOLOM_L_PICKLIST).value,
                  _ws.cell(r, KOLOM_F_OPR).value)
        if g is None and l is None and f is None:
            _ws.cell(r, KOLOM_F_OPR, OPERATOR)
            _ws.cell(r, KOLOM_G_TGL, datetime.combine(tanggal, datetime.min.time()))
            _baris_cari_mulai = r + 1
            return r
        if l is None and isinstance(g, datetime) and g.date() == tanggal:
            _baris_cari_mulai = r + 1
            return r
        r += 1


def _tandai_kuning(baris: int) -> None:
    from openpyxl.styles import PatternFill

    isian = PatternFill(fill_type="solid", fgColor=WARNA_KUNING)
    for c in range(KOLOM_FILL_AWAL, KOLOM_FILL_AKHIR + 1):
        _ws.cell(baris, c).fill = isian


def _tulis_terlompat(nomor: list[int], tanggal: date) -> None:
    for n in nomor:
        r = _cari_baris(tanggal)
        _ws.cell(r, KOLOM_L_PICKLIST, n)
        _ws.cell(r, KOLOM_T_JENIS, TEKS_TERLOMPAT)
        _tandai_kuning(r)


def _tulis_baris(baris_riwayat: dict, nomor_terlompat: list[int] | None = None) -> None:
    """Tulis 1 entri antrean (lihat catat()) ke workbook yang sedang dibuka terapkan()."""
    n = _angka_picklist(baris_riwayat.get("No Picklist", ""))
    if n is None:
        return
    try:
        waktu = (datetime.strptime(baris_riwayat["Waktu"], "%d-%m-%Y %H:%M")
                if baris_riwayat.get("Waktu") else datetime.now())
        if nomor_terlompat:
            _tulis_terlompat(nomor_terlompat, waktu.date())
        r = _cari_baris(waktu.date())
        _ws.cell(r, KOLOM_H_JAM, _jam_desimal(waktu))
        _ws.cell(r, KOLOM_L_PICKLIST, n)
        if baris_riwayat.get("Total Pesanan") is not None:
            _ws.cell(r, KOLOM_M_LOLOS, baris_riwayat["Total Pesanan"])
        if baris_riwayat.get("Resi Keluar") is not None:
            _ws.cell(r, KOLOM_N_PRINT, baris_riwayat["Resi Keluar"])
        if baris_riwayat.get("SKU") is not None:
            _ws.cell(r, KOLOM_T_JENIS, baris_riwayat["SKU"])
        tanpa_resi = baris_riwayat.get("Tanpa Resi")
        if tanpa_resi:
            _ws.cell(r, KOLOM_U_CATATAN, ", ".join(tanpa_resi))
        if str(baris_riwayat.get("Catatan", "")).startswith(("GAGAL", "TERHENTI")):
            _tandai_kuning(r)
    except Exception as e:     # noqa: BLE001 - 1 baris bermasalah jangan gagalkan baris lain
        log.warning("  Gagal tulis %s untuk %s: %s", NAMA_SALINAN,
                   baris_riwayat.get("No Picklist"), e)
