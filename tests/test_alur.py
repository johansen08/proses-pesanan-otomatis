"""Uji alur.py (satu sumber definisi langkah/TIPE/flag) dan menu_konsol.py (menu konsol yang
dipanggil semua bat\\proses-*.bat) - TANPA menyentuh Jubelio: proses main.py/rekap_waktu.py
ditiru dengan fungsi kecil, ketikan keyboard ditiru dengan daftar.

Menggantikan uji lama yang membaca isi .bat (simulasi cmd.exe tiap TIPE, kesamaan .bat vs
KATALOG UI): kini tidak ada daftar langkah di .bat yang bisa menyimpang.

Jalankan:  .venv\\Scripts\\python tests\\test_alur.py
"""
import shlex
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import tempfile  # noqa: E402

import alur  # noqa: E402
import coba_ulang  # noqa: E402
import main as m  # noqa: E402
import menu_konsol as mk  # noqa: E402

coba_ulang.FOLDER_LOG = Path(tempfile.mkdtemp())     # jangan baca logs/ sungguhan

JUMLAH_LANGKAH = {"TIPE 1": 9, "TIPE 2": 13, "TIPE 3": 12, "TIPE 4": 10, "MALAM": 6,
                  "EVENT - TIPE 1": 16, "EVENT - TIPE 2": 20, "EVENT - TIPE 3": 16,
                  "EVENT - TIPE 4": 17, "EVENT - MALAM": 13}


def _katalog(judul):
    return alur.FLAG_EVENT if judul in alur.JUDUL_EVENT else alur.FLAG


def _urut(judul):
    return alur.langkah_urut(judul, alur.PRESET[judul])


def uji_preset_lengkap_dan_nama_ada_di_katalog():
    assert set(alur.PRESET) == set(JUMLAH_LANGKAH), set(alur.PRESET) ^ set(JUMLAH_LANGKAH)
    for judul, jumlah in JUMLAH_LANGKAH.items():
        assert judul in alur.JUDUL_VALID
        assert len(set(alur.PRESET[judul])) == len(alur.PRESET[judul]), f"{judul}: langkah ganda"
        asing = [n for n in alur.PRESET[judul] if n not in _katalog(judul)]
        assert not asing, (judul, asing)
        assert len(_urut(judul)) == jumlah, (judul, len(_urut(judul)))
    for katalog, judul_katalog in ((alur.KATALOG, [j for j in alur.PRESET if j not in alur.JUDUL_EVENT]),
                                   (alur.KATALOG_EVENT, [j for j in alur.PRESET if j in alur.JUDUL_EVENT])):
        nama = [n for n, _ in katalog]
        assert len(set(nama)) == len(nama), "nama langkah ganda dalam satu katalog"
        terpakai = {n for j in judul_katalog for n in alur.PRESET[j]}
        assert terpakai == set(nama), f"langkah katalog tak dipakai preset mana pun: {set(nama) - terpakai}"
    print(f"  {len(alur.PRESET)} preset: tanpa langkah ganda, semua nama ada di katalognya, jumlah langkah tetap")


def uji_langkah_urut_mengikuti_katalog_bukan_urutan_kiriman():
    acak = ["Upload faktur & pesanan ke IRESIS", "SPX-J&T Spesial", "Urgent Lazada", "Recheck stok", "tidak ada"]
    assert alur.langkah_urut("TIPE 1", acak) == [
        "Recheck stok", "Urgent Lazada", "SPX-J&T Spesial", "Upload faktur & pesanan ke IRESIS"]
    print("  langkah_urut(): urutan katalog, nama tak dikenal dibuang")


def uji_semua_langkah_diterima_argparse_main_sungguhan():
    """Tiap langkah di KATALOG/KATALOG_EVENT, dalam mode sungguhan & uji, lolos argparse main.py +
    validasi mode event (berhenti tepat sebelum muat_env/login): salah ketik flag ketahuan di sini,
    bukan di hari event."""

    class Berhenti(Exception):
        pass

    total = 0
    for judul in alur.PRESET:
        for nama in _urut(judul):
            for uji in (False, True):
                argumen = alur.susun_argumen(judul, nama, uji)
                with mock.patch.object(sys, "argv", ["main.py", *argumen]), \
                        mock.patch.object(m, "muat_env", side_effect=Berhenti):
                    try:
                        m._main()
                    except Berhenti:
                        total += 1
                    except SystemExit as e:
                        raise AssertionError(f"{judul}/{nama}: argparse menolak {argumen} (exit {e.code})")
    assert total == 2 * sum(JUMLAH_LANGKAH.values()), total
    print(f"  {total} perintah (preset x sungguhan/uji): semuanya diterima argparse & validasi mode event")


def uji_susun_argumen_jalankan_lewati_malam_dan_non_wajib():
    s = alur.susun_argumen
    assert s("TIPE 1", "Urgent Lazada") == ["--urgent", "--channel", "lazada", "--jalankan", "--lewati-malam"]
    assert s("TIPE 1", "Urgent Lazada", uji=True) == ["--urgent", "--channel", "lazada", "--lewati-malam"]
    assert s("TIPE 2", "Urgent Lazada") == ["--urgent", "--channel", "lazada", "--jalankan"]
    assert s("MALAM", "Urgent Lazada") == ["--urgent", "--channel", "lazada", "--jalankan"]
    assert s("EVENT - TIPE 3", "Urgent GTL & SiCepat")[-1] == "--lewati-malam"
    assert s("EVENT - TIPE 2", "Urgent GTL & SiCepat")[-1] == "--jalankan"
    assert s("TIPE 1", "SPX-J&T Spesial")[-1] == "--non-wajib-sore"
    assert s("TIPE 4", "SPX-J&T Spesial")[-1] == "--non-wajib"
    assert s("TIPE 2", "SPX Spesial")[-1] == "--non-wajib" and "--non-wajib" not in s("TIPE 2", "J&T Spesial")
    assert "--non-wajib" not in s("MALAM", "SPX-J&T Spesial")
    assert s("EVENT - TIPE 2", "SPX Hemat Spesial") == [
        "--label", "--event", "--kurir", "spx-hemat", "--tanpa-reguler", "--jalankan"]
    print("  susun_argumen(): --jalankan, --lewati-malam (TIPE 1/KUSTOM/EVENT 1,3,4), --non-wajib(-sore)")


def uji_aturan_bisnis_harian():
    """Aturan yang tidak boleh bergeser diam-diam (dulu dikunci lewat isi .bat)."""
    for judul in ("TIPE 1", "TIPE 2", "TIPE 3", "TIPE 4"):
        urut = _urut(judul)
        assert urut[:2] == ["Recheck stok", "Sampel TikTok (nilai 0)"], judul
        assert urut[-1] == alur.LANGKAH_IRESIS, judul
        pagi, siang = "SPX ≤ 12.00 (Resi Pagi)" in urut, "J&T ≤ 15.00 (Resi Siang)" in urut
        assert (pagi, siang) == (judul == "TIPE 2", judul == "TIPE 4"), judul
        gabung = [n for n in urut if n in alur.NON_WAJIB_SPX_GABUNG]
        dipisah = [n for n in urut if n in alur.NON_WAJIB_SPX_DIPISAH]
        assert (len(gabung), len(dipisah)) == ((3, 0) if judul in ("TIPE 1", "TIPE 4") else (0, 3)), judul
        nw = [n for n in urut if alur.flag_non_wajib(judul, n)]
        assert len(nw) == 3, (judul, nw)
    assert LANGKAH_MALAM_HARIAN == _urut("MALAM")
    assert alur.LANGKAH_IRESIS not in _urut("MALAM")
    print("  harian: recheck+sampel+IRESIS di TIPE 1-4, Resi Pagi hanya TIPE 2, Resi Siang hanya TIPE 4, "
          "gabung/dipisah sesuai TIPE, MALAM tanpa IRESIS, non wajib 3 langkah per TIPE")


LANGKAH_MALAM_HARIAN = ["Urgent Lazada", "Urgent GTL & SiCepat", "Urgent JNE & LEX",
                        "SPX-J&T Spesial", "SPX-J&T 1 qty reguler", "SPX-J&T Kombinasi"]


def uji_aturan_bisnis_event():
    pagi_nama = {"SPX Standard Pagi ≤ 12.00 (per lantai)", "SPX Hemat Pagi Spesial",
                 "SPX Hemat Pagi 1 qty reguler", "SPX Hemat Pagi Kombinasi"}
    for judul in (j for j in alur.PRESET if j in alur.JUDUL_EVENT):
        urut = _urut(judul)
        malam = judul == "EVENT - MALAM"
        for nama in urut:
            flag = alur.FLAG_EVENT[nama]
            if "--label" in flag or "--reguler" in flag:   # J&T/SPX Hemat selalu dengan --event
                assert "--event" in flag and flag[flag.index("--kurir") + 1] in (
                    "jnt", "jnt-ndd", "spx-hemat", "spx-hemat-pagi"), (judul, nama)
        urgent = [n for n in urut if alur.FLAG_EVENT[n][:1] == ["--urgent"]]
        assert len(urgent) == 3, (judul, urgent)
        lewati = {judul in alur.JUDUL_LEWATI_MALAM}
        assert all(("--lewati-malam" in alur.susun_argumen(judul, n)) in lewati for n in urgent), judul
        assert (urut[-1] == alur.LANGKAH_IRESIS) == (not malam), judul
        assert (urut[0] == "Recheck stok" and urut[1] == "Sampel TikTok (nilai 0)") == (not malam), judul
        assert ("J&T ≤ 15.00 (Resi Siang)" in urut) == (judul == "EVENT - TIPE 4"), judul
        pagi = [i for i, n in enumerate(urut) if n in pagi_nama]
        assert len(pagi) == (4 if judul == "EVENT - TIPE 2" else 0), (judul, pagi)
        assert not any(alur.flag_non_wajib(judul, n) for n in urut), judul
    urut = _urut("EVENT - TIPE 2")
    idx_pagi = [i for i, n in enumerate(urut) if n in pagi_nama]
    harian = [i for i, n in enumerate(urut) if n in ("J&T Spesial", "SPX Hemat Spesial", "SPX Standard (per lantai)")]
    assert idx_pagi == list(range(idx_pagi[0], idx_pagi[0] + 4)) and min(harian) > max(idx_pagi), \
        "Shopee Pagi harus selesai sebelum langkah seharian"
    print("  event: --event pada J&T/Hemat, Shopee Pagi hanya TIPE 2 & mendahului seharian, Resi Siang hanya "
          "TIPE 4, MALAM tanpa recheck/sampel/IRESIS, --lewati-malam sesuai")


def uji_preset_dan_nama_langkah_ada_di_ui_html():
    """UI (index.html) masih punya salinan nama langkah sendiri: semua nama di alur.py harus ada
    di sana (salah ketik = tombol UI tidak cocok katalog server)."""
    html = (ROOT / "data" / "prototype-desktop" / "index.html").read_text(encoding="utf-8")
    hilang = sorted({n for k in (alur.KATALOG, alur.KATALOG_EVENT) for n, _ in k
                     if n not in html})
    assert not hilang, f"nama langkah tidak ada di index.html: {hilang}"
    for judul in alur.PRESET:
        if judul in ("TIPE 1", "TIPE 2", "TIPE 3", "TIPE 4", "MALAM") or judul in alur.JUDUL_EVENT:
            assert judul.replace("EVENT - ", "") in html or judul in html, judul
    print("  semua nama langkah alur.py ada di index.html")


# ----------------------------------------------------------------------------- menu konsol
class Papan:
    """Ketikan keyboard palsu + catatan proses yang dijalankan."""

    def __init__(self, *ketikan):
        self.ketikan, self.panggilan, self.cetak_ = list(ketikan), [], []

    def masukan(self, prompt=""):
        self.cetak_.append(prompt)
        assert self.ketikan, f"menu minta ketikan lagi: {prompt!r}"
        return self.ketikan.pop(0)

    def jalankan(self, argumen, env):
        self.panggilan.append((list(argumen), dict(env)))
        return 0

    def cetak(self, teks=""):
        self.cetak_.append(teks)

    def flag_main(self):
        return [shlex.join(a[2:]) for a, _ in self.panggilan if Path(a[1]).name == "main.py"]

    def rekap(self):
        return [a[2] for a, _ in self.panggilan if Path(a[1]).name == "rekap_waktu.py"]


def _menu(papan, mode="harian", uji=False, jam_ok=True):
    mk.menu(mode, uji, "2026-10-12/3", masukan=papan.masukan, cetak=papan.cetak,
            dalam_jam=lambda kunci: jam_ok, jalankan=papan.jalankan, sekarang=iter(range(1000, 9999)).__next__)


def uji_menu_tiap_tipe_menjalankan_tepat_langkah_alur_sekali():
    for mode, judul_list in (("harian", ["TIPE 1", "TIPE 2", "TIPE 3", "TIPE 4"]),
                             ("event", ["EVENT - TIPE 1", "EVENT - TIPE 2", "EVENT - TIPE 3",
                                        "EVENT - TIPE 4", "EVENT - MALAM"])):
        for no, judul in enumerate(judul_list, 1):
            papan = Papan(str(no), "Y", "", "0")
            _menu(papan, mode)
            harapan = [shlex.join(alur.susun_argumen(judul, n)) for n in _urut(judul)]
            assert papan.flag_main() == harapan, (mode, judul, papan.flag_main(), harapan)
            assert papan.rekap() == [judul], (judul, papan.rekap())
            rekap_argv = papan.panggilan[-1][0]
            assert len(rekap_argv) == 3 + len(harapan) and rekap_argv[3].startswith("RECHECK STOK:" if "MALAM" not in judul
                                                                                    else "URGENT LAZADA:"), rekap_argv
            assert all(env["LABEL_SESI_DIR"] == "2026-10-12/3" and float(env["WAKTU_MENU_MULAI"]) > 0
                       for _, env in papan.panggilan)
            assert "--jalankan" in harapan[0] and all("--jalankan" in h for h in papan.flag_main())
    print("  menu harian & event: tiap pilihan menjalankan tepat langkah preset-nya, berurutan, sekali, "
          "lalu rekap; LABEL_SESI_DIR & WAKTU_MENU_MULAI terisi")


def uji_menu_keluar_batal_dan_pilihan_salah_tidak_menjalankan_apa_pun():
    papan = Papan("0")
    _menu(papan)
    assert not papan.panggilan
    papan = Papan("1", "N", "0")          # jawab N di konfirmasi
    _menu(papan)
    assert not papan.panggilan
    papan = Papan("9", "", "x", "", "0")  # pilihan tidak dikenal
    _menu(papan)
    assert not papan.panggilan and any("tidak dikenali" in t for t in papan.cetak_)
    papan = Papan("1", "n", "0")          # huruf kecil = bukan Y
    _menu(papan)
    assert not papan.panggilan
    print("  menu: 0 keluar, N membatalkan, pilihan tak dikenal diulang; tidak ada main.py yang jalan")


def uji_menu_cek_jam_peringatan_y_n():
    papan = Papan("2", "N", "0")           # di luar jam, jawab N -> batal sebelum konfirmasi
    _menu(papan, jam_ok=False)
    assert not papan.panggilan and any("di luar jam" in t for t in papan.cetak_)
    assert not any(p.startswith("Lanjutkan TIPE 2") for p in papan.cetak_)
    papan = Papan("2", "Y", "Y", "", "0")  # di luar jam, tetap lanjut
    _menu(papan, jam_ok=False)
    assert len(papan.flag_main()) == len(_urut("TIPE 2"))
    papan = Papan("5", "Y", "", "0")       # EVENT - MALAM tidak punya cek jam
    _menu(papan, "event", jam_ok=False)
    assert len(papan.flag_main()) == len(_urut("EVENT - MALAM")) and not any("di luar jam" in t for t in papan.cetak_)
    print("  cek jam: di luar jam -> tanya Y/N; MALAM event tanpa cek jam")


def uji_mode_uji_tanpa_jalankan_dan_tanpa_konfirmasi():
    for mode, judul in (("harian", "TIPE 1"), ("event", "EVENT - TIPE 2")):
        no = "1" if mode == "harian" else "2"
        papan = Papan(no, "", "0")         # TIDAK ada ketikan Y/N
        _menu(papan, mode, uji=True)
        assert len(papan.flag_main()) == len(_urut(judul)) and not any("--jalankan" in f for f in papan.flag_main())
        assert papan.rekap() == [judul]
    print("  --uji: tanpa konfirmasi Y/N, tanpa --jalankan")


def uji_malam_langsung_tanpa_menu_dan_tanpa_iresis():
    papan = Papan("Y", "")
    mk.malam(False, "s/1", masukan=papan.masukan, cetak=papan.cetak, jalankan=papan.jalankan,
             sekarang=iter(range(1000, 9999)).__next__)
    assert papan.flag_main() == [shlex.join(alur.susun_argumen("MALAM", n)) for n in LANGKAH_MALAM_HARIAN]
    assert papan.rekap() == ["MALAM"] and not any("upload-iresis" in f for f in papan.flag_main())
    papan = Papan("N")
    mk.malam(False, "s/1", masukan=papan.masukan, cetak=papan.cetak, jalankan=papan.jalankan)
    assert not papan.panggilan
    papan = Papan("Y", "")
    mk.malam(True, "s/1", masukan=papan.masukan, cetak=papan.cetak, jalankan=papan.jalankan)
    assert papan.flag_main() and not any("--jalankan" in f for f in papan.flag_main())
    print("  malam: tanpa menu, 6 langkah, tanpa IRESIS; N membatalkan; --uji tanpa --jalankan")


def uji_nama_langkah_aman_untuk_konsol():
    assert mk.tampil("SPX ≤ 12.00 (Resi Pagi)") == "SPX <= 12.00 (Resi Pagi)"
    papan = Papan("4", "Y", "", "0")
    _menu(papan)
    assert all("≤" not in t for t in papan.cetak_)
    assert all("≤" not in e for a, _ in papan.panggilan for e in a[3:] if Path(a[1]).name == "rekap_waktu.py")
    print("  nama langkah: tanda kurang-dari-sama-dengan diganti '<=' di banner & rekap (konsol Windows cp1252/cp437)")


def uji_main_argumen_dan_sesi_dihitung_sekali():
    with mock.patch.object(m, "sesi_label_baru", return_value="2026-10-12/9") as sesi, \
            mock.patch("builtins.input", side_effect=["0"]):
        assert mk.main(["harian", "--uji"]) == 0
    assert sesi.call_count == 1
    try:
        mk.main(["tidak-ada"])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("mode tak dikenal harus ditolak argparse")
    print("  main(): sesi label dihitung sekali per peluncuran, mode tak dikenal ditolak")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
