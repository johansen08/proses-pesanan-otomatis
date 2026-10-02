# Pecah Picklist 1qty Reguler per Grup Rak - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bagian "1qty" picklist sisa reguler (`--reguler --bagian 1qty`) dipecah lagi jadi
picklist terpisah per grup rak gudang (2A, 3A, 1B, 2B, 3B, + "lainnya"), bukan 1 picklist
gabungan seperti sekarang.

**Architecture:** Tidak ada field rak di daftar pesanan Jubelio (`ready-to-process`) - rak
cuma bisa diketahui lewat endpoint `zones-racks-combination` (daftar string kombinasi rak unik
format `GROUP-ZONE-SLOT`) dikombinasikan dengan parameter `combination[]` di `ready-to-process`
(filter pesanan yang kombinasi raknya cocok). Alurnya: ambil semua kombinasi rak tunggal ->
kelompokkan per grup -> query ulang `ready-to-process` per grup (dengan filter channel/kurir
reguler yang sama) buat dapat `salesorder_id` per grup -> partisi `satu_qty` (hasil
`pisah_reguler()` yang sudah ada) berdasarkan keanggotaan id itu. Sisa yang tidak match ->
"lainnya". Lihat spec lengkap di
[docs/superpowers/specs/2026-10-02-pecah-1qty-per-rak-design.md](../specs/2026-10-02-pecah-1qty-per-rak-design.md).

**Tech Stack:** Python 3.13, `requests` (lewat `Klien` di `src/proses_label.py`), test manual
(`tests/test_proses_label.py`, server Jubelio tiruan `JubelioPalsu*`, dijalankan langsung
`python tests/test_proses_label.py` - BUKAN pytest).

## Global Constraints

- Semua kode/komentar/nama fungsi Bahasa Indonesia, ikuti konvensi yang sudah ada di
  `src/proses_label.py` (lihat [CLAUDE.md](../../../CLAUDE.md)).
- Tidak ada pytest - test dijalankan sebagai skrip biasa:
  `.venv\Scripts\python tests\test_proses_label.py`. Fungsi test harus diawali `uji_` supaya
  otomatis terdeteksi oleh loop `for nama, f in globals().items()` di akhir file test
  (lihat `tests/test_proses_label.py:905-912`) - tidak ada registry terpisah yang perlu
  diupdate.
- Skrip test berhenti di assertion/exception PERTAMA yang gagal (bukan pytest yang lanjut ke
  semua test) - jalankan skrip lengkap tiap langkah verifikasi, perhatikan fungsi `uji_` mana
  yang disebut di traceback kalau gagal.
- Bagian `"kombinasi"` reguler (multi-baris/qty>1), picklist urgent, Shopee Pagi, J&T Resi
  Siang, dan SKU spesial TIDAK boleh berubah perilakunya - perubahan hanya di bagian `"1qty"`
  dari `rencana_reguler()`/`proses_reguler()`.
- Tidak ada opsi CLI baru - perilaku `--reguler --bagian 1qty` berubah langsung, bukan opt-in
  (lihat keputusan desain di spec).
- Urutan grup: `GRUP_RAK = ["2A", "3A", "1B", "2B", "3B"]`, lalu `"lainnya"` paling akhir -
  urutan ini HARUS konsisten di semua fungsi (dict harus mempertahankan urutan insersi).
- Setelah SEMUA task selesai, jalankan juga `tests/test_main.py` dan `tests/test_sku_spesial.py`
  (regresi) - keduanya tidak disentuh perubahan ini tapi harus tetap lulus.

---

### Task 1: `ambil_kombinasi_rak()` - ambil daftar kombinasi rak tunggal dari Jubelio

**Files:**
- Modify: `src/proses_label.py` (tambah konstanta setelah baris 151, tambah fungsi setelah
  `ambil_pesanan_reguler()` di baris 519 - lihat Task 5 untuk peta lengkap urutan fungsi baru)
- Test: `tests/test_proses_label.py` (tambah test baru sebelum baris 643
  `def uji_reguler_maksimal_200_per_picklist():`)

**Interfaces:**
- Produces: `ambil_kombinasi_rak(k: Klien) -> list[str]` - daftar string kombinasi rak TUNGGAL
  (bukan gabungan multi-rak dipisah `" - "`, bukan string kosong), dipakai Task 3 & Task 5.
- Konsumsi: endpoint `sales/v2/orders/zones-racks-combination` lewat `Klien.get()` yang sudah
  ada (`k.get(path, params) -> dict`, lihat `src/proses_label.py:230-233`).

- [ ] **Step 1: Tulis test yang gagal (fungsi belum ada)**

Tambahkan di `tests/test_proses_label.py`, SEBELUM `def uji_reguler_maksimal_200_per_picklist():`
(baris 643):

```python
class JubelioPalsuKombinasiRak:
    """Server tiruan endpoint zones-racks-combination, 2 halaman (page_size kecil) supaya
    paging ikut teruji."""

    def __init__(self, kombinasi: list[str], page_size: int = 2):
        self.kombinasi = kombinasi
        self.page_size = page_size
        self.log = []

    def get(self, url, params=None, headers=None, timeout=None, cookies=None):
        self.log.append(("GET", url, params))
        assert headers.get("authorization") == "TKN"
        assert url.endswith("zones-racks-combination")
        assert params.get("status") == "PAID"
        assert params.get("combination_type") == "racks"
        page = params["page"]
        awal = (page - 1) * self.page_size
        potongan = self.kombinasi[awal:awal + self.page_size]
        data = [{"combination": c} for c in potongan]
        return Resp(data={"data": data, "totalCount": len(self.kombinasi)})


def uji_ambil_kombinasi_rak_buang_gabungan_dan_kosong():
    kombinasi = ["", "2A-B1-1", "3A-C2-2", "2A-B1-1 - 3B-H1-2", "1B-A2-3"]
    j = JubelioPalsuKombinasiRak(kombinasi, page_size=2)
    k = pl.Klien("TKN", sesi=j, tidur=lambda s: None)
    hasil = pl.ambil_kombinasi_rak(k)
    assert hasil == ["2A-B1-1", "3A-C2-2", "1B-A2-3"], hasil
    assert len(j.log) == 3, "5 baris / page_size 2 -> 3 halaman"
    print("  ambil_kombinasi_rak: string kosong & gabungan (\" - \") dibuang, paging jalan")
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: berhenti di `uji_ambil_kombinasi_rak_buang_gabungan_dan_kosong` dengan
`AttributeError: module 'proses_label' has no attribute 'ambil_kombinasi_rak'`.

- [ ] **Step 3: Implementasi minimal**

Di `src/proses_label.py`, tambahkan konstanta baru tepat setelah baris 151
(`LABEL_REGULER_KOMBINASI = "KOMBINASI-REGULER"   # sisanya (multi-baris/qty>1), tidak spesial`):

```python
# Pecah lagi bagian "1qty reguler" per grup rak gudang (lihat docs/superpowers/specs/
# 2026-10-02-pecah-1qty-per-rak-design.md) - grup 1A sengaja tidak ada (tidak dipakai di
# gudang ini, dikonfirmasi lewat sniff 02-10-2026). Urutan di sini = urutan pembuatan
# picklist (bukan alfabetis) - diminta tim operasional supaya picker jalan runtut.
GRUP_RAK = ["2A", "3A", "1B", "2B", "3B"]
LABEL_RAK_LAINNYA = "LAINNYA"            # pesanan 1qty yang rak-nya di luar GRUP_RAK
MAKS_KOMBINASI_PER_PANGGILAN = 40        # batasi panjang query combination[] per request
```

Lalu tambahkan fungsi baru setelah `ambil_pesanan_reguler()` (baris 519, sebelum
`def pisah_reguler(...)` di baris 522):

```python
def ambil_kombinasi_rak(k: Klien) -> list[str]:
    """Semua kombinasi rak TUNGGAL (bukan gabungan multi-rak dipisah " - ", bukan string
    kosong) dari pesanan berstatus PAID, lewat sales/v2/orders/zones-racks-combination
    (paging sampai habis). Dipakai untuk memetakan salesorder_id -> grup rak lewat
    kelompokkan_kombinasi_per_grup() + ambil_id_per_grup_rak()."""
    hasil, mentah, page = [], 0, 1
    while True:
        params = {"page": page, "q": "", "sort_by": "combination", "sort_direction": "asc",
                  "page_size": 50, "combination_query": "", "location_ids[0]": -1,
                  "combination_type": "racks", "status": "PAID"}
        j = k.get("sales/v2/orders/zones-racks-combination", params)
        data = j.get("data") or []
        mentah += len(data)
        hasil += [row["combination"] for row in data
                 if row.get("combination") and " - " not in row["combination"]]
        if not data or mentah >= int(j.get("totalCount") or 0):
            return hasil
        page += 1
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: lanjut sampai minimal `uji_ambil_kombinasi_rak_buang_gabungan_dan_kosong` tercetak
lulus (skrip boleh lanjut atau berhenti di test berikutnya yang belum ada fungsinya - itu
wajar, lanjut ke Task 2).

- [ ] **Step 5: Commit**

```bash
git add src/proses_label.py tests/test_proses_label.py
git commit -m "Tambah ambil_kombinasi_rak() untuk data kombinasi rak Jubelio"
```

---

### Task 2: `kelompokkan_kombinasi_per_grup()` - kelompokkan kombinasi per grup rak

**Files:**
- Modify: `src/proses_label.py` (tambah fungsi setelah `ambil_kombinasi_rak()` dari Task 1)
- Test: `tests/test_proses_label.py` (tambah setelah test Task 1)

**Interfaces:**
- Consumes: `GRUP_RAK` (Task 1).
- Produces: `kelompokkan_kombinasi_per_grup(kombinasi: list[str]) -> dict[str, list[str]]` -
  key selalu semua `GRUP_RAK` (walau list-nya kosong), urutan sama seperti `GRUP_RAK`. Dipakai
  Task 3.

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan di `tests/test_proses_label.py` setelah `uji_ambil_kombinasi_rak_buang_gabungan_dan_kosong`:

```python
def uji_kelompokkan_kombinasi_per_grup():
    kombinasi = ["2A-B1-1", "2A-B2-2", "3A-C2-2", "1B-A2-3", "2B-D1-1", "3B-E1-1",
                 "4C-F1-1", "1A-X1-1"]
    hasil = pl.kelompokkan_kombinasi_per_grup(kombinasi)
    assert list(hasil.keys()) == pl.GRUP_RAK, hasil
    assert hasil["2A"] == ["2A-B1-1", "2A-B2-2"]
    assert hasil["3A"] == ["3A-C2-2"]
    assert hasil["1B"] == ["1B-A2-3"]
    assert hasil["2B"] == ["2B-D1-1"]
    assert hasil["3B"] == ["3B-E1-1"]
    print("  kelompokkan_kombinasi_per_grup: prefix di luar GRUP_RAK (4C, 1A) diabaikan, "
          "urutan key = GRUP_RAK")
```

- [ ] **Step 2: Jalankan, pastikan gagal**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: berhenti di `uji_kelompokkan_kombinasi_per_grup` dengan `AttributeError`.

- [ ] **Step 3: Implementasi minimal**

Tambahkan setelah `ambil_kombinasi_rak()`:

```python
def kelompokkan_kombinasi_per_grup(kombinasi: list[str]) -> dict[str, list[str]]:
    """Kelompokkan string kombinasi rak tunggal (lihat ambil_kombinasi_rak()) berdasarkan
    prefix sebelum '-' pertama, hanya untuk prefix yang ada di GRUP_RAK. Prefix di luar
    GRUP_RAK diabaikan di sini - pesanan dengan rak itu otomatis masuk LABEL_RAK_LAINNYA
    lewat pisah_satu_qty_per_rak(), bukan di sini."""
    hasil = {grup: [] for grup in GRUP_RAK}
    for c in kombinasi:
        prefix = c.split("-", 1)[0]
        if prefix in hasil:
            hasil[prefix].append(c)
    return hasil
```

- [ ] **Step 4: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```

- [ ] **Step 5: Commit**

```bash
git add src/proses_label.py tests/test_proses_label.py
git commit -m "Tambah kelompokkan_kombinasi_per_grup()"
```

---

### Task 3: `ambil_id_per_grup_rak()` - cari salesorder_id per grup rak (dengan batching)

**Files:**
- Modify: `src/proses_label.py` (tambah fungsi setelah `kelompokkan_kombinasi_per_grup()`)
- Test: `tests/test_proses_label.py` (tambah setelah test Task 2)

**Interfaces:**
- Consumes: `MAKS_KOMBINASI_PER_PANGGILAN` (Task 1), `CHANNEL_ID_SHOPEE`, `TIPE_PESANAN_FILTER`
  (sudah ada), `Klien.get()` (sudah ada).
- Produces: `ambil_id_per_grup_rak(k: Klien, kombinasi_per_grup: dict[str, list[str]], channel_ids: list[int] | None, couriers: list[str] | None) -> dict[str, set[int]]`
  - key sama seperti `kombinasi_per_grup` (jadi urutan `GRUP_RAK`). Dipakai Task 5
  (`_kelompok_1qty_per_rak()`).

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan di `tests/test_proses_label.py` setelah `uji_kelompokkan_kombinasi_per_grup`:

```python
class JubelioPalsuGrupRak:
    """Server tiruan ready-to-process khusus filter combination[] - tiap pesanan dipetakan ke
    1 kombinasi rak lewat `rak`, dicocokkan terhadap nilai combination[] yang dikirim."""

    def __init__(self, rak: dict[int, str]):
        self.rak = rak           # {salesorder_id: kombinasi}
        self.log = []

    def get(self, url, params=None, headers=None, timeout=None, cookies=None):
        self.log.append(("GET", url, dict(params)))
        assert headers.get("authorization") == "TKN"
        assert url.endswith("ready-to-process/")
        combos = {v for kk, v in params.items() if kk.startswith("combination[")}
        assert combos, "harus selalu ada combination[] saat dipanggil ambil_id_per_grup_rak"
        cocok = [so for so, c in self.rak.items() if c in combos]
        return Resp(data={"data": [{"salesorder_id": so} for so in cocok],
                          "totalCount": len(cocok)})


def uji_ambil_id_per_grup_rak_filter_dan_batching():
    # grup "2A" sengaja punya 45 kombinasi (> MAKS_KOMBINASI_PER_PANGGILAN=40) supaya
    # batching ikut teruji - cuma 1 pesanan sungguhan nyangkut di kombinasi ke-45.
    kombinasi_2a = [f"2A-Z{i}-1" for i in range(45)]
    rak = {1: kombinasi_2a[44], 2: "3A-C2-2", 3: "4C-X-1"}
    kombinasi_per_grup = {"2A": kombinasi_2a, "3A": ["3A-C2-2"], "1B": [], "2B": [], "3B": []}
    j = JubelioPalsuGrupRak(rak)
    k = pl.Klien("TKN", sesi=j, tidur=lambda s: None)

    hasil = pl.ambil_id_per_grup_rak(k, kombinasi_per_grup, pl.CHANNEL_IDS_REGULER,
                                     pl.KURIR_FILTER_REGULER)
    assert hasil == {"2A": {1}, "3A": {2}, "1B": set(), "2B": set(), "3B": set()}, hasil
    panggilan_2a = [p for p in j.log if {v for kk, v in p[2].items()
                                        if kk.startswith("combination[")} & set(kombinasi_2a)]
    assert len(panggilan_2a) == 2, "45 kombinasi / 40 per panggilan -> 2 panggilan utk grup 2A"
    assert any(params.get("channel_ids[0]") == pl.CHANNEL_ID_TIKTOK_SHOP
              and params.get("couriers[1]") == "spx" for _, _, params in j.log)
    assert any({kk for kk in params if kk.startswith("order_type[")} for _, _, params in j.log), \
        "kurir SPX ikut -> filter order_type (buang pengiriman kilat) harus ikut ditambahkan"
    print("  ambil_id_per_grup_rak: filter combination[] cocok per grup, dibatch 40/panggilan, "
          "channel/kurir/tipe pesanan ikut diteruskan")
```

- [ ] **Step 2: Jalankan, pastikan gagal**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: berhenti di `uji_ambil_id_per_grup_rak_filter_dan_batching` dengan `AttributeError`.

- [ ] **Step 3: Implementasi minimal**

Tambahkan setelah `kelompokkan_kombinasi_per_grup()`:

```python
def _potong(seq: list, n: int) -> list[list]:
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def ambil_id_per_grup_rak(k: Klien, kombinasi_per_grup: dict[str, list[str]],
                          channel_ids: list[int] | None = None,
                          couriers: list[str] | None = None) -> dict[str, set[int]]:
    """Untuk tiap grup di kombinasi_per_grup (lihat kelompokkan_kombinasi_per_grup()), cari
    salesorder_id yang kombinasi raknya cocok lewat ready-to-process?combination[]=... (bisa
    diulang), dibatasi channel_ids/couriers yang sama seperti ambil_pesanan_reguler(). Daftar
    kombinasi dipecah per MAKS_KOMBINASI_PER_PANGGILAN nilai supaya query string tidak
    kepanjangan. Dipakai _kelompok_1qty_per_rak()."""
    pakai_filter_tipe = ((channel_ids and CHANNEL_ID_SHOPEE in channel_ids)
                         or any(c.lower() == "spx" for c in couriers or []))
    hasil = {}
    for grup, daftar in kombinasi_per_grup.items():
        ids = set()
        for potongan in _potong(daftar, MAKS_KOMBINASI_PER_PANGGILAN):
            page, ambil = 1, 0
            while True:
                params = {"q": "", "page": page, "page_size": 200, "sku_filter": "false",
                          "sort_by": "transaction_date", "sort_direction": "ASC",
                          "combination_type": "racks"}
                params.update({f"combination[{i}]": c for i, c in enumerate(potongan)})
                if channel_ids:
                    params.update({f"channel_ids[{i}]": c for i, c in enumerate(channel_ids)})
                if couriers:
                    params.update({f"couriers[{i}]": c for i, c in enumerate(couriers)})
                if pakai_filter_tipe:
                    params.update({f"order_type[{i}]": t
                                   for i, t in enumerate(TIPE_PESANAN_FILTER)})
                j = k.get("wms/sales/v2/orders/ready-to-process/", params)
                data = j.get("data") or []
                ambil += len(data)
                ids.update(o["salesorder_id"] for o in data)
                if not data or ambil >= int(j.get("totalCount") or 0):
                    break
                page += 1
        hasil[grup] = ids
    return hasil
```

- [ ] **Step 4: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```

- [ ] **Step 5: Commit**

```bash
git add src/proses_label.py tests/test_proses_label.py
git commit -m "Tambah ambil_id_per_grup_rak() dengan batching combination[]"
```

---

### Task 4: `pisah_satu_qty_per_rak()` - partisi pesanan 1qty per grup (murni logika)

**Files:**
- Modify: `src/proses_label.py` (tambah fungsi setelah `ambil_id_per_grup_rak()`)
- Test: `tests/test_proses_label.py` (tambah setelah test Task 3)

**Interfaces:**
- Consumes: `GRUP_RAK`, `LABEL_RAK_LAINNYA` (Task 1).
- Produces: `pisah_satu_qty_per_rak(satu_qty: list[dict], id_per_grup: dict[str, set[int]]) -> dict[str, list[dict]]`
  - key = `GRUP_RAK + [LABEL_RAK_LAINNYA]`, urutan itu. Dipakai Task 5.

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan di `tests/test_proses_label.py` setelah `uji_ambil_id_per_grup_rak_filter_dan_batching`:

```python
def uji_pisah_satu_qty_per_rak():
    satu_qty = [{"salesorder_id": 1, "salesorder_no": "SO-1"},
               {"salesorder_id": 2, "salesorder_no": "SO-2"},
               {"salesorder_id": 3, "salesorder_no": "SO-3"},
               {"salesorder_id": 4, "salesorder_no": "SO-4"}]
    id_per_grup = {"2A": {1}, "3A": {2}, "1B": set(), "2B": set(), "3B": set()}
    hasil = pl.pisah_satu_qty_per_rak(satu_qty, id_per_grup)
    assert list(hasil.keys()) == pl.GRUP_RAK + [pl.LABEL_RAK_LAINNYA], hasil
    assert [o["salesorder_no"] for o in hasil["2A"]] == ["SO-1"]
    assert [o["salesorder_no"] for o in hasil["3A"]] == ["SO-2"]
    assert hasil["1B"] == hasil["2B"] == hasil["3B"] == []
    assert [o["salesorder_no"] for o in hasil[pl.LABEL_RAK_LAINNYA]] == ["SO-3", "SO-4"], \
        "SO-3/SO-4 tidak ada di grup manapun -> masuk LAINNYA"
    print("  pisah_satu_qty_per_rak: partisi per grup benar, sisa masuk LAINNYA, urutan "
          "key = GRUP_RAK + LAINNYA")
```

- [ ] **Step 2: Jalankan, pastikan gagal**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: berhenti di `uji_pisah_satu_qty_per_rak` dengan `AttributeError`.

- [ ] **Step 3: Implementasi minimal**

Tambahkan setelah `ambil_id_per_grup_rak()`:

```python
def pisah_satu_qty_per_rak(satu_qty: list[dict],
                           id_per_grup: dict[str, set[int]]) -> dict[str, list[dict]]:
    """Partisi satu_qty (hasil pisah_reguler()[0]) ke grup rak (GRUP_RAK, urutan itu) +
    LABEL_RAK_LAINNYA (pesanan yang salesorder_id-nya tidak cocok grup manapun di
    id_per_grup - lihat ambil_id_per_grup_rak()). Murni logika data, tidak memanggil API."""
    hasil = {grup: [] for grup in GRUP_RAK}
    hasil[LABEL_RAK_LAINNYA] = []
    for o in satu_qty:
        grup_cocok = next((grup for grup in GRUP_RAK
                           if o["salesorder_id"] in id_per_grup.get(grup, ())), None)
        hasil[grup_cocok or LABEL_RAK_LAINNYA].append(o)
    return hasil
```

- [ ] **Step 4: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```

- [ ] **Step 5: Commit**

```bash
git add src/proses_label.py tests/test_proses_label.py
git commit -m "Tambah pisah_satu_qty_per_rak()"
```

---

### Task 5: Wiring ke `rencana_reguler()`/`proses_reguler()` + fallback error

**Files:**
- Modify: `src/proses_label.py:554-590` (fungsi `rencana_reguler()` dan `proses_reguler()`)
- Test: `tests/test_proses_label.py:586-709` (`JubelioPalsuReguler`,
  `uji_reguler_keluarkan_spesial_dan_pisah_1qty_kombinasi` - DIUBAH, bukan ditambah baru) +
  2 test baru (fallback error, mode uji)

**Interfaces:**
- Consumes: `ambil_kombinasi_rak()` (Task 1), `kelompokkan_kombinasi_per_grup()` (Task 2),
  `ambil_id_per_grup_rak()` (Task 3), `pisah_satu_qty_per_rak()` (Task 4), `CHANNEL_IDS_REGULER`,
  `KURIR_FILTER_REGULER`, `_proses_channel_batch()`, `_nama_kurir()`, `_label_kurir()`,
  `_label_kurir_file()` (semua sudah ada).
- Produces: `_kelompok_1qty_per_rak(k: Klien, satu_qty: list[dict]) -> dict[str, list[dict]]`
  (fungsi baru, internal). `rencana_reguler()`/`proses_reguler()` perilakunya berubah untuk
  `bagian == "1qty"`, signature TIDAK berubah.

Catatan penting: `_kelompok_1qty_per_rak()` SELALU query dengan `CHANNEL_IDS_REGULER` +
`KURIR_FILTER_REGULER` penuh (J&T+SPX), TIDAK dibatasi parameter `kurir` dari
`proses_reguler()`/`rencana_reguler()` - karena hasilnya cuma dipakai untuk CEK KEANGGOTAAN
(`salesorder_id` ada di grup mana), bukan untuk filter ulang siapa yang diproses (`satu_qty`
yang diteruskan ke fungsi ini SUDAH difilter kurir lewat `ambil_pesanan_reguler(k, kurir)` di
pemanggil). Ini menyederhanakan kode: 1 fungsi, tidak perlu parameter `kurir` tambahan.

- [ ] **Step 1: Ubah test existing supaya mencerminkan perilaku baru (akan gagal dulu)**

Di `tests/test_proses_label.py`, pada class `JubelioPalsuReguler` (mulai baris 586), tambahkan
data rak dan handler `zones-racks-combination` + `combination[]`. Ganti seluruh class jadi:

```python
class JubelioPalsuReguler:
    """Server tiruan khusus skenario picklist sisa reguler (TikTok Shop & Shopee)."""

    def __init__(self):
        self.log = []
        # TikTok Shop (source 131076): SO-1..SO-5 total_qty 1 (calon 1 qty reguler),
        # SO-6 total_qty 2 (calon kombinasi). SO-1 & SO-2 "sudah" SKU spesial -> dikeluarkan.
        # + Shopee (source 64): SO-7 total_qty 3 (kombinasi), SO-8 total_qty 1 (1 qty reguler).
        # + kebocoran channel lain (source 4, Lazada) utk pastikan disaring ulang.
        # + SO-10 nilai 0 (sampel/kreator, mis. TT-586350230929114342-67824) -> harus
        # dikeluarkan ambil_pesanan_channel() sebelum sempat masuk pisah_reguler().
        self.pesanan = [
            {"salesorder_id": 1, "salesorder_no": "SO-1", "source": 131076, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 2, "salesorder_no": "SO-2", "source": 131076, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 3, "salesorder_no": "SO-3", "source": 131076, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 4, "salesorder_no": "SO-4", "source": 131076, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 5, "salesorder_no": "SO-5", "source": 131076, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 6, "salesorder_no": "SO-6", "source": 131076, "total_qty": "2.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 7, "salesorder_no": "SO-7", "source": 64, "total_qty": "3.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 8, "salesorder_no": "SO-8", "source": 64, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 9, "salesorder_no": "SO-9", "source": 4, "total_qty": "1.0000", "grand_total": "35900.0000"},
            {"salesorder_id": 10, "salesorder_no": "SO-10", "source": 131076, "total_qty": "1.0000", "grand_total": "0.0000"},
        ]
        # Rak per pesanan 1qty (SO-3/4/5/8 - lihat docstring di atas): SO-3 grup 2A, SO-4 grup
        # 3A, SO-8 grup 2B, SO-5 rak di luar 5 grup target -> harus jatuh ke LAINNYA. Grup 1B
        # & 3B sengaja TIDAK punya pesanan sama sekali -> harus dilewati tanpa bikin picklist.
        self.rak = {3: "2A-B1-1", 4: "3A-C2-2", 5: "4C-D3-3", 8: "2B-E4-4"}
        self.kombinasi_rak = list(self.rak.values()) + ["1B-F5-5", "3B-G6-6"]
        self.picklist_no = 0

    def get(self, url, params=None, headers=None, timeout=None, cookies=None):
        self.log.append(("GET", url, params))
        assert headers.get("authorization") == "TKN"
        if url.endswith("zones-racks-combination"):
            assert params.get("status") == "PAID" and params.get("combination_type") == "racks"
            data = [{"combination": c} for c in self.kombinasi_rak]
            return Resp(data={"data": data, "totalCount": len(data)})
        if url.endswith("ready-to-process/"):
            combos = {v for kk, v in params.items() if kk.startswith("combination[")}
            if combos:
                data = [{"salesorder_id": so} for so, c in self.rak.items() if c in combos]
                return Resp(data={"data": data, "totalCount": len(data)})
            assert params.get("sort_by") == "transaction_date" and params.get("sort_direction") == "ASC", \
                "resi terlama harus diambil duluan, supaya masuk picklist pertama kalau dipecah"
            assert params.get("channel_ids[0]") == pl.CHANNEL_ID_TIKTOK_SHOP
            assert params.get("channel_ids[1]") == pl.CHANNEL_ID_SHOPEE
            assert params.get("couriers[0]") == "j&t" and params.get("couriers[1]") == "spx"
            assert [params[f"order_type[{i}]"] for i in range(len(pl.TIPE_PESANAN_FILTER))] \
                == pl.TIPE_PESANAN_FILTER, \
                "channel Shopee & kurir SPX -> pesanan kilat harus difilter"
            return Resp(data={"data": self.pesanan, "totalCount": len(self.pesanan)})
        raise AssertionError(f"GET tak dikenal {url}")

    def post(self, url, json=None, headers=None, timeout=None, cookies=None):
        self.log.append(("POST", url, json))
        assert headers.get("authorization") == "TKN"
        if url.endswith("items-to-pick/"):
            return Resp(data=[{"salesorder_detail_id": 9000 + i, "item_id": 1, "location_id": -1,
                               "qty_ordered": "1.0000", "salesorder_id": i, "bundle_item_id": 0,
                               "package_detail_id": None, "package_id": None, "end_qty": "999.0000",
                               "item_full_name": "X", "salesorder_no": f"SO{i}"} for i in json["ids"]])
        if url.endswith("wms/sales/picklists/"):
            self.picklist_no += 1
            no = f"PICK-{910000 + self.picklist_no}"
            return Resp(data={"status": "ok", "data": {
                "picks": [{"picklist_id": self.picklist_no, "picklist_no": no, "status": "ok"}],
                "invalidSO": []}})
        raise AssertionError(f"POST tak dikenal {url}")
```

Lalu ganti isi `uji_reguler_keluarkan_spesial_dan_pisah_1qty_kombinasi()` (baris 661-709),
BAGIAN SETELAH `print("  pisah_reguler: ...")` (baris 674) sampai akhir fungsi, jadi:

```python
    panggilan = []
    asli = pl.lanjutkan_picklist

    def stub(k, pid, pno, jumlah, sku, folder_label, nama_file=None):
        panggilan.append((pid, pno, jumlah, sku, folder_label))
        return {"Waktu": "-", "SKU": sku, "No Picklist": pno, "Total Pesanan": jumlah,
                "Resi Keluar": jumlah, "File Label": f"{pno}_{sku}_x.pdf", "Catatan": ""}
    pl.lanjutkan_picklist = stub
    try:
        with tempfile.TemporaryDirectory() as d:
            riwayat = Path(d) / "riwayat.xlsx"
            hasil = pl.proses_reguler(k, resi_spesial_semua, riwayat, Path(d) / "label")
            from openpyxl import load_workbook
            baris = list(load_workbook(riwayat).active.values)
    finally:
        pl.lanjutkan_picklist = asli

    per_label = {h["SKU"]: h for h in hasil}
    assert per_label["1QTY-REGULER-2A"]["Total Pesanan"] == 1, per_label
    assert per_label["1QTY-REGULER-3A"]["Total Pesanan"] == 1, per_label
    assert per_label["1QTY-REGULER-2B"]["Total Pesanan"] == 1, per_label
    assert per_label["1QTY-REGULER-LAINNYA"]["Total Pesanan"] == 1, per_label
    assert "1QTY-REGULER-1B" not in per_label and "1QTY-REGULER-3B" not in per_label, \
        "grup tanpa pesanan (1B, 3B) tidak boleh bikin picklist"
    assert per_label["KOMBINASI-REGULER"]["Total Pesanan"] == 2
    assert list(per_label.keys()) == ["1QTY-REGULER-2A", "1QTY-REGULER-3A",
                                      "1QTY-REGULER-2B", "1QTY-REGULER-LAINNYA",
                                      "KOMBINASI-REGULER"], \
        "urutan harus ikut GRUP_RAK (2A,3A,1B,2B,3B) lalu LAINNYA - 1B/3B dilewati krn kosong"
    assert len(baris) == 1 + 5, "5 picklist reguler tercatat di riwayat (4 grup rak + kombinasi)"
    print("  proses_reguler: 1qty dipecah per grup rak (2A/3A/2B/LAINNYA, 1B & 3B dilewati "
          "krn kosong), KOMBINASI-REGULER tetap 1 picklist gabungan")

    # bagian="1qty": cuma proses bagian itu
    pl.lanjutkan_picklist = stub
    try:
        with tempfile.TemporaryDirectory() as d:
            hasil = pl.proses_reguler(k, resi_spesial_semua, Path(d) / "r.xlsx",
                                      Path(d) / "label", bagian="1qty")
    finally:
        pl.lanjutkan_picklist = asli
    assert {h["SKU"] for h in hasil} == {"1QTY-REGULER-2A", "1QTY-REGULER-3A",
                                         "1QTY-REGULER-2B", "1QTY-REGULER-LAINNYA"}, hasil
    print("  bagian bisa dibatasi 1qty (dipecah per grup rak) atau kombinasi saja")
```

- [ ] **Step 2: Jalankan, pastikan gagal**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: berhenti di `uji_reguler_keluarkan_spesial_dan_pisah_1qty_kombinasi` dengan
`KeyError: '1QTY-REGULER-2A'` (karena `proses_reguler()` belum diubah, masih menghasilkan SKU
`"1QTY-REGULER"` tunggal).

- [ ] **Step 3: Implementasi wiring**

Di `src/proses_label.py`, tambahkan fungsi baru setelah `pisah_satu_qty_per_rak()` (Task 4),
SEBELUM `_BAGIAN_REGULER = {...}` (baris 532):

```python
def _kelompok_1qty_per_rak(k: Klien, satu_qty: list[dict]) -> dict[str, list[dict]]:
    """Bungkus ambil_kombinasi_rak()+kelompokkan_kombinasi_per_grup()+ambil_id_per_grup_rak()+
    pisah_satu_qty_per_rak(): hasilnya peta grup -> daftar pesanan 1qty (urutan GRUP_RAK +
    LABEL_RAK_LAINNYA). Selalu query rak dengan CHANNEL_IDS_REGULER + KURIR_FILTER_REGULER
    penuh (bukan parameter `kurir` dari proses_reguler()) karena cuma dipakai cek keanggotaan
    salesorder_id - `satu_qty` yang masuk ke sini sudah difilter kurir sebelumnya. Kalau
    pengambilan data rak gagal (API down dsb), SEMUA pesanan 1qty jatuh ke LABEL_RAK_LAINNYA
    supaya tidak ada yang hilang, tidak menghentikan proses reguler lainnya."""
    try:
        kombinasi = ambil_kombinasi_rak(k)
        id_per_grup = ambil_id_per_grup_rak(k, kelompokkan_kombinasi_per_grup(kombinasi),
                                            CHANNEL_IDS_REGULER, KURIR_FILTER_REGULER)
    except Exception as e:      # noqa: BLE001 - jangan gagalkan seluruh 1qty gara2 gagal rak
        log.warning("  Gagal ambil data rak (%s) - semua 1qty masuk kelompok \"%s\"",
                   e, LABEL_RAK_LAINNYA)
        id_per_grup = {}
    return pisah_satu_qty_per_rak(satu_qty, id_per_grup)
```

Lalu ganti `rencana_reguler()` (baris 554-565) jadi:

```python
def rencana_reguler(k: Klien, resi_spesial_semua: set[str], bagian: str | None = None,
                    kurir: str | None = None) -> None:
    """Mode uji picklist sisa reguler: hanya membaca data, tidak mengubah apa pun di Jubelio.
    `kurir`: lihat cari_pesanan(). Bagian "1qty" dipecah lagi per grup rak - lihat
    _kelompok_1qty_per_rak()/GRUP_RAK."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir), resi_spesial_semua)
    for kunci, (nama, _, idx) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        if kunci == "1qty":
            for grup, pesanan in _kelompok_1qty_per_rak(k, kelompok[idx]).items():
                batch = bagi_batch([o["salesorder_id"] for o in pesanan])
                log.info("[UJI] Reguler %-20s pesanan siap proses %3d -> %d picklist "
                         "(maks %d/picklist)", _nama_kurir(f"{nama} {grup}", kurir),
                         len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)
            continue
        pesanan = kelompok[idx]
        batch = bagi_batch([o["salesorder_id"] for o in pesanan])
        log.info("[UJI] Reguler %-20s pesanan siap proses %3d -> %d picklist (maks %d/picklist)",
                 _nama_kurir(nama, kurir), len(pesanan), len(batch), MAKS_PESANAN_PICKLIST)
```

Lalu ganti `proses_reguler()` (baris 568-590) jadi:

```python
def proses_reguler(k: Klien, resi_spesial_semua: set[str], file_riwayat: Path,
                   folder_label: Path, bagian: str | None = None,
                   kurir: str | None = None) -> list[dict]:
    """Picklist "sisa reguler" (bukan SKU spesial) channel TikTok Shop & Shopee, kurir J&T/SPX
    (atau 1 kurir saja - lihat cari_pesanan(), dipakai TIPE 2 & TIPE 3): (1) 1 SKU
    1 qty yang tidak spesial - dipecah lagi per grup rak (lihat _kelompok_1qty_per_rak(),
    GRUP_RAK; kegagalan 1 grup tidak menghentikan grup lain), (2) kombinasi/multi-baris/qty>1
    (tidak dipecah per rak). Dipanggil SETELAH proses SKU spesial selesai (perlu
    resi_spesial_semua supaya tidak dobel proses). Sebanyak mungkin per picklist (maks
    MAKS_PESANAN_PICKLIST, dipecah kalau lebih)."""
    kelompok = pisah_reguler(ambil_pesanan_reguler(k, kurir), resi_spesial_semua)
    hasil = []
    for kunci, (nama, label, idx) in _BAGIAN_REGULER.items():
        if bagian and bagian != kunci:
            continue
        if kunci == "1qty":
            for grup, pesanan in _kelompok_1qty_per_rak(k, kelompok[idx]).items():
                nama_grup, label_grup = f"{nama} {grup}", f"{label}-{grup}"
                try:
                    hasil += _proses_channel_batch(
                        k, f"Reguler {_nama_kurir(nama_grup, kurir)}",
                        _label_kurir(label_grup, kurir), pesanan, file_riwayat, folder_label,
                        label_file=_label_kurir_file(label_grup, kurir))
                except Exception as e:      # noqa: BLE001 - grup lain tetap lanjut
                    log.exception("  GAGAL reguler %s: %s", nama_grup, e)
                    hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"),
                                  "SKU": _label_kurir(label_grup, kurir),
                                  "Catatan": f"GAGAL: {e}"})
            continue
        try:
            hasil += _proses_channel_batch(k, f"Reguler {_nama_kurir(nama, kurir)}",
                                           _label_kurir(label, kurir), kelompok[idx],
                                           file_riwayat, folder_label,
                                           label_file=_label_kurir_file(label, kurir))
        except Exception as e:      # noqa: BLE001 - bagian lain tetap lanjut
            log.exception("  GAGAL reguler %s: %s", nama, e)
            hasil.append({"Waktu": datetime.now().strftime("%d-%m-%Y %H:%M"),
                          "SKU": _label_kurir(label, kurir), "Catatan": f"GAGAL: {e}"})
    return hasil
```

- [ ] **Step 4: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: `uji_reguler_keluarkan_spesial_dan_pisah_1qty_kombinasi` lulus, skrip lanjut ke test
berikutnya (`uji_shopee_pagi_filter_channel_dan_jam_cutoff`, tidak terpengaruh perubahan ini).

- [ ] **Step 5: Tambah test fallback error (kombinasi rak gagal diambil)**

Tambahkan di `tests/test_proses_label.py` setelah
`uji_reguler_keluarkan_spesial_dan_pisah_1qty_kombinasi`:

```python
class JubelioPalsuGagalRak:
    def get(self, url, params=None, headers=None, timeout=None, cookies=None):
        if url.endswith("zones-racks-combination"):
            raise pl.requests.exceptions.ConnectionError("simulasi Jubelio down")
        raise AssertionError(f"GET tak dikenal {url}")


def uji_kelompok_1qty_per_rak_fallback_saat_gagal_ambil_kombinasi():
    k = pl.Klien("TKN", sesi=JubelioPalsuGagalRak(), tidur=lambda s: None)
    satu_qty = [{"salesorder_id": 1, "salesorder_no": "SO-1"},
               {"salesorder_id": 2, "salesorder_no": "SO-2"}]
    hasil = pl._kelompok_1qty_per_rak(k, satu_qty)
    assert list(hasil.keys()) == pl.GRUP_RAK + [pl.LABEL_RAK_LAINNYA], hasil
    assert all(hasil[g] == [] for g in pl.GRUP_RAK), hasil
    assert [o["salesorder_no"] for o in hasil[pl.LABEL_RAK_LAINNYA]] == ["SO-1", "SO-2"], hasil
    print("  _kelompok_1qty_per_rak: gagal ambil kombinasi rak -> semua pesanan jatuh ke "
          "LAINNYA, tidak melempar exception")
```

Catatan: `Klien._kirim()` (dipakai `Klien.get()`) hanya menangkap
`requests.exceptions.ConnectionError`/`Timeout` untuk RETRY (lihat `src/proses_label.py:217-228`,
`MAKS_COBA_KONEKSI`), lalu tetap melempar ulang setelah percobaan terakhir habis - jadi
exception ini akan diteruskan sampai ke `_kelompok_1qty_per_rak()` dan tertangkap `except
Exception` di sana. `tidur=lambda s: None` supaya retry (jeda `JEDA_COBA_KONEKSI_S` detik, 3x
percobaan) tidak benar-benar menunggu saat test.

- [ ] **Step 6: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```

- [ ] **Step 7: Tambah test mode uji (rencana_reguler) tidak mengubah apa pun**

Tambahkan di `tests/test_proses_label.py` setelah test Step 5 di atas:

```python
def uji_rencana_reguler_mode_uji_tidak_mengubah_apapun():
    j = JubelioPalsuReguler()
    k = pl.Klien("TKN", sesi=j, tidur=lambda s: None)
    pl.rencana_reguler(k, resi_spesial_semua={"SO-1", "SO-2"})
    assert all(m == "GET" for m, _, _ in j.log), j.log
    print("  rencana_reguler (mode uji, termasuk pembagian per grup rak): hanya GET")
```

- [ ] **Step 8: Jalankan, pastikan lulus**

```bash
.venv\Scripts\python tests\test_proses_label.py
```
Expected: semua `uji_*` tercetak lulus, diakhiri `SEMUA UJI LULUS`.

- [ ] **Step 9: Commit**

```bash
git add src/proses_label.py tests/test_proses_label.py
git commit -m "Pecah picklist 1qty reguler per grup rak (2A/3A/1B/2B/3B/lainnya)"
```

---

### Task 6: Update dokumentasi `README.md`

**Files:**
- Modify: `README.md:272-316` (bagian "3. Picklist sisa reguler (`--reguler`)")

**Interfaces:** Tidak ada (dokumentasi saja).

- [ ] **Step 1: Update bagian "3. Picklist sisa reguler"**

Di `README.md`, cari paragraf berikut (sekitar baris 279-280):

```
- **1 Qty Reguler**: 1 SKU, qty 1 (resi tunggal yang SKU-nya tidak mencapai syarat spesial).
- **Kombinasi Reguler**: sisanya — pesanan qty > 1 (multi-baris/multi-SKU atau 1 SKU qty > 1).
```

Ganti jadi:

```
- **1 Qty Reguler**: 1 SKU, qty 1 (resi tunggal yang SKU-nya tidak mencapai syarat spesial) -
  dipecah LAGI jadi beberapa picklist berdasarkan grup rak gudang (`GRUP_RAK` di
  `src/proses_label.py`: `2A`, `3A`, `1B`, `2B`, `3B`, berurutan - grup `1A` tidak ada di
  gudang ini), supaya picker tidak bolak-balik antar zona. Pesanan yang rak-nya di luar 5
  grup itu digabung jadi 1 picklist `LAINNYA`. Grup yang tidak ada pesanannya dilewati (tidak
  bikin picklist kosong). Lihat
  [docs/superpowers/specs/2026-10-02-pecah-1qty-per-rak-design.md](docs/superpowers/specs/2026-10-02-pecah-1qty-per-rak-design.md)
  untuk detail mekanismenya (endpoint `zones-racks-combination` + filter `combination[]`).
- **Kombinasi Reguler**: sisanya — pesanan qty > 1 (multi-baris/multi-SKU atau 1 SKU qty > 1),
  TIDAK dipecah per rak (tetap 1 picklist gabungan seperti sebelumnya).
```

Lalu cari paragraf berikut (sekitar baris 311-316):

```
`proses-harian.bat` TIPE 1/TIPE 4, langkah "SPX - J&T 1 QTY REGULER"/"SPX - J&T KOMBINASI" =
`jalankan.bat --reguler --bagian 1qty --jalankan` / `jalankan.bat --reguler --bagian kombinasi --jalankan`
(digabung). TIPE 2/TIPE 3, langkah "J&T 1 QTY REGULER"/"J&T KOMBINASI"/"SPX 1 QTY
REGULER"/"SPX KOMBINASI" = perintah yang sama ditambah `--kurir jnt`/`--kurir spx`.
`proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama. Kolom SKU di riwayat:
`1QTY-REGULER` / `KOMBINASI-REGULER` (digabung), atau `J&T-1QTY-REGULER` / `SPX-1QTY-REGULER`
/ `J&T-KOMBINASI-REGULER` / `SPX-KOMBINASI-REGULER` (dipisah lewat `--kurir`). Nama file PDF
tidak boleh memuat simbol `&` (dibuang otomatis), jadi khusus nama file J&T dituliskan `JNT`
tanpa simbol, mis. `label-pengiriman/PICK-000155300_1QTY-REGULER_...pdf` atau
`label-pengiriman/PICK-000155301_JNT-1QTY-REGULER_...pdf`.
```

Ganti jadi:

```
`proses-harian.bat` TIPE 1/TIPE 4, langkah "SPX - J&T 1 QTY REGULER"/"SPX - J&T KOMBINASI" =
`jalankan.bat --reguler --bagian 1qty --jalankan` / `jalankan.bat --reguler --bagian kombinasi --jalankan`
(digabung). TIPE 2/TIPE 3, langkah "J&T 1 QTY REGULER"/"J&T KOMBINASI"/"SPX 1 QTY
REGULER"/"SPX KOMBINASI" = perintah yang sama ditambah `--kurir jnt`/`--kurir spx`.
`proses-harian-uji.bat` = versi mode uji (tanpa `--jalankan`) yang sama. Kolom SKU di riwayat
untuk bagian 1 Qty Reguler kini per grup rak: `1QTY-REGULER-2A` / `1QTY-REGULER-3A` /
`1QTY-REGULER-1B` / `1QTY-REGULER-2B` / `1QTY-REGULER-3B` / `1QTY-REGULER-LAINNYA` (digabung),
atau diawali `J&T-`/`SPX-` kalau dipisah lewat `--kurir` (mis. `J&T-1QTY-REGULER-2A`). Bagian
Kombinasi Reguler tidak berubah: `KOMBINASI-REGULER` (digabung) atau `J&T-KOMBINASI-REGULER` /
`SPX-KOMBINASI-REGULER` (dipisah). Nama file PDF tidak boleh memuat simbol `&` (dibuang
otomatis), jadi khusus nama file J&T dituliskan `JNT` tanpa simbol, mis.
`label-pengiriman/PICK-000155300_1QTY-REGULER-2A_...pdf` atau
`label-pengiriman/PICK-000155301_JNT-1QTY-REGULER-2A_...pdf`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Update README: 1 Qty Reguler dipecah per grup rak"
```

---

### Task 7: Verifikasi akhir (regresi penuh)

**Files:** Tidak ada perubahan - verifikasi saja.

- [ ] **Step 1: Jalankan semua test yang kemungkinan terdampak**

```bash
.venv\Scripts\python tests\test_proses_label.py
.venv\Scripts\python tests\test_main.py
.venv\Scripts\python tests\test_sku_spesial.py
```
Expected: ketiganya mencetak `SEMUA UJI LULUS` (atau sejenisnya) tanpa error.

- [ ] **Step 2: Cek log realistis lewat mode uji sungguhan (tanpa ubah apa pun)**

```bash
jalankan.bat --reguler --bagian 1qty
```
Expected: baris log `[UJI] Reguler 1 Qty Reguler 2A ...`, `... 3A ...`, `... 1B ...`,
`... 2B ...`, `... 3B ...`, `... LAINNYA ...` (6 baris, urutan itu) - bandingkan total pesanan
gabungan semua grup dengan jumlah yang biasanya muncul di baris `1 Qty Reguler` sebelum
perubahan ini, pastikan tidak ada pesanan yang hilang (total harus sama).

- [ ] **Step 3: Commit (kalau ada sisa perubahan, mis. dari Step 1-2 tidak ada file berubah -
  langkah ini boleh dilewati)**

Tidak ada commit di task ini kecuali Step 1/2 menemukan perbaikan yang perlu dilakukan di
task sebelumnya.
