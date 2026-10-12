"""Catat picklist/proses yang TERHENTI atau GAGAL (mis. timeout unduh label PDF - lihat
main.cetak_bermasalah()) ke file lintas-proses, supaya tetap terlihat di rekap paling akhir
tiap TIPE proses-harian.bat lewat rekap_waktu.py - bukan hanya tercetak sekali di tengah log
lalu tenggelam begitu langkah berikutnya berjalan (insiden 2026-10-06: picklist urgent
bermasalah luput kebaca karena cuma scroll ke rekap paling bawah).

main.cetak_bermasalah() sendiri sudah mencetak blok peringatan ini LANGSUNG saat terjadi -
modul ini cuma menyimpan salinannya ke file (pola sama dengan peringatan_picklist.py/
peringatan_resi.py) supaya proses python lain (rekap_waktu.py, dipanggil .bat setelah semua
langkah satu TIPE selesai) bisa membacanya kembali lewat baca_sejak().

Folder log diatur main.py lewat atur_folder(); tanpa itu (mis. di test) peringatan tidak
disimpan di mana pun (hanya diteruskan ke pemanggil lewat cetak_bermasalah()).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import jurnal_peringatan

_file_peringatan: Path | None = None

# Picklist 'dibuat' tanpa catatan selesai/gagal selama ini dianggap yatim. Satu picklist normal
# selesai dalam hitungan menit; batas ini dibuat longgar supaya proses yang masih berjalan
# (mis. menunggu resi lama) tidak salah dituding.
UMUR_YATIM_S = 60 * 60
ALASAN_YATIM = "proses berhenti mendadak sebelum picklist selesai (tidak ada catatan selesai/gagal)"


def atur_folder(folder_log: Path) -> None:
    global _file_peringatan
    _file_peringatan = folder_log / "picklist_bermasalah.jsonl"


def catat(pesan: str) -> None:
    jurnal_peringatan.catat_pesan(_file_peringatan, pesan)


def baca_sejak(epoch: float) -> list[str]:
    """Peringatan yang tercatat sejak `epoch` (dari file, lintas proses python)."""
    return jurnal_peringatan.baca_sejak(_file_peringatan, epoch)


def _file_terhenti() -> Path | None:
    return _file_peringatan.with_name("picklist_terhenti.jsonl") if _file_peringatan else None


def _tulis_terhenti(op: str, picklist_no: str, nama: str, folder_label: Path, alasan: str,
                    tag: str | None, subfolder: str | None) -> None:
    """Satu baris jurnal picklist_terhenti.jsonl untuk op "tambah" (gagal) / "dibuat" (yatim)."""
    sekarang = datetime.now()
    jurnal_peringatan.tambah_baris(_file_terhenti(), {
        "op": op, "epoch": sekarang.timestamp(), "waktu": sekarang.strftime("%d-%m-%Y %H:%M"),
        "picklist": picklist_no, "nama": nama, "tag": tag, "subfolder": subfolder,
        "sesi": f"{folder_label.parent.name}/{folder_label.name}", "alasan": alasan})


def catat_terhenti(picklist_no: str, nama: str, folder_label: Path, alasan: str,
                   tag: str | None = None, subfolder: str | None = None) -> None:
    """Simpan picklist yang TERHENTI (langkah 3-6 gagal, mis. timeout unduh label PDF) secara
    terstruktur - cukup untuk menjalankan `main.py --lanjut` lagi dari UI (tombol "Download
    ulang") tanpa menyalin perintah dari Catatan. Log append-only (aman lintas thread/proses);
    keadaan akhir dilipat di daftar_terhenti()."""
    _tulis_terhenti("tambah", picklist_no, nama, folder_label, alasan, tag, subfolder)


def catat_dibuat(picklist_no: str, nama: str, folder_label: Path,
                 tag: str | None = None, subfolder: str | None = None) -> None:
    """Jurnal tulis-dulu: panggil SEGERA setelah picklist berhasil dibuat di Jubelio (aksi yang
    tidak bisa diulang). Kalau proses mati mendadak (PC mati/sleep, konsol ditutup, dimatikan)
    sebelum langkah 3-6 selesai, tidak ada kode yang sempat mencatat apa pun - catatan ini yang
    membuat picklist yatim tetap terlihat di daftar_terhenti() setelah UMUR_YATIM_S. Dihapus
    oleh tandai_selesai() (sukses) atau diganti catat_terhenti() (gagal biasa)."""
    _tulis_terhenti("dibuat", picklist_no, nama, folder_label, ALASAN_YATIM, tag, subfolder)


def tandai_selesai(picklist_no: str) -> None:
    """Picklist sudah berhasil sampai akhir (atau berhasil dilanjutkan) -> keluar dari daftar."""
    jurnal_peringatan.tambah_baris(_file_terhenti(), {
        "op": "selesai", "epoch": datetime.now().timestamp(), "picklist": picklist_no})


def daftar_terhenti(sekarang: float | None = None) -> list[dict]:
    """Picklist yang masih terhenti (belum ada catatan 'selesai' setelah catatan terakhirnya),
    terbaru di atas. Tiap item: picklist, nama, tag, subfolder, sesi, alasan, waktu. Termasuk
    picklist YATIM: tercatat 'dibuat' tapi tidak pernah selesai/gagal dan sudah lebih tua dari
    UMUR_YATIM_S (prosesnya diduga mati mendadak); yang lebih muda dianggap masih berjalan."""
    sekarang = datetime.now().timestamp() if sekarang is None else sekarang
    aktif: dict[str, dict] = {}
    dibuat: dict[str, dict] = {}
    for d in jurnal_peringatan.baca_baris(_file_terhenti()):
        no = d.get("picklist")
        if d.get("op") == "tambah" and no:
            aktif[no] = d
            dibuat.pop(no, None)
        elif d.get("op") == "dibuat" and no:
            dibuat[no] = d
        elif d.get("op") == "selesai":
            aktif.pop(no, None)
            dibuat.pop(no, None)
    for no, d in dibuat.items():
        if sekarang - d.get("epoch", 0) >= UMUR_YATIM_S:
            aktif[no] = d
    return sorted(aktif.values(), key=lambda d: d.get("epoch", 0), reverse=True)


def pesan_yatim(sekarang: float | None = None) -> list[str]:
    """Peringatan siap cetak untuk picklist yatim saja (lihat daftar_terhenti())."""
    return [f"{d['picklist']} ({d.get('nama')}, sesi {d.get('sesi')}) dibuat {d.get('waktu')} "
            f"tapi tidak pernah selesai - proses sebelumnya diduga mati mendadak. "
            f"Lanjutkan dari UI (tombol Terputus/Download ulang) atau main.py --lanjut."
            for d in daftar_terhenti(sekarang) if d.get("op") == "dibuat"]


def cetak(peringatan: list[str],
          judul: str = "PERHATIAN: PICKLIST TERHENTI/GAGAL (LANGKAH SEBELUMNYA)") -> None:
    """Cetak blok peringatan yang mencolok (dipanggil rekap_waktu.py di akhir tiap TIPE)."""
    jurnal_peringatan.cetak(peringatan, judul)
