"""Uji regresi file .bat.

1) File .bat WAJIB berakhiran baris CRLF. Di file LF, cmd.exe salah menghitung posisi saat
mencari label (`call :catat_waktu`, `goto menu`), sehingga eksekusi melompat ke baris
yang salah: memilih TIPE 1 bisa menjalankan langkah TIPE 2/3/4, dan menu "0. Keluar"
malah melanjutkan proses SUNGGUHAN (kejadian 2026-10-01: "0" menjalankan
"8/8 SPX KOMBINASI"). Sejak menu pindah ke src/menu_konsol.py (daftar langkah di src/alur.py,
diuji tests/test_alur.py) bat menu hanya peluncur tipis tanpa label; CRLF tetap dicek untuk
semua .bat.

2) Perintah di dalam `for /f ... in ('...')` TIDAK boleh diawali tanda kutip ganda.
Kenapa: for /f menjalankan perintahnya lewat `cmd /c`. Kalau perintah diawali `"` dan
berisi kutip lain (mis. `".venv\\Scripts\\python.exe" -c "import time; ..."`), cmd.exe
membuang kutip PERTAMA dan TERAKHIR, sehingga yang dijalankan jadi
`.venv\\Scripts\\python.exe" -c "import ...` dan muncul error:

    '.venv\\Scripts\\python.exe" -c "import' is not recognized as an internal or
    external command, operable program or batch file.

Bug ini sudah berulang kali muncul lagi tiap ada for /f baru yang menyalin pola baris
biasa `".venv\\Scripts\\python.exe" src\\main.py ...` (yang AMAN di luar for /f). Solusinya:
tulis path python.exe TANPA kutip di dalam for /f (path relatif tanpa spasi, aman karena
.bat sudah `cd /d "%~dp0"` / `"%~dp0.."` untuk yang di bat/).

Jalankan:  .venv\\Scripts\\python tests\\test_bat.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAT_DI_ROOT = ["proses-pesanan.bat"]      # satu-satunya .bat yang boleh di root
POLA_FOR_F = re.compile(r"for\s+/f\b.*?\bin\s*\(\s*(['`])(.*)\1\s*\)\s*do\b", re.IGNORECASE)


def perintah_for_f_berkutip(baris):
    """Kembalikan perintah di dalam for /f kalau diawali kutip ganda (= bug), selain itu None."""
    cocok = POLA_FOR_F.search(baris)
    if cocok and cocok.group(2).lstrip().startswith('"'):
        return cocok.group(2)
    return None


def path_bat(nama):
    """Lokasi file .bat: di root (pintu masuk harian) atau di folder bat/ (sisanya)."""
    for lokasi in (ROOT / nama, ROOT / "bat" / nama):
        if lokasi.exists():
            return lokasi
    raise FileNotFoundError(nama)


def semua_file_bat():
    return sorted(p for p in ROOT.rglob("*.bat") if ".venv" not in p.parts)


def bisa_simulasi_cmd():
    if sys.platform != "win32":
        print("  (dilewati: bukan Windows)")
        return False
    if not (ROOT / ".venv" / "Scripts" / "python.exe").exists():
        print("  (dilewati: .venv\\Scripts\\python.exe belum ada)")
        return False
    return True


def uji_semua_bat_berakhiran_crlf():
    files = semua_file_bat()
    salah = [str(f.relative_to(ROOT)) for f in files if re.search(rb"(?<!\r)\n", f.read_bytes())]
    assert not salah, (
        "file .bat berakhiran baris LF, WAJIB CRLF (cmd.exe salah lompat label di file LF): "
        + ", ".join(salah) + " - ubah ke CRLF, mis. di VS Code klik 'LF' di status bar -> 'CRLF'")
    print(f"  {len(files)} file .bat dicek: semua berakhiran baris CRLF")


def uji_root_hanya_berisi_proses_pesanan_bat():
    """Aturan struktur: satu-satunya .bat di root = proses-pesanan.bat (buka app); sisanya bat/."""
    ada = sorted(f.name for f in ROOT.glob("*.bat"))
    assert ada == BAT_DI_ROOT, ada
    for nama in ("proses-harian", "proses-malam", "cetak-label", "jalankan", "instalasi"):
        assert (ROOT / "bat" / f"{nama}.bat").exists(), nama
    for f in (ROOT / "bat").glob("*.bat"):
        assert 'cd /d "%~dp0.."' in f.read_text(encoding="utf-8"), f.name
    assert 'cd /d "%~dp0"' in (ROOT / "proses-pesanan.bat").read_text(encoding="utf-8")
    print("  root hanya proses-pesanan.bat; semua .bat lain di bat/ dengan cd /d \"%~dp0..\"")


def uji_gitattributes_paksa_crlf_untuk_bat():
    isi = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^\*\.bat\s.*\beol=crlf\b", isi, re.MULTILINE), isi
    print("  .gitattributes: *.bat dipaksa eol=crlf saat checkout (clone di PC lain tetap CRLF)")


PELUNCUR = {"proses-harian.bat": "harian", "proses-harian-uji.bat": "harian --uji",
            "proses-event.bat": "event", "proses-event-uji.bat": "event --uji",
            "proses-malam.bat": "malam", "proses-malam-uji.bat": "malam --uji"}


def uji_bat_menu_hanya_peluncur_tipis_ke_menu_konsol():
    """Daftar langkah/urutan/flag SEKARANG ada di src/alur.py (diuji tests/test_alur.py). Bat menu
    tidak boleh menulis ulang: tepat satu panggilan python ke menu_konsol.py, tanpa main.py,
    tanpa label/goto/call (sumber bug lompat label cmd, insiden 2026-10-01)."""
    for nama, arg in PELUNCUR.items():
        isi = path_bat(nama).read_text(encoding="utf-8")
        baris = [b for b in isi.splitlines() if b.strip() and not b.lower().startswith("rem")]
        panggil = [b for b in baris if "python.exe" in b]
        assert panggil == [rf'".venv\Scripts\python.exe" src\menu_konsol.py {arg}'], (nama, panggil)
        assert not any("main.py" in b for b in baris), nama
        assert not any(b.startswith(":") or b.lower().startswith(("goto", "call")) for b in baris), (nama, baris)
        assert len(baris) <= 6, (nama, baris)
    print(f"  {len(PELUNCUR)} bat menu: satu panggilan menu_konsol.py, tanpa daftar langkah/label")


def uji_pendeteksi_mengenali_pola_salah_dan_benar():
    salah = r'''for /f "delims=" %%t in ('".venv\Scripts\python.exe" -c "import time"') do set "X=%%t"'''
    benar = r'''for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import time"') do set "X=%%t"'''
    tanpa_kutip = r'''for /f "delims=" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"'''
    assert perintah_for_f_berkutip(salah) is not None
    assert perintah_for_f_berkutip(benar) is None
    assert perintah_for_f_berkutip(tanpa_kutip) is None
    print("  pendeteksi: menandai perintah for /f berkutip di awal, membiarkan yang tanpa kutip")


def uji_tidak_ada_for_f_dengan_perintah_berkutip_di_semua_bat():
    files = semua_file_bat()
    assert files, "tidak ada file .bat ditemukan - cek ROOT"
    pelanggaran = []
    for f in files:
        for no, baris in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if perintah_for_f_berkutip(baris):
                pelanggaran.append(f"{f.relative_to(ROOT)}:{no}: {baris.strip()}")
    assert not pelanggaran, (
        "for /f dengan perintah diawali kutip ganda (hapus kutip di sekitar path "
        "python.exe):\n" + "\n".join(pelanggaran))
    print(f"  {len(files)} file .bat dicek: tidak ada perintah for /f yang diawali kutip ganda")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
