"""Fungsi kecil yang dipakai bersama beberapa modul: tulis JSON atomik dan setup logging."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def tulis_json_atomik(file: Path, data, indent: int = 1) -> None:
    """Tulis `data` sebagai JSON ke `file` secara atomik: ke file sementara (unik per PID) dulu,
    baru os.replace, supaya file lama tetap utuh kalau proses terputus di tengah."""
    file.parent.mkdir(parents=True, exist_ok=True)
    sementara = file.with_name(f"{file.name}.{os.getpid()}.tmp")
    sementara.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
    os.replace(sementara, file)


def atur_log(folder_log: Path, awalan: str, datefmt: str) -> None:
    """Logging ke `folder_log/<awalan>_YYYY-MM.log` + layar (stdout)."""
    folder_log.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt=datefmt,
        handlers=[
            logging.FileHandler(folder_log / f"{awalan}_{datetime.now():%Y-%m}.log",
                                encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
