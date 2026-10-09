"""Uji regresi file .bat.

1) File .bat WAJIB berakhiran baris CRLF. Di file LF, cmd.exe salah menghitung posisi saat
mencari label (`call :catat_waktu`, `goto menu`), sehingga eksekusi melompat ke baris
yang salah: memilih TIPE 1 bisa menjalankan langkah TIPE 2/3/4, dan menu "0. Keluar"
malah melanjutkan proses SUNGGUHAN (kejadian 2026-10-01: "0" menjalankan
"8/8 SPX KOMBINASI"). Dicek statis + simulasi tiap TIPE di cmd.exe sungguhan dengan
python palsu (tidak menyentuh Jubelio).

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
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MENU_BAT = ("proses-harian.bat", "proses-harian-uji.bat")
MENU_EVENT = ("proses-event.bat", "proses-event-uji.bat")
# Langkah J&T Resi Siang di proses-event.bat dijalankan bersyarat (jawaban Y/N di awal):
# barisnya diawali `if /i "%JNT_SIANG%"=="Y" ` - awalan itu dibuang saat mengekstrak argumen.
POLA_PANGGIL_MAIN = re.compile(
    r'^(?:if /i "%JNT_SIANG%"=="Y" )?"\.venv\\Scripts\\python\.exe" src\\main\.py (.*)$')

# main.py & rekap_waktu.py palsu untuk simulasi: cuma mencatat argumen, tanpa Jubelio.
MAIN_PALSU = '''import sys
from pathlib import Path
def sesi_label_baru(): return "SIM"
def dalam_jam_menu(menu): return True
if __name__ == "__main__":
    with open(Path(__file__).parent.parent / "panggilan.txt", "a") as f:
        f.write(" ".join(sys.argv[1:]) + "\\n")
'''
REKAP_PALSU = '''import sys
from pathlib import Path
(Path(__file__).parent.parent / "rekap.txt").write_text(sys.argv[1])
'''

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


def langkah_tipe(nama_bat, tipe):
    """Argumen main.py tiap langkah TIPE `tipe`, urut sesuai isi blok :tipeN di file .bat."""
    return langkah_blok(nama_bat, f"tipe{tipe}")


def langkah_blok(nama_bat, label):
    """Argumen main.py tiap langkah di blok `:label` file .bat (sampai label berikutnya)."""
    baris = path_bat(nama_bat).read_text(encoding="utf-8").splitlines()
    hasil = []
    for b in baris[baris.index(f":{label}") + 1:]:
        if b.startswith(":"):
            break
        cocok = POLA_PANGGIL_MAIN.match(b)
        if cocok:
            hasil.append(cocok.group(1))
    return hasil


def simulasikan_menu(nama_bat, masukan, batas_detik=60):
    """Jalankan file .bat ASLI (disalin byte-identik) di cmd.exe dengan main.py/rekap_waktu.py
    palsu dan `masukan` sebagai ketikan keyboard. Berhenti saat rekap tercetak, cmd keluar
    sendiri, atau batas waktu habis. Return (argumen main.py yang dipanggil berurutan,
    argumen TIPE di rekap atau None, apakah cmd keluar sendiri)."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        sumber = path_bat(nama_bat)
        lokasi_bat = tmp / sumber.relative_to(ROOT)       # bat/ ikut dipertahankan (cd /d "%~dp0..")
        lokasi_bat.parent.mkdir(exist_ok=True)
        shutil.copyfile(sumber, lokasi_bat)
        (tmp / ".venv" / "Scripts").mkdir(parents=True)
        shutil.copyfile(ROOT / ".venv" / "Scripts" / "python.exe",
                        tmp / ".venv" / "Scripts" / "python.exe")
        shutil.copyfile(ROOT / ".venv" / "pyvenv.cfg", tmp / ".venv" / "pyvenv.cfg")
        (tmp / "src").mkdir()
        (tmp / "src" / "main.py").write_text(MAIN_PALSU, encoding="utf-8")
        (tmp / "src" / "rekap_waktu.py").write_text(REKAP_PALSU, encoding="utf-8")
        (tmp / "masukan.txt").write_bytes(masukan.encode())
        rekap = tmp / "rekap.txt"
        with open(tmp / "masukan.txt", "rb") as stdin:
            p = subprocess.Popen(["cmd", "/c", str(lokasi_bat)], stdin=stdin,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            batas = time.monotonic() + batas_detik
            while p.poll() is None and not rekap.exists() and time.monotonic() < batas:
                time.sleep(0.2)
            keluar_sendiri = p.poll() is not None
            if not keluar_sendiri:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
                p.wait()
        file_panggilan = tmp / "panggilan.txt"
        panggilan = file_panggilan.read_text().splitlines() if file_panggilan.exists() else []
        return panggilan, (rekap.read_text() if rekap.exists() else None), keluar_sendiri


def uji_semua_bat_berakhiran_crlf():
    files = semua_file_bat()
    salah = [str(f.relative_to(ROOT)) for f in files if re.search(rb"(?<!\r)\n", f.read_bytes())]
    assert not salah, (
        "file .bat berakhiran baris LF, WAJIB CRLF (cmd.exe salah lompat label di file LF): "
        + ", ".join(salah) + " - ubah ke CRLF, mis. di VS Code klik 'LF' di status bar -> 'CRLF'")
    print(f"  {len(files)} file .bat dicek: semua berakhiran baris CRLF")


def uji_gitattributes_paksa_crlf_untuk_bat():
    isi = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert re.search(r"^\*\.bat\s.*\beol=crlf\b", isi, re.MULTILINE), isi
    print("  .gitattributes: *.bat dipaksa eol=crlf saat checkout (clone di PC lain tetap CRLF)")


def uji_simulasi_tiap_tipe_menjalankan_langkah_sesuai_urutan_file():
    if not bisa_simulasi_cmd():
        return
    for nama in MENU_BAT:
        for tipe in "1234":
            harapan = langkah_tipe(nama, tipe)
            assert harapan, (nama, tipe)
            panggilan, rekap, _ = simulasikan_menu(nama, f"{tipe}\r\nY\r\n")
            assert panggilan == harapan, (
                f"{nama} TIPE {tipe} melompat ke langkah yang salah", "harapan:", harapan,
                "kenyataan:", panggilan)
            assert rekap == f"TIPE {tipe}", (nama, tipe, rekap)
    print("  proses-harian.bat & versi uji: TIPE 1-4 menjalankan tepat langkah di bloknya "
          "masing-masing, berurutan, sekali saja (simulasi cmd.exe, python palsu)")


def uji_simulasi_menu_0_keluar_tanpa_menjalankan_apa_pun():
    if not bisa_simulasi_cmd():
        return
    for nama in MENU_BAT:
        panggilan, rekap, keluar_sendiri = simulasikan_menu(nama, "0\r\n", batas_detik=20)
        assert keluar_sendiri and not panggilan and rekap is None, (
            nama, keluar_sendiri, panggilan, rekap)
    print("  menu 0: cmd langsung keluar, tidak ada main.py yang dijalankan")


def uji_simulasi_menu_event_menjalankan_langkah_sesuai_urutan_file():
    """proses-event.bat: pilihan 1 & 2 menjalankan tepat langkah di bloknya (J&T Resi Siang
    hanya kalau dijawab Y); versi uji menjalankan semua langkah tanpa pertanyaan apa pun."""
    if not bisa_simulasi_cmd():
        return
    for nama in MENU_EVENT:
        uji = nama.endswith("-uji.bat")
        for pilihan, label, judul in (("1", "event1", "EVENT - SESI BIASA"),
                                      ("2", "event2", "EVENT - TEPAT JAM 13.00")):
            semua = langkah_blok(nama, label)
            assert semua, (nama, label)
            siang = [a for a in semua if a.startswith("--jnt-siang")]
            assert len(siang) == (1 if pilihan == "1" else 0), (nama, label, siang)
            if uji:
                jawaban = {"": f"{pilihan}\r\n"}
            elif pilihan == "1":
                jawaban = {"N": "1\r\nY\r\nN\r\n", "Y": "1\r\nY\r\nY\r\n",
                           "kosong": "1\r\nY\r\n\r\n"}
            else:
                jawaban = {"": "2\r\nY\r\n"}
            for kunci, masukan in jawaban.items():
                panggilan, rekap, _ = simulasikan_menu(nama, masukan)
                harapan = [a for a in semua if uji or kunci == "Y" or a not in siang]
                assert panggilan == harapan, (
                    f"{nama} pilihan {pilihan} (jawaban J&T Siang: {kunci!r}) salah langkah",
                    "harapan:", harapan, "kenyataan:", panggilan)
                assert rekap == judul, (nama, pilihan, rekap)
    print("  proses-event.bat & versi uji: pilihan 1-2 menjalankan tepat langkah di bloknya, "
          "berurutan; J&T Resi Siang hanya kalau dijawab Y (bawaan tidak), versi uji semua langkah")


def uji_simulasi_menu_event_batal_dan_keluar_tidak_menjalankan_apa_pun():
    if not bisa_simulasi_cmd():
        return
    for nama in MENU_EVENT:
        panggilan, rekap, keluar_sendiri = simulasikan_menu(nama, "0\r\n", batas_detik=20)
        assert keluar_sendiri and not panggilan and rekap is None, (nama, panggilan, rekap)
    # jawab N di konfirmasi: kembali ke menu, tidak menjalankan apa pun (lalu 0 = keluar)
    panggilan, rekap, keluar_sendiri = simulasikan_menu(
        "proses-event.bat", "1\r\nN\r\n0\r\n", batas_detik=30)
    assert keluar_sendiri and not panggilan and rekap is None, (panggilan, rekap)
    print("  proses-event.bat: menu 0 langsung keluar; jawab N di konfirmasi tidak menjalankan "
          "apa pun")


def uji_bat_event_uji_sama_dengan_sungguhan_tanpa_jalankan():
    """Versi uji harus menjalankan PERSIS langkah yang sama dengan versi sungguhan (hanya tanpa
    --jalankan): mencegah keduanya menyimpang diam-diam saat salah satu diedit."""
    for label in ("event1", "event2"):
        asli = langkah_blok("proses-event.bat", label)
        uji = langkah_blok("proses-event-uji.bat", label)
        assert all(a.endswith(" --jalankan") for a in asli), asli
        assert not any("--jalankan" in a for a in uji), uji
        assert [a[:-len(" --jalankan")] for a in asli] == uji, (label, asli, uji)
    print("  proses-event.bat vs proses-event-uji.bat: langkah identik, uji tanpa --jalankan")


def uji_bat_event_urutan_pagi_dan_pemisahan_kurir():
    """Aturan bisnis yang tidak boleh bergeser diam-diam: Shopee Pagi SEBELUM langkah seharian,
    J&T/SPX Hemat selalu dengan --event, tidak ada langkah harian (digabung) di .bat event."""
    sesi1 = langkah_blok("proses-event.bat", "event1")
    sesi2 = langkah_blok("proses-event.bat", "event2")
    for sesi in (sesi1, sesi2):
        for a in sesi:
            if "--label" in a or "--reguler" in a:
                assert "--event" in a and ("--kurir jnt" in a or "--kurir spx-hemat" in a), a
        assert sesi[0].startswith("--recheck-stok") and sesi[1].startswith("--sampel")
        assert sesi[-2].startswith("--tulis-excel") and sesi[-1].startswith("--upload-iresis")
    assert not any("--pagi" in a or "spx-hemat-pagi" in a for a in sesi1)
    pagi = [i for i, a in enumerate(sesi2) if "--pagi" in a or "spx-hemat-pagi" in a]
    harian = [i for i, a in enumerate(sesi2)
              if ("--kurir jnt" in a or "--kurir spx-hemat " in a + " " or a.startswith("--spx-standard --j"))
              and i not in pagi]
    assert len(pagi) == 4 and pagi == list(range(pagi[0], pagi[0] + 4)), pagi
    assert harian and min(harian) > max(pagi), "Shopee Pagi harus selesai sebelum langkah seharian"
    print("  .bat event: Shopee Pagi (4 langkah) mendahului langkah seharian; semua --label/"
          "--reguler memakai --event")


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


def uji_catat_waktu_benar_benar_jalan_di_cmd():
    """Jalankan subrutin :catat_waktu ASLI dari tiap proses-harian*.bat di cmd.exe sungguhan."""
    if not bisa_simulasi_cmd():
        return
    for nama in MENU_BAT:
        baris = path_bat(nama).read_text(encoding="utf-8").splitlines()
        awal = baris.index(":catat_waktu")
        akhir = baris.index("exit /b 0", awal)
        isi = [
            "@echo off",
            f'cd /d "{ROOT}"',
            "call :catat_waktu HASIL",
            "echo HASIL=[%HASIL%]",
            "exit /b 0",
            *baris[awal:akhir + 1],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bat = Path(tmp) / "uji_catat_waktu.bat"
            bat.write_text("\r\n".join(isi) + "\r\n", encoding="utf-8")
            hasil = subprocess.run(["cmd", "/c", str(bat)], capture_output=True, text=True)
        assert "not recognized" not in hasil.stderr, (nama, hasil.stderr)
        assert re.search(r"HASIL=\[\d+(\.\d+)?\]", hasil.stdout), (nama, hasil.stdout, hasil.stderr)
    print("  :catat_waktu di proses-harian.bat & versi uji: menghasilkan epoch di cmd.exe sungguhan")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
