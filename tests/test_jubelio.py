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


def _tempel(monkeypatch_dict, nama, fungsi):
    """Ganti atribut modul `requests` sementara; dikembalikan oleh pemanggil lewat try/finally."""
    import requests
    lama = getattr(requests, nama)
    setattr(requests, nama, fungsi)
    monkeypatch_dict[nama] = lama
    return lama


def _pulihkan(lama_dict):
    import requests
    for nama, fungsi in lama_dict.items():
        setattr(requests, nama, fungsi)


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

    _tempel(lama, "post", post_palsu)
    try:
        token = jb.login("a@b.com", "rahasia")
    finally:
        _pulihkan(lama)
    assert token == "TKN-ABC"
    assert dipanggil["url"] == jb.URL_LOGIN
    assert dipanggil["json"]["email"] == "a@b.com" and dipanggil["json"]["password"] == "rahasia"
    assert "x-login-check" in dipanggil["headers"]
    print("  login: sukses -> token dikembalikan, body & header login terkirim benar")


def uji_login_gagal_http_bukan_200():
    lama = {}
    _tempel(lama, "post", lambda *a, **k: Resp(401, {"message": "Email/password salah"}))
    try:
        try:
            jb.login("a@b.com", "salah")
        except jb.JubelioError as e:
            assert "401" in str(e) and "Email/password salah" in str(e), e
        else:
            raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _pulihkan(lama)
    print("  login: HTTP 401 -> JubelioError dengan pesan dari respons")


def uji_login_sukses_tapi_token_kosong():
    lama = {}
    _tempel(lama, "post", lambda *a, **k: Resp(200, {}))
    try:
        try:
            jb.login("a@b.com", "x")
        except jb.JubelioError as e:
            assert "token" in str(e).lower()
        else:
            raise AssertionError("seharusnya JubelioError kalau token tidak ada di respons")
    finally:
        _pulihkan(lama)
    print("  login: HTTP 200 tapi tanpa token -> JubelioError")


# -------------------------------------------------- ambil_url_laporan()
def uji_ambil_url_laporan_sukses():
    lama = {}
    _tempel(lama, "get", lambda *a, **k: Resp(200, {"status": "ok", "url": "https://x/?token=1"}))
    try:
        url = jb.ambil_url_laporan("TKN")
    finally:
        _pulihkan(lama)
    assert url == "https://x/?token=1"
    print("  ambil_url_laporan: status ok -> url dikembalikan")


def uji_ambil_url_laporan_status_bukan_ok():
    lama = {}
    _tempel(lama, "get", lambda *a, **k: Resp(200, {"status": "error", "url": None}))
    try:
        try:
            jb.ambil_url_laporan("TKN")
        except jb.JubelioError:
            pass
        else:
            raise AssertionError("seharusnya JubelioError kalau status bukan ok / url kosong")
    finally:
        _pulihkan(lama)
    print("  ambil_url_laporan: status bukan 'ok' atau url kosong -> JubelioError")


# -------------------------------------------------- unduh_excel()
def uji_unduh_excel_sukses_simpan_file():
    lama = {}
    isi = b"PK\x03\x04isi excel palsu"
    dipanggil = {}

    def get_palsu(url, timeout=None, cookies=None, headers=None):
        dipanggil["url"], dipanggil["cookies"] = url, cookies
        return Resp(200, content=isi, headers={"content-type": "application/vnd.ms-excel"})

    _tempel(lama, "get", get_palsu)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tujuan = jb.unduh_excel("TKN", "https://report-prod.jubelio.com/?&token=X", Path(tmp))
            assert tujuan.exists() and tujuan.read_bytes() == isi
            assert tujuan.parent == Path(tmp)
    finally:
        _pulihkan(lama)
    assert dipanggil["url"] == "https://report-prod.jubelio.com/xlsx/?&token=X"
    assert dipanggil["cookies"] == {"JB_OMNI_ACCESS_TOKEN": "TKN"}
    print("  unduh_excel: file disimpan ke folder tujuan, memakai url /xlsx/ & cookie token")


def uji_unduh_excel_bukan_file_excel():
    lama = {}
    _tempel(lama, "get", lambda *a, **k: Resp(200, content=b"<html>bukan excel</html>",
                                              headers={"content-type": "text/html"}))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                jb.unduh_excel("TKN", "https://x/?token=1", Path(tmp))
            except jb.JubelioError as e:
                assert "bukan file Excel" in str(e)
            else:
                raise AssertionError("seharusnya JubelioError kalau respons bukan file xlsx (bukan 'PK')")
    finally:
        _pulihkan(lama)
    print("  unduh_excel: konten tidak diawali 'PK' (bukan zip/xlsx) -> JubelioError")


def uji_unduh_excel_http_gagal():
    lama = {}
    _tempel(lama, "get", lambda *a, **k: Resp(500, text="server error"))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                jb.unduh_excel("TKN", "https://x/?token=1", Path(tmp))
            except jb.JubelioError as e:
                assert "500" in str(e)
            else:
                raise AssertionError("seharusnya JubelioError kalau HTTP bukan 200")
    finally:
        _pulihkan(lama)
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
    # page_size tetap 25 di jubelio.py -> untuk memaksa halaman ke-2 benar-benar diambil,
    # halaman pertama harus penuh (25 item) dan totalCount > 25.
    halaman1 = [{"salesorder_no": f"X{i}", "grand_total": "1000.0000"} for i in range(25)]
    halaman2 = [{"salesorder_no": "C", "grand_total": "5000.0000"}]
    sesi = SesiPalsu([halaman1, halaman2], hasil_q={})
    lama = {}
    import requests
    lama["Session"] = requests.Session
    requests.Session = lambda: sesi
    try:
        nilai = jb.ambil_nilai_pesanan("TKN", {"X0", "C"})
    finally:
        requests.Session = lama["Session"]
    assert nilai["X0"] == 1000.0 and nilai["C"] == 5000.0 and len(nilai) == 26, nilai
    halaman_diminta = sorted({p["page"] for p in sesi.log if not p.get("q")})
    assert halaman_diminta == [1, 2], halaman_diminta
    print("  ambil_nilai_pesanan: halaman ke-2 ikut diambil & digabung selama totalCount > "
          "yang sudah terkumpul")


def uji_ambil_nilai_pesanan_cari_satu_per_satu_yang_belum_ketemu():
    halaman = [[{"salesorder_no": "A", "grand_total": "10000.0000"}]]
    sesi = SesiPalsu(halaman, hasil_q={"B": {"salesorder_no": "B", "grand_total": "2500.0000"}})
    lama = {}
    import requests
    lama["Session"] = requests.Session
    requests.Session = lambda: sesi
    try:
        nilai = jb.ambil_nilai_pesanan("TKN", {"A", "B", "TIDAK-ADA"})
    finally:
        requests.Session = lama["Session"]
    assert nilai == {"A": 10000.0, "B": 2500.0}, nilai
    # "TIDAK-ADA" dicari (q) tapi tidak ketemu -> tidak masuk dict, tidak error
    dicari_individual = [p["q"] for p in sesi.log if p.get("q")]
    assert set(dicari_individual) == {"B", "TIDAK-ADA"}, dicari_individual
    print("  ambil_nilai_pesanan: resi yang tak ketemu di daftar halaman dicari satu-satu via q, "
          "yang tetap tak ketemu dilewati tanpa error")


if __name__ == "__main__":
    for nama, f in list(globals().items()):
        if nama.startswith("uji_"):
            print(nama)
            f()
    print("SEMUA UJI LULUS")
