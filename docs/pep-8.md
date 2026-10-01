# PEP 8 — Panduan Gaya Kode Python (Ringkas)

## Layout Kode

- **Indentasi**: 4 spasi per level. Jangan campur tab & spasi (Python melarangnya).
- **Continuation line**: selaraskan dengan delimiter pembuka, atau gunakan hanging indent (tambah 4 spasi, tanpa argumen di baris pertama).
- **Panjang baris**: maksimal 79 karakter untuk kode, 72 karakter untuk docstring/komentar. Boleh sampai 99 karakter jika tim sepakat.
- **Wrap baris panjang**: gunakan tanda kurung implisit `()`, `[]`, `{}` — bukan backslash `\` (kecuali untuk `with` multi-context pra-3.10 atau `assert`).
- **Line break pada operator biner**: pecah *sebelum* operator (gaya matematika), bukan sesudah.
- **Blank lines**:
  - 2 baris kosong sebelum/sesudah fungsi & class top-level.
  - 1 baris kosong antar method di dalam class.
  - Gunakan secukupnya untuk memisahkan blok logis dalam fungsi.
- **Encoding**: gunakan UTF-8, tanpa deklarasi encoding. Identifier harus ASCII, gunakan bahasa Inggris.
- **Import**:
  - Satu import per baris (`import os` lalu `import sys`, bukan `import os, sys`). `from x import a, b` boleh.
  - Letakkan di atas file, setelah docstring, sebelum konstanta modul.
  - Urutan grup: (1) standard library, (2) third-party, (3) lokal — pisahkan dengan baris kosong.
  - Gunakan absolute import; relative import eksplisit boleh untuk package kompleks.
  - Hindari `from module import *` (kecuali untuk republish API publik).
- **Dunder modul** (`__all__`, `__version__`, dll): letakkan setelah docstring modul, sebelum import (kecuali `from __future__ import`).

## String

- Quote tunggal `'` atau ganda `"` sama saja — pilih satu gaya, konsisten. Gunakan quote lain untuk hindari backslash di dalam string.
- Triple-quoted string selalu pakai `"""`.

## Whitespace

- **Hindari** spasi berlebih:
  - Langsung di dalam `()`, `[]`, `{}`.
  - Sebelum koma, titik dua, titik koma.
  - Sebelum `(` pemanggilan fungsi atau indexing/slicing.
  - Untuk meratakan (align) operator `=` di beberapa baris.
- Slice: `:` diperlakukan sebagai operator, spasi simetris di kedua sisi (`ham[1:9]`, `ham[lower+offset : upper+offset]`), kecuali parameter dihilangkan.
- Tidak ada trailing whitespace.
- Selalu beri satu spasi di sekitar: `=`, augmented assignment (`+=` dll), perbandingan (`==`, `<`, `in`, `is`, dll), boolean (`and`, `or`, `not`).
- Operator dengan prioritas berbeda: boleh tambah spasi di sekitar operator prioritas terendah untuk kejelasan.
- Anotasi fungsi: spasi normal di sekitar `:` dan `->`.
- **Jangan** pakai spasi di sekitar `=` untuk keyword argument atau default value parameter tanpa anotasi (`def f(x=0)`), TAPI pakai spasi jika parameter punya anotasi tipe (`def f(x: int = 0)`).
- Hindari compound statement (`if x: y()`) dan multiple statement dengan `;` di satu baris.

## Trailing Comma

- Wajib untuk tuple satu elemen: `FILES = ('setup.cfg',)`.
- Berguna saat list/argumen ditulis satu per baris (memudahkan version control), tapi jangan taruh trailing comma di baris yang sama dengan closing delimiter.

## Komentar

- Komentar yang kontradiktif dengan kode lebih buruk dari tidak ada komentar — selalu update.
- Kalimat lengkap, huruf kapital di awal (kecuali identifier lowercase).
- Block comment: sejajar dengan kode, mulai dengan `# ` (satu spasi).
- Inline comment: pisahkan minimal 2 spasi dari statement, mulai dengan `# `. Gunakan sparingly, jangan menyatakan hal yang sudah jelas dari kode.
- Docstring: wajib untuk modul, fungsi, class, method publik. `"""` penutup docstring multiline di baris sendiri; untuk one-liner, `"""` penutup di baris yang sama.

## Konvensi Penamaan

- **Hindari** huruf `l`, `O`, `I` sebagai nama variabel satu karakter (mirip angka 1/0).
- **Module & package**: huruf kecil semua, boleh underscore untuk module (`lower_case`), package sebaiknya tanpa underscore.
- **Class**: `CapWords` (PascalCase). Akronim dalam CapWords: semua huruf kapital (`HTTPServerError`, bukan `HttpServerError`).
- **Type variable** (generic): `CapWords` pendek (`T`, `AnyStr`); suffix `_co`/`_contra` untuk covariant/contravariant.
- **Exception**: ikuti konvensi class, tambah suffix `Error` jika memang error.
- **Fungsi & variabel**: `lower_case_with_underscores`.
- **Argumen fungsi**: `self` untuk instance method, `cls` untuk class method. Jika bentrok keyword, tambah trailing underscore (`class_`), jangan disingkat.
- **Method & instance variable**: `lower_case_with_underscores`.
  - 1 leading underscore (`_name`) = non-public/internal (weak indicator).
  - 2 leading underscore (`__name`) = memicu name mangling, untuk hindari bentrok nama di subclass.
- **Konstanta**: `UPPER_CASE_WITH_UNDERSCORES`, biasanya di level modul.
- **Interface publik**: deklarasikan eksplisit lewat `__all__`. Interface internal tetap diberi prefix underscore meski `__all__` sudah diatur.

## Desain untuk Inheritance

- Default-kan atribut ke non-public jika ragu (lebih mudah dibuat public nanti daripada sebaliknya).
- Atribut data publik: ekspos langsung tanpa getter/setter berlebihan; gunakan `property` jika nanti butuh logika tambahan.
- Gunakan double leading underscore untuk atribut yang tidak boleh diakses/ditimpa subclass (name mangling).

## Rekomendasi Pemrograman

- Untuk konkatenasi string performa-sensitif, gunakan `''.join()`, bukan `+=` berulang.
- Bandingkan dengan `None`, `True`, `False` pakai `is`/`is not`, bukan `==`. Jangan tulis `if x == True`, cukup `if x`.
- Gunakan `is not` daripada `not ... is`.
- Implementasikan keenam rich comparison (`__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`) atau pakai `functools.total_ordering`.
- Gunakan `def` untuk fungsi bernama, jangan `f = lambda x: ...`.
- Exception custom: turunkan dari `Exception`, bukan `BaseException`. Tambah suffix `Error` jika memang error.
- Gunakan `raise X from Y` untuk exception chaining yang eksplisit.
- Tangkap exception spesifik, hindari bare `except:` (kecuali untuk logging lalu re-raise, atau cleanup + `raise`).
- Batasi isi blok `try` seminimal mungkin agar tidak menutupi bug lain.
- Gunakan `with` (context manager) untuk resource lokal, bukan manual open/close.
- Context manager sebaiknya dipanggil lewat fungsi terpisah jika melakukan lebih dari sekadar acquire/release resource.
- Konsisten dalam `return`: semua return dalam fungsi harus mengembalikan ekspresi, atau tidak sama sekali (gunakan `return None` eksplisit jika perlu).
- Gunakan `str.startswith()`/`str.endswith()`, bukan slicing manual untuk cek prefix/suffix.
- Gunakan `isinstance()` untuk cek tipe, bukan `type(obj) is type(x)`.
- Manfaatkan sequence kosong sebagai falsy: `if not seq`, bukan `if len(seq) == 0`.
- Hindari `return`/`break`/`continue` di dalam blok `finally` yang melompat keluar (akan membatalkan exception yang sedang menyebar).

## Anotasi Tipe (Type Hints)

- Gunakan sintaks PEP 484 untuk anotasi fungsi.
- Variable annotation (PEP 526): satu spasi setelah `:`, tidak ada spasi sebelum `:`. Jika ada nilai, `=` diberi satu spasi di kedua sisi.
  - Benar: `code: int`, `label: str = 'x'`
  - Salah: `code:int`, `code : int`, `result: int=0`
