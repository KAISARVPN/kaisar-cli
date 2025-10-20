from datetime import datetime, timedelta
import sys
import os

# Impor untuk warna-warni!
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Gagal mengimpor colorama. Silakan install dengan 'pip install colorama'")
    # Jika colorama tidak ada, buat variabel palsu agar skrip tidak error
    class FakeColor:
        def __getattr__(self, name):
            return ""
    Fore = FakeColor()
    Style = FakeColor()

from app.client.engsel2 import get_pending_transaction, get_transaction_history
from app.menus.util import clear_screen

# --- Palet Warna untuk Tampilan Keren ---
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
B = Fore.BLUE
M = Fore.MAGENTA
C = Fore.CYAN
W = Fore.WHITE
RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT

def show_transaction_history(api_key, tokens):
    in_transaction_menu = True

    while in_transaction_menu:
        clear_screen()
        # --- Header Manis ---
        print(f"{BRIGHT}{M}╔{'═' * 46}╗{RESET}")
        print(f"{BRIGHT}{M}║ ✨ Riwayat Transaksi Manis Anda ✨ ║{RESET}")
        print(f"{BRIGHT}{M}╚{'═' * 46}╝{RESET}\n")

        # --- Penampilan Proses (Loading) ---
        print(f"{C}Mohon tunggu sebentar, kami sedang mengambil catatan indah transaksimu... 💖{RESET}")

        data = None
        history = []
        try:
            data = get_transaction_history(api_key, tokens)
            history = data.get("list", [])
        except Exception as e:
            # --- Pesan Error yang Lebih Ramah ---
            print(f"\n{R}{BRIGHT}Oops! Terjadi sedikit kendala saat mengambil data: {e} 😥{RESET}")
            history = []
        
        # Hapus pesan loading jika sudah selesai
        clear_screen()
        print(f"{BRIGHT}{M}╔{'═' * 46}╗{RESET}")
        print(f"{BRIGHT}{M}║ ✨ Riwayat Transaksi Manis Anda ✨ ║{RESET}")
        print(f"{BRIGHT}{M}╚{'═' * 46}╝{RESET}\n")

        if len(history) == 0:
            # --- Pesan Manis untuk Riwayat Kosong ---
            print(f"{Y}Sepertinya Anda belum memiliki riwayat transaksi.")
            print(f"{Y}Yuk, mulai bertransaksi dan buat kenangan di sini! 😊{RESET}")
        
        for idx, transaction in enumerate(history, start=1):
            transaction_timestamp = transaction.get("timestamp", 0)
            
            # Koreksi Logika Waktu: Asumsi timestamp adalah UTC, konversi ke WIB (UTC+7)
            dt_utc = datetime.utcfromtimestamp(transaction_timestamp)
            dt_jakarta = dt_utc + timedelta(hours=7) # WIB adalah UTC+7
            
            formatted_time = dt_jakarta.strftime("%d %B %Y | %H:%M WIB")

            # --- Logika Warna untuk Status ---
            status = transaction.get('status', 'N/A').upper()
            payment_status = transaction.get('payment_status', 'N/A').upper()

            status_color = G if status == 'SUCCESS' else (R if status == 'FAILED' else Y)
            payment_status_color = G if payment_status == 'PAID' else (R if payment_status == 'FAILED' else Y)
            
            status_str = f"{status_color}{status}{RESET}"
            payment_status_str = f"{payment_status_color}{payment_status}{RESET}"

            # --- Tampilan Riwayat yang Lebih Rapi ---
            print(f"{BRIGHT}{W}{idx}. {transaction['title']} - {C}{transaction['price']}{RESET}")
            print(f"   {B}Tanggal          : {W}{formatted_time}")
            print(f"   {B}Metode Pembayaran: {W}{transaction['payment_method_label']}")
            print(f"   {B}Status Transaksi : {status_str}")
            print(f"   {B}Status Pembayaran: {payment_status_str}")
            print(f"{M}{'─' * 55}{RESET}") # Pemisah antar transaksi

        # --- Opsi Menu yang Keren ---
        print(f"\n{BRIGHT}{G}0. Refresh Data 🔄{RESET}")
        print(f"{BRIGHT}{R}00. Kembali ke Menu Utama 🏠{RESET}")
        
        try:
            # --- Prompt Input yang Manis ---
            choice = input(f"\n{Y}Pilih opsi (dengan cinta ❤️): {W}")
        except KeyboardInterrupt:
            in_transaction_menu = False
            print(f"\n{R}Sampai jumpa lagi!{RESET}")
            
        if choice == "0":
            continue
        elif choice == "00":
            in_transaction_menu = False
        else:
            print(f"\n{R}Oops, pilihan '{choice}' tidak ada. Coba lagi ya!{RESET}")
            try:
                # Beri jeda agar pengguna bisa membaca pesan error
                input(f"{W}(Tekan Enter untuk melanjutkan...){RESET}")
            except KeyboardInterrupt:
                in_transaction_menu = False
                print(f"\n{R}Sampai jumpa lagi!{RESET}")

