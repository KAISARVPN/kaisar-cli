import time
from colorama import Fore, Style, init
from app.client.engsel import get_otp, submit_otp
from app.menus.util import clear_screen, pause
from app.service.auth import AuthInstance

# Inisialisasi Colorama
init(autoreset=True)

# --- Palet Warna ---
HEADER = Fore.CYAN + Style.BRIGHT
SUCCESS = Fore.GREEN + Style.BRIGHT
ERROR = Fore.RED + Style.BRIGHT
WARNING = Fore.YELLOW + Style.BRIGHT
INFO = Fore.MAGENTA
PROMPT = Fore.WHITE + Style.BRIGHT
RESET = Style.RESET_ALL

def print_header(title: str):
    """Mencetak header menu yang keren dan rapi."""
    clear_screen()
    print(HEADER + "=======================================================")
    print(f"            ✨ {title} ✨")
    print(HEADER + "=======================================================" + RESET)

def show_login_menu():
    """Fungsi ini sepertinya tidak terpakai, tapi tetap saya poles!"""
    print_header("Login ke MyXL")
    print(PROMPT + "1." + RESET + " Request OTP")
    print(PROMPT + "2." + RESET + " Submit OTP")
    print(PROMPT + "99." + RESET + " Tutup aplikasi")
    print(HEADER + "-------------------------------------------------------")
    
def login_prompt(api_key: str):
    """Menampilkan proses login yang lebih ramah dan berwarna."""
    print_header("Portal Login MyXL")
    print(INFO + "Silakan masukkan nomor XL kesayanganmu untuk memulai.")
    print(f"{WARNING}(Contoh: 6281234567890){RESET}")
    phone_number = input(PROMPT + "Nomor: ")

    if not phone_number.startswith("628") or len(phone_number) < 10 or len(phone_number) > 14:
        print(ERROR + "\nUps! Nomor tidak valid. Pastikan diawali '628' dan panjangnya pas ya.")
        time.sleep(2)
        return None

    try:
        print(INFO + "\nSedang mengirimkan kode OTP... mohon tunggu sebentar ⏳")
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            print(ERROR + "Gagal mengirim OTP. Mungkin ada gangguan, coba lagi nanti.")
            time.sleep(2)
            return None
        
        print(SUCCESS + "🚀 OTP sukses meluncur ke nomormu!")
        
        try_count = 5
        while try_count > 0:
            print(WARNING + f"\nKamu punya {try_count} kesempatan lagi.")
            otp = input(PROMPT + "Masukkan 6 digit OTP dari SMS: ")
            
            if not otp.isdigit() or len(otp) != 6:
                print(ERROR + "OTP harus 6 digit angka ya. Coba lagi.")
                continue
            
            print(INFO + "Memvalidasi OTP...")
            tokens = submit_otp(api_key, phone_number, otp)
            
            if not tokens:
                print(ERROR + "Waduh, OTP-nya salah. Jangan menyerah, coba lagi!")
                try_count -= 1
                continue
            
            print(SUCCESS + "\n🎉 Hore! Berhasil login. Selamat datang kembali!")
            time.sleep(1.5) # Kasih jeda biar terasa manisnya
            return phone_number, tokens["refresh_token"]

        print(ERROR + "\nGagal login setelah beberapa percobaan. Yuk, istirahat dulu, coba lagi nanti.")
        time.sleep(2)
        return None, None
    except Exception as e:
        print(ERROR + f"Terjadi kesalahan tak terduga: {e}")
        time.sleep(2)
        return None, None

def show_account_menu():
    """Menu utama untuk manajemen akun yang sudah di-makeover."""
    clear_screen()
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active_user = AuthInstance.get_active_user()
    
    in_account_menu = True
    add_user = False
    
    while in_account_menu:
        print_header("Manajemen Akun MyXL")
        
        # Cek jika perlu login (belum ada akun / mau tambah akun)
        if AuthInstance.get_active_user() is None or add_user:
            if add_user:
                print(INFO + "Mari kita tambahkan akun baru...\n")
            else:
                print(WARNING + "Sepertinya belum ada akun yang aktif. Yuk, login dulu!\n")
                
            number, refresh_token = login_prompt(AuthInstance.api_key)
            
            if not refresh_token:
                print(ERROR + "Gagal menambah akun. Kita coba lagi lain kali ya.")
                pause()
                add_user = False # Batalkan mode tambah akun jika gagal
                # Jika gagal login pertama kali, dan tidak ada user lain, loop akan kembali
                # dan memaksa login lagi (ini sudah benar)
                if AuthInstance.get_active_user() is None:
                    continue 
                else:
                    # Jika sudah ada user lain, kembali ke menu list akun
                    AuthInstance.load_tokens() # Muat ulang data terbaru
                    users = AuthInstance.refresh_tokens
                    active_user = AuthInstance.get_active_user()
                    continue
            
            AuthInstance.add_refresh_token(int(number), refresh_token)
            AuthInstance.load_tokens() # Muat ulang data terbaru
            users = AuthInstance.refresh_tokens
            active_user = AuthInstance.get_active_user()
            
            if add_user:
                print(SUCCESS + "Akun baru berhasil ditambahkan!")
                add_user = False
                time.sleep(1.5)
            continue # Kembali ke atas untuk menampilkan daftar akun
        
        # --- Tampilan Daftar Akun ---
        print(INFO + "📬 Akun Tersimpan:")
        if not users or len(users) == 0:
            print(WARNING + "Belum ada akun tersimpan.")
        else:
            for idx, user in enumerate(users):
                is_active = active_user and user["number"] == active_user["number"]
                active_marker = SUCCESS + " ( ✨ Akun Aktif )" + RESET if is_active else ""
                print(f"  {PROMPT}{idx + 1}.{RESET} {user['number']}{active_marker}")
        
        print(HEADER + "-------------------------------------------------------")
        print(INFO + "Pilihan Menu:")
        print(f"  {PROMPT}0{RESET}  : Tambah Akun Baru")
        print(f"  {PROMPT}1-{len(users)}{RESET} : Ganti Akun Aktif (masukkan nomor urut)")
        print(f"  {PROMPT}del <no>{RESET} : Hapus Akun (misal: 'del 1')")
        print(f"  {PROMPT}00{RESET} : Kembali ke Menu Utama")
        print(HEADER + "-------------------------------------------------------")
        
        input_str = input(PROMPT + "Pilihanmu: ")
        
        if input_str == "00":
            in_account_menu = False
            return active_user["number"] if active_user else None
        
        elif input_str == "0":
            add_user = True
            continue
            
        elif input_str.isdigit() and 1 <= int(input_str) <= len(users):
            selected_user = users[int(input_str) - 1]
            print(SUCCESS + f"\nBerhasil ganti akun! Selamat datang, {selected_user['number']}!")
            time.sleep(1.5)
            return selected_user['number'] # Keluar dari menu akun dan kembali ke menu utama
            
        elif input_str.startswith("del "):
            parts = input_str.split()
            if len(parts) == 2 and parts[1].isdigit():
                del_index = int(parts[1])
                
                if not (1 <= del_index <= len(users)):
                    print(ERROR + "Nomor urut tidak valid.")
                    pause()
                    continue

                user_to_delete = users[del_index - 1]
                
                # Cek jika mencoba hapus akun aktif
                if active_user and user_to_delete["number"] == active_user["number"]:
                    print(ERROR + "Tidak bisa menghapus akun yang sedang aktif.")
                    print(WARNING + "Silakan ganti ke akun lain dulu sebelum menghapus.")
                    pause()
                    continue
                
                confirm = input(WARNING + f"Yakin ingin menghapus akun {user_to_delete['number']}? (y/n): ")
                if confirm.lower() == 'y':
                    AuthInstance.remove_refresh_token(user_to_delete["number"])
                    AuthInstance.load_tokens() # Muat ulang data
                    users = AuthInstance.refresh_tokens
                    active_user = AuthInstance.get_active_user()
                    print(SUCCESS + "\nAkun berhasil dihapus. Selamat tinggal..")
                    pause()
                else:
                    print(INFO + "\nPenghapusan akun dibatalkan.")
                    pause()
            else:
                print(ERROR + "Perintah tidak valid. Gunakan format: del <nomor urut>")
                pause()
            continue
            
        else:
            print(ERROR + "Input tidak valid. Silahkan pilih dari menu yang ada ya.")
            pause()
            continue

# Jika file ini dijalankan langsung (untuk testing)
if __name__ == "__main__":
    # Anda bisa menambahkan mock object untuk AuthInstance di sini untuk testing
    print(ERROR + "File ini sebaiknya di-import, bukan dijalankan langsung.")
    # Contoh pemanggilan (perlu mock object yang sesuai)
    # show_account_menu() 
