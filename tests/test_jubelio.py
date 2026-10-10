"""Uji jubelio.py dengan requests ditiru (tanpa akses internet sungguhan).

Jalankan:  .venv\\Scripts\\python tests\\test_jubelio.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import jubelio as jb  # noqa: E402


class Resp:
    def __init__(self, status=200, data=None, content=None, headers=None, text=None):
        self.status_code = status
        self._data = data
        self.content = content if content is not None else b""
        self.text = text if text is not None else ""
        self.headers = headers or {}

    def json(self):
        return self._data


# jubelio.py memakai 1 requests.Session dibagi (dicache di jubelio._sesi_bersama - lihat
# jubelio._sesi()) supaya koneksi dipakai ulang antar panggilan - jadi di sini ditiru dengan
# mengganti requests.Session (bukan requests.get/post module-level, yang tidak lagi dipanggil
# langsung), dan _sesi_bersama DIRESET sebelum & sesudah tiap uji supaya tidak ada sesi tiruan
# uji sebelumnya yang "nyangkut" di cache lintas fungsi uji.
class _SesiPalsu:
    """Sesi requests tiruan generik: `get`/`post` dilempar ke fungsi yang diberikan."""

    def __init__(self, get=None, post=None):
        self._get, self._post = get, post

    def get(self, *a, **k):
        return self._get(*a, **k)

    def post(self, *a, **k):
        return self._post(*a, **k)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _pasang_sesi(lama_dict, sesi):
    import requests
    lama_dict["Session"] = requests.Session
    requests.Session = lambda: sesi
    jb._sesi_bersama = None


def _lepas_sesi(lama_dict):
    import requests
    requests.Session = lama_dict["Session"]
    jb._sesi_bersama = None


# -------------------------------------------------- url_excel (fungsi murni)
def uji_url_excel_ganti_path_jadi_xlsx():
    url = jb.url_excel("https://report-prod.jubelio.com/?&token=RPT123")
    assert url == "https://report-prod.jubelio.com/xlsx/?&token=RPT123", url
    print("  url_excel: path '/' diganti '/xlsx/', query & host dipertahankan")


# -------------------------------------------------- login()
def uji_login_sukses_kembalikan_token():
    lama = {}
    dipanggil = {}

    def post_palsu(url, json=None, timeout=None, headers=None):
        dipanggil["url"], dipanggil["json"], dipanggil["headers"] = url, json, headers
        return Resp(200, {"token": "TKN-ABC"})

    _pasang_sesi(lama, _SesiPalsu(post=post_palsu))
    try:
        token = jb.login("a@b.com", "rahasia")
    finally:
        _lepas_sesi(lama)
    assert token == "TKN-ABC"
    assert dipanggil["url"] == jb.URL_LOGIN
    assert dipanggil["json"]["email"] == "a@b.com" and dipanggil["json"]["password"] == "rahasia"
    assert "x-login-check" in dipanggil["headers"]
    print("  login: sukses -> token dikembalikan, body & header login terkirim benar")


def uji_login_gagal_http_bukan_200():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(post=lambda *a, **k: Resp(401, {"message": "Email/password salah"})))
    try:
        try:
            jb.login("a@b.com", "salah")
        except jb.JubelioError as e:
            assert "401" in str(e) and "Email/password salah" in str(e), e
        else:
            raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _lepas_sesi(lama)
    print("  login: HTTP 401 -> JubelioError dengan pesan dari respons")


def uji_login_sukses_tapi_token_kosong():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(post=lambda *a, **k: Resp(200, {})))
    try:
        try:
            jb.login("a@b.com", "x")
        except jb.JubelioError as e:
            assert "token" in str(e).lower()
        else:
            raise AssertionError("seharusnya JubelioError kalau token tidak ada di respons")
    finally:
        _lepas_sesi(lama)
    print("  login: HTTP 200 tapi tanpa token -> JubelioError")


# -------------------------------------------------- ambil_url_laporan()
def uji_ambil_url_laporan_sukses():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(
        get=lambda *a, **k: Resp(200, {"status": "ok", "url": "https://x/?token=1"})))
    try:
        url = jb.ambil_url_laporan("TKN")
    finally:
        _lepas_sesi(lama)
    assert url == "https://x/?token=1"
    print("  ambil_url_laporan: status ok -> url dikembalikan")


def uji_ambil_url_laporan_status_bukan_ok():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(
        get=lambda *a, **k: Resp(200, {"status": "error", "url": None})))
    try:
        try:
            jb.ambil_url_laporan("TKN")
        except jb.JubelioError:
            pass
        else:
            raise AssertionError("seharusnya JubelioError kalau status bukan ok / url kosong")
    finally:
        _lepas_sesi(lama)
    print("  ambil_url_laporan: status bukan 'ok' atau url kosong -> JubelioError")


# -------------------------------------------------- unduh_excel()
def uji_unduh_excel_sukses_simpan_file():
    lama = {}
    isi = b"PK\x03\x04isi excel palsu"
    dipanggil = {}

    def get_palsu(url, timeout=None, cookies=None, headers=None):
        dipanggil["url"], dipanggil["cookies"] = url, cookies
        return Resp(200, content=isi, headers={"content-type": "application/vnd.ms-excel"})

    _pasang_sesi(lama, _SesiPalsu(get=get_palsu))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tujuan = jb.unduh_excel("TKN", "https://report-prod.jubelio.com/?&token=X", Path(tmp))
            assert tujuan.exists() and tujuan.read_bytes() == isi
            assert tujuan.parent == Path(tmp)
    finally:
        _lepas_sesi(lama)
    assert dipanggil["url"] == "https://report.jubelio.com/xlsx/?&token=X"
    assert dipanggil["cookies"] == {"JB_OMNI_ACCESS_TOKEN": "TKN"}
    print("  unduh_excel: file disimpan ke folder tujuan, memakai url /xlsx/ & cookie token")


def uji_unduh_excel_fallback_ke_report_prod():
    lama = {}
    isi = b"PKisi excel palsu"
    urls = []

    def get_palsu(url, timeout=None, cookies=None, headers=None):
        urls.append(url)
        if "report-prod" not in url:
            return Resp(504, content=b"", headers={})
        return Resp(200, content=isi, headers={})

    _pasang_sesi(lama, _SesiPalsu(get=get_palsu))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tujuan = jb.unduh_excel("TKN", "https://report-prod.jubelio.com/?&token=X", Path(tmp))
            assert tujuan.read_bytes() == isi
    finally:
        _lepas_sesi(lama)
    assert urls == ["https://report.jubelio.com/xlsx/?&token=X",
                    "https://report-prod.jubelio.com/xlsx/?&token=X"], urls
    print("  unduh_excel: report.jubelio.com gagal -> fallback report-prod.jubelio.com")


def uji_unduh_excel_bukan_file_excel():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(get=lambda *a, **k: Resp(
        200, content=b"<html>bukan excel</html>", headers={"content-type": "text/html"})))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                jb.unduh_excel("TKN", "https://x/?token=1", Path(tmp))
            except jb.JubelioError as e:
                assert "bukan file Excel" in str(e)
            else:
                raise AssertionError("seharusnya JubelioError kalau respons bukan file xlsx (bukan 'PK')")
    finally:
        _lepas_sesi(lama)
    print("  unduh_excel: konten tidak diawali 'PK' (bukan zip/xlsx) -> JubelioError")


def uji_unduh_excel_http_gagal():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(get=lambda *a, **k: Resp(500, text="server error")))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                jb.unduh_excel("TKN", "https://x/?token=1", Path(tmp))
            except jb.JubelioError as e:
                assert "500" in str(e)
            else:
                raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _lepas_sesi(lama)
    print("  unduh_excel: HTTP bukan 200 -> JubelioError")


# -------------------------------------------------- ambil_nilai_pesanan()
class SesiPalsu:
    """Meniru requests.Session() dipakai di ambil_nilai_pesanan (paginasi + pencarian q)."""

    def __init__(self, halaman: list[list[dict]], hasil_q: dict[str, dict]):
        self.halaman = halaman    # list per halaman (page 1, 2, ...) dari data "biasa"
        self.hasil_q = hasil_q    # {q: order-dict} untuk pencarian individual
        self.log = []

    def get(self, url, headers=None, timeout=None, params=None):
        self.log.append(dict(params))
        q = params.get("q", "")
        if q:
            o = self.hasil_q.get(q)
            return Resp(200, {"data": [o] if o else [], "totalCount": 1 if o else 0})
        page = params["page"]
        if page > len(self.halaman):
            return Resp(200, {"data": [], "totalCount": sum(len(h) for h in self.halaman)})
        return Resp(200, {"data": self.halaman[page - 1],
                          "totalCount": sum(len(h) for h in self.halaman)})

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def uji_ambil_nilai_pesanan_gabung_semua_halaman():
    # page_size tetap 200 di jubelio.py -> untuk memaksa halaman ke-2 benar-benar diambil,
    # halaman pertama harus penuh (200 item) dan totalCount > 200.
    halaman1 = [{"salesorder_no": f"X{i}", "grand_total": "1000.0000"} for i in range(200)]
    halaman2 = [{"salesorder_no": "C", "grand_total": "5000.0000"}]
    sesi = SesiPalsu([halaman1, halaman2], hasil_q={})
    lama = {}
    _pasang_sesi(lama, sesi)
    try:
        nilai = jb.ambil_nilai_pesanan("TKN", {"X0", "C"})
    finally:
        _lepas_sesi(lama)
    assert nilai["X0"] == 1000.0 and nilai["C"] == 5000.0 and len(nilai) == 201, nilai
    halaman_diminta = sorted({p["page"] for p in sesi.log if not p.get("q")})
    assert halaman_diminta == [1, 2], halaman_diminta
    print("  ambil_nilai_pesanan: halaman ke-2 ikut diambil & digabung selama totalCount > "
          "yang sudah terkumpul")


def uji_ambil_nilai_pesanan_cari_satu_per_satu_yang_belum_ketemu():
    halaman = [[{"salesorder_no": "A", "grand_total": "10000.0000"}]]
    sesi = SesiPalsu(halaman, hasil_q={"B": {"salesorder_no": "B", "grand_total": "2500.0000"}})
    lama = {}
    _pasang_sesi(lama, sesi)
    try:
        nilai = jb.ambil_nilai_pesanan("TKN", {"A", "B", "TIDAK-ADA"})
    finally:
        _lepas_sesi(lama)
    assert nilai == {"A": 10000.0, "B": 2500.0}, nilai
    # "TIDAK-ADA" dicari (q) tapi tidak ketemu -> tidak masuk dict, tidak error
    dicari_individual = [p["q"] for p in sesi.log if p.get("q")]
    assert set(dicari_individual) == {"B", "TIDAK-ADA"}, dicari_individual
    print("  ambil_nilai_pesanan: resi yang tak ketemu di daftar halaman dicari satu-satu via q, "
          "yang tetap tak ketemu dilewati tanpa error")


# -------------------------------------------------- ambil_stok_kosong() / recheck_stok()
def uji_ambil_stok_kosong_gabung_semua_halaman():
    halaman1 = [{"salesorder_no": f"X{i}", "wms_status": "EMPTY_STOCK"} for i in range(200)]
    halaman2 = [{"salesorder_no": "C", "wms_status": "EMPTY_STOCK"}]
    sesi = SesiPalsu([halaman1, halaman2], hasil_q={})
    lama = {}
    _pasang_sesi(lama, sesi)
    try:
        hasil = jb.ambil_stok_kosong("TKN")
    finally:
        _lepas_sesi(lama)
    assert len(hasil) == 201, len(hasil)
    assert {o["salesorder_no"] for o in hasil} == {f"X{i}" for i in range(200)} | {"C"}
    print("  ambil_stok_kosong: halaman ke-2 ikut diambil & digabung selama totalCount > "
          "yang sudah terkumpul")


class SesiGagalPalsu:
    """Sesi palsu yang selalu membalas HTTP 500 - meniru requests.Session() dipakai
    ambil_stok_kosong()."""

    def get(self, url, headers=None, timeout=None, params=None):
        return Resp(500, text="server error")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def uji_ambil_stok_kosong_http_gagal():
    lama = {}
    _pasang_sesi(lama, SesiGagalPalsu())
    try:
        try:
            jb.ambil_stok_kosong("TKN")
        except jb.JubelioError as e:
            assert "500" in str(e)
        else:
            raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _lepas_sesi(lama)
    print("  ambil_stok_kosong: HTTP bukan 200 -> JubelioError")


def uji_recheck_stok_sukses():
    lama = {}
    dipanggil = {}

    def get_palsu(url, headers=None, timeout=None):
        dipanggil["url"], dipanggil["headers"] = url, headers
        return Resp(200, {"status": "ok"})

    _pasang_sesi(lama, _SesiPalsu(get=get_palsu))
    try:
        jb.recheck_stok("TKN")   # tidak error = sukses
    finally:
        _lepas_sesi(lama)
    assert dipanggil["url"] == jb.URL_RECHECK_STOK
    assert dipanggil["headers"]["authorization"] == "TKN"
    print("  recheck_stok: GET tanpa body/parameter ke URL_RECHECK_STOK, authorization terisi")


def uji_recheck_stok_status_bukan_ok():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(get=lambda *a, **k: Resp(200, {"status": "gagal"})))
    try:
        try:
            jb.recheck_stok("TKN")
        except jb.JubelioError:
            pass
        else:
            raise AssertionError("seharusnya JubelioError kalau status respons bukan 'ok'")
    finally:
        _lepas_sesi(lama)
    print("  recheck_stok: respons status bukan 'ok' -> JubelioError")


def uji_recheck_stok_http_gagal():
    lama = {}
    _pasang_sesi(lama, _SesiPalsu(get=lambda *a, **k: Resp(500, text="server error")))
    try:
        try:
            jb.recheck_stok("TKN")
        except jb.JubelioError as e:
            assert "500" in str(e)
        else:
            raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _lepas_sesi(lama)
    print("  recheck_stok: HTTP bukan 200 -> JubelioError")


# -------------------------------------------------- retry timeout/koneksi putus
def uji_retry_timeout_lalu_berhasil():
    import requests
    jeda, panggilan = [], []

    def fn():
        panggilan.append(1)
        if len(panggilan) < 3:
            raise requests.exceptions.ReadTimeout("Read timed out")
        return Resp(200, data={"ok": 1})

    r = jb._kirim_dengan_retry429(fn, tidur=jeda.append)
    assert r.status_code == 200 and len(panggilan) == 3
    assert jeda == [jb.JEDA_COBA_KONEKSI_S, jb.JEDA_COBA_KONEKSI_S * 2], jeda
    print("  retry: 2x ReadTimeout lalu sukses -> diulang dengan jeda bertambah")


def uji_retry_timeout_habis_jatah_melempar_error():
    import requests
    panggilan = []

    def fn():
        panggilan.append(1)
        raise requests.exceptions.ReadTimeout("Read timed out")

    try:
        jb._kirim_dengan_retry429(fn, tidur=lambda s: None)
    except requests.exceptions.ReadTimeout:
        assert len(panggilan) == jb.MAKS_COBA_KONEKSI
    else:
        raise AssertionError("seharusnya ReadTimeout setelah jatah habis")
    print("  retry: timeout terus-menerus -> menyerah setelah MAKS_COBA_KONEKSI")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
