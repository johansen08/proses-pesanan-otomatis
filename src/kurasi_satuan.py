"""Penanda "satuan sudah dikurasi" dan lokasi folder hasil pilah satuan (SPESIAL-SATUAN-<sesi> &
SISA-SATUAN-<sesi>), dipakai bersama pilah_satuan.py (menulis), print_spesial.py (cetak bulk) dan
server_ui.py (UI web). Hanya stdlib - sengaja ringan supaya print_spesial.py tidak ikut memuat pandas.

Kurasi = PDF satuan asal (`<tanggal>/<sesi>/SATUAN/PICK-....pdf`) yang halamannya SUDAH dipindah
ke folder hasil pilah. Isinya jangan dicetak lagi (dobel dengan SPESIAL-SATUAN/SISA-SATUAN), jadi
cetak bulk & UI memperlakukannya seperti "sudah tercetak". Penanda disimpan di logs/satuan_dikurasi.json
({path absolut PDF asal: "1-2-3"}); nama file asal TIDAK diubah (catatan sudah_dicetak berbasis path).
Penanda hanya berlaku selama folder hasil pilah-nya masih ada.
"""
from __future__ import annotations

import json
from pathlib import Path

import util_umum

ROOT = Path(__file__).resolve().parent.parent
FILE_KURASI = ROOT / "logs" / "satuan_dikurasi.json"
AWALAN_SPESIAL = "SPESIAL-SATUAN"
AWALAN_SISA = "SISA-SATUAN"
AWALAN_HASIL = (AWALAN_SPESIAL, AWALAN_SISA)


def folder_hasil(folder_tanggal: Path, awalan: str, sesi: str) -> Path:
    return folder_tanggal / f"{awalan}-{sesi}"


def _baca_mentah(file: Path | None = None) -> dict[str, str]:
    file = file or FILE_KURASI
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def baca(file: Path | None = None) -> dict[str, str]:
    """{path absolut PDF asal: label sesi} yang penandanya MASIH berlaku (folder hasil ada)."""
    hasil = {}
    for path, sesi in _baca_mentah(file).items():
        folder_tanggal = Path(path).parent.parent.parent       # <tanggal>/<sesi>/SATUAN/x.pdf
        if any(folder_hasil(folder_tanggal, a, sesi).is_dir() for a in AWALAN_HASIL):
            hasil[path] = sesi
    return hasil


def catat(pdfs: list[Path], sesi: str, file: Path | None = None) -> None:
    """Tandai `pdfs` dikurasi ke hasil pilah `sesi` (menimpa penanda lama file yang sama)."""
    file = file or FILE_KURASI
    data = _baca_mentah(file)
    for f in pdfs:
        data[str(f.resolve())] = sesi
    util_umum.tulis_json_atomik(file, data)


def bentrok(pdfs: list[Path], sesi: str, file: Path | None = None) -> dict[str, list[str]]:
    """{label sesi lama: [nama PDF]} untuk PDF yang SUDAH dikurasi ke folder hasil LAIN (label sesi
    berbeda dari `sesi`) yang masih ada. Membuat hasil baru di atasnya = resi yang sama ada di dua
    folder hasil (dobel cetak), jadi pilah_satuan menolaknya."""
    aktif = baca(file)
    hasil: dict[str, list[str]] = {}
    for f in pdfs:
        lama = aktif.get(str(f.resolve()))
        if lama and lama != sesi:
            hasil.setdefault(lama, []).append(f.name)
    return hasil


def hapus(pdfs: list[Path], sesi: str, file: Path | None = None) -> None:
    """Cabut penanda `pdfs` yang menunjuk ke hasil pilah `sesi` (mis. mode hanya-Excel: tidak ada
    PDF pengganti, jadi file asal tidak boleh bertanda dikurasi)."""
    file = file or FILE_KURASI
    data = _baca_mentah(file)
    tersisa = {k: v for k, v in data.items() if not (v == sesi and k in {str(f.resolve()) for f in pdfs})}
    if tersisa != data:
        util_umum.tulis_json_atomik(file, tersisa)


def daftar_hasil(folder_sesi: Path, awalan: str) -> list[Path]:
    """PDF folder hasil pilah `<awalan>-*` di tingkat TANGGAL, dilampirkan ke folder sesi TERAKHIR
    tanggal itu (cetak bulk bekerja per folder sesi; dengan begitu satu folder hasil tidak muncul
    berulang di --semua-sesi). Urut nama file. Kosong kalau bukan sesi terakhir / tidak ada."""
    folder_tanggal = folder_sesi.parent
    sesi = [d for d in folder_tanggal.iterdir() if d.is_dir() and d.name.isdigit()]
    if not sesi or folder_sesi.name != max(sesi, key=lambda d: int(d.name)).name:
        return []
    hasil = []
    for d in sorted(folder_tanggal.glob(f"{awalan}-*")):
        if d.is_dir():
            hasil += sorted(f for f in d.glob("*.pdf") if f.is_file())
    return hasil
