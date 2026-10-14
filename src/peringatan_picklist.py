"""Deteksi nomor picklist yang terlompat (picklist batal/gagal dibuat di Jubelio).

Nomor picklist Jubelio berurutan. Kalau pembuatan picklist ditolak/error di sisi Jubelio
(mis. "Internal Server Error"), nomornya bisa sudah terpakai tapi picklist-nya tidak ada,
sehingga picklist berikutnya melompat (mis. PICK-000155661 lalu PICK-000155663; 155662 tidak
ada di Jubelio). Modul ini mengingat nomor picklist terakhir yang dibuat program (lintas
proses python, disimpan di file) dan mencatat peringatan kalau ada nomor yang terlompat,
supaya di akhir proses tim resi tahu dan bisa menginformasikannya.

Catatan: nomor terlompat juga bisa karena ada orang lain membuat picklist langsung di
Jubelio di sela-sela program berjalan - pesannya sengaja menyebut kemungkinan ini.

Folder log diatur main.py lewat atur_folder(); tanpa itu (mis. di test) peringatan hanya
disimpan di memori proses ini.
"""
from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jurnal_peringatan

MAKS_NOMOR_DITAMPILKAN = 20
# Verifikasi nomor terlompat ke Jubelio (GET sales/picklists/{id}, ~0,19 dtk/permintaan): paralel
# dan dibatasi waktu supaya gap ribuan nomor (PC lain bekerja semalam) tidak menahan proses.
PEKERJA_CEK = 10
BATAS_WAKTU_CEK_S = 30

log = logging.getLogger("sku-spesial")

_file_terakhir: Path | None = None
_file_peringatan: Path | None = None
_sesi: list[str] = []      # peringatan yang muncul di proses python ini
_hilang_terakhir: list[int] = []   # nomor terlompat dari periksa_nomor() PALING TERAKHIR
_sudah_ada_picklist = False        # sudah ada picklist yang dibuat di proses python ini?


def atur_folder(folder_log: Path) -> None:
    global _file_terakhir, _file_peringatan, _sudah_ada_picklist
    _sudah_ada_picklist = False
    _file_terakhir = folder_log / "picklist_terakhir.txt"
    _file_peringatan = folder_log / "picklist_terlompat.jsonl"


def _angka(picklist_no: str) -> int | None:
    m = re.fullmatch(r"PICK-0*(\d+)", str(picklist_no).strip().upper())
    return int(m.group(1)) if m else None


def _baca_terakhir() -> int | None:
    try:
        return int(_file_terakhir.read_text().strip()) if _file_terakhir else None
    except (OSError, ValueError):
        return None


def catat(pesan: str) -> None:
    log.warning("  %s", pesan)
    _sesi.append(pesan)
    jurnal_peringatan.catat_pesan(_file_peringatan, pesan)


def cek_ada_di_jubelio(ada_picklist, nomor: list[int], batas_detik: float = BATAS_WAKTU_CEK_S,
                       pekerja: int = PEKERJA_CEK) -> dict[int, bool | None]:
    """Cek ke Jubelio nomor mana yang SUNGGUH ada. `ada_picklist(id) -> bool` (False = 404).
    Hasil: True ada (dibuat PC/orang lain), False tidak ada (batal/gagal), None tidak diketahui
    (error API atau batas waktu habis). Nomor diperiksa urut naik; sisa setelah batas waktu = None."""
    mulai = time.monotonic()

    def satu(n: int) -> bool | None:
        if time.monotonic() - mulai > batas_detik:
            return None
        try:
            return bool(ada_picklist(n))
        except Exception as e:  # noqa: BLE001 - gagal cek tidak boleh menghentikan proses
            log.debug("Cek picklist %d ke Jubelio gagal: %s", n, e)
            return None

    with ThreadPoolExecutor(max_workers=max(1, min(pekerja, len(nomor) or 1))) as ex:
        return dict(zip(nomor, ex.map(satu, nomor)))


def _ringkas(nomor: list[int]) -> str:
    daftar = ", ".join(f"PICK-{i:09d}" for i in nomor[:MAKS_NOMOR_DITAMPILKAN])
    if len(nomor) > MAKS_NOMOR_DITAMPILKAN:
        daftar += f", ... (+{len(nomor) - MAKS_NOMOR_DITAMPILKAN} lagi)"
    return daftar


def periksa_nomor(picklist_no: str, ada_picklist=None) -> str | None:
    """Panggil tiap kali picklist baru berhasil dibuat. Mengembalikan pesan peringatan
    kalau ada nomor yang terlompat sejak picklist terakhir yang dicatat, selain itu None.
    Nomor yang terlompat (kalau ada) juga disimpan utk ambil_nomor_hilang().
    `ada_picklist(id) -> bool` (opsional): nomor di gap dicek ke Jubelio - yang ternyata ADA
    (dibuat PC lain semalam, dst) bukan lagi peringatan; hanya yang tidak ada / belum bisa
    dipastikan yang dilaporkan."""
    global _hilang_terakhir, _sudah_ada_picklist
    n = _angka(picklist_no)
    if n is None:
        return None
    terakhir = _baca_terakhir()
    pesan = None
    _hilang_terakhir = []
    if terakhir is not None and n > terakhir + 1:
        hilang_nomor = list(range(terakhir + 1, n))
        ada_di_jubelio = 0
        belum_pasti: list[int] = []
        if ada_picklist is not None:
            status = cek_ada_di_jubelio(ada_picklist, hilang_nomor)
            ada_di_jubelio = sum(1 for v in status.values() if v)
            belum_pasti = [i for i, v in status.items() if v is None]
            hilang_nomor = [i for i, v in status.items() if not v]
            if ada_di_jubelio:
                log.info("  Gap PICK-%09d..PICK-%09d: %d nomor ada di Jubelio (dibuat di luar "
                         "proses ini, bukan masalah)", terakhir + 1, n - 1, ada_di_jubelio)
        # Gap sebelum picklist PERTAMA proses ini hanya diperingatkan, tidak masuk
        # ambil_nomor_hilang() (=> tidak ditulis "PICKLIST CANCEL" di PICKLIST.xlsx): terjadi
        # sebelum program jalan, bisa jadi dibuat orang lain di PC lain.
        if _sudah_ada_picklist:
            _hilang_terakhir = hilang_nomor
        if hilang_nomor:
            if ada_picklist is None:
                sebab = ("Kemungkinan picklist batal/gagal dibuat karena Jubelio error (atau dibuat "
                         "orang lain di Jubelio)")
                awal = "Tidak ada di program"
            else:
                sebab = ("Sudah dicek ke Jubelio: nomor ini tidak ditemukan di sana "
                         f"({ada_di_jubelio} nomor lain di gap yang sama ada = dibuat PC lain)")
                if belum_pasti:
                    sebab += f"; {len(belum_pasti)} di antaranya belum bisa dipastikan (batas waktu/error API)"
                awal = "Tidak ada di Jubelio"
            pesan = (f"Nomor picklist terlompat: setelah PICK-{terakhir:09d} langsung "
                     f"PICK-{n:09d}. {awal}: {_ringkas(hilang_nomor)}. {sebab} - cek nomor tsb "
                     f"di Jubelio dan informasikan ke tim resi.")
            catat(pesan)
    _sudah_ada_picklist = True
    if _file_terakhir and (terakhir is None or n > terakhir):
        try:
            _file_terakhir.write_text(str(n))
        except OSError:
            pass
    return pesan


def ambil_nomor_hilang() -> list[int]:
    """Nomor picklist yang terlompat dari periksa_nomor() PALING TERAKHIR (kosong kalau tidak
    ada gap, atau gap itu terjadi SEBELUM picklist pertama proses ini) - dipakai
    rekap_master_excel.catat() utk menandai baris kuning "PICKLIST CANCEL" di PICKLIST.xlsx
    sesi, meniru pola manual yang sudah ada di file master (row 29, 05-10-2026).
    Panggil SEGERA setelah periksa_nomor() dipanggil utk picklist yang baru dibuat - sebelum
    periksa_nomor() dipanggil lagi untuk picklist berikutnya (nilainya ditimpa tiap panggilan)."""
    return _hilang_terakhir


def baca_sejak(epoch: float) -> list[str]:
    """Peringatan yang tercatat sejak `epoch` (dari file, lintas proses python)."""
    return jurnal_peringatan.baca_sejak(_file_peringatan, epoch)


def cetak(peringatan: list[str], judul: str = "PERHATIAN: PICKLIST TERLOMPAT / BATAL") -> None:
    """Cetak blok peringatan yang mencolok (dipanggil paling akhir)."""
    jurnal_peringatan.cetak(peringatan, judul)


def cetak_sesi() -> None:
    cetak(_sesi)
