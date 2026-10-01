"""Cetak rekap durasi tiap langkah satu TIPE proses-harian.bat/proses-harian-uji.bat.

Dipanggil dari .bat setelah semua langkah satu TIPE selesai, dengan timestamp
(epoch, dari time.time()) yang sudah dicatat .bat sebelum & sesudah tiap langkah
lewat subrutin :catat_waktu - skrip ini cuma menghitung selisih & mencetak tabelnya,
tidak mengukur waktu sendiri (supaya .bat tetap satu sumber kebenaran urutan langkah).

Pemakaian:
    python src/rekap_waktu.py "TIPE 1" "URGENT LAZADA:<mulai>:<selesai>" "...:<mulai>:<selesai>"
"""
import sys


def format_durasi(detik):
    detik = int(round(detik))
    menit, sisa_detik = divmod(detik, 60)
    if menit:
        return f"{menit} menit {sisa_detik} detik"
    return f"{sisa_detik} detik"


def main():
    judul = sys.argv[1]
    entri = []
    total = 0.0
    for arg in sys.argv[2:]:
        nama, mulai, selesai = arg.rsplit(":", 2)
        durasi = max(0.0, float(selesai) - float(mulai))
        entri.append((nama, durasi))
        total += durasi

    lebar_nama = max((len(nama) for nama, _ in entri), default=0)

    print()
    print("=" * 60)
    print(f"  REKAP WAKTU PROSES - {judul}")
    print("=" * 60)
    for nama, durasi in entri:
        print(f"  {nama.ljust(lebar_nama)} : {format_durasi(durasi)}")
    print("-" * 60)
    print(f"  {'TOTAL'.ljust(lebar_nama)} : {format_durasi(total)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
