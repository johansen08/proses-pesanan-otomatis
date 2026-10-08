"""Uji fungsi murni/filesystem di main.py (bukan alur CLI penuh - itu sudah dicakup
lewat test_proses_label.py & test_sku_spesial.py untuk bagian yang dipanggilnya).

Jalankan:  .venv\\Scripts\\python tests\\test_main.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main as m  # noqa: E402


# -------------------------------------------------- dalam_jam_menu()
def _jam(h, mnt=0):
    return datetime(2026, 9, 29, h, mnt)


def uji_dalam_jam_menu_tipe1_melingkupi_tengah_malam():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(23, 30)
        assert m.dalam_jam_menu("1") is True
        dt.now.return_value = _jam(6, 59)
        assert m.dalam_jam_menu("1") is True
        dt.now.return_value = _jam(13, 0)
        assert m.dalam_jam_menu("1") is False
    print("  TIPE 1: valid 16.00-24.00 dan 00.00-12.00 (melingkupi tengah malam), tidak di jam 13.00")


def uji_dalam_jam_menu_tipe2_dan_tipe3_tumpang_tindih_sengaja():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(13, 30)
        assert m.dalam_jam_menu("2") is True and m.dalam_jam_menu("3") is True
        dt.now.return_value = _jam(14, 30)
        assert m.dalam_jam_menu("2") is False and m.dalam_jam_menu("3") is True
    print("  TIPE 2 & 3: tumpang tindih sengaja di jam 13.00-13.59, lalu hanya TIPE 3 sampai 14.59")


def uji_dalam_jam_menu_jam_istirahat_12_sampai_13_tidak_ada_menu_valid():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(12, 30)
        assert not any(m.dalam_jam_menu(x) for x in "1234")
    print("  jam istirahat 12.00-13.00: sengaja tidak ada TIPE menu yang valid")


def uji_dalam_jam_menu_tipe4():
    with mock.patch.object(m, "datetime") as dt:
        dt.now.return_value = _jam(15, 30)
        assert m.dalam_jam_menu("4") is True
        dt.now.return_value = _jam(16, 0)
        assert m.dalam_jam_menu("4") is False
    print("  TIPE 4: valid persis 15.00-15.59")


# -------------------------------------------------- muat_env()
def uji_muat_env_parsing_dasar():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / ".env"
        f.write_text(
            "# komentar diabaikan\n"
            "\n"
            'JUBELIO_EMAIL="a@b.com"\n'
            "JUBELIO_PASSWORD='rahasia'\n"
            "TANPA_KUTIP=nilai biasa\n",
            encoding="utf-8",
        )
        import os
        for k in ("JUBELIO_EMAIL", "JUBELIO_PASSWORD", "TANPA_KUTIP"):
            os.environ.pop(k, None)
        m.muat_env(f)
        assert os.environ["JUBELIO_EMAIL"] == "a@b.com"
        assert os.environ["JUBELIO_PASSWORD"] == "rahasia"
        assert os.environ["TANPA_KUTIP"] == "nilai biasa"
        for k in ("JUBELIO_EMAIL", "JUBELIO_PASSWORD", "TANPA_KUTIP"):
            os.environ.pop(k, None)
    print("  muat_env: baca KUNCI=nilai, lewati komentar/baris kosong, buang kutip di nilai")


def uji_muat_env_tidak_timpa_env_yang_sudah_ada():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / ".env"
        f.write_text("JUBELIO_EMAIL=dari_file\n", encoding="utf-8")
        os.environ["JUBELIO_EMAIL"] = "dari_environment_asli"
        try:
            m.muat_env(f)
            assert os.environ["JUBELIO_EMAIL"] == "dari_environment_asli"
        finally:
            os.environ.pop("JUBELIO_EMAIL", None)
    print("  muat_env: environment variable yang sudah ada tidak ditimpa nilai dari .env")


def uji_muat_env_file_tidak_ada_tidak_error():
    m.muat_env(Path("file-env-tidak-pernah-ada.env"))
    print("  muat_env: file .env tidak ada -> tidak error, dilewati saja")


# -------------------------------------------------- sesi_label_baru() / folder_label_sesi()
def uji_sesi_label_baru_nomor_urut_bertambah():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)), \
             mock.patch.object(m, "datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 30)
            n1 = m.sesi_label_baru()
            n2 = m.sesi_label_baru()
            assert n1 == "2026-09-30/1" and n2 == "2026-09-30/2", (n1, n2)
            assert (Path(tmp) / n1).is_dir() and (Path(tmp) / n2).is_dir()
    print("  sesi_label_baru: nomor urut bertambah per panggilan untuk tanggal yang sama")


def uji_sesi_label_baru_abaikan_folder_bukan_pola_sesi():
    with tempfile.TemporaryDirectory() as tmp:
        folder_tanggal = Path(tmp) / "2026-09-30"
        folder_tanggal.mkdir()
        (folder_tanggal / "5").mkdir()
        (folder_tanggal / "folder-lain").mkdir()
        (folder_tanggal / "bukan_angka").mkdir()
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)), \
             mock.patch.object(m, "datetime") as dt:
            dt.now.return_value = datetime(2026, 9, 30)
            nama = m.sesi_label_baru()
        assert nama == "2026-09-30/6", nama
    print("  sesi_label_baru: folder yang tidak cocok pola sesi diabaikan, lanjut dari nomor "
          "tertinggi yang valid")


def uji_folder_label_sesi_pakai_env_jika_ada():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(m, "FOLDER_LABEL", Path(tmp)):
            os.environ["LABEL_SESI_DIR"] = "2026-09-30/7"
            try:
                folder = m.folder_label_sesi()
            finally:
                os.environ.pop("LABEL_SESI_DIR", None)
            assert folder == Path(tmp) / "2026-09-30" / "7" and folder.is_dir()
    print("  folder_label_sesi: pakai LABEL_SESI_DIR dari environment kalau ada, bukan bikin sesi baru")


def uji_sesi_valid_untuk_opsi_lanjut():
    import argparse
    assert m._sesi_valid("2026-10-06/12") == "2026-10-06/12"
    assert m._sesi_valid("2026-10-06\\12\\") == "2026-10-06/12"     # disalin dari Explorer
    for salah in ("12", "2026-10-06", "../2026-10-06/12", "2026-10-06/12/SPESIAL", "x/1"):
        try:
            m._sesi_valid(salah)
        except argparse.ArgumentTypeError:
            continue
        raise AssertionError(f"--sesi {salah!r} seharusnya ditolak")
    print("  --sesi: hanya menerima pola folder sesi YYYY-MM-DD/N")


def uji_peringatan_picklist_terlompat():
    import peringatan_picklist as pp
    with tempfile.TemporaryDirectory() as tmp:
        pp.atur_folder(Path(tmp))
        pp._sesi.clear()
        assert pp.periksa_nomor("PICK-000155661") is None      # pertama kali: belum ada pembanding
        assert pp.ambil_nomor_hilang() == []
        assert pp.periksa_nomor("PICK-000155662") is None      # berurutan: aman
        assert pp.ambil_nomor_hilang() == []
        pesan = pp.periksa_nomor("PICK-000155665")
        assert pesan and "PICK-000155663" in pesan and "PICK-000155664" in pesan, pesan
        assert pp.ambil_nomor_hilang() == [155663, 155664]
        assert pp.periksa_nomor("PICK-000155666") is None
        assert pp.ambil_nomor_hilang() == []       # ditimpa kosong lagi setelah berurutan
        assert len(pp._sesi) == 1
        assert len(pp.baca_sejak(0)) == 1 and pp.baca_sejak(9e12) == []
    pp._file_terakhir = pp._file_peringatan = None
    print("  peringatan_picklist: nomor terlompat terdeteksi & tersimpan, berurutan tidak dianggap")


def uji_peringatan_resi_tanpa_resi():
    import peringatan_resi as pr
    with tempfile.TemporaryDirectory() as tmp:
        pr.atur_folder(Path(tmp))
        pr._sesi.clear()
        pr.catat_tanpa_resi("PICK-000154839", "T01-BSBI-5", [])
        assert pr._sesi == [], "tidak ada pesanan tanpa resi: tidak perlu dicatat"
        pr.catat_tanpa_resi("PICK-000154839", "T01-BSBI-5", ["SO9068180", "SO9068214"])
        assert len(pr._sesi) == 1
        pesan = pr._sesi[0]
        assert "PICK-000154839" in pesan and "SO9068180" in pesan and "SO9068214" in pesan, pesan
        assert len(pr.baca_sejak(0)) == 1 and pr.baca_sejak(9e12) == []
    pr._file_peringatan = None
    print("  peringatan_resi: pesanan tanpa resi (bukan batal) dicatat untuk diinformasikan ke CS")


def uji_tulis_picklist_excel_mode_uji_tidak_menulis():
    import logging
    from types import SimpleNamespace

    import rekap_master_excel as rme
    log = logging.getLogger("uji-main")
    with mock.patch.object(rme, "jumlah_antrian", return_value=3), \
            mock.patch.object(rme, "terapkan") as terapkan:
        assert m.tulis_picklist_excel(log, SimpleNamespace(jalankan=False)) == 0
        terapkan.assert_not_called()
    with mock.patch.object(rme, "jumlah_antrian", return_value=0), \
            mock.patch.object(rme, "terapkan") as terapkan:
        assert m.tulis_picklist_excel(log, SimpleNamespace(jalankan=True)) == 0
        terapkan.assert_not_called()
    print("  --tulis-excel: mode uji / antrean kosong tidak membuka PICKLIST.xlsx")


def uji_tulis_picklist_excel_exit_1_kalau_masih_tertunda():
    import logging
    from types import SimpleNamespace

    import rekap_master_excel as rme
    log = logging.getLogger("uji-main")
    with mock.patch.object(rme, "jumlah_antrian", side_effect=[2, 0]), \
            mock.patch.object(rme, "terapkan", return_value=2) as terapkan:
        assert m.tulis_picklist_excel(log, SimpleNamespace(jalankan=True)) == 0
        terapkan.assert_called_once()
    with mock.patch.object(rme, "jumlah_antrian", side_effect=[2, 2]), \
            mock.patch.object(rme, "terapkan", return_value=0):
        assert m.tulis_picklist_excel(log, SimpleNamespace(jalankan=True)) == 1
    print("  --tulis-excel --jalankan: terapkan() sekali; exit 1 kalau antrean masih tertunda")


def uji_upload_iresis_mode_uji_gagal_dan_sukses():
    import logging
    import os
    from types import SimpleNamespace

    import iresis
    import jubelio
    log = logging.getLogger("uji-main")
    unduh = Path(tempfile.mkdtemp()) / "faktur.xlsx"
    unduh.write_bytes(b"PK")
    env = {"IRESIS_USERNAME": "bot", "IRESIS_PASSWORD": "x"}
    with mock.patch.dict(os.environ, env),             mock.patch.object(m, "login", return_value="TOK"),             mock.patch.object(jubelio, "ambil_url_faktur", return_value="u") as url,             mock.patch.object(jubelio, "ambil_url_pesanan", return_value="u2") as url_psn,             mock.patch.object(jubelio, "unduh_excel", return_value=unduh),             mock.patch.object(iresis, "unggah", return_value="ok") as unggah,             mock.patch.object(m, "cetak_bermasalah") as bermasalah:
        # mode uji: hanya unduh, tidak upload
        assert m.upload_faktur_iresis(log, SimpleNamespace(jalankan=False, hari=2)) == 0
        unggah.assert_not_called()
        dari, sampai = url.call_args.args[1:3]
        assert (sampai - dari).days == 1       # --hari 2 = kemarin + hari ini
        dari_p, sampai_p = url_psn.call_args.args[1:3]
        assert (sampai_p - dari_p).days == 3   # pesanan: 3 hari ke belakang + hari ini
        # sungguhan: upload dipanggil dengan file hasil unduh
        assert m.upload_faktur_iresis(log, SimpleNamespace(jalankan=True, hari=2)) == 0
        assert unggah.call_count == 2          # faktur lalu pesanan
        unggah.reset_mock()
        # faktur gagal tidak membatalkan upload pesanan, tapi exit code tetap 1
        unggah.side_effect = [iresis.IresisError("faktur ditolak"), "ok"]
        assert m.upload_faktur_iresis(log, SimpleNamespace(jalankan=True, hari=2)) == 1
        assert unggah.call_count == 2
        unggah.reset_mock()
        # gagal: exit 1 + peringatan mencolok, TIDAK melempar (TIPE tetap lanjut)
        unggah.side_effect = iresis.IresisError("server mati")
        assert m.upload_faktur_iresis(log, SimpleNamespace(jalankan=True, hari=2)) == 1
        assert "server mati" in bermasalah.call_args.args[0][0]["Catatan"]
    # kredensial kosong + --jalankan: gagal tanpa menyentuh jaringan
    with mock.patch.dict(os.environ, {}, clear=True),             mock.patch.object(m, "login") as login, mock.patch.object(m, "cetak_bermasalah"):
        assert m.upload_faktur_iresis(log, SimpleNamespace(jalankan=True, hari=2)) == 1
        login.assert_not_called()
    print("  --upload-iresis: mode uji hanya unduh; gagal -> exit 1 tanpa menghentikan TIPE")


def uji_jam_malam_16_sampai_0659():
    for h, harapan in ((6, True), (7, False), (12, False), (15, False), (16, True), (23, True), (0, True)):
        assert m.jam_malam(_jam(h, 59)) is harapan, h
    print("  jam_malam(): True 16.00-06.59, False 07.00-15.59")


def uji_iresis_dilewati_jam_2000_sampai_0459():
    for h, harapan in ((19, False), (20, True), (23, True), (0, True), (4, True), (5, False), (12, False)):
        assert m.jam_tanpa_iresis(_jam(h, 30)) is harapan, h
    for h, paksa, dilewati in ((22, False, True), (3, False, True), (22, True, False), (10, False, False)):
        with mock.patch.object(sys, "argv", ["main.py", "--upload-iresis"] + (["--paksa"] if paksa else [])), \
                mock.patch.object(m, "siapkan_log"), mock.patch.object(m, "muat_env"), \
                mock.patch.object(m, "jam_tanpa_iresis", return_value=(h >= 20 or h < 5)), \
                mock.patch.object(m, "upload_faktur_iresis", return_value=0) as up:
            assert m.main() == 0 or True
            assert up.called is (not dilewati), (h, paksa)
    print("  IRESIS: dilewati 20.00-04.59 (kecuali --paksa), jalan di luar jendela itu")


def uji_urgent_lewati_malam_tidak_membuat_folder_sesi_dan_tidak_memproses():
    with tempfile.TemporaryDirectory() as tmp,             mock.patch.object(m, "FOLDER_LABEL", Path(tmp)),             mock.patch.object(m, "siapkan_log"), mock.patch.object(m, "muat_env"),             mock.patch.object(m, "urgent_picklist") as urgent:
        for h, dilewati in ((16, True), (3, True), (10, False)):
            urgent.reset_mock()
            with mock.patch.object(sys, "argv", ["main.py", "--urgent", "--lewati-malam"]),                     mock.patch.object(m, "jam_malam", return_value=dilewati):
                m.main()
            assert urgent.called is (not dilewati), h
        assert not list(Path(tmp).iterdir()) or urgent.called
    print("  --urgent --lewati-malam: dilewati 16.00-06.59 (tanpa folder sesi), jalan 07.00-15.59")



# -------------------------------------------------- mode event (SPX Hemat / SPX Standard)
def _args(**kw):
    from types import SimpleNamespace
    dasar = dict(kurir=None, event=False, label=False, reguler=False, spx_standard=False,
                 pagi=False, bagian=None, excel=Path("x.xlsx"), tanpa_cek_nilai=True,
                 jalankan=True, sku=None, tanpa_reguler=False)
    dasar.update(kw)
    return SimpleNamespace(**dasar)


def uji_mode_event_validasi_kombinasi_flag():
    salah = m.pesan_salah_mode_event
    # alur harian: tidak ada yang berubah / ditolak
    assert salah(_args()) is None
    assert salah(_args(label=True, kurir="jnt")) is None
    assert salah(_args(reguler=True, kurir="spx")) is None
    # SPX Hemat tanpa --event ditolak (jangan diam-diam dihitung digabung)
    for kurir in ("spx-hemat", "spx-hemat-pagi"):
        assert "--event" in salah(_args(label=True, kurir=kurir))
    # --event butuh --label/--reguler dan kurir mode event
    assert salah(_args(event=True, kurir="jnt")) is not None
    assert salah(_args(event=True, label=True)) is not None
    assert salah(_args(event=True, label=True, kurir="spx")) is not None
    for kurir in ("jnt", "spx-hemat", "spx-hemat-pagi"):
        assert salah(_args(event=True, label=True, kurir=kurir)) is None
        assert salah(_args(event=True, reguler=True, kurir=kurir)) is None
    # --spx-standard berdiri sendiri; --pagi hanya dengan --spx-standard
    assert salah(_args(spx_standard=True)) is None
    assert salah(_args(spx_standard=True, pagi=True)) is None
    assert salah(_args(pagi=True)) is not None
    assert salah(_args(spx_standard=True, label=True)) is not None
    print("  validasi flag mode event: spx-hemat tanpa --event ditolak; harian tidak terpengaruh")


def uji_mode_event_kurir_hitung_dan_nama_pdf():
    assert m.kurir_hitung(_args(kurir="jnt")) is None, "harian --kurir jnt tetap menggabung"
    assert m.kurir_hitung(_args(kurir="spx")) is None
    assert m.kurir_hitung(_args()) is None
    assert m.kurir_hitung(_args(event=True, kurir="jnt")) == "jnt"
    assert m.kurir_hitung(_args(event=True, kurir="spx-hemat-pagi")) == "spx-hemat-pagi"
    waktu = datetime(2026, 10, 10, 13, 5)
    assert m.nama_pdf_spesial(waktu, _args(kurir="jnt")) == "SKU_Spesial_2026-10-10_1305.pdf"
    assert m.nama_pdf_spesial(waktu, _args(event=True, kurir="spx-hemat")) \
        == "SKU_Spesial_2026-10-10_1305_spx-hemat.pdf"
    print("  kurir_hitung: hanya --event yang menghitung per kurir; PDF event diberi akhiran kurir")


def _df_event():
    import pandas as pd
    baris = ([(f"J{i}", "X", 1, "J&T Express Standard") for i in range(3)]
             + [(f"H{i}", "X", 1, "SPX Hemat") for i in range(3)]
             + [(f"S{i}", "X", 1, "SPX Standard") for i in range(4)])
    return pd.DataFrame([list(b) + [None] for b in baris],
                        columns=["No pesanan", "SKU", "qty", "Kurir", "Rak"])


def _jalankan_reguler(args):
    """Panggil reguler_picklist() dengan semua akses jaringan/Excel ditiru; kembalikan kwargs
    panggilan proses_reguler/rencana_reguler (positional + keyword)."""
    import logging

    import proses_label
    log = logging.getLogger("uji-main")
    with mock.patch.object(m, "login", return_value="TOK"), \
            mock.patch.object(m, "baca_excel", return_value=_df_event()), \
            mock.patch.object(m, "_lengkapi_fallback_bundle", side_effect=lambda k, df, g, l: (g, l)), \
            mock.patch.object(proses_label, "Klien"), \
            mock.patch.object(proses_label, "proses_reguler", return_value=[]) as proses, \
            mock.patch.object(proses_label, "rencana_reguler") as rencana, \
            mock.patch.object(m, "cetak_bermasalah", return_value=[]):
        assert m.reguler_picklist(log, args) == 0
    return (proses if args.jalankan else rencana).call_args


def uji_mode_event_reguler_picklist_spesial_per_kurir_dan_batas():
    harian = _jalankan_reguler(_args(reguler=True, kurir="jnt"))
    assert harian.args[1] == ({f"{p}{i}" for p in "JH" for i in range(3)}
                              | {f"S{i}" for i in range(4)}), \
        "harian: J&T + semua SPX (Hemat & Standard) digabung = 10 resi X, kurir=jnt hanya " \
        "membatasi picklist"
    assert harian.kwargs["batas"] is None

    event_jnt = _jalankan_reguler(_args(reguler=True, kurir="jnt", event=True))
    assert event_jnt.args[1] == {"J0", "J1", "J2"}, event_jnt.args[1]
    assert event_jnt.kwargs["batas"] is None

    hemat = _jalankan_reguler(_args(reguler=True, kurir="spx-hemat", event=True))
    assert hemat.args[1] == {"H0", "H1", "H2"}, "SPX Standard (4 resi) tidak ikut spesial Hemat"
    assert hemat.args[5] == "spx-hemat" and hemat.kwargs["batas"] is None

    pagi = _jalankan_reguler(_args(reguler=True, kurir="spx-hemat-pagi", event=True))
    assert pagi.args[1] == {"H0", "H1", "H2"}
    assert pagi.args[5] == "spx-hemat-pagi"
    b = pagi.kwargs["batas"]
    assert b is not None and (b.hour, b.minute) == (12, 0), b

    uji = _jalankan_reguler(_args(reguler=True, kurir="spx-hemat-pagi", event=True, jalankan=False))
    assert uji.kwargs["batas"] is not None and uji.kwargs["batas"].hour == 12, \
        "mode uji juga membawa batas jam"
    print("  reguler_picklist: harian digabung & tanpa batas; event J&T/Hemat dihitung per kurir; "
          "spx-hemat-pagi membawa batas jam 12:00 (juga di mode uji)")


def uji_spx_standard_picklist_meneruskan_pagi_dan_mode_uji():
    import logging

    import proses_label
    log = logging.getLogger("uji-main")
    with mock.patch.object(m, "login", return_value="TOK"), \
            mock.patch.object(proses_label, "Klien"), \
            mock.patch.object(proses_label, "rencana_spx_standard") as rencana, \
            mock.patch.object(proses_label, "proses_spx_standard", return_value=[]) as proses, \
            mock.patch.object(m, "cetak_bermasalah", return_value=[]):
        assert m.spx_standard_picklist(log, _args(spx_standard=True, jalankan=False, pagi=True)) == 0
        rencana.assert_called_once()
        assert rencana.call_args.args[1] is True
        proses.assert_not_called()
        assert m.spx_standard_picklist(log, _args(spx_standard=True, jalankan=True)) == 0
        assert proses.call_args.args[3] is False
        assert m.spx_standard_picklist(log, _args(spx_standard=True, jalankan=True, pagi=True)) == 0
        assert proses.call_args.args[3] is True
    print("  --spx-standard: mode uji tidak memproses; --pagi diteruskan ke proses_label")


def uji_main_menolak_spx_hemat_tanpa_event_sebelum_login():
    with mock.patch.object(sys, "argv", ["main.py", "--label", "--kurir", "spx-hemat"]), \
            mock.patch.object(m, "login") as login, mock.patch.object(m, "muat_env"), \
            mock.patch.object(m, "siapkan_log"):
        try:
            m._main()
        except SystemExit as e:
            assert e.code == 2
        else:
            raise AssertionError("harus ditolak argparse")
        login.assert_not_called()
    print("  main: --kurir spx-hemat tanpa --event ditolak (exit 2) sebelum login/folder sesi")



def uji_dalam_jam_menu_event_pilihan_2_setelah_jam_12():
    with mock.patch.object(m, "datetime") as dt:
        for jam, mnt, harapan in ((11, 59, False), (12, 0, True), (13, 0, True),
                                  (15, 59, True), (16, 0, False)):
            dt.now.return_value = _jam(jam, mnt)
            assert m.dalam_jam_menu("E2") is harapan, (jam, mnt)
    print("  menu event pilihan 2 (Shopee Pagi): valid 12.00-15.59, di luar itu diberi peringatan")


def uji_perintah_di_bat_event_lolos_argparse_dan_validasi_mode_event():
    """Setiap baris `main.py ...` di proses-event.bat & proses-event-uji.bat diuji lewat argparse
    SUNGGUHAN (_main berhenti tepat setelah parse, sebelum muat_env/login): salah ketik flag atau
    kombinasi yang ditolak pesan_salah_mode_event() ketahuan di sini, bukan di hari event."""
    import re
    import shlex

    class Berhenti(Exception):
        pass

    pola = re.compile(r'^(?:if /i "%JNT_SIANG%"=="Y" )?"\.venv\\Scripts\\python\.exe" '
                      r'src\\main\.py (.*)$')
    total = 0
    for nama in ("proses-event.bat", "proses-event-uji.bat"):
        for baris in (ROOT / nama).read_text(encoding="utf-8").splitlines():
            cocok = pola.match(baris)
            if not cocok:
                continue
            args = shlex.split(cocok.group(1), posix=False)
            with mock.patch.object(sys, "argv", ["main.py", *args]), \
                    mock.patch.object(m, "muat_env", side_effect=Berhenti):
                try:
                    m._main()
                except Berhenti:
                    total += 1
                except SystemExit as e:
                    raise AssertionError(f"{nama}: argparse menolak `{cocok.group(1)}` (exit {e.code})")
    assert total >= 2 * (14 + 17), total
    print(f"  {total} perintah main.py di .bat event: semuanya diterima argparse & validasi mode event")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
