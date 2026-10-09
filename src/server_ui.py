"""Server lokal untuk UI desktop (prototype-desktop/index.html) - menu CETAK.

Hanya melayani 127.0.0.1 (komputer ini saja). UI membaca daftar sesi/file label sungguhan
dari folder label-pengiriman dan mencetak file pilihan lewat
`print_spesial.py --file-dari ... --printer ... --tanpa-konfirmasi` (proses terpisah, jadi
semua aturan cetak - dedupe sudah_dicetak, pantau printer, daftar gagal - sama persis dengan
CLI). Program ini TIDAK mencetak sendiri.

Jalankan:  .venv\\Scripts\\python src\\server_ui.py [--port 8765] [--buka]

API (JSON):
  GET  /api/sesi     sesi label 3 hari terakhir -> jenis -> file PDF (+ status sudah dicetak)
  GET  /api/printer  nama printer yang terhubung
  POST /api/cetak    {"files": ["2026-10-07/1/SPESIAL/PICK-....pdf", ...], "printer": "...",
                      "ulang": false} -> {"job": id}; satu job sekaligus (409 kalau masih jalan)
  GET  /api/job?printer=NAMA   status & baris log job printer itu (tanpa parameter: job terakhir)
  GET  /api/jobs               ringkasan job semua printer
  (printer BERBEDA boleh mencetak bersamaan; printer yang sama antre -> 409)
  GET  /api/harian/info          jam cocok per TIPE, peringatan hari ini, apakah ada job berjalan
  POST /api/harian/jalankan      {"langkah": [nama...], "judul": "TIPE 1"} -> {"job": id}
                                 (SUNGGUHAN: lihat jalankan_harian.py; 409 kalau masih berjalan)
  GET  /api/harian/job?dari=N    status per langkah + baris log ke-N dst
  POST /api/harian/hentikan      matikan langkah berjalan & batalkan sisanya
  GET  /api/terhenti             picklist terhenti (mis. gagal unduh PDF) + status job download ulang
  POST /api/terhenti/jalankan    {"picklist": ["PICK-...", ...]} -> `main.py --lanjut` berurutan
                                 (SUNGGUHAN; 409 kalau download ulang/proses harian masih berjalan)
Jenis yang ditampilkan: spesial, satuan, kombinasi, gtl-sicepat (JENIS_UI). Jenis lain
(spx-pagi, jnt-siang, event, dst) tetap lewat cetak-label.bat.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import uuid
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jalankan_harian as jh
import print_spesial as ps

ROOT = ps.ROOT
HTML_UI = ROOT / "prototype-desktop" / "index.html"
HARI_UI = 3                      # hari ini, kemarin, 2 hari lalu
JENIS_UI = [("Spesial", "spesial"), ("Satuan", "satuan"), ("Kombinasi", "kombinasi"),
            ("GTL-SiCepat", "gtl-sicepat")]
BARIS_LOG_MAKS = 400

_jobs: dict[str, dict] = {}      # kunci = nama printer: printer BERBEDA boleh mencetak bersamaan
_terakhir: str | None = None
_kunci = threading.Lock()


def _rel(f: Path) -> str:
    return f.resolve().relative_to(ps.FOLDER_LABEL.resolve()).as_posix()


def data_sesi(hari_ini: date | None = None) -> dict:
    """Sesi label HARI_UI hari terakhir (terlama -> terbaru di dalam tiap hari), tiap jenis
    berisi file PDF urut nomor PICK. Jenis tanpa file tidak dimasukkan."""
    hari_ini = hari_ini or date.today()
    sudah = ps.baca_sudah_dicetak()
    per_tanggal: dict[str, list[dict]] = {}
    for folder in ps.daftar_folder_sesi(ps.FOLDER_LABEL, HARI_UI, hari_ini):
        jenis_out, terpakai, waktu = [], set(), []
        for nama, kode in JENIS_UI:
            files = []
            for f in ps.daftar_label(folder, kode):
                if f in terpakai:
                    continue
                terpakai.add(f)
                st = f.stat()
                waktu.append(st.st_mtime)
                files.append({"f": f.name, "rel": _rel(f), "kb": max(1, round(st.st_size / 1024)),
                              "done": str(f.resolve()) in sudah})
            if files:
                jenis_out.append({"nama": nama, "files": files})
        if not jenis_out:
            continue   # sesi tanpa label jenis yang ditampilkan (mis. baru dibuat/kosong)
        per_tanggal.setdefault(folder.parent.name, []).append({
            "no": int(folder.name), "id": f"{folder.parent.name}/{folder.name}",
            "jam": datetime.fromtimestamp(min(waktu)).strftime("%H.%M") if waktu else "--.--",
            "jenis": jenis_out})
    return {"hari_ini": hari_ini.isoformat(),
            "hari": [{"tanggal": t, "sesi": per_tanggal[t]} for t in sorted(per_tanggal)]}


def mulai_cetak(files: list[str], printer: str, ulang: bool = False) -> str:
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
    p = [sys.executable, str(Path(__file__).with_name("main.py")), "--lanjut", d["picklist"],
         "--nama", d["nama"]]
    if d.get("tag"):
        p += ["--tag", d["tag"]]
    if d.get("subfolder"):
        p += ["--subfolder", d["subfolder"]]
    return p + ["--sesi", d["sesi"], "--jalankan"]


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
                return self._kirim(200, {"printer": ps.daftar_printer()})
            if url.path == "/api/job":
                nama = parse_qs(url.query).get("printer", [_terakhir])[0]
                return self._kirim(200, _publik(_jobs.get(nama)))
            if url.path == "/api/jobs":     # ringkasan semua printer (UI memulihkan status setelah refresh)
                return self._kirim(200, {"jobs": {n: {"status": j["status"], "total": j["total"],
                                                      "id": j["id"]} for n, j in _jobs.items()}})
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
                             "/api/terhenti/jalankan") \
                or "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._kirim(404, {"error": "tidak ada"})
        try:
            data = json.loads(corpus or b"{}")
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
            files, printer = data.get("files"), data.get("printer")
            if not isinstance(files, list) or not all(isinstance(x, str) for x in files):
                return self._kirim(400, {"error": "files harus daftar path"})
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
    ap.add_argument("--menu", choices=["harian", "cetak"], default="harian",
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
