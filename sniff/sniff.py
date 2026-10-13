"""Rekam semua request fetch/XHR (request + response body) di seller-id.tokopedia.com,
lintas banyak tab/halaman, ke satu file JSON. Jalankan: python sniff.py, lalu Ctrl+C untuk stop.

Cookie opsional: taruh file `seller-id.tokopedia.com.cookies.json` di folder ini,
isi JSON list of dict, mis. [{"name": "sessionid", "value": "...", "domain": ".tokopedia.com"}].
"""

from __future__ import annotations

from pathlib import Path

from sniff_drission import jalankan

START_URL = "https://seller-id.tokopedia.com/promotion/marketing-tools/discount/edit/7670014846093788935?back=1&scene=republish&shop_region=ID"
COOKIE_FILE = Path(__file__).parent / "seller-id.tokopedia.com.cookies.json"

if __name__ == "__main__":
    jalankan(START_URL, prefix="sniff", cookie_file=COOKIE_FILE)
