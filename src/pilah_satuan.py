"""Pilah ulang label SATUAN yang sudah dibuat/dicetak: cari SKU yang (digabung dari banyak
sesi/picklist) punya >= MIN_RESI resi sehingga bisa dikelompokkan seperti SKU spesial.

SYARAT (divalidasi, ditolak kalau tidak terpenuhi): hanya satuan GABUNGAN J&T + SPX (subfolder
`SATUAN` persis, bukan JNT_SATUAN/SPX_SATUAN/event) dari sesi yang mulai diproses 07.00-12.00 atau 20.00-07.00
(cap waktu terawal di nama file PDF sesi); resi berkurir selain J&T/SPX tidak dihitung spesial.
`--abaikan-jendela` (uji) hanya melewati syarat jam.

Program ini READ-ONLY terhadap Jubelio (hanya GET `sales/picklists/{id}`) dan TIDAK membuat
picklist/resi baru. Alurnya:
  1. Cari PDF di subfolder SATUAN (dan JNT_SATUAN/SPX_SATUAN dst) semua sesi di folder tanggal.
  2. Tiap PDF -> nomor picklist dari nama file -> API Jubelio: SKU, nomor pesanan, resi per item.
  3. Tiap halaman PDF dicocokkan ke item lewat "No Resi" (cadangan: "No Pesanan") di teks label.
  4. SKU dengan >= MIN_RESI halaman dikumpulkan: PDF label baru per SKU (halaman yang sama,
     urut sesi/picklist asal) + ringkasan Excel per resi (untuk menarik label cetak fisik).
Hasil di `<folder tanggal>/SPESIAL-SATUAN-<sesi>/` (mis. SPESIAL-SATUAN-1-2-3): PDF per SKU dan
`detail-resi-spesial-satuan-<sesi>.xlsx` (format sama persis dengan detail-resi-spesial.xlsx: 1 sheet, 4 kolom).
Halaman yang TIDAK terpilih jadi spesial masuk `<folder tanggal>/SISA-SATUAN-<sesi>/`: PDF per kelompok rak
asal (1QTY-REGULER-2A/3A/1B/2B/3B/LAINNYA, gabungan lintas sesi/picklist, urut nomor PICK).

Pemakaian:
  python src/pilah_satuan.py --tanggal 2026-10-13 [--sesi 1-2-3]   (tanpa --sesi: semua sesi)
  --analisis-saja (tanpa tulis file), --cache FILE, --json: dipakai server_ui.py (menu Pilah di UI)
  python src/pilah_satuan.py --folder label-pengiriman/2026-10-13 [--min-resi 3] [--tanpa-pdf]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter

import kurasi_satuan
import nama_sesi as pola_sesi
import proses_label
from sku_spesial import AWALAN_SKU_DIKECUALIKAN_SPESIAL, KURIR_DIIZINKAN, MIN_RESI

ROOT = Path(__file__).resolve().parent.parent
FOLDER_LABEL = ROOT / "label-pengiriman"
# Pilah HANYA berlaku untuk satuan GABUNGAN J&T + SPX (subfolder `SATUAN` persis; varian per kurir
# JNT_SATUAN/SPX_SATUAN/SPXHEMAT_SATUAN/... = mode dipisah, tidak ikut) dari sesi yang mulai diproses
# antara 07.00-12.00 atau 20.00-07.00 (lewat tengah malam); sesi yang mulai 12.01-19.59 tidak boleh dipilah.
# Hasil analisis di cache (--cache) hanya dipercaya selama ini: pesanan bisa dibatalkan di Jubelio
# di antara "Analisis" dan "Buat folder" - cache lama bisa memuat label pesanan yang sudah batal.
UMUR_CACHE_MAKS_S = 15 * 60
# Sesi yang file PDF-nya diubah dalam rentang ini dianggap MASIH ditulis proses harian: PDF-nya belum
# lengkap, jadi tidak boleh dipilah (0 = nonaktif, dipakai tes).
MASA_TENANG_S = 120
FOLDER_SATUAN_GABUNG = "SATUAN"
# Jendela (menit sejak 00.00, batas inklusif); (mulai > akhir) = melewati tengah malam.
JENDELA_PILAH_MENIT = ((7 * 60, 12 * 60), (20 * 60, 7 * 60))
TEKS_JENDELA = "07.00-12.00 atau 20.00-07.00"
NAMA_FOLDER_HASIL = kurasi_satuan.AWALAN_SPESIAL
NAMA_FOLDER_SISA = kurasi_satuan.AWALAN_SISA
POLA_PICK = re.compile(r"^PICK-0*(\d+)_", re.IGNORECASE)
POLA_WAKTU_FILE = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})(\d{2})\.pdf$", re.IGNORECASE)
POLA_PICK_PENUH = re.compile(r"^(PICK-\d+)_", re.IGNORECASE)
POLA_RESI = re.compile(r"No Resi:\s*([A-Za-z0-9]+)")
POLA_PESANAN = re.compile(r"No Pesanan\s*:\s*([A-Za-z0-9\-]+)")

log = logging.getLogger("pilah-satuan")


def parse_sesi(teks: str | None) -> list[str] | None:
    """"1-2-3" / "1,2,3" / "1 2 3" -> ["1", "2", "3"] (unik, urut); kosong -> None (semua sesi)."""
    if not teks or not teks.strip():
        return None
    bagian = [b for b in re.split(r"[-,\s]+", teks.strip().upper().replace("-PEMULIHAN", "P")) if b]
    if not all(pola_sesi.POLA_KODE.match(b.upper()) for b in bagian):
        raise ValueError(f"Sesi harus angka (P di belakang = folder N-PEMULIHAN) dipisah '-' atau ',': {teks!r}")
    return sorted({f"{int(b.rstrip('Pp'))}{'P' if b.upper().endswith('P') else ''}" for b in bagian},
                  key=pola_sesi.urutan_kode)


class SesiTidakValid(ValueError):
    """Sesi yang diminta tidak boleh dipilah (bukan satuan gabungan / di luar jendela jam proses /
    masih ditulis proses harian)."""


class KurasiBentrok(ValueError):
    """Sebagian PDF satuan sudah dikurasi ke folder hasil pilah LAIN yang masih ada."""


def pesan_bentrok(b: dict[str, list[str]]) -> str:
    return ("; ".join(f"{len(n)} PDF sudah dikurasi ke SPESIAL-SATUAN-{s} / SISA-SATUAN-{s}" for s, n in sorted(b.items()))
            + " - hapus folder hasil itu dulu atau pilih sesi yang persis sama")


def umur_file_terbaru(folder_sesi: Path) -> float | None:
    """Detik sejak PDF di folder sesi terakhir diubah (None kalau tak ada PDF)."""
    waktu = []
    for f in folder_sesi.rglob("*.pdf"):
        try:
            waktu.append(f.stat().st_mtime)
        except OSError:
            pass
    return time.time() - max(waktu) if waktu else None


def waktu_mulai_sesi(folder_sesi: Path) -> datetime | None:
    """Waktu sesi mulai diproses = cap waktu TERAWAL di nama file PDF mana pun di folder sesi
    (`..._2026-10-13_201932.pdf`); bukan mtime, yang berubah karena sinkron/salin. None kalau
    tak ada PDF bercap waktu."""
    waktu = []
    for f in folder_sesi.rglob("*.pdf"):
        m = POLA_WAKTU_FILE.search(f.name)
        if m:
            try:
                waktu.append(datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}"))
            except ValueError:
                pass
    return min(waktu) if waktu else None


def sesi_asal(folder_sesi: Path) -> Path:
    """Folder N-PEMULIHAN dibuat ulang di jam pemulihan, padahal syarat jendela jam menyangkut kapan sesi
    ASALNYA diproses (satuan gabungan J&T + SPX hanya dari proses pagi/malam). Penanda `pulihan.json`
    ({"asal": "YYYY-MM-DD/N"}, ditulis main.py --pulihkan-sesi) menunjuk sesi asal; tanpa penanda =
    folder itu sendiri."""
    try:
        asal = json.loads((folder_sesi / pola_sesi.NAMA_PENANDA_PULIHAN).read_text(encoding="utf-8"))["asal"]
        folder = folder_sesi.parent.parent / asal
        return folder if folder.is_dir() else folder_sesi
    except (OSError, ValueError, KeyError, TypeError):
        return folder_sesi


def pdf_satuan_gabungan(folder_sesi: Path) -> list[Path]:
    """PDF di subfolder `SATUAN` persis (gabungan J&T + SPX) sebuah sesi."""
    return [f for f in (folder_sesi / FOLDER_SATUAN_GABUNG).glob("*.pdf") if POLA_PICK.match(f.name)]


def dalam_jendela(menit: int) -> bool:
    """`menit` (sejak 00.00) jatuh di salah satu JENDELA_PILAH_MENIT (batas inklusif; jendela yang
    awalnya lebih besar dari akhirnya melewati tengah malam, mis. 20.00-07.00)."""
    return any(a <= menit <= b if a <= b else menit >= a or menit <= b for a, b in JENDELA_PILAH_MENIT)


def periksa_sesi(folder_sesi: Path, abaikan_jendela: bool = False) -> tuple[bool, str | None]:
    """(boleh dipilah, alasan kalau tidak). `abaikan_jendela`: lewati syarat jam (hanya CLI, uji)."""
    if not pdf_satuan_gabungan(folder_sesi):
        ada_kurir = any(folder_sesi.glob("*SATUAN/*.pdf"))
        return False, ("Satuan dipisah per kurir (bukan gabungan J&T + SPX)" if ada_kurir
                       else "Tidak ada label satuan")
    umur = umur_file_terbaru(folder_sesi)
    if MASA_TENANG_S and umur is not None and umur < MASA_TENANG_S:
        return False, f"Sesi masih menulis label ({int(umur)} detik lalu) - tunggu proses selesai"
    if abaikan_jendela:
        return True, None
    mulai = waktu_mulai_sesi(sesi_asal(folder_sesi)) or waktu_mulai_sesi(folder_sesi)
    if mulai is None:
        return False, "Waktu proses sesi tidak diketahui"
    menit = mulai.hour * 60 + mulai.minute
    if not dalam_jendela(menit):
        return False, f"Diproses {mulai:%H.%M} - di luar {TEKS_JENDELA}"
    return True, None


def pdf_terpilih(folder_tanggal: Path, sesi: list[str] | None = None,
                 abaikan_jendela: bool = False) -> tuple[list[Path], list[str]]:
    """(PDF satuan, daftar sesi) yang BOLEH dipilah. `sesi` eksplisit: salah satu tidak boleh ->
    SesiTidakValid (tidak ada yang diproses diam-diam). Tanpa `sesi`: semua sesi yang boleh."""
    if sesi:
        kandidat = sesi
    else:
        kandidat = sorted((k for d in folder_tanggal.iterdir() if d.is_dir() and (k := pola_sesi.kode_sesi(d.name))),
                          key=pola_sesi.urutan_kode)
    ganda = sorted({k for k in kandidat if k.endswith("P") and k[:-1] in kandidat}, key=pola_sesi.urutan_kode)
    if sesi and ganda:   # sesi asal + hasil pemulihannya berisi resi yang sama -> dobel
        raise SesiTidakValid("Sesi " + ", ".join(f"{k[:-1]} dan {k}" for k in ganda) +
                             ": pilih salah satu (N-PEMULIHAN berisi ulang semua picklist sesi N)")
    kandidat = [k for k in kandidat if k not in {g[:-1] for g in ganda}] if not sesi else kandidat
    layak, ditolak = [], []
    for nomor in kandidat:
        ok, alasan = periksa_sesi(folder_tanggal / pola_sesi.folder_dari_kode(nomor), abaikan_jendela)
        (layak if ok else ditolak).append(nomor if ok else (nomor, alasan))
    if sesi and ditolak:
        raise SesiTidakValid("; ".join(f"Sesi {n}: {a}" for n, a in ditolak))
    if not layak:
        raise SesiTidakValid("Tidak ada sesi yang boleh dipilah (hanya satuan gabungan J&T + SPX "
                             f"yang diproses {TEKS_JENDELA})")
    return cari_pdf_satuan(folder_tanggal, layak), layak


def cari_pdf_satuan(folder_tanggal: Path, sesi: list[str] | None = None) -> list[Path]:
    """PDF di subfolder `SATUAN` (gabungan J&T + SPX) sesi terpilih (default semua sesi), urut
    nomor PICK. Varian per kurir (JNT_SATUAN dst) TIDAK ikut."""
    pola = ([f"{pola_sesi.folder_dari_kode(s)}/{FOLDER_SATUAN_GABUNG}/*.pdf" for s in sesi] if sesi
            else [f"*/{FOLDER_SATUAN_GABUNG}/*.pdf"])
    hasil = [f for p in pola for f in folder_tanggal.glob(p) if POLA_PICK.match(f.name)]
    return sorted(hasil, key=lambda f: int(POLA_PICK.match(f.name).group(1)))


def kunci_halaman(teks: str) -> tuple[str | None, str | None]:
    """(No Resi, No Pesanan) dari teks satu halaman label; None kalau tidak ketemu."""
    resi = POLA_RESI.search(teks)
    pesanan = POLA_PESANAN.search(teks)
    return (resi.group(1) if resi else None, pesanan.group(1) if pesanan else None)


def _angka(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 1.0   # field tak ada/kosong: anggap qty 1 (picklist satuan memang 1 qty)


def sku_dikecualikan(sku: str) -> bool:
    """Awalan SKU yang tidak pernah jadi spesial (sama dengan spesial biasa, mis. C225-UB)."""
    return str(sku or "").upper().startswith(tuple(a.upper() for a in AWALAN_SKU_DIKECUALIKAN_SPESIAL))


def item_picklist(k, nomor: int) -> list[dict]:
    """Item picklist (tanpa yang CANCELED) -> {sku, pesanan, resi, kurir, boleh_spesial}.
    `boleh_spesial` False (resi tetap jadi sisa) untuk pesanan yang di spesial biasa juga tidak lolos:
    bundle (item komponen ber-`bundle_item_id`; bundle PTAA pun tidak bisa dikenali dari kode komponen,
    jadi semua bundle ditolak - BD dst), lebih dari 1 item per pesanan, atau qty bukan 1."""
    p = k.get(f"sales/picklists/{nomor}")
    items = [i for i in p.get("items") or [] if i.get("wms_status") != "CANCELED"]
    jumlah = Counter(str(i.get("salesorder_no") or "") for i in items)
    hasil = []
    for i in items:
        pesanan = str(i.get("salesorder_no") or "")
        boleh = (jumlah[pesanan] == 1 and not i.get("bundle_item_id")
                 and _angka(i.get("qty_ordered")) == 1)
        hasil.append({"sku": str(i.get("item_code") or ""), "pesanan": pesanan,
                      "resi": str(i.get("tracking_no") or ""), "kurir": str(i.get("shipper") or ""),
                      "boleh_spesial": boleh})
    return hasil


def petakan_halaman(pdf: Path, items: list[dict]) -> tuple[list[dict], int]:
    """Cocokkan tiap halaman PDF ke item (resi dulu, lalu nomor pesanan).
    Mengembalikan (baris per halaman yang cocok, jumlah halaman tak cocok)."""
    per_resi = {i["resi"]: i for i in items if i["resi"]}
    per_pesanan = {i["pesanan"]: i for i in items if i["pesanan"]}
    baris, tak_cocok = [], 0
    for no, halaman in enumerate(PdfReader(str(pdf)).pages):
        resi, pesanan = kunci_halaman(halaman.extract_text() or "")
        item = per_resi.get(resi) or per_pesanan.get(pesanan)
        if not item:
            tak_cocok += 1
            continue
        baris.append({**item, "pdf": pdf, "halaman": no})
    return baris, tak_cocok


def kurir_diizinkan(kurir: str) -> bool:
    """Sama dengan R3 SKU spesial: teks kurir diawali J&T atau SPX (tak peka huruf besar/kecil)."""
    return str(kurir or "").strip().upper().startswith(tuple(a.upper() for a in KURIR_DIIZINKAN))


def kelompokkan(baris: list[dict], min_resi: int = MIN_RESI) -> tuple[dict[str, list[dict]], dict[str, int]]:
    """(SKU dengan >= min_resi halaman, jumlah resi SKU yang di bawah ambang). Resi dobel
    (halaman yang sama muncul 2x) hanya dihitung sekali. Resi berkurir selain J&T/SPX tidak
    pernah dihitung (tetap jadi sisa satuan)."""
    per_sku: dict[str, dict[str, dict]] = defaultdict(dict)
    for b in baris:
        if (not kurir_diizinkan(b.get("kurir")) or sku_dikecualikan(b["sku"])
                or not b.get("boleh_spesial", True)):
            continue
        per_sku[b["sku"]].setdefault(b["resi"] or b["pesanan"], b)
    layak = {s: list(d.values()) for s, d in per_sku.items() if len(d) >= min_resi}
    sisa = {s: len(d) for s, d in per_sku.items() if len(d) < min_resi}
    return layak, sisa


def kelompok_sisa(baris: list[dict], layak: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Halaman yang TIDAK dipindah ke SPESIAL-SATUAN, dikelompokkan per kelompok rak asalnya
    (token di nama file, mis. "1QTY-REGULER-2A"), urut nomor PICK lalu halaman. Resi dobel
    hanya diambil sekali."""
    dipakai = {b["resi"] or b["pesanan"] for bs in layak.values() for b in bs}
    per_kelompok: dict[str, list[dict]] = defaultdict(list)
    for b in sorted(baris, key=lambda b: (int(POLA_PICK.match(b["pdf"].name).group(1)), b["halaman"])):
        kunci = b["resi"] or b["pesanan"]
        if kunci in dipakai:
            continue
        dipakai.add(kunci)
        per_kelompok[nama_kelompok(b["pdf"])].append(b)
    return dict(per_kelompok)


def nama_kelompok(pdf: Path) -> str:
    """"PICK-000162177_1QTY-REGULER-2A_2026-...pdf" -> "1QTY-REGULER-2A"."""
    bagian = pdf.stem.split("_")
    return bagian[1] if len(bagian) > 1 else "LAINNYA"


def tulis_pdf(folder: Path, sku: str, baris: list[dict], awalan: str = "SPESIAL-SATUAN",
              rak: str | None = None) -> Path:
    """`rak`: kelompok rak dominan, disisipkan di nama file (`SPESIAL-SATUAN_2A_<SKU>_3resi.pdf`) supaya
    urutan nama = urutan cetak (rak -> SKU)."""
    w = PdfWriter()
    sumber: dict[Path, PdfReader] = {}
    for b in baris:
        rd = sumber.setdefault(b["pdf"], PdfReader(str(b["pdf"])))
        w.add_page(rd.pages[b["halaman"]])
    nama = re.sub(r'[\\/:*?"<>|\s]+', "_", sku)
    tujuan = folder / (f"{awalan}_{rak}_{nama}_{len(baris)}resi.pdf" if rak else f"{awalan}_{nama}_{len(baris)}resi.pdf")
    with open(tujuan, "wb") as f:
        w.write(f)
    return tujuan


def _kode_kelompok(kelompok: str) -> str:
    return kelompok.replace("1QTY-REGULER-", "")


def rak_dominan(baris: list[dict]) -> str:
    """Kelompok rak (2A/3A/1B/2B/3B/LAINNYA) tempat paling banyak halaman SKU itu berasal."""
    hitung = Counter(_kode_kelompok(nama_kelompok(b["pdf"])) for b in baris)
    return sorted(hitung.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def urutan_spesial(layak: dict[str, list[dict]]) -> list[tuple[str, list[dict]]]:
    """SKU spesial urut cetak: kelompok rak dulu (1B, 2A, 2B, 3A, 3B, LAINNYA = urutan lantai), lalu SKU -
    seperti spesial biasa yang mengikuti urutan fisik rak, bukan abjad SKU saja."""
    return sorted(layak.items(), key=lambda kv: (rak_dominan(kv[1]), kv[0]))


def nama_sesi(pdfs: list[Path]) -> str:
    """Sesi yang benar-benar dipakai, mis. "1-2-3" (dari nama folder sesi PDF)."""
    kode = {pola_sesi.kode_sesi(f.parent.parent.name) or f.parent.parent.name for f in pdfs}
    return "-".join(sorted(kode, key=lambda n: (pola_sesi.POLA_KODE.match(n) is None, pola_sesi.urutan_kode(n), n)))


def tulis_excel(folder: Path, layak: dict[str, list[dict]], sesi: str) -> Path:
    """detail-resi-spesial-satuan-<sesi>.xlsx: FORMAT SAMA PERSIS dengan detail-resi-spesial.xlsx
    (proses_label.catat_detail_spesial) - satu sheet "Detail", kolom KOLOM_DETAIL_SPESIAL
    (No Picklist, SKU, No Pesanan, No Resi), lebar kolom sama, tanpa kolom/sheet tambahan.
    No Picklist = picklist satuan asal resi itu; baris terkelompok per SKU."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Detail"
    ws.append(list(proses_label.KOLOM_DETAIL_SPESIAL))
    for kol, lebar in zip("ABCD", (18, 16, 22, 18)):
        ws.column_dimensions[kol].width = lebar
    for sku, baris in urutan_spesial(layak):
        for b in baris:
            nilai = {"No Picklist": POLA_PICK_PENUH.match(b["pdf"].name).group(1), "SKU": sku,
                     "No Pesanan": b["pesanan"], "No Resi": b["resi"]}
            ws.append([nilai[kol] for kol in proses_label.KOLOM_DETAIL_SPESIAL])
    tujuan = folder / f"detail-resi-spesial-satuan-{sesi}.xlsx"
    wb.save(tujuan)
    return tujuan


PENANDA_JSON = "##HASIL## "      # baris stdout berisi ringkasan JSON (dibaca server_ui.py)


def tanda_pdf(pdfs: list[Path], folder_tanggal: Path) -> list[list]:
    """Tanda tangan daftar PDF (path relatif + ukuran) - penentu cache analisis masih berlaku."""
    return [[f.relative_to(folder_tanggal).as_posix(), f.stat().st_size] for f in pdfs]


def baca_cache(cache: Path | None, folder_tanggal: Path, pdfs: list[Path]) -> tuple[list[dict], int] | None:
    """Baris hasil pemetaan dari cache analisis kalau tanggal & daftar PDF-nya sama persis."""
    if not cache or not cache.is_file():
        return None
    try:
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("folder") != str(folder_tanggal) or d.get("tanda") != tanda_pdf(pdfs, folder_tanggal):
            return None
        if not 0 <= time.time() - float(d.get("dibuat", 0)) <= UMUR_CACHE_MAKS_S:
            return None   # kedaluwarsa (atau tanpa cap waktu): pesanan bisa sudah batal
        if any("boleh_spesial" not in b for b in d["baris"]):
            return None   # cache dari versi lama (belum menyimpan syarat bundle/multi-item/qty)
        return [{**b, "pdf": folder_tanggal / b["pdf"]} for b in d["baris"]], int(d["tak_cocok"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def simpan_cache(cache: Path, folder_tanggal: Path, pdfs: list[Path], semua: list[dict], tak_cocok: int) -> None:
    cache.parent.mkdir(parents=True, exist_ok=True)
    sementara = cache.with_name(cache.name + ".tmp")
    sementara.write_text(json.dumps({
        "folder": str(folder_tanggal), "tanda": tanda_pdf(pdfs, folder_tanggal), "tak_cocok": tak_cocok,
        "dibuat": time.time(),
        "baris": [{**b, "pdf": b["pdf"].relative_to(folder_tanggal).as_posix()} for b in semua]},
        ensure_ascii=False), encoding="utf-8")
    sementara.replace(cache)


def kumpulkan(k, folder_tanggal: Path, pdfs: list[Path], cache: Path | None = None) -> tuple[list[dict], int]:
    """(baris halaman->SKU/resi, jumlah halaman tak cocok) dari semua `pdfs`; dari cache analisis
    bila masih berlaku (tanpa memanggil Jubelio), kalau tidak dari API lalu disimpan ke cache."""
    dari_cache = baca_cache(cache, folder_tanggal, pdfs)
    if dari_cache:
        log.info("Memakai hasil analisis sebelumnya (%d PDF) - Jubelio tidak dipanggil", len(pdfs))
        return dari_cache
    semua, tak_cocok_total = [], 0
    for pdf in pdfs:
        nomor = int(POLA_PICK.match(pdf.name).group(1))
        baris, tak_cocok = petakan_halaman(pdf, item_picklist(k, nomor))
        tak_cocok_total += tak_cocok
        semua += baris
        log.info("%s: %d halaman dipetakan%s", pdf.name, len(baris),
                 f", {tak_cocok} halaman TIDAK cocok" if tak_cocok else "")
    if cache:
        try:
            simpan_cache(cache, folder_tanggal, pdfs, semua, tak_cocok_total)
        except OSError as e:
            log.warning("Cache analisis tidak tersimpan: %s", e)
    return semua, tak_cocok_total


def _sidik(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def nomor_terlompat_satuan(pdfs: list[Path]) -> list[int]:
    """Nomor PICK yang terlompat DI ANTARA picklist satuan satu sesi (kelompok 2A, 3A, 1B, ... dibuat
    berurutan) dan tidak ada di folder sesi itu - tanda ada picklist satuan yang gagal/terhenti, jadi
    pesanannya tidak ikut terhitung. Hanya peringatan (hasil pilah tetap sah)."""
    per_sesi: dict[Path, list[int]] = defaultdict(list)
    for f in pdfs:
        per_sesi[f.parent.parent].append(int(POLA_PICK.match(f.name).group(1)))
    hilang: set[int] = set()
    for folder_sesi, nomor in per_sesi.items():
        ada = {int(m.group(1)) for f in folder_sesi.rglob("*.pdf") if (m := POLA_PICK.match(f.name))}
        hilang |= set(range(min(nomor), max(nomor) + 1)) - ada
    return sorted(hilang)


def bersihkan_hasil_lama(folder: Path) -> dict[Path, str]:
    """Hapus file keluaran program ini yang ada di `folder` (pilah ulang dengan pilihan lain
    tidak boleh menyisakan PDF lama). Hanya pola nama buatan sendiri. Mengembalikan {path: sidik
    isi} file yang dihapus, untuk membandingkan dengan hasil baru (lihat selesai_tulis())."""
    lama: dict[Path, str] = {}
    for pola in ("SPESIAL-SATUAN_*.pdf", "SISA-SATUAN_*.pdf", "detail-resi-spesial-satuan-*.xlsx"):
        for f in folder.glob(pola):
            lama[f] = _sidik(f)
            f.unlink()
    return lama


def selesai_tulis(lama: dict[Path, str], baru: list[Path]) -> int:
    """Status "sudah tercetak" file hasil yang ISINYA berubah atau yang hilang tidak boleh
    menempel (nama sama, isi beda = label lain); file dengan isi identik tetap tercetak
    (PDF dibuat deterministik). Mengembalikan jumlah catatan yang dilupakan."""
    import print_spesial
    sama = {f for f in baru if f in lama and f.suffix == ".pdf" and _sidik(f) == lama[f]}
    return print_spesial.lupakan_sudah_dicetak([f for f in lama if f not in sama])


def pilah(k, folder_tanggal: Path, min_resi: int = MIN_RESI, buat_pdf: bool = True,
          sesi: list[str] | None = None, tulis: bool = True, cache: Path | None = None,
          abaikan_jendela: bool = False) -> dict:
    """`tulis=False`: hanya analisis (tidak ada folder/file dibuat). Sesi yang tidak memenuhi
    syarat (satuan gabungan, diproses 07.00-12.00 / 20.00-07.00) ditolak: SesiTidakValid."""
    pdfs, sesi_ok = pdf_terpilih(folder_tanggal, sesi, abaikan_jendela)
    sesi = sesi or sesi_ok
    if not pdfs:
        raise SesiTidakValid(f"Tidak ada PDF satuan gabungan di {folder_tanggal} untuk sesi {'-'.join(sesi)}")
    semua, tak_cocok_total = kumpulkan(k, folder_tanggal, pdfs, cache)
    layak, sisa = kelompokkan(semua, min_resi)
    label_sesi = "-".join(sesi)
    hasil = {"pdf": len(pdfs), "halaman": len(semua), "tak_cocok": tak_cocok_total,
             "kurir_lain": sum(1 for b in semua if not kurir_diizinkan(b.get("kurir"))),
             "layak": layak, "sisa_sku": len(sisa), "file": [], "sesi": label_sesi}
    sisa_halaman = kelompok_sisa(semua, layak)
    hasil["sisa"] = sisa_halaman
    hasil["terlompat"] = nomor_terlompat_satuan(pdfs)
    hasil["bentrok"] = kurasi_satuan.bentrok(pdfs, label_sesi)
    if not tulis:
        return hasil
    if hasil["bentrok"] and buat_pdf:   # mode hanya-Excel tidak menandai dikurasi, jadi tidak bentrok
        raise KurasiBentrok(pesan_bentrok(hasil["bentrok"]))
    # Hasil pilah sebelumnya (sesi yang sama) selalu dibersihkan - termasuk folder yang kali ini tidak
    # terisi lagi (mis. ambang berubah sehingga tak ada sisa), supaya tidak tertinggal PDF usang.
    folder = kurasi_satuan.folder_hasil(folder_tanggal, NAMA_FOLDER_HASIL, label_sesi)
    folder_sisa = kurasi_satuan.folder_hasil(folder_tanggal, NAMA_FOLDER_SISA, label_sesi)
    lama: dict[Path, str] = {}
    for f in (folder, folder_sisa):
        if f.is_dir():
            lama.update(bersihkan_hasil_lama(f))
    if layak:
        folder.mkdir(parents=True, exist_ok=True)
        hasil["folder"] = folder
        hasil["file"].append(tulis_excel(folder, layak, label_sesi))
        if buat_pdf:
            for sku, baris in urutan_spesial(layak):
                hasil["file"].append(tulis_pdf(folder, sku, baris, rak=rak_dominan(baris)))
    if sisa_halaman and buat_pdf:
        folder_sisa.mkdir(parents=True, exist_ok=True)
        hasil["folder_sisa"] = folder_sisa
        for kelompok, baris in sorted(sisa_halaman.items()):
            hasil["file"].append(tulis_pdf(folder_sisa, kelompok, baris, "SISA-SATUAN"))
    for f in (folder, folder_sisa):   # folder yang kini kosong (tidak ada yang ditulis) dibuang
        if f.is_dir() and not any(f.iterdir()):
            f.rmdir()
    if lama:
        selesai_tulis(lama, hasil["file"])
    if buat_pdf and (layak or sisa_halaman):
        kurasi_satuan.catat(pdfs, label_sesi)   # PDF satuan asal ditandai "dikurasi" (jangan dicetak lagi)
        hasil["dikurasi"] = len(pdfs)
    elif not buat_pdf:
        kurasi_satuan.hapus(pdfs, label_sesi)   # hanya Excel: tak ada PDF pengganti -> asal tidak dikurasi
    return hasil


def ringkasan_json(h: dict) -> dict:
    """Ringkasan hasil untuk UI: SKU spesial (jumlah, kelompok rak dominan, jumlah per sesi) dan
    jumlah resi sisa per kelompok rak."""
    spesial = []
    for sku, baris in urutan_spesial(h["layak"]):   # urutan = urutan cetak (rak -> SKU)
        per_sesi = Counter(b["pdf"].parent.parent.name for b in baris)
        spesial.append({"sku": sku, "n": len(baris), "rak": rak_dominan(baris), "sesi": dict(per_sesi)})
    return {"sesi": h["sesi"], "pdf": h["pdf"], "halaman": h["halaman"], "tak_cocok": h["tak_cocok"],
            "kurir_lain": h["kurir_lain"],
            "terlompat": [f"PICK-{n:09d}" for n in h["terlompat"]],
            "bentrok": {s: len(n) for s, n in h["bentrok"].items()},
            "tanpa_pdf": not any(f.suffix == ".pdf" for f in h["file"]) and bool(h["file"]),
            "spesial": spesial, "sisa": {_kode_kelompok(k): len(b) for k, b in h["sisa"].items()},
            "folder": [f.name for f in (h.get("folder"), h.get("folder_sisa")) if f],
            "file": len(h["file"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tanggal", help="YYYY-MM-DD (folder label-pengiriman/<tanggal>); default hari ini")
    ap.add_argument("--sesi", metavar="1-2-3", help="sesi yang dipilah, mis. 1-2-3 atau 1,3 (default semua)")
    ap.add_argument("--folder", type=Path, help="folder tanggal langsung (menggantikan --tanggal)")
    ap.add_argument("--min-resi", type=int, default=MIN_RESI)
    ap.add_argument("--tanpa-pdf", action="store_true", help="hanya Excel, tanpa PDF per SKU")
    ap.add_argument("--analisis-saja", action="store_true", help="hitung & tampilkan saja, tidak membuat file/folder")
    ap.add_argument("--cache", type=Path, metavar="FILE",
                    help="pakai/simpan hasil analisis di FILE (dipakai UI: 'Buat folder' tidak memanggil Jubelio lagi)")
    ap.add_argument("--abaikan-jendela", action="store_true",
                    help="UJI SAJA: lewati syarat jam proses sesi (satuan gabungan tetap wajib)")
    ap.add_argument("--json", action="store_true", help="cetak ringkasan JSON (untuk server_ui.py)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import main as modul_main
    modul_main.muat_env(ROOT / ".env")
    folder = args.folder or FOLDER_LABEL / (args.tanggal or date.today().isoformat())
    if not folder.is_dir():
        print(f"Folder tidak ada: {folder}")
        return 1
    try:
        sesi = parse_sesi(args.sesi)
    except ValueError as e:
        print(e)
        return 1
    try:
        pdfs, sesi = pdf_terpilih(folder, sesi, args.abaikan_jendela)
    except SesiTidakValid as e:
        print(f"DITOLAK: {e}")
        return 1
    # login hanya kalau cache analisis tidak bisa dipakai
    k = None if baca_cache(args.cache, folder, pdfs) else proses_label.Klien(modul_main.login(log))
    try:
        h = pilah(k, folder, args.min_resi, not args.tanpa_pdf, sesi, not args.analisis_saja, args.cache,
                  args.abaikan_jendela)
    except KurasiBentrok as e:
        print(f"DITOLAK: {e}")
        return 1
    print(f"\n{h['pdf']} PDF satuan, {h['halaman']} halaman dipetakan ke SKU"
          f" ({h['tak_cocok']} halaman tak cocok)")
    print(f"SKU yang bisa dikelompokkan (>= {args.min_resi} resi): {len(h['layak'])} SKU, "
          f"{sum(len(b) for b in h['layak'].values())} resi; SKU lain di bawah ambang: {h['sisa_sku']}")
    for sku, baris in sorted(h["layak"].items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"  {sku}: {len(baris)} resi")
    if h["kurir_lain"]:
        print(f"{h['kurir_lain']} resi berkurir selain J&T/SPX tidak dihitung spesial")
    if h["terlompat"]:
        print("PERINGATAN: nomor PICK terlompat di antara picklist satuan (picklist gagal/terhenti? pesanannya "
              "tidak ikut terhitung): " + ", ".join(f"PICK-{n:09d}" for n in h["terlompat"]))
    if h["bentrok"] and args.analisis_saja:
        print("PERINGATAN: " + pesan_bentrok(h["bentrok"]) + " (tidak bisa dibuat sebelum dibereskan)")
    print("Sisa satuan per kelompok: " + (", ".join(
        f"{_kode_kelompok(k)}={len(b)}" for k, b in sorted(h["sisa"].items())) or "-"))
    for f in h["file"]:
        print("Dibuat:", f)
    if args.json:
        print(PENANDA_JSON + json.dumps(ringkasan_json(h), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
