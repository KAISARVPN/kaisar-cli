import sys
import json
from datetime import datetime
import time
from dotenv import load_dotenv

# Import dari Rich
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.status import Status
from rich.padding import Padding

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

WIDTH = 55 # Variabel ini mungkin tidak terlalu relevan lagi dengan Panel

def show_main_menu(profile):
    clear_screen()
    
    # 1. Banner "KAISAR Cli"
    banner_text = Text("KAISAR Cli", style="bold bright_cyan", justify="center")
    console.print(Panel(banner_text, style="blue", padding=(1, 0)))
    console.print() # Spasi

    # 2. Panel Profil
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d")
    profile_text = (
        f"Nomor: [bold yellow]{profile['number']}[/] | Type: [bold]{profile['subscription_type']}[/]\n"
        f"Pulsa: [bold green]Rp {profile['balance']}[/] | Aktif sampai: [cyan]{expired_at_dt}[/]\n"
        f"[italic dim]{profile['point_info']}[/italic]"
    )
    console.print(Panel(profile_text, title="[bold]Profil Akun[/]", title_align="left", border_style="green"))

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
        "[bold default]------------------------------------[/]\n"
        "[bold red]99.[/] Tutup aplikasi"
    )
    console.print(Panel(menu_text, title="[bold]Menu Utama[/]", title_align="left", border_style="cyan"))


show_menu = True
def main():
    
    while True:
        active_user = AuthInstance.get_active_user()

        # Logged in
        if active_user is not None:
            profile = {}
            # Menggunakan status spinner untuk proses loading data
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
                    time.sleep(0.5) # Sedikit jeda agar spinner terlihat
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
                with console.status("[bold green]Mengambil data paket Anda...", spinner="arrow3"):
                    fetch_my_packages()
                continue
            elif choice == "3":
                with console.status("[bold green]Memuat menu HOT...", spinner="arrow3"):
                    show_hot_menu()
            elif choice == "44":
                with console.status("[bold green]Memuat menu HOT-2...", spinner="arrow3"):
                    show_hot_menu2()
            elif choice == "5":
                family_code = console.input("[bold]Enter family code (or '99' to cancel): [/]")
                if family_code == "99":
                    continue
                with console.status(f"[bold green]Mencari paket family: {family_code}...[/]", spinner="arrow3"):
                    get_packages_by_family(family_code)
            elif choice == "6":
                with console.status("[bold green]Memuat riwayat transaksi...", spinner="arrow3"):
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
                
                # Spinner untuk proses pembelian
                with console.status(f"[bold magenta]Memulai proses pembelian untuk family: {family_code}...[/]", spinner="line"):
                    purchase_by_family(
                        family_code,
                        use_decoy,
                        pause_on_success,
                        delay_seconds,
                        start_from_option
                    )
            elif choice == "00":
                with console.status("[bold green]Memuat menu bookmark...", spinner="arrow3"):
                    show_bookmark_menu()
            elif choice == "99":
                console.print("[bold yellow]Menutup aplikasi... Sampai jumpa![/]")
                sys.exit(0)
            elif choice == "t":
                with console.status("[bold green]Fetching package...[/]", spinner="arrow3"):
                    res = get_package(
                        AuthInstance.api_key,
                        active_user["tokens"],
                        ""
                    )
                console.print_json(json.dumps(res))
                pause()
                pass
            elif choice == "s":
                with console.status("[bold red]Entering sentry mode...[/]", spinner="dots"):
                    enter_sentry_mode()
            else:
                console.print("[bold red]Pilihan tidak valid. Silakan coba lagi.[/]")
                pause()
        else:
            # Not logged in
            console.print(Panel("[bold yellow]Anda belum login. Silakan pilih akun.[/]", title="Login Diperlukan"))
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

