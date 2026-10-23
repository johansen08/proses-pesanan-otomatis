"""Server lokal untuk UI desktop (data/prototype-desktop/index.html) - menu CETAK.

Hanya melayani 127.0.0.1 (komputer ini saja). UI membaca daftar sesi/file label sungguhan
dari folder label-pengiriman dan mencetak file pilihan lewat
`print_spesial.py --file-dari ... --printer ... --tanpa-konfirmasi` (proses terpisah, jadi
semua aturan cetak - dedupe sudah_dicetak, pantau printer, daftar gagal - sama persis dengan
CLI). Program ini TIDAK mencetak sendiri.

Jalankan:  .venv\\Scripts\\python src\\server_ui.py [--port 8765] [--buka]

API (JSON):
  GET  /api/sesi     sesi label 3 hari terakhir -> jenis -> file PDF (+ status sudah dicetak)
  GET  /api/sebagian file terputus di tengah cetak (halaman tercetak/total)
  POST /api/sebagian/lanjut {"item": [{"rel": "...pdf", "mulai": N}], "printer": "..."} -> lanjut cetak
                     dari halaman N saja (`print_spesial.py --lanjut-sebagian --mulai-dari`)
  GET  /api/printer  nama printer yang terhubung
  POST /api/cetak    {"files": ["2026-10-07/1/SPESIAL/PICK-....pdf", ...], "printer": "...",
                      "ulang": false} -> {"job": id}; satu job sekaligus (409 kalau masih jalan)
  GET  /api/job?printer=NAMA   status & baris log job printer itu (tanpa parameter: job terakhir)
  GET  /api/jobs               ringkasan job semua printer
  (printer BERBEDA boleh mencetak bersamaan; printer yang sama antre -> 409)
  GET  /api/harian/info          jam cocok per TIPE, peringatan hari ini, apakah ada job berjalan
  POST /api/harian/jalankan      {"langkah": [nama...], "judul": "TIPE 1"} -> {"job": id}
                                 (judul "EVENT - TIPE 1".."EVENT - MALAM"/"EVENT - KUSTOM" = menu Event)
                                 (SUNGGUHAN: lihat jalankan_harian.py; 409 kalau masih berjalan)
  GET  /api/harian/job?dari=N    status per langkah + baris log ke-N dst
  POST /api/harian/hentikan      matikan langkah berjalan & batalkan sisanya
  GET  /api/terhenti             picklist terhenti (mis. gagal unduh PDF) + status job download ulang
  POST /api/terhenti/jalankan    {"picklist": ["PICK-...", ...]} -> `main.py --lanjut` berurutan
                                 (SUNGGUHAN; 409 kalau download ulang/proses harian masih berjalan)
  GET  /api/pilah/sesi           sesi 3 hari terakhir yang punya PDF SATUAN (jumlah picklist & label, `layak`:
                                 hanya satuan gabungan J&T + SPX dari sesi yang diproses 07.00-12.00 / 20.00-07.00 boleh dipilah)
  POST /api/pilah/analisis       {"tanggal": "YYYY-MM-DD", "sesi": ["1","2"], "min_resi": 3} -> {"job": id}
                                 (`pilah_satuan.py --analisis-saja`: READ-ONLY ke Jubelio, tidak menulis file;
                                 "tanpa_pdf": true = hanya Excel, label fisik sudah dicetak)
  POST /api/pilah/buat           sama, tapi membuat folder SPESIAL-SATUAN-<sesi> & SISA-SATUAN-<sesi>
                                 (memakai cache hasil analisis maks 15 menit -> Jubelio tidak dipanggil lagi; 409 kalau
                                 pilah/proses harian/download ulang masih berjalan; 400 kalau sebagian PDF sudah
                                 dikurasi ke folder hasil lain)
  GET  /api/pilah/job            status, baris log, kemajuan, dan "hasil" (ringkasan JSON) job pilah terakhir
  GET  /api/pulih/sesi           sesi bernomor biasa 3 hari terakhir + status tiap picklist (data lokal) + nama folder
                                 pemulihan berikutnya (`berikut`)
  POST /api/pulih/cek            {"tanggal": "YYYY-MM-DD", "sesi": "10"} -> `main.py --pulihkan-sesi` MODE UJI (hanya membaca Jubelio)
  POST /api/pulih/jalankan       sama, SUNGGUHAN (`--jalankan`): ulang resi/PDF/Excel SELURUH picklist sesi ke folder
                                 baru N-PEMULIHAN (409 kalau pemulihan/proses harian/download ulang/pilah berjalan)
  GET  /api/pulih/job            status, kemajuan, `hasil` per picklist, `folder` tujuan, baris log
  GET  /api/operator             {"aktif", "daftar", "terkunci"} (terkunci = proses harian/download ulang jalan)
  POST /api/operator             {"aksi": "tambah"|"aktif", "nama": "..."} (ganti operator aktif -> 409
                                 kalau proses harian/download ulang berjalan; lihat operator_aktif.py)
Jenis yang ditampilkan (JENIS_UI): spesial/satuan/kombinasi per kurir (J&T, SPX, SPX Hemat, SPX Hemat Pagi)
+ sisanya tanpa kurir, gtl-sicepat, lazada (dicetak skala 68% oleh print_spesial.cetak()). PDF lain
(event, JNE-LEX, dst) tampil per nama subfolder.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jalankan_harian as jh
import kurasi_satuan
import nama_sesi
import operator_aktif as oa
import print_spesial as ps

ROOT = ps.ROOT
HTML_UI = ROOT / "data" / "prototype-desktop" / "index.html"
HARI_UI = 3                      # hari ini, kemarin, 2 hari lalu
# Urutan penting: PDF dimiliki kelompok PERTAMA yang cocok (`terpakai` di data_sesi), jadi varian
# per kurir (subfolder JNT_/SPX_/SPXHEMAT_...) harus sebelum kelompok gabungan ("Spesial" dst),
# yang tinggal memuat sisanya (subfolder tanpa awalan kurir).
JENIS_UI = [(f"{dasar} {kurir}", f"{kode}-{kk}")
            for dasar, kode in (("Spesial", "spesial"), ("Satuan", "satuan"), ("Kombinasi", "kombinasi"))
            for kurir, kk in (("J&T", "jnt"), ("J&T NDD", "jnt-ndd"), ("SPX", "spx"),
                              ("SPX Hemat", "spx-hemat"), ("SPX Hemat Pagi", "spx-hemat-pagi"))]
JENIS_UI += [("Spesial", "spesial"), ("Satuan", "satuan"), ("Kombinasi", "kombinasi"),
             ("GTL-SiCepat Spesial", "gtl-spesial"), ("GTL-SiCepat", "gtl-sicepat"), ("Urgent Lazada · skala 68%", "lazada"),
             ("Shopee Pagi Spesial", "spx-pagi-spesial"), ("Shopee Pagi", "spx-pagi"), ("J&T Resi Siang", "jnt-siang"), ("SPX Standard", "spx-standard")]
BARIS_LOG_MAKS = 400
HASIL_PILAH = ("SPESIAL-SATUAN", "SISA-SATUAN")   # awalan folder hasil pilah_satuan.py

_jobs: dict[str, dict] = {}      # kunci = nama printer: printer BERBEDA boleh mencetak bersamaan
_terakhir: str | None = None
_kunci = threading.Lock()


def _rel(f: Path) -> str:
    return f.resolve().relative_to(ps.FOLDER_LABEL.resolve()).as_posix()


def _info_file(f: Path, sudah: set, waktu: list[float], kurasi: dict | None = None) -> dict:
    """Entri file PDF untuk UI; mtime-nya ditambahkan ke `waktu` (penentu jam sesi). `kurasi`
    (kurasi_satuan.baca()): kunci "kurasi" (label sesi hasil pilah) hanya ada kalau PDF satuan
    ini sudah dikurasi - halamannya sudah ada di SPESIAL-SATUAN/SISA-SATUAN, jangan dicetak lagi."""
    st = f.stat()
    waktu.append(st.st_mtime)
    info = {"f": f.name, "rel": _rel(f), "kb": max(1, round(st.st_size / 1024)),
            "done": str(f.resolve()) in sudah}
    sesi = (kurasi or {}).get(str(f.resolve()))
    if sesi:
        info["kurasi"] = sesi
    return info


def data_sesi(hari_ini: date | None = None) -> dict:
    """Sesi label HARI_UI hari terakhir (terlama -> terbaru di dalam tiap hari), tiap jenis
    berisi file PDF urut nomor PICK; PDF di luar jenis itu ikut per nama subfolder. Kosong tidak dimasukkan."""
    hari_ini = hari_ini or date.today()
    sudah = ps.baca_sudah_dicetak()
    kurasi = kurasi_satuan.baca()
    per_tanggal: dict[str, list[dict]] = {}
    for folder in ps.daftar_folder_sesi(ps.FOLDER_LABEL, HARI_UI, hari_ini):
        jenis_out, terpakai, waktu = [], set(), []
        for nama, kode in JENIS_UI:
            files = []
            for f in ps.daftar_label(folder, kode):
                if f in terpakai:
                    continue
                terpakai.add(f)
                files.append(_info_file(f, sudah, waktu, kurasi))
            if files:
                jenis_out.append({"nama": nama, "files": files})
        # Semua PDF lain di sesi (subfolder JNT_SIANG/SPX_PAGI/URGENT/event/dst atau langsung di
        # folder sesi) ikut tampil per nama subfolder, supaya tidak ada PDF yang tidak bisa dicetak.
        sisa: dict[str, list[Path]] = {}
        for f in sorted(folder.rglob("*.pdf"), key=lambda p: (p.parent.name, p.name)):
            if f in terpakai or not f.is_file():
                continue
            rel_dir = f.parent.relative_to(folder).as_posix()
            sisa.setdefault(rel_dir if rel_dir != "." else "(folder sesi)", []).append(f)
        for nama, daftar in sisa.items():
            files = []
            for f in daftar:
                files.append(_info_file(f, sudah, waktu, kurasi))
            jenis_out.append({"nama": nama, "files": files})
        if not jenis_out:
            continue   # sesi tanpa label jenis yang ditampilkan (mis. baru dibuat/kosong)
        per_tanggal.setdefault(folder.parent.name, []).append({
            "no": nama_sesi.nomor_sesi(folder.name), "id": f"{folder.parent.name}/{folder.name}",
            **({} if folder.name.isdigit() else {"judul": folder.name}),
            "jam": datetime.fromtimestamp(min(waktu)).strftime("%H.%M") if waktu else "--.--",
            "jenis": jenis_out})
    for tanggal in sorted(per_tanggal):   # folder hasil pilah (pilah_satuan.py) ikut bisa dicetak
        for d in [x for awalan in HASIL_PILAH for x in sorted((ps.FOLDER_LABEL / tanggal).glob(f"{awalan}-*"))]:
            if not d.is_dir():
                continue
            waktu: list[float] = []
            files = [_info_file(f, sudah, waktu, kurasi) for f in sorted(d.glob("*.pdf"))]
            if files:
                per_tanggal[tanggal].append({
                    "no": 0, "id": f"{tanggal}/{d.name}", "judul": d.name,
                    "jam": datetime.fromtimestamp(min(waktu)).strftime("%H.%M"),
                    "jenis": [{"nama": "Spesial hasil pilah" if d.name.startswith(HASIL_PILAH[0]) else
                               "Sisa satuan hasil pilah", "files": files}]})
    return {"hari_ini": hari_ini.isoformat(),
            "hari": [{"tanggal": t, "sesi": per_tanggal[t]} for t in sorted(per_tanggal)]}


PRINTER_VIRTUAL = ("onenote", "print to pdf", "xps", "fax", "save as pdf", "simpan sebagai pdf")


def printer_virtual(nama: str) -> bool:
    """Printer bawaan Windows yang bukan printer label (tidak ditawarkan di cetak banyak printer)."""
    return any(k in nama.lower() for k in PRINTER_VIRTUAL)


TTL_PRINTER_S = 60
_cache_printer: tuple[float, list[str]] | None = None   # (waktu monotonic, daftar nama)
_kunci_printer = threading.Lock()


def daftar_printer_cache() -> list[str]:
    """Daftar printer dengan cache TTL_PRINTER_S detik. Get-Printer memulai proses PowerShell
    (~3 detik, jauh lebih lama saat PC sibuk menjalankan proses harian/event), padahal printer
    jarang berubah - tanpa cache tiap tab baru menunggu selama itu. Kegagalan tidak di-cache.
    Kunci menyerialkan panggilan: tab yang dibuka bersamaan menunggu satu PowerShell yang sama."""
    global _cache_printer
    with _kunci_printer:
        sekarang = time.monotonic()
        if _cache_printer and sekarang - _cache_printer[0] < TTL_PRINTER_S:
            return list(_cache_printer[1])
        daftar = ps.daftar_printer()
        _cache_printer = (time.monotonic(), daftar)
        return list(daftar)


def _hangatkan_printer() -> None:
    try:
        daftar_printer_cache()
    except Exception:   # hangat-hangatan saja; kegagalan muncul lagi (dengan pesan) saat UI memintanya
        pass


def info_sebagian() -> list[dict]:
    """File yang terputus di tengah cetak (logs/cetak_sebagian.json) dan masih ada di disk."""
    hasil = []
    for p, d in ps.baca_sebagian().items():
        f = Path(p)
        try:
            rel = _rel(f)
        except ValueError:
            continue
        if f.exists():
            hasil.append({"f": f.name, "rel": rel, "tercetak": int(d["halaman_tercetak"]),
                          "total": int(d["total"]), "printer": d["printer"], "waktu": d["waktu"]})
    return hasil


def mulai_lanjut_sebagian(item: list[dict], printer: str) -> str:
    """Lanjutkan file terputus dari halaman pilihan UI: [{"rel": ..., "mulai": N}, ...]."""
    tercatat = {x["rel"]: x for x in info_sebagian()}
    mulai_dari = {}
    for it in item:
        rel, mulai = it.get("rel"), it.get("mulai")
        if rel not in tercatat:
            raise ps.CetakError(f"Bukan file terputus: {rel}")
        if not isinstance(mulai, int) or not 1 <= mulai <= tercatat[rel]["total"]:
            raise ps.CetakError(f"Halaman mulai harus 1-{tercatat[rel]['total']}: {rel}")
        mulai_dari[rel] = mulai
    if not mulai_dari:
        raise ps.CetakError("Tidak ada file yang dipilih")
    return mulai_cetak(list(mulai_dari), printer, mulai_dari=mulai_dari)


def mulai_cetak(files: list[str], printer: str, ulang: bool = False,
                mulai_dari: dict[str, int] | None = None) -> str:
    """Validasi pilihan lalu jalankan print_spesial.py --file-dari di proses terpisah.
    Melempar ps.CetakError (pilihan tidak valid) atau RuntimeError (printer itu masih mencetak /
    file yang sama sedang dicetak printer lain). Printer BERBEDA boleh jalan bersamaan."""
    global _terakhir
    ps.pilih_file_spesifik(files)            # tolak lebih awal: di luar folder, bukan PDF, hilang
    if not printer:
        raise ps.CetakError("Printer belum dipilih")
    with _kunci:
        j = _jobs.get(printer)
        if j and j["status"] == "jalan":
            raise RuntimeError(f'Printer "{printer}" masih mencetak')
        baru = {str(f) for f in ps.pilih_file_spesifik(files)}
        for lain, jl in _jobs.items():
            if jl["status"] == "jalan" and baru & jl["files"]:
                raise RuntimeError(f'Ada file pilihan yang sedang dicetak printer "{lain}"')
        ps.FOLDER_LOG.mkdir(exist_ok=True)
        daftar = ps.FOLDER_LOG / f"pilihan_ui_{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:6]}.txt"
        daftar.write_text("\n".join(files) + "\n", encoding="utf-8")
        perintah = [sys.executable, str(Path(__file__).with_name("print_spesial.py")),
                    "--file-dari", str(daftar), "--printer", printer, "--tanpa-konfirmasi"]
        if ulang:
            perintah.append("--cetak-ulang-semua")
        if mulai_dari:
            perintah = [sys.executable, str(Path(__file__).with_name("print_spesial.py")),
                        "--lanjut-sebagian", "--printer", printer, "--tanpa-konfirmasi"]
            for rel, hal in mulai_dari.items():
                perintah += ["--mulai-dari", f"{ps.FOLDER_LABEL.resolve() / rel}={hal}"]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        proses = subprocess.Popen(
            perintah, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=env, cwd=str(ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        job = {"id": uuid.uuid4().hex[:8], "printer": printer, "status": "jalan", "kode": None,
               "lines": [], "total": len(files), "files": baru}
        _jobs[printer] = job
        _terakhir = printer
        threading.Thread(target=_baca_keluaran, args=(proses, job), daemon=True).start()
        return job["id"]


def mulai_cetak_banyak(files: list[str], printers: list[str], ulang: bool = False) -> dict[str, dict]:
    """Cetak pilihan di BEBERAPA printer sekaligus: file dibagi jadi blok berurutan yang seimbang
    menurut jumlah halaman (ps.bagi_ke_printer), tiap printer = satu job biasa (mulai_cetak) di
    proses terpisah. Semua printer harus bebas SEBELUM satu pun dimulai (tidak ada pembagian
    setengah jalan). Return {printer: {"job": id, "file": jumlah file}} (urut printer pilihan,
    printer berlebih - file lebih sedikit dari printer - tidak dipakai)."""
    if not printers or not all(isinstance(p, str) and p.strip() for p in printers):
        raise ps.CetakError("Printer belum dipilih")
    if len(set(printers)) != len(printers):
        raise ps.CetakError("Printer dipilih dobel")
    daftar = ps.pilih_file_spesifik(files)
    with _kunci:
        sibuk = [p for p in printers if (_jobs.get(p) or {}).get("status") == "jalan"]
    if sibuk:
        raise RuntimeError("Printer masih mencetak: " + ", ".join(sibuk))
    bobot = {f: (_jumlah_halaman(f) or max(1, f.stat().st_size // 5000)) for f in daftar}
    blok = ps.bagi_ke_printer(daftar, len(printers), bobot)
    hasil: dict[str, dict] = {}
    try:
        for printer, bagian in zip(printers, blok):
            job = mulai_cetak([_rel(f) for f in bagian], printer, ulang)
            hasil[printer] = {"job": job, "file": len(bagian)}
    except (ps.CetakError, RuntimeError):
        if not hasil:
            raise
        # sebagian printer sudah jalan; sisanya gagal mulai -> beritahu, jangan sembunyikan
        raise RuntimeError("Sebagian printer sudah mencetak (" + ", ".join(hasil) + "), tapi "
                           + printer + " gagal dimulai - cetak file bagiannya lewat Cetak biasa") from None
    return hasil


_lanjut: dict | None = None      # job "Download ulang" picklist terhenti (satu sekaligus)


def info_terhenti() -> dict:
    """Picklist yang masih terhenti (gagal unduh PDF dsb) + keadaan job download ulang."""
    import peringatan_gagal
    peringatan_gagal.atur_folder(jh.FOLDER_LOG)
    j = _lanjut
    return {"daftar": peringatan_gagal.daftar_terhenti(),
            "job": None if not j else {"status": j["status"], "lines": j["lines"],
                                       "total": j["total"], "maju": j["maju"],
                                       "gagal": j["gagal"]}}


def mulai_lanjut(picklist: list[str]) -> None:
    """Jalankan `main.py --lanjut ... --jalankan` BERURUTAN untuk picklist terhenti yang dipilih
    (proses terpisah per picklist, SUNGGUHAN: mengubah data di Jubelio). Melempar RuntimeError
    kalau masih ada job lanjut / proses harian berjalan, ValueError kalau pilihan tidak valid."""
    global _lanjut
    import peringatan_gagal
    peringatan_gagal.atur_folder(jh.FOLDER_LOG)
    ada = {d["picklist"]: d for d in peringatan_gagal.daftar_terhenti()}
    if not isinstance(picklist, list) or not picklist or not all(isinstance(x, str) and x in ada for x in picklist):
        raise ValueError("Pilihan tidak ada di daftar picklist terhenti")
    pilih = [ada[p] for p in dict.fromkeys(picklist)]
    with _kunci:
        if _lanjut and _lanjut["status"] == "jalan":
            raise RuntimeError("Download ulang sebelumnya masih berjalan")
        if jh.keadaan()["status"] == "jalan":
            raise RuntimeError("Masih ada proses harian yang berjalan")
        _lanjut = {"status": "jalan", "lines": [], "total": len(pilih), "maju": 0, "gagal": 0}
        threading.Thread(target=_kerjakan_lanjut, args=(_lanjut, pilih), daemon=True).start()


def _perintah_lanjut(d: dict) -> list[str]:
    import coba_ulang
    return coba_ulang.perintah_lanjut(d)


def _kerjakan_lanjut(job: dict, pilih: list[dict]) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    for i, d in enumerate(pilih, 1):
        job["lines"].append(f"=== {i}/{len(pilih)} {d['picklist']} ({d['nama']}) ===")
        try:
            p = jh._luncurkan(_perintah_lanjut(d), env)
            for baris in p.stdout:
                job["lines"].append(baris.rstrip())
                del job["lines"][:-BARIS_LOG_MAKS]
            kode = p.wait()
        except OSError as e:
            job["lines"].append(f"GAGAL menjalankan: {e}")
            kode = -1
        if kode != 0:
            job["gagal"] += 1
            job["lines"].append(f"GAGAL: {d['picklist']} masih terhenti")
        job["maju"] = i
    job["status"] = "gagal" if job["gagal"] else "selesai"


def info_operator() -> dict:
    """Daftar operator + apakah penggantian operator sedang dikunci (ada proses yang menulis
    PICKLIST.xlsx: satu sesi tidak boleh memuat dua operator)."""
    terkunci = jh.keadaan()["status"] == "jalan" or bool(_lanjut and _lanjut["status"] == "jalan")
    return {**oa.info(), "terkunci": terkunci}


def ubah_operator(aksi, nama) -> dict:
    """Tambah operator / ganti operator aktif. Melempar oa.OperatorError (400) atau RuntimeError (409)."""
    if aksi == "tambah":
        oa.tambah(nama)
    elif aksi == "aktif":
        if info_operator()["terkunci"]:
            raise RuntimeError("Operator tidak bisa diganti saat proses berjalan")
        oa.set_aktif(nama)
    else:
        raise oa.OperatorError("aksi harus 'tambah' atau 'aktif'")
    return info_operator()


# ---------------------------------------------------------------- pilah satuan (pilah_satuan.py)
_pilah: dict | None = None       # job pilah terakhir (satu sekaligus)
_hal_cache: dict[tuple, int] = {}
POLA_TANGGAL = re.compile(r"^\d{4}-\d{2}-\d{2}$")
POLA_LABEL_PILAH = re.compile(r"^\d+P?(?:-\d+P?)*(?:\+\d+P?(?:-\d+P?)*)*$")   # label hasil pilah: "1-2", "1-2+3"


def _jumlah_halaman(f: Path) -> int:
    st = f.stat()
    kunci = (str(f), st.st_mtime_ns, st.st_size)
    if kunci not in _hal_cache:
        from pypdf import PdfReader
        try:
            _hal_cache[kunci] = len(PdfReader(str(f)).pages)
        except Exception:   # PDF rusak: tampil 0 halaman, jangan menjatuhkan daftar
            _hal_cache[kunci] = 0
    return _hal_cache[kunci]


def _pdf_satuan_sesi(folder: Path) -> list[Path]:
    """PDF satuan gabungan (subfolder SATUAN); kalau sesi hanya punya satuan per kurir, PDF itu
    (cuma untuk ditampilkan - sesinya ditandai tidak boleh dipilah)."""
    import pilah_satuan as pl
    gabungan = sorted(pl.pdf_satuan_gabungan(folder))
    return gabungan or [f for f in sorted(folder.glob("*SATUAN/*.pdf")) if pl.POLA_PICK.match(f.name)]


def data_pilah(hari_ini: date | None = None) -> dict:
    """Sesi HARI_UI hari terakhir yang punya PDF SATUAN: nomor, jam, jumlah picklist & label, dan
    `layak` (+ `alasan` kalau tidak): hanya satuan gabungan J&T + SPX dari sesi yang diproses
    07.00-12.00 / 20.00-07.00 yang boleh dipilah (pilah_satuan.periksa_sesi)."""
    import pilah_satuan as pl
    hari_ini = hari_ini or date.today()
    per_tanggal: dict[str, list[dict]] = {}
    for folder in ps.daftar_folder_sesi(ps.FOLDER_LABEL, HARI_UI, hari_ini):
        pdfs = _pdf_satuan_sesi(folder)
        if not pdfs:
            continue
        layak, alasan = pl.periksa_sesi(folder)
        mulai = (pl.waktu_mulai_sesi(pl.sesi_asal(folder)) or pl.waktu_mulai_sesi(folder)
                 or datetime.fromtimestamp(min(f.stat().st_mtime for f in pdfs)))
        per_tanggal.setdefault(folder.parent.name, []).append({
            "no": nama_sesi.nomor_sesi(folder.name), "kode": nama_sesi.kode_sesi(folder.name),
            **({} if folder.name.isdigit() else {"judul": folder.name}), "picklist": len(pdfs), "label": sum(_jumlah_halaman(f) for f in pdfs),
            "jam": mulai.strftime("%H.%M"), "layak": layak, "alasan": alasan})
    return {"hari_ini": hari_ini.isoformat(),
            "hari": [{"tanggal": t, "sesi": per_tanggal[t], "lanjutan": _hasil_bisa_dilanjutkan(ps.FOLDER_LABEL / t)}
                     for t in sorted(per_tanggal)]}


def _hasil_bisa_dilanjutkan(folder_tanggal: Path) -> list[str]:
    """Label hasil pilah (mis. "1-2", "1-2+3") yang SISA-SATUAN-nya masih berisi PDF di tingkat atas - itulah
    yang bisa dilanjutkan dengan sesi baru (pilah lanjutan). Yang sisanya sudah dipindah/tidak ada: tidak."""
    awalan = kurasi_satuan.AWALAN_SISA + "-"
    try:
        return sorted(d.name[len(awalan):] for d in folder_tanggal.iterdir()
                      if d.is_dir() and d.name.startswith(awalan) and any(d.glob("*.pdf")))
    except OSError:
        return []


def info_pilah() -> dict:
    j = _pilah
    if not j:
        return {"status": "kosong", "lines": []}
    return {k: v for k, v in j.items() if k != "perintah"}


def mulai_pilah(data: dict, mode: str) -> None:
    """Jalankan `pilah_satuan.py` (proses terpisah) untuk tanggal/sesi pilihan. mode "analisis" =
    hitung saja; "buat" = tulis folder hasil. ValueError kalau pilihan tidak valid, RuntimeError
    kalau job pilah sebelumnya masih berjalan."""
    global _pilah
    tanggal, sesi, min_resi = data.get("tanggal"), data.get("sesi"), data.get("min_resi", 3)
    tanpa_pdf = data.get("tanpa_pdf", False)
    if not isinstance(tanpa_pdf, bool):
        raise ValueError("tanpa_pdf harus true/false")
    if not isinstance(tanggal, str) or not POLA_TANGGAL.match(tanggal):
        raise ValueError("tanggal harus YYYY-MM-DD")
    if not isinstance(sesi, list) or not sesi or not all(
            isinstance(x, str) and nama_sesi.POLA_KODE.match(x) for x in sesi):
        raise ValueError("sesi harus daftar kode (mis. [\"1\", \"2\", \"11P\"] - P = N-PEMULIHAN)")
    if isinstance(min_resi, bool) or not isinstance(min_resi, int) or not 1 <= min_resi <= 50:
        raise ValueError("min_resi harus angka 1-50")
    sesi = sorted({f"{int(x.rstrip('P'))}{'P' if x.endswith('P') else ''}" for x in sesi}, key=nama_sesi.urutan_kode)
    if any(k.endswith("P") and k[:-1] in sesi for k in sesi):
        raise ValueError("Sesi N dan N-PEMULIHAN-nya berisi resi yang sama - pilih salah satu")
    folder = ps.FOLDER_LABEL / tanggal
    if not folder.is_dir():
        raise ValueError(f"Tidak ada folder label untuk {tanggal}")
    import pilah_satuan as pl
    lanjutan = data.get("lanjutan_dari")
    if lanjutan is not None and (not isinstance(lanjutan, str) or not POLA_LABEL_PILAH.match(lanjutan)):
        raise ValueError("lanjutan_dari harus label hasil pilah sebelumnya (mis. \"1-2\" atau \"1-2+3\")")
    ditolak = [f"Sesi {x}: {alasan}" for x in sesi
               for ok, alasan in [pl.periksa_sesi(folder / nama_sesi.folder_dari_kode(x))] if not ok]
    if ditolak:   # satuan gabungan J&T + SPX dari sesi 07.00-12.00 / 20.00-07.00 saja (lihat pilah_satuan.periksa_sesi)
        raise ValueError("; ".join(ditolak))
    if lanjutan:   # pilah lanjutan: hasil lama harus ada, sesi tidak tumpang tindih, SISA lama belum dicetak
        pl.periksa_lanjutan(folder, lanjutan, sesi)
    elif mode == "buat" and not tanpa_pdf:   # hasil baru di atas PDF yang sudah dikurasi ke folder lain = resi dobel
        bentrok = kurasi_satuan.bentrok(pl.cari_pdf_satuan(folder, sesi), "-".join(sesi))
        if bentrok:
            raise ValueError(pl.pesan_bentrok(bentrok))
    perintah = [sys.executable, str(ROOT / "src" / "pilah_satuan.py"), "--folder", str(folder),
                "--sesi", "-".join(sesi), "--min-resi", str(min_resi), "--json",
                "--cache", str(jh.FOLDER_LOG / "pilah_analisis.json")]
    if lanjutan:
        perintah += ["--lanjutan-dari", lanjutan]
    if mode == "analisis":
        perintah.append("--analisis-saja")
    if tanpa_pdf:
        perintah.append("--tanpa-pdf")
    with _kunci:
        if _pilah and _pilah["status"] == "jalan":
            raise RuntimeError("Proses pilah sebelumnya masih berjalan")
        # label sesi sedang dibuat proses harian / download ulang = PDF belum lengkap -> hasil pilah salah
        if jh.keadaan()["status"] == "jalan" or (_lanjut and _lanjut["status"] == "jalan"):
            raise RuntimeError("Masih ada proses harian / download ulang yang berjalan - tunggu selesai, "
                               "label sesi belum lengkap")
        _pilah = {"id": uuid.uuid4().hex[:8], "mode": mode, "status": "jalan", "tanggal": tanggal,
                  "tanpa_pdf": tanpa_pdf, "lanjutan_dari": lanjutan,
                  "sesi": sesi, "lines": [], "total": sum(len(pl.pdf_satuan_gabungan(folder / nama_sesi.folder_dari_kode(x)))
                              for x in sesi + (pl.parse_sesi(lanjutan.replace("+", "-")) if lanjutan else [])),
                  "maju": 0, "hasil": None, "kode": None}
        threading.Thread(target=_kerjakan_pilah, args=(_pilah, perintah), daemon=True).start()


# ---------------------------------------------------------------- pemulihan sesi (tab Pulih)
_pulih: dict | None = None        # job pemulihan terakhir (satu sekaligus)


def data_pulih(hari_ini: date | None = None) -> dict:
    """Sesi bernomor biasa HARI_UI hari terakhir + status tiap picklist (data LOKAL: jurnal, PICKLIST.xlsx, PDF -
    lihat pulihkan_sesi.status_sesi). `berikut` = nama folder pemulihan yang akan dibuat untuk tanggal itu."""
    import peringatan_gagal
    import peringatan_resi
    import pulihkan_sesi
    hari_ini = hari_ini or date.today()
    peringatan_gagal.atur_folder(jh.FOLDER_LOG)
    peringatan_resi.atur_folder(jh.FOLDER_LOG)
    terhenti = {d["picklist"]: d.get("alasan") or "Terhenti" for d in peringatan_gagal.daftar_terhenti()}
    tanpa_resi = {p for p in peringatan_resi.baca_target(HARI_UI)}
    jurnal = jh.FOLDER_LOG / "picklist_terhenti.jsonl"
    per_tanggal: dict[str, list[dict]] = {}
    for folder in ps.daftar_folder_sesi(ps.FOLDER_LABEL, HARI_UI, hari_ini):
        if not folder.name.isdigit():
            continue
        sesi = f"{folder.parent.name}/{folder.name}"
        info = pulihkan_sesi.status_sesi(folder, sesi, jurnal, terhenti, tanpa_resi)
        if not info["pl"]:
            continue
        info["pemulihan"] = sorted(d.name for d in folder.parent.iterdir()
                                   if d.is_dir() and d.name.endswith("-" + nama_sesi.SUFIKS_PEMULIHAN)
                                   and pulihkan_sesi.asal_pemulihan(d) == sesi)
        per_tanggal.setdefault(folder.parent.name, []).append(info)
    hasil = []
    for t in sorted(per_tanggal):
        terbesar = max((nama_sesi.nomor_sesi(d.name) or 0 for d in (ps.FOLDER_LABEL / t).iterdir() if d.is_dir()),
                       default=0)
        hasil.append({"tanggal": t, "berikut": nama_sesi.nama_pemulihan(terbesar + 1), "sesi": per_tanggal[t]})
    return {"hari_ini": hari_ini.isoformat(), "hari": hasil}


def info_pulih() -> dict:
    j = _pulih
    if not j:
        return {"status": "kosong", "lines": []}
    return dict(j)


def mulai_pulih(data: dict, mode: str) -> None:
    """Jalankan `main.py --pulihkan-sesi <tanggal>/<sesi> [--jalankan]` (proses terpisah). mode "cek" = mode uji
    (hanya membaca Jubelio), "jalankan" = SUNGGUHAN (mengubah data di Jubelio, menulis folder N-PEMULIHAN).
    ValueError = pilihan tidak valid, RuntimeError = proses lain masih berjalan."""
    global _pulih
    tanggal, sesi = data.get("tanggal"), data.get("sesi")
    if not isinstance(tanggal, str) or not POLA_TANGGAL.match(tanggal):
        raise ValueError("tanggal harus YYYY-MM-DD")
    if not isinstance(sesi, str) or not sesi.isdigit():
        raise ValueError("sesi harus nomor sesi biasa (mis. \"10\")")
    folder = ps.FOLDER_LABEL / tanggal / str(int(sesi))
    if not folder.is_dir():
        raise ValueError(f"Sesi {tanggal}/{sesi} tidak ada")
    import pulihkan_sesi
    daftar = pulihkan_sesi.daftar_picklist(jh.FOLDER_LOG / "picklist_terhenti.jsonl", folder,
                                           f"{tanggal}/{int(sesi)}")
    if not daftar:
        raise ValueError("Sesi itu tidak punya picklist yang bisa dipulihkan")
    perintah = [sys.executable, str(ROOT / "src" / "main.py"), "--pulihkan-sesi", f"{tanggal}/{int(sesi)}"]
    if mode == "jalankan":
        perintah.append("--jalankan")
    with _kunci:
        if _pulih and _pulih["status"] == "jalan":
            raise RuntimeError("Pemulihan sebelumnya masih berjalan")
        if jh.keadaan()["status"] == "jalan" or (_lanjut and _lanjut["status"] == "jalan") \
                or (_pilah and _pilah["status"] == "jalan"):
            raise RuntimeError("Masih ada proses harian / download ulang / pilah yang berjalan - tunggu selesai")
        _pulih = {"id": uuid.uuid4().hex[:8], "mode": mode, "status": "jalan", "tanggal": tanggal, "sesi": str(int(sesi)),
                  "lines": [], "total": len(daftar), "maju": 0, "aktif": {}, "tahap": {}, "hasil": {}, "folder": None, "kode": None}
        threading.Thread(target=_kerjakan_pulih, args=(_pulih, perintah), daemon=True).start()


# keluaran main.py berawalan "2026-10-20 08:41 INFO   " (util_umum.atur_log) - awalan itu opsional di sini
_AWAL_LOG = r"^(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2} \w+\s+)?\s*"
_POLA_PULIH_OK = re.compile(_AWAL_LOG + r"OK (PICK-\d+): resi (\d+)/(\d+)(?: - belum dapat resi: (.*))?$")
_POLA_PULIH_CEK = re.compile(_AWAL_LOG + r"CEK (PICK-\d+): kini (\d+)/(\d+)")
_POLA_PULIH_GAGAL = re.compile(_AWAL_LOG + r"(?:GAGAL|TERHENTI) (PICK-\d+): (.*)$")
_POLA_PULIH_MULAI = re.compile(_AWAL_LOG + r"=== Pulihkan (PICK-\d+) \((.*)\)")
_POLA_PULIH_TAHAP = re.compile(_AWAL_LOG + r"\[(\d)\] (PICK-\d+)")


def _baris_pulih(job: dict, baris: str) -> None:
    """Baca satu baris keluaran main.py --pulihkan-sesi: kemajuan, hasil per picklist, folder tujuan."""
    if (m := _POLA_PULIH_MULAI.match(baris)):
        job["aktif"][m.group(1)] = f"{m.group(1)} {m.group(2)}"
    elif (m := _POLA_PULIH_TAHAP.match(baris)):
        nama = job["aktif"].get(m.group(2))
        if nama:     # tahap terakhir yang dicapai picklist itu (3 picking, 5 resi, 6 unduh PDF)
            job["tahap"][m.group(2)] = {"3": "picking", "5": "minta resi", "6": "unduh PDF"}.get(m.group(1), "")
    elif (m := _POLA_PULIH_OK.match(baris)):
        resi, total = int(m.group(2)), int(m.group(3))
        job["hasil"][m.group(1)] = {"resi": resi, "total": total, "sisa": total - resi}
        job["maju"] += 1
        job["aktif"].pop(m.group(1), None)
    elif (m := _POLA_PULIH_CEK.match(baris)):
        job["hasil"][m.group(1)] = {"kini": int(m.group(2)), "total": int(m.group(3))}
        job["maju"] += 1
    elif (m := _POLA_PULIH_GAGAL.match(baris)):
        job["hasil"][m.group(1)] = {"gagal": m.group(2)}
        job["maju"] += 1
        job["aktif"].pop(m.group(1), None)
    elif "Hasil pemulihan ke folder:" in baris:
        job["folder"] = Path(baris.split("folder:", 1)[1].strip()).name


def _kerjakan_pulih(job: dict, perintah: list[str]) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    try:
        p = jh._luncurkan(perintah, env)
        for baris in p.stdout:
            baris = baris.rstrip()
            _baris_pulih(job, baris)
            job["lines"].append(baris)
            del job["lines"][:-BARIS_LOG_MAKS]
        job["kode"] = p.wait()
    except OSError as e:
        job["lines"].append(f"GAGAL menjalankan: {e}")
        job["kode"] = -1
    job["status"] = "selesai" if job["kode"] == 0 else "gagal"


def _kerjakan_pilah(job: dict, perintah: list[str]) -> None:
    import pilah_satuan as pl
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    try:
        p = jh._luncurkan(perintah, env)
        for baris in p.stdout:
            baris = baris.rstrip()
            if baris.startswith(pl.PENANDA_JSON):
                try:
                    job["hasil"] = json.loads(baris[len(pl.PENANDA_JSON):])
                except ValueError:
                    job["lines"].append("Ringkasan hasil tidak terbaca")
                continue
            if "halaman dipetakan" in baris:
                job["maju"] += 1
            job["lines"].append(baris)
            del job["lines"][:-BARIS_LOG_MAKS]
        job["kode"] = p.wait()
    except OSError as e:
        job["lines"].append(f"GAGAL menjalankan: {e}")
        job["kode"] = -1
    job["status"] = "selesai" if job["kode"] == 0 and job["hasil"] else "gagal"


def _publik(job: dict | None) -> dict:
    """Job tanpa daftar path internal (untuk JSON)."""
    if not job:
        return {"status": "kosong", "lines": []}
    return {k: v for k, v in job.items() if k != "files"}


def _baca_keluaran(proses: subprocess.Popen, job: dict) -> None:
    for baris in proses.stdout:
        job["lines"].append(baris.rstrip())
        del job["lines"][:-BARIS_LOG_MAKS]
    job["kode"] = proses.wait()
    job["status"] = "selesai" if job["kode"] == 0 else "gagal"


class Server(ThreadingHTTPServer):
    # Windows: dengan SO_REUSEADDR, server kedua BISA bind ke port yang sudah dipakai (bukan error) -
    # matikan supaya klik dua kali tombol buka app terdeteksi lewat OSError di main().
    allow_reuse_address = False

    def handle_error(self, request, client_address):
        # Klien (tab/browser) menutup koneksi sebelum jawaban terkirim - mis. tab ditutup atau
        # di-refresh saat Get-Printer masih jalan. Tidak berbahaya; jangan cetak traceback.
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    server_version = "UIcetak"

    def log_message(self, fmt, *args):   # senyap; log cetak ada di logs/
        pass

    def _kirim(self, kode: int, isi, tipe: str = "application/json; charset=utf-8") -> None:
        body = isi if isinstance(isi, bytes) else json.dumps(isi, ensure_ascii=False).encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self) -> bool:
        # tolak DNS-rebinding: hanya boleh diakses lewat localhost/127.0.0.1
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._host_ok():
            return self._kirim(403, {"error": "host ditolak"})
        try:
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                return self._kirim(200, HTML_UI.read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/sesi":
                return self._kirim(200, data_sesi())
            if url.path == "/api/printer":
                daftar = daftar_printer_cache()
                return self._kirim(200, {"printer": daftar, "virtual": [p for p in daftar if printer_virtual(p)]})
            if url.path == "/api/job":
                nama = parse_qs(url.query).get("printer", [_terakhir])[0]
                return self._kirim(200, _publik(_jobs.get(nama)))
            if url.path == "/api/jobs":     # ringkasan semua printer (UI memulihkan status setelah refresh)
                return self._kirim(200, {"jobs": {n: {"status": j["status"], "total": j["total"],
                                                      "id": j["id"]} for n, j in _jobs.items()}})
            if url.path == "/api/pilah/sesi":
                return self._kirim(200, data_pilah())
            if url.path == "/api/pilah/job":
                return self._kirim(200, info_pilah())
            if url.path == "/api/pulih/sesi":
                return self._kirim(200, data_pulih())
            if url.path == "/api/pulih/job":
                return self._kirim(200, info_pulih())
            if url.path == "/api/operator":
                return self._kirim(200, info_operator())
            if url.path == "/api/sebagian":
                return self._kirim(200, {"daftar": info_sebagian()})
            if url.path == "/api/terhenti":
                return self._kirim(200, info_terhenti())
            if url.path == "/api/harian/info":
                return self._kirim(200, jh.info())
            if url.path == "/api/harian/job":
                dari = parse_qs(url.query).get("dari", ["0"])[0]
                return self._kirim(200, jh.keadaan(int(dari) if dari.isdigit() else 0))
        except ps.CetakError as e:
            return self._kirim(500, {"error": str(e)})
        self._kirim(404, {"error": "tidak ada"})

    def do_POST(self):
        corpus = self.rfile.read(int(self.headers.get("Content-Length") or 0))   # selalu dibaca habis
        if not self._host_ok():
            return self._kirim(403, {"error": "host ditolak"})
        # wajib JSON: form lintas-situs tidak bisa mengirim tipe ini tanpa preflight CORS
        if self.path not in ("/api/cetak", "/api/harian/jalankan", "/api/harian/hentikan",
                             "/api/terhenti/jalankan", "/api/operator", "/api/sebagian/lanjut",
                             "/api/pilah/analisis", "/api/pilah/buat", "/api/pulih/cek", "/api/pulih/jalankan") \
                or "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._kirim(404, {"error": "tidak ada"})
        try:
            data = json.loads(corpus or b"{}")
            if self.path == "/api/operator":
                try:
                    return self._kirim(200, ubah_operator(data.get("aksi"), data.get("nama")))
                except oa.OperatorError as e:
                    return self._kirim(400, {"error": str(e)})
            if self.path in ("/api/pulih/cek", "/api/pulih/jalankan"):
                try:
                    mulai_pulih(data, self.path.rsplit("/", 1)[1])
                except ValueError as e:
                    return self._kirim(400, {"error": str(e)})
                return self._kirim(200, {"mulai": True})
            if self.path in ("/api/pilah/analisis", "/api/pilah/buat"):
                try:
                    mulai_pilah(data, self.path.rsplit("/", 1)[1])
                except ValueError as e:
                    return self._kirim(400, {"error": str(e)})
                return self._kirim(200, {"mulai": True})
            if self.path == "/api/terhenti/jalankan":
                try:
                    mulai_lanjut(data.get("picklist"))
                except ValueError as e:
                    return self._kirim(400, {"error": str(e)})
                return self._kirim(200, {"mulai": True})
            if self.path == "/api/harian/hentikan":
                return self._kirim(200, {"dihentikan": jh.hentikan()})
            if self.path == "/api/harian/jalankan":
                return self._kirim(200, {"job": jh.mulai(data.get("langkah"), data.get("judul"))})
            if self.path == "/api/sebagian/lanjut":
                item, printer = data.get("item"), data.get("printer")
                if not isinstance(item, list) or not all(isinstance(x, dict) for x in item) \
                        or not isinstance(printer, str):
                    return self._kirim(400, {"error": "item (daftar) dan printer wajib diisi"})
                return self._kirim(200, {"job": mulai_lanjut_sebagian(item, printer)})
            files, printer = data.get("files"), data.get("printer")
            if not isinstance(files, list) or not all(isinstance(x, str) for x in files):
                return self._kirim(400, {"error": "files harus daftar path"})
            if "printers" in data:   # cetak bagi-rata ke beberapa printer
                printers = data["printers"]
                if not isinstance(printers, list) or not all(isinstance(x, str) for x in printers):
                    return self._kirim(400, {"error": "printers harus daftar nama printer"})
                return self._kirim(200, {"jobs": mulai_cetak_banyak(files, printers, bool(data.get("ulang")))})
            if not isinstance(printer, str):
                return self._kirim(400, {"error": "printer wajib diisi"})
            job = mulai_cetak(files, printer, bool(data.get("ulang")))
        except ps.CetakError as e:
            return self._kirim(400, {"error": str(e)})
        except RuntimeError as e:
            return self._kirim(409, {"error": str(e)})
        except jh.HarianError as e:
            return self._kirim(409 if "berjalan" in str(e) else 400, {"error": str(e)})
        except (ValueError, json.JSONDecodeError):
            return self._kirim(400, {"error": "JSON tidak valid"})
        self._kirim(200, {"job": job})


def main() -> int:
    ap = argparse.ArgumentParser(description="Server lokal UI desktop (menu Harian & Cetak).")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--buka", action="store_true", help="Buka UI di browser setelah server jalan")
    ap.add_argument("--menu", choices=["harian", "event", "cetak"], default="harian",
                    help="Menu yang dibuka pertama oleh --buka (default harian)")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}/#{args.menu}"
    try:
        server = Server(("127.0.0.1", args.port), Handler)
    except OSError:
        # port terpakai -> anggap server UI sudah berjalan (tombol buka app diklik dua kali):
        # cukup buka tampilannya, jangan jalankan server kedua.
        print(f"UI sudah berjalan di {url}")
        if args.buka:
            webbrowser.open(url)
        return 0
    threading.Thread(target=_hangatkan_printer, daemon=True).start()   # tab pertama tidak menunggu Get-Printer
    print(f"UI berjalan di {url}  (Ctrl+C atau tutup jendela ini untuk berhenti)")
    if args.buka:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
