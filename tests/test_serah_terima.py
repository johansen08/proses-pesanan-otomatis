"""Uji serah_terima.py (kunci serah-terima antar perangkat & cek file konflik sinkron) - murni
filesystem sementara, tanpa API.

Jalankan:  .venv\\Scripts\\python tests\\test_serah_terima.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import serah_terima as st  # noqa: E402


def _siap(tmp: str) -> Path:
    log = Path(tmp) / "logs"
    log.mkdir()
    st.atur_folder(log)
    st._memegang = False
    return log


def _sebagai(nama: str):
    return mock.patch.dict(os.environ, {"PERANGKAT": nama})


def uji_ambil_lepas_dan_tolak_perangkat_lain():
    with tempfile.TemporaryDirectory() as tmp:
        _siap(tmp)
        with _sebagai("PC-KANTOR"):
            assert st.ambil("harian") == (None, [])
            assert "DIPEGANG PC-KANTOR" in st.status()
        with _sebagai("LAPTOP"):
            galat, _ = st.ambil("malam")
            assert galat and "PC-KANTOR" in galat and "--abaikan-kunci" in galat
            # dipaksa: lolos, tapi dicatat sebagai peringatan
            galat, peringatan = st.ambil("malam", abaikan=True)
            assert galat is None and peringatan and peringatan[0].startswith("DIPAKSA")
        with _sebagai("PC-KANTOR"):
            st.lepas()   # kunci sudah diambil alih LAPTOP: tidak boleh menimpa
            assert st._baca()["perangkat"] == "LAPTOP" and st._baca()["pid"]
        with _sebagai("LAPTOP"):
            st._memegang = True
            st.lepas()
            d = st._baca()
            assert d["pid"] == [] and d["perangkat_terakhir"] == "LAPTOP"
            assert "BEBAS" in st.status()


def uji_perangkat_sama_boleh_paralel():
    with tempfile.TemporaryDirectory() as tmp:
        _siap(tmp)
        with _sebagai("PC-KANTOR"), mock.patch.object(os, "getpid", return_value=111):
            assert st.ambil("cetak A")[0] is None
        with _sebagai("PC-KANTOR"), mock.patch.object(os, "getpid", return_value=222):
            assert st.ambil("cetak B")[0] is None
            assert st._baca()["pid"] == [111, 222]
            st.lepas()
            assert st._baca()["pid"] == [111]   # masih dipegang proses 111


def uji_kunci_basi_diambil_alih_dan_file_rusak_dianggap_bebas():
    with tempfile.TemporaryDirectory() as tmp:
        log = _siap(tmp)
        basi = time.time() - st.TTL_DETIK - 60
        (log / "serah_terima.json").write_text(json.dumps(
            {"perangkat": "PC-KANTOR", "pid": [1], "pembaruan": basi}), encoding="utf-8")
        with _sebagai("LAPTOP"):
            assert st.ambil("malam")[0] is None
        st._memegang = False
        (log / "serah_terima.json").write_text("{setengah tersinkron", encoding="utf-8")
        with _sebagai("PC-KANTOR"):
            assert st.ambil("harian")[0] is None


def uji_peringatan_kalau_perangkat_lain_baru_selesai():
    with tempfile.TemporaryDirectory() as tmp:
        log = _siap(tmp)
        (log / "serah_terima.json").write_text(json.dumps(
            {"perangkat": "PC-KANTOR", "pid": [], "perangkat_terakhir": "PC-KANTOR",
             "selesai": time.time() - 60, "pembaruan": time.time() - 60}), encoding="utf-8")
        with _sebagai("LAPTOP"):
            galat, peringatan = st.ambil("malam")
            assert galat is None and len(peringatan) == 1 and "SINKRON" in peringatan[0]
        st._memegang = False
        (log / "serah_terima.json").write_text(json.dumps(
            {"perangkat": "PC-KANTOR", "pid": [], "perangkat_terakhir": "PC-KANTOR",
             "selesai": time.time() - 3 * 3600}), encoding="utf-8")
        with _sebagai("LAPTOP"):
            assert st.ambil("malam") == (None, [])


def uji_tanpa_atur_folder_tidak_berbuat_apa_apa():
    st._file_kunci = None
    assert st.ambil("x") == (None, [])
    st.lepas()


def uji_cari_konflik():
    from datetime import date
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hari_ini = root / "label-pengiriman" / str(date.today()) / "1"
        lama = root / "label-pengiriman" / "2020-01-01" / "1"
        for f in (root / "logs", root / "data", hari_ini, lama):
            f.mkdir(parents=True)
        for ok in ("logs/sudah_dicetak.txt", "data/riwayat_picklist.xlsx"):
            (root / ok).write_text("x")
        (hari_ini / "PICKLIST.xlsx").write_text("x")
        salah = [root / "logs/sudah_dicetak.sync-conflict-20261009-201500-ABC.txt",
                 root / "logs/picklist_terakhir (1).txt",
                 root / "data/riwayat_picklist-LAPTOP-X1.xlsx",
                 hari_ini / "PICKLIST - conflicted copy.xlsx",
                 lama / "PICKLIST (1).xlsx"]   # sesi lama: di luar jendela hari, tidak diperiksa
        for f in salah:
            f.write_text("x")
        with _sebagai("LAPTOP-X1"):
            hasil = st.cari_konflik(root, hari=3)
        assert set(hasil) == set(salah[:4]), hasil
        with _sebagai("LAPTOP-X1"):
            lap = st.laporan_konflik(root)
        assert lap and "4 file" in lap[0]
        # tanpa konflik -> kosong
        for f in salah:
            f.unlink()
        with _sebagai("LAPTOP-X1"):
            assert st.laporan_konflik(root) == []


if __name__ == "__main__":
    for nama, fungsi in sorted(globals().items()):
        if nama.startswith("uji_") and callable(fungsi):
            fungsi()
            print("OK", nama)
    print("Semua uji serah_terima lolos.")
