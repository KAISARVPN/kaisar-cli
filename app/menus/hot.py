import requests
import time
from colorama import Fore, Style, init
from app.client.engsel import get_family, get_package_details
from app.menus.package import show_package_details
from app.service.auth import AuthInstance
from app.menus.util import clear_screen, pause
from app.client.ewallet import show_multipayment
from app.client.qris import show_qris_payment
from app.client.balance import settlement_balance
from app.type_dict import PaymentItem

# Inisialisasi Colorama
init(autoreset=True)

# --- Palet Warna ---
HEADER = Fore.CYAN + Style.BRIGHT
SUCCESS = Fore.GREEN + Style.BRIGHT
ERROR = Fore.RED + Style.BRIGHT
WARNING = Fore.YELLOW + Style.BRIGHT
INFO = Fore.MAGENTA
PROMPT = Fore.WHITE + Style.BRIGHT
LIST_ITEM = Fore.WHITE
RESET = Style.RESET_ALL

def print_header(title: str):
    """Mencetak header menu yang keren dan rapi."""
    clear_screen()
    print(HEADER + "=======================================================")
    print(f"            {title}")
    print(HEADER + "=======================================================" + RESET)

def show_hot_menu():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    
    in_bookmark_menu = True
    while in_bookmark_menu:
        print_header("🔥 Paket Hot 🔥")
        print(INFO + "Mencari paket hot terbaik untukmu... ⏳\n")
        
        try:
            url = "https://me.mashu.lol/pg-hot.json"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                print(ERROR + "Gagal mengambil data hot package. Mungkin server sedang sibuk.")
                pause()
                return None

            hot_packages = response.json()

            for idx, p in enumerate(hot_packages):
                print(f"{PROMPT}{idx + 1}.{LIST_ITEM} {p['family_name']}")
                print(f"   {INFO}Variant:{RESET} {p['variant_name']} / {p['option_name']}")
                print(HEADER + "-------------------------------------------------------")
            
            print(f"\n{PROMPT}00.{RESET} Kembali ke menu utama")
            print(HEADER + "-------------------------------------------------------")
            choice = input(PROMPT + "Pilih paket (nomor): ")
            
            if choice == "00":
                in_bookmark_menu = False
                return None
                
            if choice.isdigit() and 1 <= int(choice) <= len(hot_packages):
                selected_bm = hot_packages[int(choice) - 1]
                family_code = selected_bm["family_code"]
                is_enterprise = selected_bm["is_enterprise"]
                
                print(INFO + "\nMemeriksa detail paket keluarga...")
                family_data = get_family(api_key, tokens, family_code, is_enterprise)
                if not family_data:
                    print(ERROR + "Gagal mengambil data family. Paket ini mungkin sudah tidak tersedia.")
                    pause()
                    continue
                
                package_variants = family_data["package_variants"]
                option_code = None
                for variant in package_variants:
                    if variant["name"] == selected_bm["variant_name"]:
                        selected_variant = variant
                        package_options = selected_variant["package_options"]
                        for option in package_options:
                            if option["order"] == selected_bm["order"]:
                                selected_option = option
                                option_code = selected_option["package_option_code"]
                                break
                
                if option_code:
                    print(SUCCESS + "Paket ditemukan! Menampilkan detail...")
                    time.sleep(1)
                    show_package_details(api_key, tokens, option_code, is_enterprise)            
                else:
                    print(ERROR + "Oops! Gagal menemukan kode opsi paket yang sesuai.")
                    pause()
            
            else:
                print(ERROR + "Input tidak valid. Silahkan pilih nomor yang ada di daftar ya.")
                pause()
                continue
        except requests.Timeout:
            print(ERROR + "Server tidak merespon (timeout). Coba lagi nanti.")
            pause()
            return None
        except Exception as e:
            print(ERROR + f"Terjadi kesalahan: {e}")
            pause()
            return None

def show_hot_menu2():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    
    in_bookmark_menu = True
    while in_bookmark_menu:
        print_header("💥 Paket Hot 2 (Spesial) 💥")
        print(INFO + "Mencari paket spesial (Hot 2) untukmu... ⏳\n")
        
        try:
            url = "https://me.mashu.lol/pg-hot2.json"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(ERROR + "Gagal mengambil data hot package 2.")
                pause()
                return None

            hot_packages = response.json()

            for idx, p in enumerate(hot_packages):
                print(f"{PROMPT}{idx + 1}.{LIST_ITEM} {p['name']}")
                print(f"   {SUCCESS}Harga: {p['price']}{RESET}")
                print(HEADER + "-------------------------------------------------------")
            
            print(f"\n{PROMPT}00.{RESET} Kembali ke menu utama")
            print(HEADER + "-------------------------------------------------------")
            choice = input(PROMPT + "Pilih paket (nomor): ")
            
            if choice == "00":
                in_bookmark_menu = False
                return None
                
            if choice.isdigit() and 1 <= int(choice) <= len(hot_packages):
                selected_package = hot_packages[int(choice) - 1]
                packages = selected_package.get("packages", [])
                
                if len(packages) == 0:
                    print(WARNING + "Paket ini belum memiliki isi. Coba pilih yang lain.")
                    pause()
                    continue
                
                print(INFO + "\nMengumpulkan detail paket... Ini mungkin butuh beberapa saat.")
                payment_items = []
                package_details_ok = True
                
                for package in packages:
                    print(f"{INFO}  -> Mengambil data {package['family_code']}...")
                    package_detail = get_package_details(
                        api_key,
                        tokens,
                        package["family_code"],
                        package["variant_code"],
                        package["order"],
                        package["is_enterprise"],
                    )
                    
                    if not package_detail:
                        print(ERROR + f"Gagal mengambil detail paket untuk {package['family_code']}. Pembelian dibatalkan.")
                        package_details_ok = False
                        break # Hentikan loop jika satu saja gagal
                    
                    payment_items.append(
                        PaymentItem(
                            item_code=package_detail["package_option"]["package_option_code"],
                            product_type="",
                            item_price=package_detail["package_option"]["price"],
                            item_name=package_detail["package_option"]["name"],
                            tax=0,
                            token_confirmation=package_detail["token_confirmation"],
                        )
                    )
                
                if not package_details_ok:
                    pause()
                    continue # Kembali ke menu daftar paket
                
                print(SUCCESS + "Semua detail paket berhasil dikumpulkan!")
                time.sleep(1)
                
                # --- Halaman Konfirmasi & Pembayaran ---
                print_header(f"Konfirmasi: {selected_package['name']}")
                print(f"{INFO}Nama Paket:{RESET} {PROMPT}{selected_package['name']}")
                print(f"{SUCCESS}Harga Total:{RESET} {PROMPT}{selected_package['price']}")
                print(f"{INFO}Detail Paket:{RESET} {selected_package['detail']}")
                print(HEADER + "=======================================================")

                payment_for = selected_package.get("payment_for", "BUY_PACKAGE")
                ask_overwrite = selected_package.get("ask_overwrite", False)
                overwrite_amount = selected_package.get("overwrite_amount", -1)
                token_confirmation_idx = selected_package.get("token_confirmation_idx", 0)
                amount_idx = selected_package.get("amount_idx", -1)

                in_payment_menu = True
                while in_payment_menu:
                    print(INFO + "\nPilih Metode Pembayaran:")
                    print(f"  {PROMPT}1.{RESET} Balance")
                    print(f"  {PROMPT}2.{RESET} E-Wallet")
                    print(f"  {PROMPT}3.{RESET} QRIS")
                    print(f"  {PROMPT}00.{RESET} Batalkan & Kembali")
                    print(HEADER + "-------------------------------------------------------")
                    
                    input_method = input(PROMPT + "Pilih metode (nomor): ")
                    
                    if input_method == "1":
                        if overwrite_amount == -1:
                            print(WARNING + f"\nPERHATIAN: Pastikan sisa balance KURANG DARI Rp{payment_items[-1]['item_price']}!!!")
                            balance_answer = input(PROMPT + "Apakah kamu yakin ingin melanjutkan pembelian? (y/n): ")
                            if balance_answer.lower() != "y":
                                print(ERROR + "Pembelian dibatalkan olehmu.")
                                pause()
                                in_payment_menu = False
                                continue

                        settlement_balance(
                            api_key,
                            tokens,
                            payment_items,
                            payment_for,
                            ask_overwrite,
                            overwrite_amount,
                            token_confirmation_idx,
                            amount_idx,
                        )
                        input(SUCCESS + "\nProses selesai. Tekan Enter untuk kembali...")
                        in_payment_menu = False
                        in_bookmark_menu = False
                        
                    elif input_method == "2":
                        show_multipayment(
                            api_key,
                            tokens,
                            payment_items,
                            payment_for,
                            ask_overwrite,
                            overwrite_amount,
                            token_confirmation_idx,
                            amount_idx,
                        )
                        input(SUCCESS + "\nProses selesai. Tekan Enter untuk kembali...")
                        in_payment_menu = False
                        in_bookmark_menu = False
                        
                    elif input_method == "3":
                        show_qris_payment(
                            api_key,
                            tokens,
                            payment_items,
                            payment_for,
                            ask_overwrite,
                            overwrite_amount,
                            token_confirmation_idx,
                            amount_idx,
                        )
                        input(SUCCESS + "\nProses selesai. Tekan Enter untuk kembali...")
                        in_payment_menu = False
                        in_bookmark_menu = False
                        
                    elif input_method == "00":
                        print(INFO + "Oke, pembelian dibatalkan.")
                        in_payment_menu = False
                        time.sleep(1)
                        continue # Kembali ke menu daftar paket
                    else:
                        print(ERROR + "Metode tidak valid. Silahkan pilih 1, 2, 3, atau 00.")
                        pause()
                        continue
            else:
                print(ERROR + "Input tidak valid. Silahkan pilih nomor yang ada di daftar ya.")
                pause()
                continue
        except requests.Timeout:
            print(ERROR + "Server tidak merespon (timeout). Coba lagi nanti.")
            pause()
            return None
        except Exception as e:
            print(ERROR + f"Terjadi kesalahan tak terduga: {e}")
            pause()
            return None

# Jika file ini dijalankan langsung (untuk testing)
if __name__ == "__main__":
    print(ERROR + "File ini sebaiknya di-import, bukan dijalankan langsung.")
