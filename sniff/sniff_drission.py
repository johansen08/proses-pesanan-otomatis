"""Inti perekam fetch/XHR berbasis DrissionPage, dipakai bersama oleh `sniff.py` dan `sniff_jubel.py`.

Merekam request + response body di semua tab ke satu file JSON (ditulis berkala dan saat berhenti).
Berhenti dengan Ctrl+C. Perekam yang lebih lengkap (semua jenis request, HAR, WebSocket, download)
ada di `sniff_jubel_v2.py` (Playwright).
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from DrissionPage import Chromium, ChromiumOptions
from DrissionPage._units.listener import DataPacket

OUTPUT_DIR = Path(__file__).parent / "sniff_output"
LOCAL_PORT = 19222  # bukan 9222 (default) - hindari bentrok dgn instance Chrome/tool lain
AUTOSAVE_INTERVAL_SEC = 5
RES_TYPES = ["XHR", "Fetch"]
MAX_BODY_CHARS = 500_000


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _truncate(text):
    if isinstance(text, str) and len(text) > MAX_BODY_CHARS:
        return text[:MAX_BODY_CHARS] + f"...[truncated, {len(text)} chars total]"
    return text


def load_cookies(cookie_file: Path) -> list[dict] | None:
    """Baca cookie (list of dict, atau satu dict) dari file JSON; None bila tidak ada/tidak valid."""
    if not cookie_file.exists():
        return None
    try:
        data = json.loads(cookie_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[sniff] gagal baca {cookie_file.name}: {e}")
        return None
    if isinstance(data, dict):
        data = [data]
    return data if isinstance(data, list) and data else None


def _rekam_request(packet: DataPacket) -> dict:
    try:
        req = packet.request
        return {
            "headers": dict(req.headers or {}),
            "params": req.params,
            "post_data": _truncate(req.postData),
        }
    except Exception as e:
        return {"error": str(e)}


def _rekam_response(packet: DataPacket) -> dict:
    try:
        resp = packet.response
        body = resp.body if resp else None
        is_binary = isinstance(body, (bytes, bytearray))
        return {
            "status": resp.status if resp else None,
            "status_text": resp.statusText if resp else None,
            "headers": dict(resp.headers or {}) if resp else {},
            "body": None if is_binary else _truncate(body),
            "binary": is_binary,
            "body_size": len(body) if is_binary else None,
        }
    except Exception as e:
        return {"error": str(e)}


def _rekam_kegagalan(packet: DataPacket) -> dict | None:
    try:
        fi = packet.fail_info
        return (
            {"error_text": fi.errorText, "canceled": fi.canceled, "blocked_reason": fi.blockedReason}
            if fi else None
        )
    except Exception as e:
        return {"error": str(e)}


def record_packet(packet: DataPacket) -> dict:
    """Ubah satu paket jaringan menjadi dict yang bisa diserialisasi ke JSON."""
    return {
        "tab_id": packet.tab_id,
        "url": packet.url,
        "method": packet.method,
        "resource_type": packet.resourceType,
        "is_failed": packet.is_failed,
        "timestamp": _now(),
        "request": _rekam_request(packet),
        "response": None if packet.is_failed else _rekam_response(packet),
        "fail_info": _rekam_kegagalan(packet) if packet.is_failed else None,
    }


class Perekam:
    """Mengumpulkan request dari semua tab ke `self.state` dan menyimpannya ke `output_path`."""

    def __init__(self, start_url: str, output_path: Path):
        self.output_path = output_path
        self.state = {
            "meta": {
                "session_start": _now(),
                "session_end": None,
                "start_url": start_url,
                "local_port": LOCAL_PORT,
            },
            "tabs": [],
            "requests": [],
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._attached: set[str] = set()
        self._threads: list[tuple[object, threading.Thread]] = []

    def _capture_loop(self, tab) -> None:
        try:
            tab.listen.start(res_type=RES_TYPES, method=True)
            for packet in tab.listen.steps():
                entry = record_packet(packet)
                with self._lock:
                    self.state["requests"].append(entry)
        except Exception as e:
            print(f"[sniff] listener tab {getattr(tab, 'tab_id', '?')} berhenti: {e}")

    def attach_tab(self, tab, tab_id: str) -> None:
        with self._lock:
            if tab_id in self._attached:
                return
            self._attached.add(tab_id)
            self.state["tabs"].append({"tab_id": tab_id, "attached_at": _now()})
        print(f"[sniff] merekam tab baru: {tab_id}")
        th = threading.Thread(target=self._capture_loop, args=(tab,), daemon=True)
        th.start()
        self._threads.append((tab, th))

    def _watch_new_tabs(self, browser) -> None:
        while not self._stop.is_set():
            new_id = browser.wait.new_tab(timeout=2)
            if new_id and new_id not in self._attached:
                try:
                    new_tab = browser.get_tab(new_id)
                except Exception:
                    continue
                self.attach_tab(new_tab, new_id)

    def save(self) -> None:
        with self._lock:
            payload = json.dumps(self.state, ensure_ascii=False, indent=2, default=str)
        tmp = self.output_path.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self.output_path)

    def _autosave_loop(self) -> None:
        while not self._stop.wait(AUTOSAVE_INTERVAL_SEC):
            self.save()

    def mulai(self, browser, tab) -> None:
        """Pasang perekam di tab awal, lalu pantau tab baru & simpan berkala di thread latar."""
        self.attach_tab(tab, tab.tab_id)
        threading.Thread(target=self._watch_new_tabs, args=(browser,), daemon=True).start()
        threading.Thread(target=self._autosave_loop, daemon=True).start()

    def berhenti(self, browser) -> None:
        self._stop.set()
        for tab, _ in self._threads:
            try:
                tab.listen.stop()
            except Exception:
                pass
        for _, th in self._threads:
            th.join(timeout=3)
        self.state["meta"]["session_end"] = _now()
        self.save()
        try:
            browser.quit()
        except Exception:
            pass


def jalankan(start_url: str, prefix: str, cookie_file: Path | None = None) -> None:
    """Buka Chrome di `start_url` dan rekam sampai Ctrl+C.

    `prefix` = awalan nama file output (sniff_output/<prefix>_<waktu>.json).
    `cookie_file` opsional: bila ada dan valid, cookie dimuat lalu halaman dibuka ulang.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.json"
    perekam = Perekam(start_url, output_path)

    co = ChromiumOptions().set_local_port(LOCAL_PORT)
    co.headless(False)
    browser = Chromium(co)
    tab = browser.latest_tab

    tab.get(start_url)
    if cookie_file is None:
        print("[sniff] mulai dari halaman login, silakan login manual di browser")
    else:
        cookies = load_cookies(cookie_file)
        if cookies:
            tab.set.cookies(cookies)
            print(f"[sniff] {len(cookies)} cookie dimuat dari {cookie_file.name}")
        else:
            print("[sniff] tidak ada file cookie valid, lanjut tanpa cookie (login manual)")
        tab.get(start_url)  # muat ulang supaya cookie terpakai

    perekam.mulai(browser, tab)
    print(f"[sniff] merekam fetch/XHR... tekan Ctrl+C untuk berhenti. Output: {output_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[sniff] menghentikan...")
    finally:
        perekam.berhenti(browser)
        print(f"[sniff] selesai, tersimpan di {output_path}")
