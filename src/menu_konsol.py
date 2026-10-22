"""Menu konsol Harian/Event/Malam - pengganti isi `bat\\proses-harian.bat`, `proses-event.bat`,
`proses-malam.bat` dan kembaran `-uji`-nya (file .bat kini hanya peluncur tipis ke sini).

Daftar langkah, flag, dan aturan tiap TIPE ada di alur.py (satu sumber, sama dengan menu Harian
di UI lewat jalankan_harian.py). Tiap langkah = SATU proses `main.py <flag> [--jalankan]`
berurutan (bukan memanggil fungsi langsung); langkah yang gagal TIDAK menghentikan langkah
berikutnya; di akhir satu TIPE dicetak rekap waktu (`rekap_waktu.py`).

Pemakaian:
    python src/menu_konsol.py harian [--uji]     # menu TIPE 1-4
    python src/menu_konsol.py event  [--uji]     # menu EVENT - TIPE 1-4 + MALAM
    python src/menu_konsol.py malam  [--uji]     # langsung proses malam, tanpa menu (tanpa IRESIS)
`--uji`: mode uji (tanpa `--jalankan` = read-only, tidak mengubah data di Jubelio) dan tanpa
konfirmasi Y/N.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import alur
import coba_ulang

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent


def _input(prompt: str = "") -> str:
    """input() dicari saat dipanggil (bukan diikat saat def) supaya mudah ditiru di tes."""
    return input(prompt)


def tampil(teks: str) -> str:
    """Konsol Windows (cp1252/cp437) tidak selalu bisa menampilkan '≤' - pakai '<='."""
    return teks.replace("≤", "<=")


def _jalankan_proses(argumen: list[str], env: dict) -> int:
    return subprocess.call(argumen, env=env, cwd=str(ROOT))


def jalankan_tipe(judul: str, uji: bool, sesi: str, jalankan=_jalankan_proses,
                  sekarang=time.time, cetak=print) -> list[str]:
    """Jalankan semua langkah preset `judul` berurutan lalu rekap waktu. Mengembalikan entri
    waktu ("NAMA:mulai:selesai") yang dikirim ke rekap_waktu.py."""
    langkah = alur.langkah_urut(judul, alur.PRESET[judul])
    awal = sekarang()
    # WAKTU_MENU_MULAI: dibaca main.py untuk --non-wajib-sore (TIPE 1), sama dengan jalankan_harian.py
    env = {**os.environ, "LABEL_SESI_DIR": sesi, "WAKTU_MENU_MULAI": str(awal)}
    waktu = []
    cetak("")
    for i, nama in enumerate(langkah, 1):
        cetak(f"=== {i}/{len(langkah)} {'Uji ' if uji else ''}{tampil(nama).upper()} ===")
        mulai = sekarang()
        jalankan([sys.executable, str(SRC / "main.py"), *alur.susun_argumen(judul, nama, uji)], env)
        waktu.append(f"{tampil(nama).upper()}:{mulai}:{sekarang()}")
        cetak("")
    # percobaan ulang otomatis picklist gagal/gagal unduh PDF selama TIPE ini (sekali lagi)
    mulai = sekarang()
    if coba_ulang.jalankan(awal, uji, lambda arg: jalankan(arg, env), cetak)[0]:
        waktu.append(f"{coba_ulang.NAMA_LANGKAH}:{mulai}:{sekarang()}")
    cetak(f"{judul} selesai.")
    jalankan([sys.executable, str(SRC / "rekap_waktu.py"), judul, *waktu], env)
    return waktu


def _ya(jawaban: str) -> bool:
    return jawaban.strip().upper() == "Y"


def konfirmasi(judul: str, catatan: str, uji: bool, masukan=_input, cetak=print) -> bool:
    if uji:
        return True
    cetak("")
    cetak(f"PERHATIAN: proses SUNGGUHAN di Jubelio. {catatan}".rstrip())
    return _ya(masukan(f"Lanjutkan {judul}? (Y/N): "))


def cek_jam(judul: str, teks_jam: str, masukan=_input, cetak=print, dalam_jam=None) -> bool:
    """Sanity check jam (soft warning Y/N, bukan blokir). True = boleh lanjut."""
    kunci = alur.MENU_JAM.get(judul)
    if kunci is None:
        return True
    if dalam_jam is None:
        from main import dalam_jam_menu as dalam_jam
    if dalam_jam(kunci):
        return True
    cetak(f"PERINGATAN: sekarang di luar jam {teks_jam}.")
    return _ya(masukan("Apakah anda tidak salah memilih menu? (Y/N): "))


def _sesi_baru() -> str:
    from main import sesi_label_baru
    return sesi_label_baru()


def menu(mode: str, uji: bool, sesi: str, masukan=_input, cetak=print, bersihkan_layar=None,
         dalam_jam=None, sesi_baru=_sesi_baru, **kw) -> None:
    """Loop menu `harian` atau `event` sampai pengguna memilih 0. `sesi` dipakai untuk TIPE
    pertama yang dijalankan; tiap TIPE berikutnya (cmd tidak ditutup) mendapat sesi baru lewat
    `sesi_baru()` - jangan memakai ulang sesi (TIPE 1 jam 07.00 + TIPE 1 jam 08.15 harus 2 sesi)."""
    sesi_terpakai = False
    butir = alur.MENU_HARIAN if mode == "harian" else alur.MENU_EVENT
    judul_menu = ("PROSES PESANAN OTOMATIS (NON EVENT)" if mode == "harian"
                  else "PROSES PESANAN OTOMATIS (EVENT: 10.10 / 11.11 / 12.12 DST)")
    if uji:
        judul_menu += " - MODE UJI (tidak ada perubahan di Jubelio)"
    while True:
        if bersihkan_layar:
            bersihkan_layar()
        cetak("=" * 66)
        cetak(f"  {judul_menu}")
        cetak("=" * 66)
        for no, (_, teks, _, _) in enumerate(butir, 1):
            cetak(f"  {no}. {'Uji ' if uji else ''}{teks}")
        cetak("  0. Keluar")
        cetak("=" * 66)
        pilih = masukan(f"Pilih menu (0-{len(butir)}): ").strip()
        if pilih == "0":
            return
        if not (pilih.isdigit() and 1 <= int(pilih) <= len(butir)):
            cetak("")
            cetak(f'Pilihan "{pilih}" tidak dikenali, coba lagi.')
            masukan("Tekan Enter untuk melanjutkan...")
            continue
        judul, _, teks_jam, catatan = butir[int(pilih) - 1]
        if teks_jam and not cek_jam(judul, teks_jam, masukan, cetak, dalam_jam):
            continue
        if not konfirmasi(judul, catatan, uji, masukan, cetak):
            continue
        if sesi_terpakai:
            sesi = sesi_baru()
            cetak(f"Sesi label: {sesi}")
        sesi_terpakai = True
        jalankan_tipe(judul, uji, sesi, cetak=cetak, **kw)
        masukan("Tekan Enter untuk kembali ke menu...")


def malam(uji: bool, sesi: str, masukan=_input, cetak=print, **kw) -> None:
    """Proses MALAM (harian): urgent + SPX-J&T gabungan, tanpa menu dan tanpa IRESIS."""
    cetak("=" * 66)
    cetak(f"  PROSES MALAM ({'MODE UJI - tidak mengubah data' if uji else 'SUNGGUHAN'})")
    cetak("  1. Urgent Lazada  2. Urgent GTL & SiCepat  3. Urgent JNE & LEX  "
          "4. SPX - J&T (spesial, 1 qty, kombinasi)")
    cetak("=" * 66)
    if uji:
        cetak("MODE UJI: hanya menampilkan rencana, tidak mengubah data di Jubelio.")
        ok = _ya(masukan("Lanjutkan uji proses malam? (Y/N): "))
    else:
        cetak("PERHATIAN: proses SUNGGUHAN di Jubelio.")
        ok = _ya(masukan("Lanjutkan proses malam? (Y/N): "))
    if ok:
        jalankan_tipe("MALAM", uji, sesi, cetak=cetak, **kw)
        masukan("Tekan Enter untuk menutup...")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["harian", "event", "malam"])
    ap.add_argument("--uji", action="store_true", help="mode uji: tanpa --jalankan & tanpa konfirmasi")
    args = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    from main import sesi_label_baru       # dihitung SEKALI per sesi menu ini (seperti .bat dulu)
    sesi = sesi_label_baru()
    print(f"Sesi label: {sesi}")
    bersihkan = (lambda: os.system("cls")) if sys.stdout.isatty() and os.name == "nt" else None
    if args.mode == "malam":
        malam(args.uji, sesi)
    else:
        menu(args.mode, args.uji, sesi, bersihkan_layar=bersihkan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
