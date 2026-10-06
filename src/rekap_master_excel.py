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

Workbook dibuka SEKALI per proses python lewat catat() (bukan tiap picklist seperti
proses_label.catat_riwayat()) karena ukurannya puluhan MB - lihat tutup(), WAJIB dipanggil di
akhir proses (main.py, lewat finally) supaya baris yang baru ditulis di memori benar-benar
tersimpan ke disk.
"""
from __future__ import annotations

import logging
import re
import shutil
import time
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger("sku-spesial")

NAMA_MASTER = "PICK LIST - EXCEL 2022 - 2024 - MASTER - TERBARU NEW.xlsx"
NAMA_SALINAN = "PICKLIST.xlsx"
SHEET = "HARI INI"
OPERATOR = "PUTRI"
BARIS_DATA_AWAL = 6
KOLOM_F_OPR, KOLOM_G_TGL, KOLOM_H_JAM = 6, 7, 8
KOLOM_L_PICKLIST, KOLOM_M_LOLOS, KOLOM_N_PRINT = 12, 13, 14
KOLOM_T_JENIS, KOLOM_U_CATATAN = 20, 21
KOLOM_FILL_AWAL, KOLOM_FILL_AKHIR = 2, 21      # B..U - lihat baris kuning "PICKLIST CANCEL"
WARNA_KUNING = "FFFFFF00"      # ARGB (alpha FF) - samakan dgn baris kuning manual di master
TEKS_TERLOMPAT = "PICKLIST CANCEL"

_root: Path | None = None
_wb = None
_ws = None
_baris_cari_mulai = BARIS_DATA_AWAL   # cache per proses - hindari scan ulang dari atas tiap catat()


def atur_root(root: Path) -> None:
    """Dipanggil sekali oleh main.py dengan ROOT project (tempat master & salinan berada)."""
    global _root, _wb, _ws, _baris_cari_mulai
    _root = root
    _wb = _ws = None
    _baris_cari_mulai = BARIS_DATA_AWAL


def _file_master() -> Path:
    return _root / NAMA_MASTER


def _file_salinan() -> Path:
    return _root / NAMA_SALINAN


def _buka() -> None:
    global _wb, _ws
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


def catat(baris_riwayat: dict, nomor_terlompat: list[int] | None = None) -> None:
    """Panggil di titik yang sama dengan proses_label.catat_riwayat() - 1 baris
    riwayat_picklist.xlsx = 1 baris PICKLIST.xlsx. `nomor_terlompat`: hasil
    peringatan_picklist.ambil_nomor_hilang() diambil SEGERA setelah picklist ini dibuat
    (sebelum picklist berikutnya dibuat) - tiap nomor dapat baris kuning tersendiri sebelum
    baris picklist ini."""
    if "No Picklist" not in baris_riwayat:
        return
    n = _angka_picklist(baris_riwayat["No Picklist"])
    if n is None:
        return
    try:
        _buka()
        if _ws is None:
            return
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
    except Exception as e:     # noqa: BLE001 - jangan sampai proses picklist utama gagal
        log.warning("  Gagal tulis %s untuk %s: %s", NAMA_SALINAN,
                   baris_riwayat.get("No Picklist"), e)


def tutup() -> None:
    """Simpan PICKLIST.xlsx ke disk SEKALI di akhir proses (dipanggil main.py lewat finally) -
    workbook dibuka & diubah di memori sepanjang proses (lihat catat()), bukan disimpan tiap
    baris, karena ukuran filenya besar. Kalau sedang dibuka di Excel (PermissionError),
    dicoba ulang singkat, lalu simpan ke file cadangan supaya baris yang sudah ditulis di
    memori proses ini tidak hilang - peringatan_gagal.catat() supaya muncul di rekap akhir."""
    global _wb, _ws
    if _wb is None:
        return
    import peringatan_gagal

    tujuan = _file_salinan()
    wb = _wb
    try:
        for coba in range(3):
            try:
                wb.save(tujuan)
                return
            except PermissionError:
                if coba < 2:
                    time.sleep(2)
        cadangan = tujuan.with_name(f"PICKLIST_tertunda_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        try:
            wb.save(cadangan)
            peringatan_gagal.catat(
                f"{tujuan.name} sedang dibuka (tutup dulu di Excel) - baris baru disimpan "
                f"sementara ke {cadangan.name}, gabungkan manual ke {tujuan.name}")
        except Exception as e:     # noqa: BLE001
            peringatan_gagal.catat(f"Gagal simpan {tujuan.name} maupun cadangannya: {e}")
    finally:
        _wb = _ws = None
