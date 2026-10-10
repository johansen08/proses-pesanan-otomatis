"""Penjaga "pesanan tak tersentuh": pesanan yang MASIH Siap Proses di Jubelio padahal sudah
dipesan hari sebelumnya, di akhir tiap TIPE (dipanggil main.py --upload-iresis, langkah terakhir).

Latar belakang (insiden 09/10/2026): 2 pesanan wajib keluar (channel Tokopedia TP-..., satu
kurir JNE) tidak pernah masuk picklist apa pun karena channel/kurirnya di luar filter semua
alur, dan program diam saja - baru ketahuan setelah lewat batas kirim. Penjaga ini mengambil
SEMUA pesanan Siap Proses tanpa filter channel/kurir (satu panggilan berhalaman), lalu
memperingatkan yang sudah menggantung sejak sebelum hari ini beserta ALASAN tebakannya
(channel/kurir di luar alur, atau tidak ikut picklist karena sebab lain).

Pola persistensi sama dengan peringatan_resi.py (logs/pesanan_tak_tersentuh.jsonl) supaya
src/rekap_waktu.py bisa mencetaknya ulang di rekap akhir TIPE. Folder log diatur main.py lewat
atur_folder(); tanpa itu (mis. di test) peringatan hanya disimpan di memori proses ini.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("sku-spesial")

WIB = timezone(timedelta(hours=7))
MAKS_NOMOR_DITAMPILKAN = 15     # nomor pesanan per kelompok alasan di 1 baris peringatan

_file_peringatan: Path | None = None
_sesi: list[str] = []
_lock = threading.Lock()


def atur_folder(folder_log: Path) -> None:
    global _file_peringatan
    _file_peringatan = folder_log / "pesanan_tak_tersentuh.jsonl"


def catat(pesan: str) -> None:
    log.warning("  %s", pesan)
    with _lock:
        _sesi.append(pesan)
        if _file_peringatan:
            baris = {"epoch": datetime.now().timestamp(),
                     "waktu": datetime.now().strftime("%d-%m-%Y %H:%M"), "pesan": pesan}
            with open(_file_peringatan, "a", encoding="utf-8") as f:
                f.write(json.dumps(baris, ensure_ascii=False) + "\n")


def baca_sejak(epoch: float) -> list[str]:
    """Peringatan yang tercatat sejak `epoch` (dari file, lintas proses python)."""
    if not _file_peringatan or not _file_peringatan.exists():
        return []
    hasil = []
    for baris in _file_peringatan.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(baris)
        except ValueError:
            continue
        if d.get("epoch", 0) >= epoch:
            hasil.append(f"[{d.get('waktu', '')}] {d.get('pesan', '')}")
    return hasil


def cetak(peringatan: list[str],
          judul: str = "PERHATIAN: PESANAN KEMARIN MASIH MENGGANTUNG DI SIAP PROSES (BELUM MASUK PICKLIST)") -> None:
    """Cetak blok peringatan yang mencolok (dipanggil paling akhir)."""
    if not peringatan:
        return
    print()
    print("!" * 60)
    print(f"  {judul}")
    print("!" * 60)
    for p in peringatan:
        print(f"  - {p}")
    print("!" * 60)


def _waktu_pesan(o: dict) -> datetime | None:
    ts = o.get("transaction_date")
    if not ts:
        return None
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(WIB)


def alasan(o: dict) -> str:
    """Tebakan kenapa pesanan ini tidak pernah masuk picklist: channel/kurir di luar semua alur
    (lihat proses_label: CHANNEL_IDS_REGULER + Lazada, dan KURIR_FILTER_*), atau sebab lain
    (stok kosong, ditolak Jubelio, ditahan jam tunda, SPX Standard mode non-event, dst)."""
    import proses_label as pl

    channel_ok = set(pl.CHANNEL_IDS_REGULER) | {pl.CHANNEL_ID_LAZADA}
    kurir = str(o.get("shipper") or "")
    nama = kurir.lower()
    # kurir yang urgent-nya lintas channel (alur GTL-SiCepat & JNE-LEX tanpa filter channel);
    # "goto logistics" = nama panjang GTL di Jubelio (kata kuncinya "gtl" tidak ada di awalnya)
    lintas_channel = any(kata in nama for kata in
                         (*pl.KURIR_FILTER_URGENT_GTL_SICEPAT, *pl.KURIR_FILTER_URGENT_JNE_LEX,
                          "goto logistics"))
    if not lintas_channel and not any(kata in nama for kata in pl.KURIR_FILTER_REGULER):
        return f"kurir {kurir or '-'} di luar semua alur"
    if not lintas_channel and o.get("source") not in channel_ok:
        return f"channel {o.get('source_name') or o.get('source')} di luar alur reguler"
    return "tidak ikut picklist (cek stok kosong / ditolak Jubelio / ditahan jam tunda)"


def cari_tak_tersentuh(pesanan: list[dict], sekarang: datetime | None = None) -> list[dict]:
    """Pesanan dengan jam pesan SEBELUM hari ini 00:00 WIB (murni logika data, tanpa API).
    Pesanan tanpa transaction_date tidak dianggap (tidak bisa dipastikan umurnya). Hasil:
    daftar dict `o` + kunci "alasan", diurutkan terlama dulu."""
    awal_hari = (sekarang or datetime.now(WIB)).astimezone(WIB).replace(
        hour=0, minute=0, second=0, microsecond=0)
    hasil = []
    for o in pesanan:
        waktu = _waktu_pesan(o)
        if waktu is not None and waktu < awal_hari:
            hasil.append({**o, "alasan": alasan(o), "_waktu": waktu})
    return sorted(hasil, key=lambda o: o["_waktu"])


def periksa(k, sekarang: datetime | None = None) -> list[str]:
    """Ambil SEMUA pesanan Siap Proses (tanpa filter channel/kurir, read-only), catat 1 peringatan
    per kelompok alasan, dan kembalikan teks peringatannya. Kegagalan API dilempar ke pemanggil
    (main.cek_pesanan_tak_tersentuh() yang menelannya - penjaga tidak boleh menggagalkan TIPE)."""
    import proses_label as pl

    semua = pl._ambil_pesanan_channel_mentah(k, None, None)
    sisa = cari_tak_tersentuh(semua, sekarang)
    log.info("Cek pesanan tak tersentuh: %d pesanan Siap Proses, %d dipesan sebelum hari ini",
             len(semua), len(sisa))
    kelompok: dict[str, list[dict]] = {}
    for o in sisa:
        kelompok.setdefault(o["alasan"], []).append(o)
    pesan_semua = []
    for alasan_k, daftar in kelompok.items():
        tampil = [f"{o['salesorder_no']} ({o.get('shipper') or '-'}, "
                  f"{o['_waktu'].strftime('%d/%m %H:%M')})"
                  for o in daftar[:MAKS_NOMOR_DITAMPILKAN]]
        lebih = f" +{len(daftar) - MAKS_NOMOR_DITAMPILKAN} lainnya" if len(daftar) > MAKS_NOMOR_DITAMPILKAN else ""
        pesan = (f"{len(daftar)} pesanan Siap Proses dipesan SEBELUM hari ini tapi belum masuk "
                 f"picklist - {alasan_k}: {', '.join(tampil)}{lebih}. Proses manual di Jubelio "
                 f"sebelum batas kirim, atau cek kenapa tidak terambil program.")
        catat(pesan)
        pesan_semua.append(pesan)
    return pesan_semua
