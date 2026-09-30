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

Dengan "--label --jalankan", PDF BARU dibuat setelah proses selesai, dari jumlah pesanan
yang benar-benar berhasil dipicklist per SKU (bukan daftar kandidat awal).

Picklist urgent (proses_label.py): TIDAK bagian dari alur "--label --jalankan" (menu 3 di
menu.bat cuma untuk kurir J&T/SPX). 2 skenario: channel Lazada, dan kurir GTL/SiCepat
(lintas channel - baik dari Tokopedia asli maupun "Shop | Tokopedia"/TikTok, urgent-nya
ditentukan kurir bukan channel). Berdiri sendiri lewat --urgent (sampai label PDF juga),
boleh dibatasi 1 skenario saja lewat --channel:
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

Pemisahan J&T/SPX (dipakai sesi JAM 13.00 & SESI SORE - lihat menu.bat/JADWAL-PROSES.md):
tambahkan --kurir jnt atau --kurir spx ke --label maupun --reguler supaya J&T dan SPX jadi
picklist terpisah saat pembuatan (bukan digabung seperti SESI PAGI). Penentuan SKU spesial
sendiri TETAP menggabung J&T+SPX, --kurir hanya membatasi resi mana yang benar-benar
dipicklist:
    python src/main.py --label --kurir jnt --tanpa-reguler --jalankan
    python src/main.py --reguler --bagian 1qty --kurir spx --jalankan

Picklist Shopee Pagi (proses_label.py): dijalankan MANUAL 1x sehari (mis. jam 13:00), BUKAN
bagian alur otomatis --label --jalankan. Semua pesanan channel Shopee yang jam pesannya (WIB)
maksimal jam 12 siang hari ini, digabung jadi 1 picklist:
    python src/main.py --shopee-pagi                      # MODE UJI: hanya tampilkan rencana
    python src/main.py --shopee-pagi --jalankan
"""
import argparse
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from proses_label import durasi
from sku_spesial import baca_excel, buat_pdf, hitung_sku_spesial, resi_kandidat

ROOT = Path(__file__).resolve().parent.parent   # root project, bukan folder src/ ini
FOLDER_EXCEL = ROOT / "laporan-siap-proses"
FOLDER_PDF = ROOT / "laporan-sku-spesial"
FOLDER_LOG = ROOT / "logs"
FOLDER_LABEL = ROOT / "label-pengiriman"
FILE_RIWAYAT = ROOT / "riwayat_picklist.xlsx"

# Folder sesi aktif di dalam FOLDER_LABEL, mis. "label-pengiriman/2026-09-30_4". Diisi sekali oleh
# main() lewat folder_label_sesi() sebelum menu mana pun dijalankan, supaya semua pilihan
# menu.bat (1-7) dalam 1x jalan menu.bat menyimpan label ke folder sesi yang sama - baru
# ganti sesi saat menu.bat ditutup & dijalankan ulang (lihat menu.bat: LABEL_SESI_DIR).
FOLDER_LABEL_SESI = FOLDER_LABEL


def sesi_label_baru() -> str:
    """Cari nomor sesi terbesar untuk tanggal hari ini di FOLDER_LABEL, lalu buat folder
    sesi berikutnya (mis. sudah ada 2026-09-30_1..2026-09-30_3 -> buat 2026-09-30_4)."""
    FOLDER_LABEL.mkdir(exist_ok=True)
    tanggal = datetime.now().strftime("%Y-%m-%d")
    pola = re.compile(rf"^{re.escape(tanggal)}_(\d+)$")
    urutan_terbesar = 0
    for item in FOLDER_LABEL.iterdir():
        if item.is_dir():
            cocok = pola.match(item.name)
            if cocok:
                urutan_terbesar = max(urutan_terbesar, int(cocok.group(1)))
    nama = f"{tanggal}_{urutan_terbesar + 1}"
    (FOLDER_LABEL / nama).mkdir(exist_ok=True)
    return nama


def folder_label_sesi() -> Path:
    """Folder sesi label aktif: pakai LABEL_SESI_DIR dari environment kalau ada (diset
    sekali oleh menu.bat saat mulai), kalau tidak buat sesi baru (mis. dipanggil langsung
    tanpa menu.bat)."""
    nama = os.environ.get("LABEL_SESI_DIR") or sesi_label_baru()
    folder = FOLDER_LABEL / nama
    folder.mkdir(exist_ok=True)
    return folder


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", type=Path, help="proses file Excel ini tanpa download")
    ap.add_argument("--tanpa-cek-nilai", action="store_true",
                    help="jangan cek nilai pesanan ke API (pesanan nilai 0 tidak dikeluarkan)")
    ap.add_argument("--label", action="store_true",
                    help="lanjut proses SKU spesial sampai label PDF (tanpa --jalankan = mode uji)")
    ap.add_argument("--tanpa-reguler", action="store_true",
                    help="dipakai bersama --label: lewati picklist sisa reguler otomatis "
                        "setelah SKU spesial selesai (SKU spesial saja)")
    ap.add_argument("--urgent", action="store_true",
                    help="hanya buat picklist urgent (channel Lazada, kurir GTL/SiCepat lintas "
                        "channel) sampai label PDF, tanpa proses SKU spesial "
                        "(tanpa --jalankan = mode uji)")
    ap.add_argument("--channel", choices=["lazada", "gtl-sicepat"],
                    help="dipakai bersama --urgent: batasi ke 1 skenario saja")
    ap.add_argument("--reguler", action="store_true",
                    help="hanya buat picklist sisa reguler (TikTok Shop & Shopee, bukan SKU "
                        "spesial) sampai label PDF, tanpa proses SKU spesial "
                        "(tanpa --jalankan = mode uji)")
    ap.add_argument("--bagian", choices=["1qty", "kombinasi"],
                    help="dipakai bersama --reguler: batasi ke 1 bagian saja")
    ap.add_argument("--kurir", choices=["jnt", "spx"],
                    help="dipakai bersama --label atau --reguler: pisahkan J&T dan SPX jadi "
                        "picklist sendiri-sendiri, bukan digabung (dipakai sesi JAM 13.00 & "
                        "SESI SORE - lihat menu.bat/JADWAL-PROSES.md); tanpa --kurir = J&T "
                        "dan SPX digabung seperti semula (SESI PAGI)")
    ap.add_argument("--shopee-pagi", action="store_true",
                    help="hanya buat picklist Shopee Pagi (channel Shopee, jam pesan s.d. "
                        "12:00 WIB hari ini) sampai label PDF - dijalankan manual 1x sehari, "
                        "BUKAN bagian alur otomatis --label (tanpa --jalankan = mode uji)")
    ap.add_argument("--sku", action="append",
                    help="hanya proses SKU ini (boleh diulang)")
    ap.add_argument("--jalankan", action="store_true",
                    help="benar-benar buat picklist, selesaikan picking, minta resi, cetak label")
    ap.add_argument("--lanjut", metavar="PICK-000xxxxxx",
                    help="lanjutkan picklist yang prosesnya terhenti")
    args = ap.parse_args()

    muat_env(ROOT / ".env")
    log = siapkan_log()
    global FOLDER_LABEL_SESI
    FOLDER_LABEL_SESI = folder_label_sesi()
    log.info("Folder sesi label: %s", FOLDER_LABEL_SESI)
    try:
        if args.lanjut:
            return lanjut_picklist(log, args)
        if args.urgent:
            return urgent_picklist(log, args)
        if args.reguler:
            return reguler_picklist(log, args)
        if args.shopee_pagi:
            return shopee_pagi_picklist(log, args)

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
            kandidat = resi_kandidat(df)
            log.info("Mengambil nilai pesanan dari API untuk %d resi kandidat", len(kandidat))
            nilai = jubelio.ambil_nilai_pesanan(token, kandidat)

        tabel, ringkasan = hitung_sku_spesial(df, nilai)
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
            return proses_label_sku(log, token, tabel, ringkasan, args, lama_daftar, waktu)

        FOLDER_PDF.mkdir(exist_ok=True)
        pdf = FOLDER_PDF / f"SKU_Spesial_{waktu:%Y-%m-%d_%H%M}.pdf"
        buat_pdf(tabel, ringkasan, pdf, waktu)
        log.info("SELESAI: %d SKU spesial, %d resi spesial -> %s",
                 ringkasan["total_sku_spesial"], ringkasan["total_resi_spesial"], pdf)
        log.info("Daftar resi spesial (urut rak) dibuat dalam %s", durasi(lama_daftar))

        if args.label:
            return proses_label_sku(log, token, tabel, ringkasan, args, lama_daftar, waktu)
        return 0
    except Exception as e:   # noqa: BLE001 - catat semua kegagalan ke log
        log.exception("GAGAL: %s", e)
        return 1


def proses_label_sku(log: logging.Logger, token: str, tabel, ringkasan: dict, args,
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
    rak_per_sku = dict(zip(tabel["SKU"], tabel["No Rak"]))
    if not args.jalankan:
        if not resi_per_sku:
            log.info("Tidak ada SKU spesial untuk diproses")
            return 0
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana(k, resi_per_sku, rak_per_sku, args.kurir)
        if not args.sku and not args.tanpa_reguler:
            resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values() for no in daftar}
            proses_label.rencana_reguler(k, resi_spesial_semua, kurir=args.kurir)
        return 0

    hasil, lama_proses = [], 0.0
    if resi_per_sku:
        log.info("MEMPROSES %d SKU spesial per rak sampai label PDF", len(resi_per_sku))
        mulai = time.monotonic()
        hasil = proses_label.proses(k, resi_per_sku, FOLDER_LABEL_SESI, FILE_RIWAYAT, rak_per_sku,
                                    args.kurir)
        lama_proses = time.monotonic() - mulai

        log.info("RINGKASAN (urut rak):")
        for h in hasil:
            log.info("  %-8s %-14s %-16s pesanan %-3s resi %-3s %-18s %s", h["Rak"], h["SKU"],
                     h.get("No Picklist", "-"), h.get("Total Pesanan", "-"), h.get("Resi Keluar", "-"),
                     h["Durasi"], h.get("Catatan", ""))
    else:
        log.info("Tidak ada SKU spesial untuk diproses")

    # PDF dibuat SETELAH proses, dari hasil AKTUAL (SKU yang benar-benar berhasil dipicklist),
    # bukan dari daftar kandidat -> total di PDF selalu sama dengan yang benar-benar diproses.
    baris_aktual = [{"No Rak": h["Rak"], "SKU": h["SKU"], "Jumlah Resi": h["Total Pesanan"]}
                    for h in hasil if h.get("No Picklist")]
    tabel_aktual = pd.DataFrame(baris_aktual, columns=["No Rak", "SKU", "Jumlah Resi"])
    ringkasan_aktual = {
        "total_sku_spesial": len(tabel_aktual),
        "total_resi_spesial": int(tabel_aktual["Jumlah Resi"].sum()) if len(tabel_aktual) else 0,
    }
    FOLDER_PDF.mkdir(exist_ok=True)
    pdf = FOLDER_PDF / f"SKU_Spesial_{waktu:%Y-%m-%d_%H%M}.pdf"
    buat_pdf(tabel_aktual, ringkasan_aktual, pdf, waktu)
    log.info("SELESAI: %d SKU spesial (benar-benar diproses), %d resi -> %s",
             ringkasan_aktual["total_sku_spesial"], ringkasan_aktual["total_resi_spesial"], pdf)

    if not args.sku and not args.tanpa_reguler:
        # Sisa reguler (TikTok Shop & Shopee, bukan SKU spesial) baru bisa dipisah dengan
        # benar SETELAH tahu daftar SKU spesial hari itu -> dijalankan di sini, bukan sebelum
        # download seperti urgent. Dilewati kalau --sku dipakai (proses cuma sebagian SKU,
        # daftar SKU spesial belum lengkap utk pengecualian), atau --tanpa-reguler (SKU
        # spesial saja).
        resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values() for no in daftar}
        log.info("MEMPROSES picklist sisa reguler (TikTok Shop & Shopee, bukan SKU spesial)")
        proses_label.proses_reguler(k, resi_spesial_semua, FILE_RIWAYAT, FOLDER_LABEL_SESI,
                                    kurir=args.kurir)

    diproses = [h["detik"] for h in hasil if h.get("No Picklist")]
    log.info("Waktu buat daftar resi spesial : %s", durasi(lama_daftar))
    log.info("Waktu proses %d SKU spesial    : %s (%d dibuat picklist, rata-rata %s per SKU)",
             len(hasil), durasi(lama_proses), len(diproses),
             durasi(sum(diproses) / len(diproses)) if diproses else "-")
    log.info("Total waktu                    : %s", durasi(lama_daftar + lama_proses))
    log.info("Riwayat: %s", FILE_RIWAYAT)
    return 1 if any(str(h.get("Catatan", "")).startswith(("GAGAL", "TERHENTI")) for h in hasil) else 0


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
    gagal = [h for h in hasil if str(h.get("Catatan", "")).startswith(("GAGAL", "TERHENTI"))]
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
        kandidat = resi_kandidat(df)
        log.info("Mengambil nilai pesanan dari API untuk %d resi kandidat", len(kandidat))
        nilai = jubelio.ambil_nilai_pesanan(token, kandidat)
    _, ringkasan = hitung_sku_spesial(df, nilai)
    resi_spesial_semua = {no for daftar in ringkasan["resi_per_sku"].values() for no in daftar}
    log.info("%d resi SKU spesial hari ini (dikeluarkan dari picklist reguler)",
             len(resi_spesial_semua))

    k = proses_label.Klien(token)
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_reguler(k, resi_spesial_semua, args.bagian, args.kurir)
        return 0
    hasil = proses_label.proses_reguler(k, resi_spesial_semua, FILE_RIWAYAT, FOLDER_LABEL_SESI,
                                        args.bagian, args.kurir)
    gagal = [h for h in hasil if str(h.get("Catatan", "")).startswith(("GAGAL", "TERHENTI"))]
    log.info("SELESAI reguler: %d picklist dibuat%s", len(hasil) - len(gagal),
             f", {len(gagal)} bermasalah" if gagal else "")
    return 1 if gagal else 0


def shopee_pagi_picklist(log: logging.Logger, args) -> int:
    import proses_label

    k = proses_label.Klien(login(log))
    if not args.jalankan:
        log.info("MODE UJI - tidak ada perubahan di Jubelio. Tambahkan --jalankan untuk memproses.")
        proses_label.rencana_shopee_pagi(k)
        return 0
    hasil = proses_label.proses_shopee_pagi(k, FILE_RIWAYAT, FOLDER_LABEL_SESI)
    gagal = [h for h in hasil if str(h.get("Catatan", "")).startswith(("GAGAL", "TERHENTI"))]
    log.info("SELESAI Shopee Pagi: %d picklist dibuat%s", len(hasil) - len(gagal),
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
    baris = proses_label.lanjutkan(k, args.lanjut, FOLDER_LABEL_SESI, FILE_RIWAYAT)
    log.info("SELESAI: %s", baris)
    return 0


if __name__ == "__main__":
    sys.exit(main())
