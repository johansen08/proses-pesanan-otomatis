"""Uji peringatan_sisa.py (penjaga pesanan Siap Proses kemarin yang tak tersentuh program) dan
pemetaan channel Tokopedia asli (TP-..., source 128) ke alur reguler - tanpa akses internet.

Latar belakang: insiden 09/10/2026, 2 resi wajib keluar (TP-... J&T Standard multi-SKU dan
TP-... JNE-MP) tidak pernah masuk picklist & tidak ada peringatan sama sekali.

Jalankan:  .venv\\Scripts\\python tests\\test_peringatan_sisa.py
"""
import datetime as dt
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import peringatan_sisa as ps  # noqa: E402
import proses_label as pl  # noqa: E402

WIB = dt.timezone(dt.timedelta(hours=7))
SEKARANG = dt.datetime(2026, 10, 9, 15, 30, tzinfo=WIB)


def _o(no, source, shipper, tgl_wib, nama_channel=None, so_id=1):
    """Pesanan Siap Proses tiruan; tgl_wib 'YYYY-MM-DD HH:MM' (WIB) -> transaction_date UTC."""
    waktu = dt.datetime.strptime(tgl_wib, "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
    return {"salesorder_id": so_id, "salesorder_no": no, "source": source, "shipper": shipper,
            "source_name": nama_channel or str(source), "grand_total": "35900.0000",
            "total_qty": "1.0000",
            "transaction_date": waktu.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}


class KlienPalsu:
    """Meniru pl.Klien.get() untuk ready-to-process (berhalaman); mencatat parameter."""

    def __init__(self, pesanan):
        self.pesanan, self.params = pesanan, []

    def get(self, path, params=None):
        assert path.endswith("ready-to-process/"), path
        self.params.append(params)
        mulai = (params["page"] - 1) * params["page_size"]
        return {"data": self.pesanan[mulai:mulai + params["page_size"]],
                "totalCount": len(self.pesanan)}


def uji_channel_tokopedia_ikut_reguler_dan_jnt_siang():
    assert pl.CHANNEL_ID_TOKOPEDIA == 128
    assert pl.CHANNEL_IDS_REGULER == [pl.CHANNEL_ID_TIKTOK_SHOP, pl.CHANNEL_ID_TOKOPEDIA,
                                      pl.CHANNEL_ID_SHOPEE]
    tp = _o("TP-586471614456366382-109465", 128, "J&T Express Standard", "2026-10-08 10:24", so_id=7)
    tt = _o("TT-1", 131076, "J&T Express Standard", "2026-10-08 10:24", so_id=8)
    k = KlienPalsu([tp, tt])
    hasil = pl.ambil_pesanan_reguler(k, kurir="jnt")
    assert {o["salesorder_no"] for o in hasil} == {"TP-586471614456366382-109465", "TT-1"}, hasil
    assert 128 in {v for kk, v in k.params[0].items() if kk.startswith("channel_ids[")}
    # J&T Siang: TP- (Tokopedia asli) ikut, pesanan sebelum jam 15:00 hari ini
    siang = pl.ambil_pesanan_jnt_siang(KlienPalsu([tp, tt]), sekarang=SEKARANG)
    assert len(siang) == 2, siang
    print("  TP-... (channel 128) ikut ambil_pesanan_reguler() & J&T Resi Siang, bukan cuma TT-...")


def uji_alasan_menebak_penyebab():
    assert "kurir JNE-MP JNE di luar" not in ps.alasan(
        _o("TP-1", 128, "JNE-MP JNE", "2026-10-08 10:00")), "JNE sekarang ada alurnya (JNE-LEX)"
    a = ps.alasan(_o("X-1", 64, "Ninja Xpress", "2026-10-08 10:00"))
    assert a == "kurir Ninja Xpress di luar semua alur", a
    a = ps.alasan(_o("X-2", 999, "J&T Express Standard", "2026-10-08 10:00", "MARKET BARU"))
    assert a == "channel MARKET BARU di luar alur reguler", a
    a = ps.alasan(_o("TP-2", 128, "J&T Express Standard", "2026-10-08 10:00"))
    assert a.startswith("tidak ikut picklist"), a      # channel & kurir sudah tercakup alur
    a = ps.alasan(_o("TT-2", 131076, "GoTo Logistics GTL Standard", "2026-10-08 10:00"))
    assert a.startswith("tidak ikut picklist"), "GTL ('GoTo Logistics GTL') dikenal alur urgent"
    assert ps.alasan(_o("LZ-1", 4, "LEX ID", "2026-10-08 10:00")).startswith("tidak ikut picklist")
    print("  alasan(): kurir/channel di luar alur ditebak, kurir urgent lintas channel dikenal")


def uji_cari_tak_tersentuh_hanya_sebelum_hari_ini():
    pesanan = [
        _o("KEMARIN", 128, "J&T Express Standard", "2026-10-08 10:24", so_id=1),
        _o("KEMARIN-MALAM", 64, "SPX Hemat", "2026-10-08 23:59", so_id=2),
        _o("HARI-INI-PAGI", 64, "SPX Hemat", "2026-10-09 00:00", so_id=3),
        _o("HARI-INI", 64, "SPX Hemat", "2026-10-09 14:00", so_id=4),
        {"salesorder_id": 5, "salesorder_no": "TANPA-TANGGAL", "source": 64, "shipper": "SPX Hemat"},
    ]
    hasil = ps.cari_tak_tersentuh(pesanan, SEKARANG)
    assert [o["salesorder_no"] for o in hasil] == ["KEMARIN", "KEMARIN-MALAM"], hasil
    print("  cari_tak_tersentuh(): hanya jam pesan < 00:00 WIB hari ini (terlama dulu); tanpa tanggal diabaikan")


def uji_periksa_ambil_semua_tanpa_filter_dan_catat_per_alasan():
    with tempfile.TemporaryDirectory() as d:
        ps._sesi.clear()
        ps.atur_folder(Path(d))
        k = KlienPalsu([
            _o("TP-JNE", 128, "Ninja Xpress", "2026-10-08 05:41", so_id=1),
            _o("TP-AMAN", 128, "J&T Express Standard", "2026-10-08 10:24", so_id=2),
            _o("SP-BARU", 64, "SPX Hemat", "2026-10-09 14:00", so_id=3),
        ])
        pesan = ps.periksa(k, SEKARANG)
        params = k.params[0]
        assert not any(kk.startswith(("channel_ids[", "couriers[")) for kk in params), \
            "penjaga harus mengambil SEMUA pesanan Siap Proses, tanpa filter channel/kurir"
        assert len(pesan) == 2, pesan
        assert any("kurir Ninja Xpress di luar semua alur" in p and "TP-JNE" in p for p in pesan)
        assert any("tidak ikut picklist" in p and "TP-AMAN" in p for p in pesan)
        assert not any("SP-BARU" in p for p in pesan), "pesanan hari ini tidak diperingatkan"
        # persisten lintas proses: dibaca rekap_waktu lewat baca_sejak()
        sejak = SEKARANG.timestamp() - 10 * 365 * 86400
        assert len(ps.baca_sejak(sejak)) == 2
        assert ps.baca_sejak(10 ** 12) == []
        assert (Path(d) / "pesanan_tak_tersentuh.jsonl").exists()
        ps._sesi.clear()
        ps._file_peringatan = None
    print("  periksa(): tanpa filter channel/kurir, 1 peringatan per alasan, tersimpan di jsonl")


def uji_periksa_tanpa_sisa_tidak_mencatat_apa_apa():
    ps._sesi.clear()
    ps._file_peringatan = None
    k = KlienPalsu([_o("SP-BARU", 64, "SPX Hemat", "2026-10-09 14:00")])
    assert ps.periksa(k, SEKARANG) == [] and ps._sesi == []
    print("  periksa(): semua pesanan hari ini -> tidak ada peringatan")


def uji_periksa_batasi_jumlah_nomor_di_pesan():
    ps._sesi.clear()
    ps._file_peringatan = None
    banyak = [_o(f"TP-{i}", 128, "Ninja Xpress", "2026-10-08 10:00", so_id=i) for i in range(40)]
    pesan = ps.periksa(KlienPalsu(banyak), SEKARANG)
    assert len(pesan) == 1 and "40 pesanan" in pesan[0]
    assert f"+{40 - ps.MAKS_NOMOR_DITAMPILKAN} lainnya" in pesan[0], pesan[0]
    ps._sesi.clear()
    print("  periksa(): nomor pesanan ditampilkan dibatasi, sisanya '+N lainnya'")


def uji_main_punya_penjaga_dan_channel_jne_lex():
    import main

    assert callable(main.cek_pesanan_tak_tersentuh)
    # kegagalan penjaga (API/login) tidak boleh melempar: TIPE tetap lanjut
    import logging
    from unittest import mock
    with mock.patch.object(main, "login", side_effect=SystemExit("tanpa .env")):
        main.cek_pesanan_tak_tersentuh(logging.getLogger("uji"))
    with mock.patch.object(main, "login", return_value="TKN"), \
            mock.patch.object(ps, "periksa", side_effect=RuntimeError("API mati")):
        main.cek_pesanan_tak_tersentuh(logging.getLogger("uji"))
    print("  main.cek_pesanan_tak_tersentuh(): gagal login/API hanya jadi warning, tidak melempar")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
