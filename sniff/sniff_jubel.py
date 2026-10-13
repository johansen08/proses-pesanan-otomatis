"""Rekam semua request fetch/XHR (request + response body) di v2.jubelio.com,
lintas banyak tab/halaman, ke satu file JSON. Jalankan: python sniff_jubel.py, lalu Ctrl+C untuk stop.

Versi ini TIDAK memakai cookie: mulai dari halaman login dan login manual di browser.
(Untuk rekaman lengkap termasuk HAR/WebSocket/download, pakai `sniff_jubel_v2.py`.)
"""

from __future__ import annotations

from sniff_drission import jalankan

START_URL = "https://v2.jubelio.com/auth/login"

if __name__ == "__main__":
    jalankan(START_URL, prefix="sniff_jubel")
