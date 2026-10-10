"""Jalankan rangkaian langkah menu HARIAN dari UI desktop (server_ui.py) - setara
proses-harian.bat / proses-malam.bat: tiap langkah = SATU proses `main.py <flag> --jalankan`
berurutan (bukan memanggil fungsi langsung), lalu rekap waktu (`rekap_waktu.py`) di akhir.
SUNGGUHAN: langkah ini mengubah data di Jubelio.

Aturan yang SAMA dengan .bat:
  - Folder sesi label dihitung SEKALI (env LABEL_SESI_DIR) dan dipakai semua langkah; dipakai
    ulang antar job selama masih hari yang sama, hari baru -> sesi baru (lihat _sesi_label()).
  - Langkah yang gagal TIDAK menghentikan langkah berikutnya (seperti .bat); statusnya dicatat
    per langkah dan peringatan dari logs/ ikut tampil di rekap.
  - Urgent memakai `--lewati-malam` hanya untuk judul "TIPE 1" (dan "KUSTOM"), tidak untuk
    TIPE 2-4 dan MALAM - sama seperti proses-harian.bat / proses-malam.bat.
  - `--non-wajib` / `--non-wajib-sore` (tulisan NON WAJIB KELUAR di kolom U) lewat flag_non_wajib();
    WAKTU_MENU_MULAI = waktu job mulai, dibaca main.py untuk TIPE 1.
  - Judul "EVENT - ..." memakai KATALOG_EVENT (padanan proses-event.bat, J&T/SPX Hemat/SPX
    Standard dipisah seharian); EVENT - TIPE 2 = pilihan 2 .bat, TIPE 1/3/4 = pilihan 1 (sesi biasa).
Urutan langkah SELALU mengikuti KATALOG / KATALOG_EVENT (bukan urutan kiriman UI).
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER_LOG = ROOT / "logs"
SRC = Path(__file__).resolve().parent

# (nama langkah di UI, flag main.py tanpa --jalankan). Urutan = urutan eksekusi.
KATALOG: list[tuple[str, list[str]]] = [
    ("Recheck stok", ["--recheck-stok"]),
    ("Sampel TikTok (nilai 0)", ["--sampel"]),
    ("Urgent Lazada", ["--urgent", "--channel", "lazada"]),
    ("Urgent GTL & SiCepat", ["--urgent", "--channel", "gtl-sicepat"]),
    ("Urgent JNE & LEX", ["--urgent", "--channel", "jne-lex"]),
    ("SPX ≤ 12.00 (Resi Pagi)", ["--shopee-pagi"]),
    ("J&T ≤ 15.00 (Resi Siang)", ["--jnt-siang"]),
    ("SPX-J&T Spesial", ["--label", "--tanpa-reguler"]),
    ("SPX-J&T 1 qty reguler", ["--reguler", "--bagian", "1qty"]),
    ("SPX-J&T Kombinasi", ["--reguler", "--bagian", "kombinasi"]),
    ("J&T Spesial", ["--label", "--kurir", "jnt", "--tanpa-reguler"]),
    ("J&T 1 qty reguler", ["--reguler", "--bagian", "1qty", "--kurir", "jnt"]),
    ("J&T Kombinasi", ["--reguler", "--bagian", "kombinasi", "--kurir", "jnt"]),
    ("SPX Spesial", ["--label", "--kurir", "spx", "--tanpa-reguler"]),
    ("SPX 1 qty reguler", ["--reguler", "--bagian", "1qty", "--kurir", "spx"]),
    ("SPX Kombinasi", ["--reguler", "--bagian", "kombinasi", "--kurir", "spx"]),
    ("Upload faktur & pesanan ke IRESIS", ["--upload-iresis"]),
]

# Menu EVENT (10.10/11.11/12.12 dst) - padanan bat\proses-event.bat: J&T, SPX Hemat, SPX Standard
# dipisah seharian (`--event`). Nama langkah dipisah dari KATALOG karena nama yang sama
# ("J&T Spesial") punya flag berbeda (`--event`). Urutan = urutan di .bat (Resi Siang sebelum
# Shopee Pagi, lalu J&T, SPX Hemat, SPX Standard).
KATALOG_EVENT: list[tuple[str, list[str]]] = [
    ("Recheck stok", ["--recheck-stok"]),
    ("Sampel TikTok (nilai 0)", ["--sampel"]),
    ("Urgent Lazada", ["--urgent", "--channel", "lazada"]),
    ("Urgent GTL & SiCepat", ["--urgent", "--channel", "gtl-sicepat"]),
    ("Urgent JNE & LEX", ["--urgent", "--channel", "jne-lex"]),
    ("J&T ≤ 15.00 (Resi Siang)", ["--jnt-siang"]),
    ("SPX Standard Pagi ≤ 12.00 (per lantai)", ["--spx-standard", "--pagi"]),
    ("SPX Hemat Pagi Spesial", ["--label", "--event", "--kurir", "spx-hemat-pagi", "--tanpa-reguler"]),
    ("SPX Hemat Pagi 1 qty reguler", ["--reguler", "--event", "--kurir", "spx-hemat-pagi", "--bagian", "1qty"]),
    ("SPX Hemat Pagi Kombinasi", ["--reguler", "--event", "--kurir", "spx-hemat-pagi", "--bagian", "kombinasi"]),
    ("J&T Spesial", ["--label", "--event", "--kurir", "jnt", "--tanpa-reguler"]),
    ("J&T 1 qty reguler", ["--reguler", "--event", "--kurir", "jnt", "--bagian", "1qty"]),
    ("J&T Kombinasi", ["--reguler", "--event", "--kurir", "jnt", "--bagian", "kombinasi"]),
    ("SPX Hemat Spesial", ["--label", "--event", "--kurir", "spx-hemat", "--tanpa-reguler"]),
    ("SPX Hemat 1 qty reguler", ["--reguler", "--event", "--kurir", "spx-hemat", "--bagian", "1qty"]),
    ("SPX Hemat Kombinasi", ["--reguler", "--event", "--kurir", "spx-hemat", "--bagian", "kombinasi"]),
    ("SPX Standard (per lantai)", ["--spx-standard"]),
    ("Upload faktur & pesanan ke IRESIS", ["--upload-iresis"]),
]
FLAG = dict(KATALOG)
FLAG_EVENT = dict(KATALOG_EVENT)
JUDUL_EVENT = {"EVENT - TIPE 1", "EVENT - TIPE 2", "EVENT - TIPE 3", "EVENT - TIPE 4",
               "EVENT - MALAM", "EVENT - KUSTOM"}
JUDUL_VALID = {"TIPE 1", "TIPE 2", "TIPE 3", "TIPE 4", "MALAM", "KUSTOM"} | JUDUL_EVENT
# Urgent `--lewati-malam`: proses-event.bat pilihan 1 (sesi biasa = TIPE 1/3/4) memakainya,
# pilihan 2 (TIPE 2, Shopee Pagi) dan MALAM tidak.
JUDUL_LEWATI_MALAM = {"TIPE 1", "KUSTOM", "EVENT - TIPE 1", "EVENT - TIPE 3", "EVENT - TIPE 4", "EVENT - KUSTOM"}
LANGKAH_IRESIS = "Upload faktur & pesanan ke IRESIS"
JUDUL_TANPA_IRESIS = {"MALAM", "EVENT - MALAM"}     # IRESIS hanya di jaringan lokal kantor: menu malam tidak boleh menyentuhnya
MENU_JAM = {"TIPE 1": "1", "TIPE 2": "2", "TIPE 3": "3", "TIPE 4": "4",     # untuk dalam_jam_menu()
            "EVENT - TIPE 1": "1", "EVENT - TIPE 2": "2", "EVENT - TIPE 3": "3", "EVENT - TIPE 4": "4"}
# Tulisan NON WAJIB KELUAR di kolom U PICKLIST.xlsx (lihat docs/jadwal-proses.md), sama dengan .bat:
# langkah SPX dipisah di TIPE 2/3 dan langkah SPX-J&T gabungan di TIPE 4 selalu (`--non-wajib`);
# langkah gabungan TIPE 1 hanya kalau menu dimulai setelah 16.00 (`--non-wajib-sore`). Event, MALAM,
# KUSTOM tidak.
NON_WAJIB_SPX_DIPISAH = {"SPX Spesial", "SPX 1 qty reguler", "SPX Kombinasi"}
NON_WAJIB_SPX_GABUNG = {"SPX-J&T Spesial", "SPX-J&T 1 qty reguler", "SPX-J&T Kombinasi"}


def flag_non_wajib(judul: str, nama_langkah: str) -> str | None:
    if judul in ("TIPE 2", "TIPE 3") and nama_langkah in NON_WAJIB_SPX_DIPISAH:
        return "--non-wajib"
    if judul == "TIPE 4" and nama_langkah in NON_WAJIB_SPX_GABUNG:
        return "--non-wajib"
    if judul == "TIPE 1" and nama_langkah in NON_WAJIB_SPX_GABUNG:
        return "--non-wajib-sore"
    return None


BARIS_MAKS = 50000

_kunci = threading.Lock()
_job: dict | None = None
_proses: subprocess.Popen | None = None
_sesi: tuple[str, str] | None = None     # (tanggal, "YYYY-MM-DD/N")


class HarianError(Exception):
    pass


def _sesi_label() -> str:
    """Folder sesi label untuk job ini: pakai ulang yang sama selama masih hari yang sama
    (seperti proses-harian.bat yang menghitungnya sekali), hari baru -> buat sesi baru."""
    global _sesi
    hari = datetime.now().strftime("%Y-%m-%d")
    if _sesi is None or _sesi[0] != hari:
        import main
        _sesi = (hari, main.sesi_label_baru())
    return _sesi[1]


def _luncurkan(argumen: list[str], env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        argumen, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env, cwd=str(ROOT),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def mulai(langkah: list[str], judul: str) -> str:
    """Validasi lalu jalankan `langkah` di thread latar. Melempar HarianError (pilihan tidak
    valid / masih ada job berjalan)."""
    global _job
    if judul not in JUDUL_VALID:
        raise HarianError(f"Judul tidak dikenal: {judul!r}")
    if not isinstance(langkah, list) or not all(isinstance(x, str) for x in langkah):
        raise HarianError("langkah harus daftar nama")
    flag = FLAG_EVENT if judul in JUDUL_EVENT else FLAG
    katalog = KATALOG_EVENT if judul in JUDUL_EVENT else KATALOG
    asing = [x for x in langkah if x not in flag]
    if asing:
        raise HarianError("Langkah tidak dikenal: " + ", ".join(asing))
    if judul in JUDUL_TANPA_IRESIS and LANGKAH_IRESIS in langkah:
        raise HarianError(f"Langkah IRESIS tidak boleh dipakai di {judul} (IRESIS hanya di jaringan lokal)")
    urut = [nama for nama, _ in katalog if nama in set(langkah)]
    if not urut:
        raise HarianError("Tidak ada langkah dipilih")
    with _kunci:
        if _job and _job["status"] == "jalan":
            raise HarianError("Masih ada proses harian yang berjalan")
        sesi = _sesi_label()
        _job = {"id": datetime.now().strftime("%H%M%S"), "judul": judul, "status": "jalan",
                "sesi": sesi, "mulai": time.time(), "berhenti": False, "lines": [], "flag": flag,
                "langkah": [{"nama": n, "status": "antri", "kode": None} for n in urut]}
        threading.Thread(target=_kerjakan, args=(_job, sesi), daemon=True).start()
        return _job["id"]


def _tambah(job: dict, baris: str) -> None:
    if len(job["lines"]) < BARIS_MAKS:    # batas pengaman memori; indeks baris tetap stabil untuk UI
        job["lines"].append(baris)


def _jalankan_proses(job: dict, argumen: list[str], env: dict) -> int:
    global _proses
    p = _luncurkan(argumen, env)
    _proses = p
    for baris in p.stdout:
        _tambah(job, baris.rstrip())
    return p.wait()


def _kerjakan(job: dict, sesi: str) -> None:
    global _proses
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
           "LABEL_SESI_DIR": sesi, "WAKTU_MENU_MULAI": str(job["mulai"])}
    lewati_malam = job["judul"] in JUDUL_LEWATI_MALAM
    total = len(job["langkah"])
    waktu = []
    _tambah(job, f"Sesi label: {sesi}")
    for i, lg in enumerate(job["langkah"], 1):
        if job["berhenti"]:
            break
        flag = list(job["flag"][lg["nama"]])
        lg["status"] = "jalan"
        _tambah(job, "")
        _tambah(job, f"=== {i}/{total} {lg['nama'].upper()} ===")
        mulai_t = time.time()
        argumen = [sys.executable, str(SRC / "main.py"), *flag, "--jalankan"]
        if lewati_malam and flag[:1] == ["--urgent"]:
            argumen.append("--lewati-malam")
        if (nw := flag_non_wajib(job["judul"], lg["nama"])):
            argumen.append(nw)
        try:
            lg["kode"] = _jalankan_proses(job, argumen, env)
        except OSError as e:
            lg["kode"] = -1
            _tambah(job, f"GAGAL menjalankan langkah: {e}")
        waktu.append(f"{lg['nama'].upper()}:{mulai_t}:{time.time()}")
        lg["status"] = "selesai" if lg["kode"] == 0 else "gagal"
        if job["berhenti"]:
            lg["status"] = "gagal"
    _proses = None
    if job["berhenti"]:
        _tambah(job, "")
        _tambah(job, "DIHENTIKAN oleh pengguna.")
    elif waktu:
        try:   # rekap waktu + peringatan, sama seperti akhir tiap TIPE di .bat
            _jalankan_proses(job, [sys.executable, str(SRC / "rekap_waktu.py"), job["judul"], *waktu], env)
        except OSError as e:
            _tambah(job, f"Rekap waktu gagal: {e}")
    if job["berhenti"]:
        job["status"] = "dihentikan"
    elif any(lg["status"] == "gagal" for lg in job["langkah"]):
        job["status"] = "gagal"
    else:
        job["status"] = "selesai"


def hentikan() -> bool:
    """Minta berhenti: proses langkah yang sedang jalan dimatikan, sisa langkah dibatalkan.
    True kalau ada job yang berjalan."""
    with _kunci:
        if not _job or _job["status"] != "jalan":
            return False
        _job["berhenti"] = True
        p = _proses
    if p and p.poll() is None:
        p.terminate()
    return True


def keadaan(dari: int = 0) -> dict:
    """Status job terakhir; `lines` hanya baris ke-`dari` ke atas (UI mengambil bertahap)."""
    if _job is None:
        return {"status": "kosong", "langkah": [], "lines": [], "total": 0}
    j = _job
    dari = max(0, dari)
    return {"id": j["id"], "judul": j["judul"], "status": j["status"], "sesi": j["sesi"],
            "langkah": [dict(x) for x in j["langkah"]], "lines": j["lines"][dari:],
            "total": len(j["lines"])}


def info() -> dict:
    """Untuk halaman Harian: apakah jam sekarang cocok tiap TIPE (sanity check seperti cek_jam
    di .bat), peringatan hari ini (picklist terlompat / tanpa resi / gagal), dan job berjalan."""
    import main
    import peringatan_gagal
    import peringatan_picklist
    import peringatan_resi
    awal_hari = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    hasil = {}
    for kunci, modul in (("picklist", peringatan_picklist), ("resi", peringatan_resi),
                         ("gagal", peringatan_gagal)):
        modul.atur_folder(FOLDER_LOG)
        hasil[kunci] = modul.baca_sejak(awal_hari)
    # picklist TERHENTI sudah punya bagian sendiri (bisa di-download ulang) - jangan dobel
    hasil["gagal"] = [m for m in hasil["gagal"] if ": TERHENTI" not in m]
    return {"jam_ok": {judul: bool(main.dalam_jam_menu(m)) for judul, m in MENU_JAM.items()},
            "peringatan": hasil,
            "berjalan": bool(_job and _job["status"] == "jalan")}
