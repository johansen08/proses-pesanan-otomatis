"""Rekam semua request fetch/XHR (request + response body) di v2.jubelio.com,
lintas banyak tab/halaman, ke satu file JSON. Jalankan: python sniff_jubel.py, lalu Ctrl+C untuk stop.

Versi ini TIDAK memakai cookie: mulai dari halaman login dan login manual di browser.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from DrissionPage import Chromium, ChromiumOptions
from DrissionPage._units.listener import DataPacket

START_URL = "https://v2.jubelio.com/auth/login"
OUTPUT_DIR = Path(__file__).parent / "sniff_output"
LOCAL_PORT = 19222  # bukan 9222 (default) - hindari bentrok dgn instance Chrome/tool lain
AUTOSAVE_INTERVAL_SEC = 5
RES_TYPES = ["XHR", "Fetch"]
MAX_BODY_CHARS = 500_000

_lock = threading.Lock()
_stop_event = threading.Event()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _truncate(text):
    if isinstance(text, str) and len(text) > MAX_BODY_CHARS:
        return text[:MAX_BODY_CHARS] + f"...[truncated, {len(text)} chars total]"
    return text


def record_packet(packet: DataPacket) -> dict:
    entry: dict = {
        "tab_id": packet.tab_id,
        "url": packet.url,
        "method": packet.method,
        "resource_type": packet.resourceType,
        "is_failed": packet.is_failed,
        "timestamp": _now(),
        "request": None,
        "response": None,
        "fail_info": None,
    }

    try:
        req = packet.request
        entry["request"] = {
            "headers": dict(req.headers or {}),
            "params": req.params,
            "post_data": _truncate(req.postData),
        }
    except Exception as e:
        entry["request"] = {"error": str(e)}

    if packet.is_failed:
        try:
            fi = packet.fail_info
            entry["fail_info"] = (
                {"error_text": fi.errorText, "canceled": fi.canceled, "blocked_reason": fi.blockedReason}
                if fi else None
            )
        except Exception as e:
            entry["fail_info"] = {"error": str(e)}
    else:
        try:
            resp = packet.response
            body = resp.body if resp else None
            is_binary = isinstance(body, (bytes, bytearray))
            entry["response"] = {
                "status": resp.status if resp else None,
                "status_text": resp.statusText if resp else None,
                "headers": dict(resp.headers or {}) if resp else {},
                "body": None if is_binary else _truncate(body),
                "binary": is_binary,
                "body_size": len(body) if is_binary else None,
            }
        except Exception as e:
            entry["response"] = {"error": str(e)}

    return entry


def capture_loop(tab, state: dict) -> None:
    try:
        tab.listen.start(res_type=RES_TYPES, method=True)
        for packet in tab.listen.steps():
            entry = record_packet(packet)
            with _lock:
                state["requests"].append(entry)
    except Exception as e:
        print(f"[sniff] listener tab {getattr(tab, 'tab_id', '?')} berhenti: {e}")


def attach_tab(tab, tab_id: str, attached: set[str], state: dict, threads: list) -> None:
    with _lock:
        if tab_id in attached:
            return
        attached.add(tab_id)
        state["tabs"].append({"tab_id": tab_id, "attached_at": _now()})
    print(f"[sniff] merekam tab baru: {tab_id}")
    th = threading.Thread(target=capture_loop, args=(tab, state), daemon=True)
    th.start()
    threads.append((tab, th))


def watch_new_tabs(browser, attached: set[str], state: dict, threads: list) -> None:
    while not _stop_event.is_set():
        new_id = browser.wait.new_tab(timeout=2)
        if new_id and new_id not in attached:
            try:
                new_tab = browser.get_tab(new_id)
            except Exception:
                continue
            attach_tab(new_tab, new_id, attached, state, threads)


def save_state(state: dict, output_path: Path) -> None:
    with _lock:
        payload = json.dumps(state, ensure_ascii=False, indent=2, default=str)
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(output_path)


def autosave_loop(state: dict, output_path: Path) -> None:
    while not _stop_event.wait(AUTOSAVE_INTERVAL_SEC):
        save_state(state, output_path)


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    session_start = datetime.now()
    output_path = OUTPUT_DIR / f"sniff_jubel_{session_start:%Y%m%d_%H%M%S}.json"
    state = {
        "meta": {
            "session_start": session_start.isoformat(timespec="seconds"),
            "session_end": None,
            "start_url": START_URL,
            "local_port": LOCAL_PORT,
        },
        "tabs": [],
        "requests": [],
    }
    attached: set[str] = set()
    threads: list = []

    co = ChromiumOptions().set_local_port(LOCAL_PORT)
    co.headless(False)
    browser = Chromium(co)
    tab = browser.latest_tab

    tab.get(START_URL)
    print("[sniff] mulai dari halaman login, silakan login manual di browser")

    attach_tab(tab, tab.tab_id, attached, state, threads)
    threading.Thread(target=watch_new_tabs, args=(browser, attached, state, threads), daemon=True).start()
    threading.Thread(target=autosave_loop, args=(state, output_path), daemon=True).start()

    print(f"[sniff] merekam fetch/XHR... tekan Ctrl+C untuk berhenti. Output: {output_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[sniff] menghentikan...")
    finally:
        _stop_event.set()
        for t, _ in threads:
            try:
                t.listen.stop()
            except Exception:
                pass
        for _, th in threads:
            th.join(timeout=3)
        state["meta"]["session_end"] = _now()
        save_state(state, output_path)
        try:
            browser.quit()
        except Exception:
            pass
        print(f"[sniff] selesai, tersimpan di {output_path}")


if __name__ == "__main__":
    main()
