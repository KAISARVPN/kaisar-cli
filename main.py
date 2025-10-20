import sys
import json
import os
from datetime import datetime
import time
from dotenv import load_dotenv

# Import dari Rich
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.status import Status
from rich.padding import Padding
from rich.table import Table # <-- TAMBAHAN
from rich import box 

# Inisialisasi console Rich
console = Console()

load_dotenv()

from app.menus.util import clear_screen, pause
from app.client.engsel import *
from app.client.engsel2 import get_tiering_info
from app.menus.payment import show_transaction_history
from app.service.auth import AuthInstance
from app.menus.bookmark import show_bookmark_menu
from app.menus.account import show_account_menu
from app.menus.package import fetch_my_packages, get_packages_by_family
from app.menus.hot import show_hot_menu, show_hot_menu2
from app.service.sentry import enter_sentry_mode
from app.menus.purchase import purchase_by_family

WIDTH = 55
USERS_DB_PATH = "db/users.json" # <-- Path ke database user

def show_main_menu(profile):
    clear_screen()
    
    # 1. Banner "KAISAR Cli"
    banner_text = Text("KAISAR Cli", style="bold bright_cyan", justify="center")
    console.print(Panel(banner_text, style="blue", padding=(1, 0), box=box.ASCII))
    console.print() 

    # 2. Panel Profil
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d")
    profile_text = (
        f"Nomor: [bold yellow]{profile['number']}[/] | Type: [bold]{profile['subscription_type']}[/]\n"
        f"Pulsa: [bold green]Rp {profile['balance']}[/] | Aktif sampai: [cyan]{expired_at_dt}[/]\n"
        f"[italic dim]{profile['point_info']}[/italic dim]"
    )
    console.print(Panel(profile_text, title="[bold]Profil Akun[/]", title_align="left", border_style="green", box=box.ASCII))

    # 3. Panel Menu
    menu_text = (
        "[bold cyan]1.[/] Login/Ganti akun\n"
        "[bold cyan]2.[/] Lihat Paket Saya\n"
        "[bold red]3.[/] Beli Paket [blink]🔥 HOT 🔥[/]\n"
        "[bold red]4.[/] Beli Paket [blink]🔥 HOT-2 🔥[/]\n"
        "[bold cyan]5.[/] Beli Paket Berdasarkan Family Code\n"
        "[bold cyan]6.[/] Riwayat Transaksi\n"
        "[bold yellow]7.[/] Purchase all packages in a family code\n"
        "[bold magenta]00.[/] Bookmark Paket\n"
        "[bold yellow]88.[/] Admin Menu\n"
        "[bold default]------------------------------------[/]\n"
        "[bold red]99.[/] Tutup aplikasi"
    )
    console.print(Panel(menu_text, title="[bold]Menu Utama[/]", title_align="left", border_style="cyan", box=box.ASCII))


# --- FUNGSI ADMIN MENU (DIPERBARUI) ---
def show_admin_menu():
    clear_screen()
    
    # 1. Dapatkan password dari environment variable
    ADMIN_PASS = os.getenv("ADMIN_PASSWORD")
    
    if not ADMIN_PASS:
        console.print(Panel("[bold red]Fitur Admin belum dikonfigurasi.[/]\nSilakan atur 'ADMIN_PASSWORD' di file .env Anda.", title="Error", box=box.ASCII, border_style="red"))
        pause()
        return

    # 2. Minta password (tersembunyi)
    password = console.input("[bold]Masukkan Password Admin: [/]", password=True)
    
    if password != ADMIN_PASS:
        console.print("[bold red]Password salah![/]")
        pause()
        return
        
    # 3. Tampilkan menu admin jika password benar
    while True:
        clear_screen()
        admin_banner = Text("ADMIN MENU", style="bold yellow", justify="center")
        console.print(Panel(admin_banner, style="red", box=box.ASCII))
        
        admin_menu_text = (
            "[bold cyan]1.[/] Masuk Sentry Mode (s)\n"
            "[bold cyan]2.[/] Test Get Package (t)\n"
            "[bold cyan]3.[/] Lihat Daftar User\n"
            "[bold cyan]4.[/] Hapus User\n"
            "[bold cyan]5.[/] Lihat Konfigurasi (.env)\n"
            "[bold red]99.[/] Kembali ke Menu Utama"
        )
        console.print(Panel(admin_menu_text, title="Opsi Admin", box=box.ASCII, border_style="yellow"))
        
        admin_choice = console.input("[bold]Pilih menu admin: [/]")
        
        if admin_choice == "1":
            # --- Masuk Sentry Mode ---
            active_user = AuthInstance.get_active_user()
            if not active_user:
                console.print("[red]Silakan login terlebih dahulu.[/]")
                pause()
                continue
            
            console.print("[bold yellow]Memasuki Sentry Mode...[/]")
            with console.status("[bold red]Entering sentry mode...[/]", spinner="dots"):
                enter_sentry_mode()
            pause()

        elif admin_choice == "2":
            # --- Test Get Package ---
            active_user = AuthInstance.get_active_user()
            if not active_user:
                console.print("[red]Silakan login terlebih dahulu.[/]")
                pause()
                continue

            console.print("[bold yellow]Menjalankan Test Get Package...[/]")
            with console.status("[bold green]Fetching package...[/]", spinner="arrow3"):
                res = get_package(
                    AuthInstance.api_key,
                    active_user["tokens"],
                    ""
                )
            console.print_json(json.dumps(res))
            pause()

        elif admin_choice == "3":
            # --- Lihat Daftar User ---
            console.print("[bold yellow]Membaca daftar user...[/]")
            try:
                with open(USERS_DB_PATH, 'r') as f:
                    users = json.load(f)
                
                table = Table(title="Daftar User Tersimpan", box=box.ASCII)
                table.add_column("No.", style="cyan")
                table.add_column("Nomor HP", style="magenta")
                
                if not users:
                    console.print("[yellow]Belum ada user tersimpan.[/]")
                else:
                    for i, user in enumerate(users):
                        table.add_row(str(i + 1), user['number'])
                    console.print(table)
                    
            except FileNotFoundError:
                console.print(f"[red]File user tidak ditemukan di {USERS_DB_PATH}[/]")
            except json.JSONDecodeError:
                console.print(f"[red]Error membaca file JSON. File mungkin rusak.[/]")
            except Exception as e:
                console.print(f"[red]Terjadi error: {e}[/]")
            pause()

        elif admin_choice == "4":
            # --- Hapus User ---
            console.print("[bold yellow]Membaca daftar user...[/]")
            try:
                with open(USERS_DB_PATH, 'r') as f:
                    users = json.load(f)
                
                if not users:
                    console.print("[yellow]Belum ada user untuk dihapus.[/]")
                    pause()
                    continue

                table = Table(title="Pilih User untuk Dihapus", box=box.ASCII)
                table.add_column("No.", style="cyan")
                table.add_column("Nomor HP", style="magenta")
                
                for i, user in enumerate(users):
                    table.add_row(str(i + 1), user['number'])
                console.print(table)
                
                choice_str = console.input("[bold]Masukkan nomor urut user yang akan dihapus (atau '99' untuk batal): [/]")
                
                if choice_str == '99':
                    continue
                    
                choice_idx = int(choice_str) - 1
                
                if 0 <= choice_idx < len(users):
                    removed_user = users.pop(choice_idx)
                    with open(USERS_DB_PATH, 'w') as f:
                        json.dump(users, f, indent=2)
                    console.print(f"[green]User {removed_user['number']} berhasil dihapus.[/]")
                else:
                    console.print("[red]Pilihan tidak valid.[/]")
                    
            except FileNotFoundError:
                console.print(f"[red]File user tidak ditemukan di {USERS_DB_PATH}[/]")
            except ValueError:
                console.print("[red]Input tidak valid. Harap masukkan angka.[/]")
            except Exception as e:
                console.print(f"[red]Terjadi error: {e}[/]")
            pause()

        elif admin_choice == "5":
            # --- Lihat Konfigurasi ---
            console.print("[bold yellow]Membaca Konfigurasi (.env)...[/]")
            
            api_key = os.getenv("API_KEY", "Tidak di-set")
            admin_pass = os.getenv("ADMIN_PASSWORD", "Tidak di-set")
            
            # Sensor password
            censored_pass = "Tidak di-set"
            if admin_pass != "Tidak di-set":
                censored_pass = (admin_pass[0] + "*" * (len(admin_pass) - 2) + admin_pass[-1]) if len(admin_pass) > 2 else admin_pass
                
            config_text = (
                f"[cyan]API_KEY:[/]\n[dim]{api_key}[/dim]\n\n"
                f"[cyan]ADMIN_PASSWORD:[/]\n[dim]{censored_pass}[/dim]"
            )
            console.print(Panel(config_text, title="Konfigurasi Aktif", box=box.ASCII, border_style="yellow"))
            pause()


        elif admin_choice == "99":
            console.print("[yellow]Kembali ke menu utama...[/]")
            break
        else:
            console.print("[red]Pilihan tidak valid.[/]")
            pause()
# --- AKHIR FUNGSI ADMIN ---


show_menu = True
def main():
    
    while True:
        active_user = AuthInstance.get_active_user()

        # Logged in
        if active_user is not None:
            profile = {}
            # Spinner untuk loading profile
            with console.status("[bold green]Mengambil data profile & balance...", spinner="dots8") as status:
                try:
                    balance = get_balance(AuthInstance.api_key, active_user["tokens"]["id_token"])
                    balance_remaining = balance.get("remaining")
                    balance_expired_at = balance.get("expired_at")
                    
                    profile_data = get_profile(AuthInstance.api_key, active_user["tokens"]["access_token"], active_user["tokens"]["id_token"])
                    sub_id = profile_data["profile"]["subscriber_id"]
                    sub_type = profile_data["profile"]["subscription_type"]
                    
                    point_info = "Points: N/A | Tier: N/A"
                    
                    if sub_type == "PREPAID":
                        tiering_data = get_tiering_info(AuthInstance.api_key, active_user["tokens"])
                        tier = tiering_data.get("tier", 0)
                        current_point = tiering_data.get("current_point", 0)
                        point_info = f"Points: [bold]{current_point}[/] | Tier: [bold]{tier}[/]"
                    
                    profile = {
                        "number": active_user["number"],
                        "subscriber_id": sub_id,
                        "subscription_type": sub_type,
                        "balance": balance_remaining,
                        "balance_expired_at": balance_expired_at,
                        "point_info": point_info
                    }
                    time.sleep(0.5)
                    status.update("[bold green]Data berhasil dimuat![/]")
                except Exception as e:
                    console.print(f"[bold red]Gagal memuat profil: {e}[/]")
                    pause()
                    continue

            show_main_menu(profile)

            choice = console.input("[bold]Pilih menu: [/]")
            if choice == "1":
                selected_user_number = show_account_menu()
                if selected_user_number:
                    AuthInstance.set_active_user(selected_user_number)
                else:
                    console.print("[yellow]Tidak ada user dipilih atau gagal memuat.[/]")
                continue
            
            elif choice == "2":
                fetch_my_packages()
                continue
            elif choice == "3":
                show_hot_menu()
            elif choice == "4":
                show_hot_menu2()
            elif choice == "5":
                family_code = console.input("[bold]Enter family code (or '99' to cancel): [/]")
                if family_code == "99":
                    continue
                get_packages_by_family(family_code)
            elif choice == "6":
                show_transaction_history(AuthInstance.api_key, active_user["tokens"])
            elif choice == "7":
                family_code = console.input("[bold]Enter family code (or '99' to cancel): [/]")
                if family_code == "99":
                    continue

                start_from_option = console.input("[bold]Start purchasing from option number (default 1): [/]")
                try:
                    start_from_option = int(start_from_option)
                except ValueError:
                    start_from_option = 1

                use_decoy = console.input("[bold]Use decoy package? (y/n): [/]").lower() == 'y'
                pause_on_success = console.input("[bold]Pause on each successful purchase? (y/n): [/]").lower() == 'y'
                delay_seconds = console.input("[bold]Delay seconds between purchases (0 for no delay): [/]")
                try:
                    delay_seconds = int(delay_seconds)
                except ValueError:
                    delay_seconds = 0
                
                with console.status(f"[bold magenta]Memulai proses pembelian untuk family: {family_code}...[/]", spinner="line"):
                    purchase_by_family(
                        family_code,
                        use_decoy,
                        pause_on_success,
                        delay_seconds,
                        start_from_option
                    )
            elif choice == "00":
                show_bookmark_menu()
            
            elif choice == "88":
                show_admin_menu()

            elif choice == "99":
                console.print("[bold yellow]Menutup aplikasi... Sampai jumpa![/]")
                sys.exit(0)
            
            else:
                console.print("[bold red]Pilihan tidak valid. Silakan coba lagi.[/]")
                pause()
        else:
            # Not logged in
            console.print(Panel("[bold yellow]Anda belum login. Silakan pilih akun.[/]", title="Login Diperlukan", box=box.ASCII))
            selected_user_number = show_account_menu()
            if selected_user_number:
                AuthInstance.set_active_user(selected_user_number)
            else:
                console.print("[bold red]Tidak ada user dipilih atau gagal memuat user.[/]")
                console.print("[bold red]Menutup aplikasi...[/]")
                sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Aplikasi dihentikan oleh pengguna.[/]")
    # except Exception as e:
    #     console.print(f"[bold red]Terjadi error yang tidak diketahui: {e}[/]")

