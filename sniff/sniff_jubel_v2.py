"""Rekam LENGKAP semua request & response di browser (semua tab) untuk analisa alur Jubelio.

Yang direkam:
  - semua request di SEMUA tab: tab awal, popup/tab baru dari halaman, dan tab yang
    dibuka sendiri (Ctrl+T) - sejak request pertama, walau tab menutup sendiri
  - semua jenis: dokumen, iframe, form POST, XHR/Fetch, script, gambar, download, dll.
  - request: method, URL, header lengkap, body
  - response: status, header lengkap, body (teks apa adanya, biner dalam base64)
  - WebSocket (pesan kirim/terima), navigasi, tab dibuka/ditutup, download + filenya

Cara pakai:
  1. Jalankan run_sniff_jubel.bat -> browser terbuka di halaman login Jubelio
  2. Lakukan aksi yang ingin direkam (boleh buka banyak tab)
  3. Kembali ke jendela hitam (console) ini lalu tekan ENTER untuk berhenti
     (jangan Ctrl+C dan jangan tutup browser dulu, supaya file HAR sempat ditulis)

Hasil di sniff_output/ (password login otomatis disensor):
  <nama>_requests.jsonl   1 baris = 1 request+response lengkap, ditulis LANGSUNG
                          (tetap ada walau program crash); ada nomor tab asalnya
  <nama>.har              format HAR standar (bisa dibuka di Chrome DevTools > Network > Import)
  <nama>_events.json      urutan kejadian: tab, navigasi, download, WebSocket
  <nama>_unduhan/         file yang terunduh

Opsi:
  --profil     pakai profil browser tetap (sniff/profil_browser) -> login tersimpan antar sesi
  --ringkas    buang domain analytics & isi file statis (JS/CSS/gambar/font) dari HAR
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

START_URL = "https://v2.jubelio.com/auth/login"
FOLDER = Path(__file__).parent
OUTPUT_DIR = FOLDER / "sniff_output"
PROFIL_TETAP = FOLDER / "profil_browser"
MAKS_BODY = 10_000_000          # byte; body lebih besar dipotong

# dipakai hanya dengan --ringkas
TIPE_TANPA_ISI = re.compile(r"^(image/|font/|text/css|audio/|video/)|javascript", re.I)
DOMAIN_ABAIKAN = re.compile(
    r"google-analytics|analytics\.google|googletagmanager|doubleclick|googleadservices|"
    r"google\.com/(rmkt|pagead)|google\.co\.id/pagead|facebook|hotjar|clarity\.ms|"
    r"bzr\.openai|bzrcdn\.openai|ecs\.us-west-2\.on\.aws|analytic-collector|freshchat|cdn-cgi/rum",
    re.I)
POLA_PASSWORD = [
    (re.compile(r'("password"\s*:\s*")(?:[^"\\]|\\.)*(")'), r"\1<DISENSOR>\2"),
    (re.compile(r"((?:^|&)password=)[^&]*"), r"\1<DISENSOR>"),
]


# Chrome tidak memberikan body request yang dikirim sebagai Blob/stream (dipakai web Jubelio
# lewat library ky), jadi body dibaca langsung dari fetch/XHR di halaman lalu dikirim ke Python.
SKRIP_BODY = r"""
(() => {
  if (window.__sniffTerpasang) return;
  window.__sniffTerpasang = true;
  const kirim = (method, url, body) => {
    try { return window.__sniffBody({method: String(method).toUpperCase(),
                                     url: new URL(url, location.href).href, body}); }
    catch (e) { return Promise.resolve(); }
  };
  const keTeks = async (b) => {
    if (b == null) return null;
    if (typeof b === 'string') return b;
    if (b instanceof Blob) return await b.text();
    if (b instanceof URLSearchParams) return b.toString();
    if (b instanceof FormData) {
      const o = [];
      for (const [k, v] of b.entries()) o.push(k + '=' + (typeof v === 'string' ? v : '[file ' + v.name + ']'));
      return o.join('&');
    }
    if (b instanceof ArrayBuffer || ArrayBuffer.isView(b)) return new TextDecoder().decode(b);
    return '[body tipe ' + Object.prototype.toString.call(b) + ']';
  };
  const asliFetch = window.fetch;
  window.fetch = async function (input, init) {
    try {
      const isReq = typeof Request !== 'undefined' && input instanceof Request;
      const method = (init && init.method) || (isReq ? input.method : 'GET');
      const url = isReq ? input.url : String(input);
      let body = null;
      if (init && init.body != null) body = await keTeks(init.body);
      else if (isReq && !['GET', 'HEAD'].includes(method.toUpperCase())) body = await input.clone().text();
      if (body) await kirim(method, url, body);
    } catch (e) {}
    return asliFetch.apply(this, arguments);
  };
  const asliOpen = XMLHttpRequest.prototype.open, asliSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__sniff = [m, u]; return asliOpen.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) {
    if (b != null && this.__sniff) { const [m, u] = this.__sniff; keTeks(b).then(t => t && kirim(m, u, t)); }
    return asliSend.apply(this, arguments);
  };
})();
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def sensor(teks: str | None) -> str | None:
    if not teks:
        return teks
    for pola, ganti in POLA_PASSWORD:
        teks = pola.sub(ganti, teks)
    return teks


def _isi_body(data: bytes | None) -> dict:
    if data is None:
        return {"body": None}
    potong = len(data) > MAKS_BODY
    data_simpan = data[:MAKS_BODY]
    try:
        hasil = {"body": sensor(data_simpan.decode("utf-8")), "body_encoding": "text"}
    except UnicodeDecodeError:
        hasil = {"body": base64.b64encode(data_simpan).decode("ascii"), "body_encoding": "base64"}
    hasil["body_size"] = len(data)
    if potong:
        hasil["body_terpotong"] = True
    return hasil


def rapikan_har(path: Path, ringkas: bool) -> tuple[int, int]:
    """Sensor password di HAR; dengan --ringkas juga buang analytics & isi file statis."""
    har = json.loads(path.read_text(encoding="utf-8"))
    semula = har["log"]["entries"]
    entri = [e for e in semula if not (ringkas and DOMAIN_ABAIKAN.search(e["request"]["url"]))]
    for e in entri:
        pd = e["request"].get("postData")
        if pd and pd.get("text"):
            pd["text"] = sensor(pd["text"])
        isi = e["response"].get("content", {})
        if ringkas and isi.get("text") and TIPE_TANPA_ISI.search(isi.get("mimeType", "")):
            isi["text"] = f"<isi dibuang, {isi.get('size', '?')} byte>"
            isi.pop("encoding", None)
    har["log"]["entries"] = entri
    path.write_text(json.dumps(har, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(semula), len(entri)


class Perekam:
    def __init__(self, out_dir: Path, nama: str):
        self.jsonl = open(out_dir / f"{nama}_requests.jsonl", "a", encoding="utf-8")
        self.events_path = out_dir / f"{nama}_events.json"
        self.folder_unduhan = out_dir / f"{nama}_unduhan"
        self.events: list[dict] = []
        self.tab: dict[int, int] = {}          # id(page) -> nomor tab
        self.pending: dict[int, dict] = {}     # id(request) -> data request
        self.jumlah = 0
        self.jumlah_unduhan = 0
        self.lock = threading.Lock()
        self.body_js: list[dict] = []          # body dari skrip halaman, belum dipasangkan

    # ------------------------------------------------------------ util
    def catat(self, jenis: str, **data) -> None:
        self.events.append({"waktu": _now(), "jenis": jenis, **data})

    def simpan_events(self) -> None:
        self.events_path.write_text(json.dumps(self.events, ensure_ascii=False, indent=1),
                                    encoding="utf-8")

    def _tulis(self, entri: dict) -> None:
        with self.lock:
            self.jsonl.write(json.dumps(entri, ensure_ascii=False) + "\n")
            self.jsonl.flush()
            self.jumlah += 1

    def _no_tab(self, req) -> int | None:
        try:
            return self.tab.get(id(req.frame.page))
        except PlaywrightError:
            return None                        # request service worker

    @staticmethod
    def _frame(req) -> str | None:
        try:
            return "utama" if req.frame.parent_frame is None else f"iframe {req.frame.url}"
        except PlaywrightError:
            return None                        # request service worker

    # ------------------------------------------------------------ tab
    def pasang_tab(self, page) -> None:
        if id(page) in self.tab:
            return
        no = self.tab[id(page)] = len(self.tab) + 1
        pembuka = page.opener()
        self.catat("tab_dibuka", tab=no, url=page.url,
                   dibuka_dari_tab=self.tab.get(id(pembuka)) if pembuka else None)
        print(f"[sniff] tab #{no} dibuka")
        page.on("close", lambda p: (self.catat("tab_ditutup", tab=no, url=p.url),
                                    print(f"[sniff] tab #{no} ditutup")))
        page.on("framenavigated", lambda f: self.catat(
            "navigasi", tab=no, frame="utama" if f.parent_frame is None else "iframe", url=f.url))
        page.on("download", lambda d: self.simpan_unduhan(no, d))
        page.on("websocket", lambda ws: self.pasang_websocket(no, ws))

    def pasang_websocket(self, no: int, ws) -> None:
        self.catat("websocket_buka", tab=no, url=ws.url)
        ws.on("framesent", lambda d: self.catat("websocket_kirim", tab=no, url=ws.url,
                                                data=sensor(d if isinstance(d, str) else repr(d))))
        ws.on("framereceived", lambda d: self.catat("websocket_terima", tab=no, url=ws.url,
                                                    data=d if isinstance(d, str) else repr(d)))
        ws.on("close", lambda _: self.catat("websocket_tutup", tab=no, url=ws.url))

    def simpan_unduhan(self, no: int, d) -> None:
        self.jumlah_unduhan += 1
        print(f"[sniff] download dimulai di tab #{no}: {d.suggested_filename}")
        self.catat("download_mulai", tab=no, url=d.url, nama_file=d.suggested_filename)
        try:
            self.folder_unduhan.mkdir(exist_ok=True)
            tujuan = self.folder_unduhan / f"{self.jumlah_unduhan}_{d.suggested_filename}"
            d.save_as(str(tujuan))             # menunggu sampai download selesai
            self.catat("download_tersimpan", tab=no, file=tujuan.name, byte=tujuan.stat().st_size)
            print(f"[sniff] file unduhan disimpan: {tujuan.name}")
        except PlaywrightError as e:
            self.catat("download_gagal", tab=no, url=d.url, error=str(e))

    # ------------------------------------------------------------ request/response
    def on_request(self, req) -> None:
        # PENTING: catat dulu tanpa memanggil fungsi Playwright yang "menunggu"
        # (mis. all_headers). Saat menunggu, event requestfinished bisa datang lebih dulu
        # sehingga request tercatat "tidak selesai". Header lengkap diambil saat selesai.
        body = req.post_data_buffer
        data = {
            "_req": req,
            "mulai": _now(), "tab": self._no_tab(req), "frame": self._frame(req),
            "method": req.method, "tipe": req.resource_type, "url": req.url,
            "redirect_dari": req.redirected_from.url if req.redirected_from else None,
            "request_headers": req.headers,
            "request_body": _isi_body(body)["body"] if body else None,
        }
        if not data["request_body"] and data["method"] not in ("GET", "HEAD"):
            # body dari skrip halaman selalu tiba SEBELUM request dikirim (fetch menunggu)
            js = self._ambil_body_js(req, data["method"], data["url"])
            if js:
                data["request_body"], data["request_body_sumber"] = js, "skrip halaman"
        self.pending[id(req)] = data
        if req.redirected_from is not None:    # request lama (3xx) tidak memicu requestfinished
            self._selesai(req.redirected_from, "redirect")

    def on_body_js(self, source, data: dict) -> None:
        try:
            halaman = id(source["page"])
        except (KeyError, TypeError):
            halaman = None
        self.body_js.append({**data, "halaman": halaman})

    def _ambil_body_js(self, req, method: str, url: str) -> str | None:
        try:
            halaman = id(req.frame.page)
        except PlaywrightError:
            halaman = None
        for i, b in enumerate(self.body_js):   # urutan kirim = urutan request di halaman itu
            if b["method"] == method and b["url"] == url and b["halaman"] == halaman:
                return sensor(self.body_js.pop(i)["body"])
        return None

    def _selesai(self, req, status_akhir: str) -> None:
        data = self.pending.pop(id(req), None)
        if data is None:
            return
        data.pop("_req", None)
        try:
            data["request_headers"] = req.all_headers()
        except PlaywrightError:
            pass
        if data["tab"] is None:                # request pertama di tab baru: tab baru terdaftar
            data["tab"] = self._no_tab(req)
        if data["frame"] is None:
            data["frame"] = self._frame(req)
        data.update({"selesai": _now(), "hasil": status_akhir})
        try:
            res = req.response()
        except PlaywrightError:
            res = None
        if res is not None:
            try:
                header = res.all_headers()
            except PlaywrightError:
                header = res.headers
            data.update({"status": res.status, "status_text": res.status_text,
                         "response_headers": header})
            if status_akhir in ("selesai", "redirect"):
                try:
                    data.update(_isi_body(res.body()))
                except PlaywrightError as e:
                    data["body_error"] = str(e)[:200]
        self._tulis(data)

    def on_finished(self, req) -> None:
        self._selesai(req, "selesai")

    def on_failed(self, req) -> None:
        # net::ERR_ABORTED pada dokumen biasanya berarti response-nya menjadi download
        self._selesai(req, f"gagal/dibatalkan: {req.failure}")

    def tutup(self) -> None:
        for data in list(self.pending.values()):   # request yang belum selesai saat berhenti
            data.pop("_req", None)
            data.update({"selesai": None, "hasil": "tidak selesai saat rekaman dihentikan"})
            self._tulis(data)
        self.pending.clear()
        self.jsonl.close()
        self.simpan_events()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=START_URL)
    ap.add_argument("--profil", action="store_true",
                    help="pakai profil browser tetap (login tersimpan antar sesi)")
    ap.add_argument("--ringkas", action="store_true",
                    help="buang analytics & isi file statis dari HAR")
    ap.add_argument("--auto-stop", type=float, help="(untuk tes) berhenti otomatis setelah N detik")
    ap.add_argument("--headless", action="store_true", help="(untuk tes)")
    ap.add_argument("--out", type=Path, help="(untuk tes) folder output lain")
    args = ap.parse_args()

    out_dir = args.out or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    nama = f"sniff_jubel_{datetime.now():%Y%m%d_%H%M%S}"
    har_path = out_dir / f"{nama}.har"
    rek = Perekam(out_dir, nama)
    berhenti = threading.Event()

    # Profil persisten = satu context untuk seluruh browser, jadi tab Ctrl+T juga terekam
    profil = PROFIL_TETAP if args.profil else Path(tempfile.mkdtemp(prefix="sniff_profil_"))
    opsi = dict(headless=args.headless, accept_downloads=True, record_har_path=str(har_path),
                record_har_content="embed", record_har_mode="full", no_viewport=True)

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(str(profil), channel="chrome", **opsi)
        except PlaywrightError:
            ctx = p.chromium.launch_persistent_context(str(profil), **opsi)
        ctx.expose_binding("__sniffBody", rek.on_body_js)
        ctx.add_init_script(SKRIP_BODY)
        ctx.on("page", rek.pasang_tab)
        ctx.on("request", rek.on_request)
        ctx.on("requestfinished", rek.on_finished)
        ctx.on("requestfailed", rek.on_failed)
        ctx.on("close", lambda _: berhenti.set())
        for pg in ctx.pages:
            rek.pasang_tab(pg)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url)

        print(f"[sniff] merekam semua tab... Output: {out_dir / nama}*")
        print("[sniff] Lakukan aksi di browser, lalu kembali ke jendela ini dan tekan ENTER.")
        if not args.auto_stop:
            threading.Thread(target=lambda: (input(), berhenti.set()), daemon=True).start()

        mulai = datetime.now()
        terakhir_simpan = mulai
        try:
            while not berhenti.is_set():
                sekarang = datetime.now()
                if args.auto_stop and (sekarang - mulai).total_seconds() > args.auto_stop:
                    break
                if (sekarang - terakhir_simpan).total_seconds() > 5:
                    rek.simpan_events()
                    terakhir_simpan = sekarang
                if not ctx.pages:
                    print("[sniff] semua tab tertutup, berhenti.")
                    break
                try:
                    ctx.pages[0].wait_for_timeout(300)   # sekaligus memproses event
                except PlaywrightError:
                    pass                                 # tab yang ditunggu baru saja ditutup
        except (KeyboardInterrupt, EOFError):
            print("[sniff] dihentikan, mencoba menyimpan...")

        rek.tutup()
        try:
            ctx.close()                      # file HAR ditulis saat context ditutup
        except PlaywrightError as e:
            print(f"[sniff] HAR mungkin tidak lengkap: {e}")

    if not args.profil:
        shutil.rmtree(profil, ignore_errors=True)
    if har_path.exists():
        semula, sisa = rapikan_har(har_path, args.ringkas)
        print(f"[sniff] HAR: {sisa} entri" + (f" ({semula - sisa} analytics dibuang)" if args.ringkas else ""))
    print(f"[sniff] selesai: {rek.jumlah} request, {len(rek.tab)} tab, {rek.jumlah_unduhan} download.")
    print(f"[sniff] {out_dir / nama}_requests.jsonl")


if __name__ == "__main__":
    main()
