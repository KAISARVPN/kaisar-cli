import json
import sys
import time  # Ditambahkan untuk jeda

import requests
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.style import Style
from rich.markup import escape  # Untuk menampilkan HTML dengan aman

from app.service.auth import AuthInstance
from app.client.engsel import get_family, get_package, get_addons, get_package_details, send_api_request
from app.client.engsel2 import unsubscribe
from app.service.bookmark import BookmarkInstance
from app.client.purchase import settlement_bounty, settlement_loyalty
from app.menus.util import clear_screen, pause, display_html  # display_html mungkin perlu disesuaikan
from app.client.qris import show_qris_payment
from app.client.ewallet import show_multipayment
from app.client.balance import settlement_balance
from app.type_dict import PaymentItem
from app.menus.purchase import purchase_n_times

# --- Inisialisasi Rich Console ---
# Kita buat console global agar bisa dipakai di semua fungsi
console = Console()

# --- Fungsi Utilitas Bantuan ---
def clear_and_print_header(title: str, style: str = "bold magenta", emoji: str = "✨"):
    """Membersihkan layar dan mencetak header panel yang cantik."""
    console.clear()
    console.print(Panel(f"{emoji} {title} {emoji}", style=style, expand=False))

def custom_pause(message: str = "Tekan [bold]Enter[/bold] untuk melanjutkan..."):
    """Pengganti pause() menggunakan Rich Prompt."""
    Prompt.ask(message, default="", show_default=False)

def print_success(message: str):
    """Mencetak pesan sukses dengan gaya yang manis."""
    console.print(f"[bold green]✓ {message} :sparkles:[/bold green]")

def print_error(message: str):
    """Mencetak pesan error dengan gaya yang jelas."""
    console.print(f"[bold red]✗ {message} :warning:[/bold red]")

def print_info(message: str):
    """Mencetak pesan informasi."""
    console.print(f"[cyan]i {message}[/cyan]")

# --- Modifikasi Fungsi Inti ---

def show_package_details(api_key, tokens, package_option_code, is_enterprise, option_order = -1):
    clear_and_print_header("Detail Paket Pilihanmu", style="bold cyan", emoji="💖")
    
    package = None
    with console.status("[bold yellow]Mengambil detail paket... Sabar ya, manis![/bold yellow]", spinner="dots4") as status:
        package = get_package(api_key, tokens, package_option_code)
        time.sleep(0.5) # Biar kelihatan prosesnya
        
    if not package:
        print_error("Gagal memuat detail paket.")
        custom_pause()
        return False

    price = package["package_option"]["price"]
    
    # Menampilkan T&C (SnK) dengan lebih aman
    detail_html = package["package_option"]["tnc"]
    # Kita gunakan display_html jika itu fungsi custom, jika tidak, kita escape
    # detail_text = display_html(detail_html) # Asumsi fungsi ini mengembalikan teks
    # Untuk contoh ini, kita anggap display_html tidak ada dan kita strip tag HTML
    import re
    detail_text = re.sub('<[^<]+?>', '', detail_html).strip()

    validity = package["package_option"]["validity"]

    option_name = package.get("package_option", {}).get("name","")
    family_name = package.get("package_family", {}).get("name","")
    variant_name = package.get("package_detail_variant", "").get("name","")
    
    title = f"{family_name} - {variant_name} - {option_name}".strip()
    
    token_confirmation = package["token_confirmation"]
    ts_to_sign = package["timestamp"]
    payment_for = package["package_family"]["payment_for"]
    
    payment_items = [
        PaymentItem(
            item_code=package_option_code,
            product_type="",
            item_price=price,
            item_name=f"{variant_name} {option_name}".strip(),
            tax=0,
            token_confirmation=token_confirmation,
        )
    ]
    
    # Tampilkan detail dalam Panel
    detail_content = Text()
    detail_content.append(f"Nama Paket: \n[bold]{title}[/bold]\n\n", style="white")
    detail_content.append(f"Harga: [bold yellow]Rp {price}[/bold]\n", style="white")
    detail_content.append(f"Masa Aktif: [bold cyan]{validity}[/bold]\n", style="white")
    detail_content.append(f"Poin Didapat: [bold magenta]{package['package_option']['point']}[/bold]\n", style="white")
    detail_content.append(f"Tipe Plan: [bold]{package['package_family']['plan_type']}[/bold]\n", style="white")

    console.print(Panel(detail_content, title="Informasi Paket", border_style="green"))

    # Tampilkan Benefits
    benefits = package["package_option"]["benefits"]
    if benefits and isinstance(benefits, list):
        benefit_table = Table(title="🎉 Benefits yang Kamu Dapat 🎉", border_style="blue", show_header=True, header_style="bold blue")
        benefit_table.add_column("Benefit", style="cyan")
        benefit_table.add_column("Total Kuota", style="yellow")
        
        for benefit in benefits:
            name = benefit['name']
            data_type = benefit['data_type']
            total = benefit['total']
            kuota_str = ""

            if data_type == "VOICE" and total > 0:
                kuota_str = f"{total/60} menit"
            elif data_type == "TEXT" and total > 0:
                kuota_str = f"{total} SMS"
            elif data_type == "DATA" and total > 0:
                if total >= 1_000_000_000:
                    kuota_gb = total / (1024 ** 3)
                    kuota_str = f"{kuota_gb:.2f} GB"
                elif total >= 1_000_000:
                    kuota_mb = total / (1024 ** 2)
                    kuota_str = f"{kuota_mb:.2f} MB"
                else:
                    kuota_str = f"{total / 1024:.2f} KB"
            elif data_type not in ["DATA", "VOICE", "TEXT"]:
                kuota_str = f"{total} ({data_type})"
            
            if benefit["is_unlimited"]:
                kuota_str = "[bold magenta]Unlimited[/bold magenta]"

            benefit_table.add_row(name, kuota_str)
        
        console.print(benefit_table)

    # Tampilkan Addons (jika perlu)
    # addons = get_addons(api_key, tokens, package_option_code)
    # ... (logika addons bisa ditambahkan di sini jika ingin ditampilkan)
    
    console.print(Panel(detail_text, title="Syarat & Ketentuan", border_style="dim yellow", expand=True))

    in_package_detail_menu = True
    while in_package_detail_menu:
        console.print("\n--- [bold cyan]Pilih Metode Pembayaran[/bold cyan] ---")
        console.print("1. Beli dengan [bold green]Pulsa[/bold green] 💵")
        console.print("2. Beli dengan [bold blue]E-Wallet[/bold blue] 📱")
        console.print("3. Bayar dengan [bold magenta]QRIS[/bold magenta] 📷")
        console.print("4. Pulsa + Decoy XCP")
        console.print("5. Pulsa + Decoy XCP V2")
        console.print("6. QRIS + Decoy Edu")
        console.print("7. [bold yellow]Beli N kali[/bold yellow] (Spam Beli) 🚀")

        if payment_for == "":
            payment_for = "BUY_PACKAGE"
        
        if payment_for == "REDEEM_VOUCHER":
            console.print("B. Ambil sebagai [bold green]Bonus[/bold green] (jika tersedia) 🎁")
            console.print("L. Beli dengan [bold magenta]Poin[/bold magenta] (jika tersedia) 🌟")
        
        if option_order != -1:
            console.print("0. Tambah ke [bold red]Bookmark[/bold red] ❤️")
        console.print("00. Kembali ke daftar paket 🔙")
        console.print("-----------------------------------")

        choice = Prompt.ask("Pilihanmu (masukkan nomor)", default="00")
        
        if choice == "00":
            return False
        if choice == "0" and option_order != -1:
            success = BookmarkInstance.add_bookmark(
                family_code=package.get("package_family", {}).get("package_family_code",""),
                family_name=package.get("package_family", {}).get("name",""),
                is_enterprise=is_enterprise,
                variant_name=variant_name,
                option_name=option_name,
                order=option_order,
            )
            if success:
                print_success("Sip! Paket favoritmu sudah disimpan. ❤️")
            else:
                print_error("Paket ini sudah ada di bookmark kamu.")
            custom_pause()
            continue
        
        def handle_purchase(success_message):
            print_success(success_message)
            custom_pause("Silakan cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
            return True

        if choice == '1':
            settlement_balance(api_key, tokens, payment_items, payment_for, True)
            return handle_purchase("Pembelian dengan pulsa sedang diproses!")
        elif choice == '2':
            show_multipayment(api_key, tokens, payment_items, payment_for, True)
            return handle_purchase("Pembayaran E-Wallet siap! Silakan selesaikan.")
        elif choice == '3':
            show_qris_payment(api_key, tokens, payment_items, payment_for, True)
            return handle_purchase("Pembayaran QRIS siap! Silakan pindai kodenya.")
        
        # --- Logika Decoy (Pilihan 4, 5, 6) ---
        # (Saya asumsikan fungsinya sudah benar, hanya menambahkan logging)
        
        def get_decoy_package(url):
            with console.status(f"[bold yellow]Mengambil data decoy dari {url}...[/bold yellow]", spinner="moon"):
                response = requests.get(url, timeout=30)
                if response.status_code != 200:
                    print_error("Gagal mengambil data decoy package.")
                    custom_pause()
                    return None
                
                decoy_data = response.json()
                decoy_package_detail = get_package_details(
                    api_key, tokens, decoy_data["family_code"],
                    decoy_data["variant_code"], decoy_data["order"],
                    decoy_data["is_enterprise"], decoy_data["migration_type"],
                )
                return decoy_package_detail, decoy_data

        if choice == '4' or choice == '5' or choice == '6':
            is_qris = choice == '6'
            decoy_url = "https://me.mashu.lol/pg-decoy-edu.json" if is_qris else "https://me.mashu.lol/pg-decoy-xcp.json"
            
            decoy_result = get_decoy_package(decoy_url)
            if not decoy_result:
                continue
            
            decoy_package_detail, decoy_data = decoy_result

            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

            if is_qris:
                # Pilihan 6: QRIS + Decoy Edu
                console.print(Panel(f"Harga Paket Utama: [bold yellow]Rp {price}[/bold yellow]\nHarga Paket Decoy: [bold yellow]Rp {decoy_package_detail['package_option']['price']}[/bold yellow]\n\n[bold red]Silakan sesuaikan amount (trial & error)[/bold red]", title="Info Decoy QRIS", border_style="red"))
                show_qris_payment(api_key, tokens, payment_items, "SHARE_PACKAGE", True, token_confirmation_idx=1)
                return handle_purchase("Pembayaran QRIS (Decoy) siap! Silakan pindai.")
            
            else:
                # Pilihan 4 & 5: Pulsa + Decoy XCP
                overwrite_amount = price + decoy_package_detail["package_option"]["price"]
                
                payment_for_decoy = "🤫" if choice == '5' else payment_for
                token_idx = 1 if choice == '5' else -1 # V2 pakai token decoy
                
                with console.status("[bold yellow]Mencoba membeli dengan decoy...[/bold yellow]", spinner="arrow3"):
                    res = settlement_balance(
                        api_key, tokens, payment_items, payment_for_decoy, False,
                        overwrite_amount, token_confirmation_idx=token_idx
                    )
                
                if res and res.get("status", "") != "SUCCESS":
                    error_msg = res.get("message", "Unknown error")
                    if "Bizz-err.Amount.Total" in error_msg:
                        try:
                            valid_amount = int(error_msg.split("=")[1].strip())
                            print_info(f"Amount salah. Mencoba lagi dengan amount: {valid_amount}")
                            
                            with console.status("[bold yellow]Mencoba lagi dengan amount yang disesuaikan...[/bold yellow]", spinner="arrow3"):
                                res = settlement_balance(
                                    api_key, tokens, payment_items, "BUY_PACKAGE", False, 
                                    valid_amount, token_confirmation_idx=-1
                                )
                                if res and res.get("status", "") == "SUCCESS":
                                    print_success("Pembelian Decoy berhasil (dengan penyesuaian)!")
                                else:
                                    print_error(f"Gagal lagi: {res.get('message', 'Error')}")
                        except Exception as e:
                            print_error(f"Gagal parsing error amount: {e}")
                    else:
                        print_error(f"Gagal: {error_msg}")
                else:
                    print_success("Pembelian Decoy berhasil!")
                
                custom_pause()
                return True

        elif choice == '7':
            use_decoy_for_n_times = Confirm.ask("Gunakan paket decoy?", default=False)
            n_times_str = Prompt.ask("Masukkan jumlah pembelian (misal: 3)", default="1")
            delay_seconds_str = Prompt.ask("Masukkan jeda antar pembelian (detik, misal: 25)", default="25")

            try:
                n_times = int(n_times_str)
                delay_seconds = int(delay_seconds_str)
                if n_times < 1:
                    raise ValueError("Jumlah harus minimal 1.")
                
                print_info(f"Akan membeli paket {n_times} kali. Mohon tunggu...")
                purchase_n_times(
                    n_times,
                    family_code=package.get("package_family", {}).get("package_family_code",""),
                    variant_code=package.get("package_detail_variant", {}).get("package_variant_code",""),
                    option_order=option_order,
                    use_decoy=use_decoy_for_n_times,
                    delay_seconds=delay_seconds,
                    pause_on_success=False,
                )
                print_success(f"Selesai membeli {n_times} kali!")

            except ValueError as e:
                print_error(f"Input tidak valid: {e}")
                custom_pause()
                continue
            
            return True # Selesai setelah spam
            
        elif choice.lower() == 'b' and payment_for == "REDEEM_VOUCHER":
            settlement_bounty(api_key, tokens, token_confirmation, ts_to_sign, package_option_code, price, variant_name)
            return handle_purchase("Pengambilan bonus sedang diproses!")
        elif choice.lower() == 'l' and payment_for == "REDEEM_VOUCHER":
            settlement_loyalty(api_key, tokens, token_confirmation, ts_to_sign, package_option_code, price)
            return handle_purchase("Pembelian dengan poin sedang diproses!")
        else:
            print_error("Pilihan tidak valid. Silakan coba lagi.")
            time.sleep(1)
            
    custom_pause()
    sys.exit(0)

def get_packages_by_family(
    family_code: str,
    is_enterprise: bool | None = None,
    migration_type: str | None = None
):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print_error("Token pengguna tidak ditemukan. Silakan login lagi.")
        custom_pause()
        return None
    
    packages = []
    data = None
    
    with console.status("[bold yellow]Mengambil daftar paket keluarga...[/bold yellow]", spinner="dots") as status:
        data = get_family(api_key, tokens, family_code, is_enterprise, migration_type)
        time.sleep(0.5)

    if not data:
        print_error("Gagal memuat data family.")
        custom_pause()
        return None
        
    price_currency = "Rp"
    rc_bonus_type = data["package_family"].get("rc_bonus_type", "")
    if rc_bonus_type == "MYREWARDS":
        price_currency = "Poin"
    
    in_package_menu = True
    while in_package_menu:
        clear_and_print_header(f"Paket dari Family: {data['package_family']['name']}", style="bold green", emoji="🛍️")
        
        console.print(f"Kode Family: [bold]{family_code}[/bold] | Tipe: [bold]{data['package_family']['package_family_type']}[/bold]")
        
        package_variants = data["package_variants"]
        
        # Gunakan Rich Table untuk tampilan yang rapi
        table = Table(title="✨ Paket yang Tersedia ✨", border_style="cyan", show_header=True, header_style="bold magenta")
        table.add_column("No.", style="bold yellow", justify="right")
        table.add_column("Variant", style="blue")
        table.add_column("Nama Paket", style="white")
        table.add_column("Harga", style="bold green", justify="right")

        option_number = 1
        packages.clear() # Hapus cache lama jika loop
        
        for variant in package_variants:
            variant_name = variant["name"]
            variant_code = variant["package_variant_code"]
            
            for i, option in enumerate(variant["package_options"]):
                option_name = option["name"]
                
                packages.append({
                    "number": option_number,
                    "variant_name": variant_name,
                    "option_name": option_name,
                    "price": option["price"],
                    "code": option["package_option_code"],
                    "option_order": option["order"]
                })
                
                # Hanya tampilkan nama variant di baris pertama
                display_variant_name = variant_name if i == 0 else ""
                                
                table.add_row(
                    str(option_number),
                    display_variant_name, 
                    option_name, 
                    f"{price_currency} {option['price']}"
                )
                
                option_number += 1
            
            if variant != package_variants[-1]:
                 table.add_row("---", "---", "---", "---", style="dim") # Pemisah antar variant

        console.print(table)
        console.print("\n[dim]Masukkan '00' untuk kembali ke menu utama.[/dim]")

        pkg_choice = Prompt.ask("Pilih paket (masukkan nomor)", default="00")
        
        if pkg_choice == "00":
            in_package_menu = False
            return None
        
        try:
            selected_pkg = next((p for p in packages if p["number"] == int(pkg_choice)), None)
        except ValueError:
            selected_pkg = None
            
        if not selected_pkg:
            print_error("Paket tidak ditemukan. Silakan masukkan nomor yang benar.")
            time.sleep(1)
            continue
        
        is_done = show_package_details(api_key, tokens, selected_pkg["code"], is_enterprise, option_order=selected_pkg["option_order"])
        if is_done:
            in_package_menu = False
            return None
        else:
            continue
        
    return packages

def fetch_my_packages():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print_error("Token pengguna tidak ditemukan.")
        custom_pause()
        return None
    
    id_token = tokens.get("id_token")
    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}
    
    res = None
    with console.status("[bold yellow]Lagi ambil data paket kamu... Sabar ya! :cupid:[/bold yellow]", spinner="hearts") as status:
        res = send_api_request(api_key, path, payload, id_token, "POST")
        time.sleep(1) # Kasih jeda biar manis
        
    if not res or res.get("status") != "SUCCESS":
        print_error("Gagal mengambil daftar paketmu.")
        console.print(f"Response: {res}", style="dim")
        custom_pause()
        return None
    
    quotas = res["data"]["quotas"]
    
    clear_and_print_header("PAKET-PAKET KAMU SAAT INI", style="bold blue", emoji="📦")
    
    my_packages =[]
    num = 1
    
    with console.status("[bold yellow]Memproses detail paket satu per satu...[/bold yellow]", spinner="dots12"):
        for quota in quotas:
            quota_code = quota["quota_code"]
            group_name = quota["group_name"]
            quota_name = quota["name"]
            family_code = "N/A"
            
            product_subscription_type = quota.get("product_subscription_type", "")
            product_domain = quota.get("product_domain", "")
            
            # Ambil detail family code
            package_details = get_package(api_key, tokens, quota_code)
            if package_details:
                family_code = package_details["package_family"]["package_family_code"]
            
            # --- Tampilkan dalam Panel ---
            panel_content = Text()
            panel_content.append(f"Group: [bold]{group_name}[/bold]\n", style="white")
            panel_content.append(f"Kode Kuota: [dim]{quota_code}[/dim]\n", style="white")
            panel_content.append(f"Kode Family: [dim]{family_code}[/dim]\n\n", style="white")

            benefits = quota.get("benefits", [])
            if len(benefits) > 0:
                panel_content.append("Benefits:\n", style="bold cyan")
                for benefit in benefits:
                    name = benefit.get("name", "")
                    data_type = benefit.get("data_type", "N/A")
                    remaining = benefit.get("remaining", 0)
                    total = benefit.get("total", 0)
                    
                    kuota_sisa_str = ""
                    kuota_total_str = ""
                    
                    if data_type == "DATA":
                        def format_data(b):
                            if b >= 1_000_000_000: return f"{b / (1024 ** 3):.2f} GB"
                            if b >= 1_000_000: return f"{b / (1024 ** 2):.2f} MB"
                            if b >= 1_000: return f"{b / 1024:.2f} KB"
                            return f"{b} B"
                        kuota_sisa_str = format_data(remaining)
                        kuota_total_str = format_data(total)
                    elif data_type == "VOICE":
                        kuota_sisa_str = f"{remaining/60:.2f} menit"
                        kuota_total_str = f"{total/60:.2f} menit"
                    elif data_type == "TEXT":
                        kuota_sisa_str = f"{remaining} SMS"
                        kuota_total_str = f"{total} SMS"
                    else:
                        kuota_sisa_str = str(remaining)
                        kuota_total_str = str(total)

                    panel_content.append(f"  - {name}: [bold yellow]{kuota_sisa_str}[/bold yellow] / {kuota_total_str}\n", style="white")

            console.print(Panel(panel_content, title=f"[{num}] {quota_name}", border_style="blue"))
            
            my_packages.append({
                "number": num,
                "name": quota_name,
                "quota_code": quota_code,
                "product_subscription_type": product_subscription_type,
                "product_domain": product_domain,
            })
            
            num += 1
            time.sleep(0.1) # Jeda kecil

    console.print("\n--- [bold cyan]Opsi[/bold cyan] ---")
    console.print("➡️  Ketik [bold]nomor[/bold] paket untuk [bold]lihat detail/beli lagi[/bold].")
    console.print("➡️  Ketik '[bold red]del <nomor>[/bold red]' untuk [bold]berhenti berlangganan[/bold].")
    console.print("➡️  Ketik '[bold]00[/bold]' untuk [bold]kembali[/bold] ke menu utama.")
    
    choice = Prompt.ask("Pilihanmu", default="00")
    
    if choice == "00":
        return None
        
    if choice.startswith("del "):
        del_parts = choice.split(" ")
        if len(del_parts) != 2 or not del_parts[1].isdigit():
            print_error("Perintah delete tidak valid. Contoh: del 1")
            custom_pause()
            return None
            
        del_number = int(del_parts[1])
        del_pkg = next((pkg for pkg in my_packages if pkg["number"] == del_number), None)
        
        if not del_pkg:
            print_error("Paket tidak ditemukan untuk dihapus.")
            custom_pause()
            return None
            
        if Confirm.ask(f"Yakin mau berhenti langganan paket [yellow]{del_pkg['name']}[/yellow]?", default=False):
            print_info(f"Berhenti berlangganan dari [yellow]{del_pkg['name']}[/yellow]...")
            success = unsubscribe(
                api_key, tokens, del_pkg["quota_code"],
                del_pkg["product_subscription_type"], del_pkg["product_domain"]
            )
            if success:
                print_success("Berhasil berhenti berlangganan. Selamat tinggal paket!")
            else:
                print_error("Gagal berhenti berlangganan dari paket.")
        else:
            print_info("Batal berhenti berlangganan.")
        
        custom_pause()
        return None
        
    selected_pkg = next((pkg for pkg in my_packages if str(pkg["number"]) == choice), None)
    
    if not selected_pkg:
        print_error("Paket tidak ditemukan. Silakan masukkan nomor yang benar.")
        custom_pause()
        return None
    
    # Tampilkan detail paket yang dipilih
    is_done = show_package_details(api_key, tokens, selected_pkg["quota_code"], False)
    if is_done:
        return None
        
    custom_pause()

# --- Entry Point (jika file ini dijalankan langsung) ---
if __name__ == "__main__":
    # Kamu bisa tambahkan fungsi utama di sini untuk testing
    console.print(Panel("💖 [bold]Selamat Datang di Script Paket Keren![/bold] 💖\n\n[dim]File ini seharusnya di-import sebagai modul, tetapi ini adalah demo tampilannya.[/dim]", style="bold magenta", padding=1))
    
    # Contoh demo
    print_success("Ini adalah contoh pesan sukses.")
    print_error("Ini adalah contoh pesan error.")
    print_info("Ini adalah contoh pesan info.")
    
    # Demo Status
    try:
        with console.status("[bold yellow]Menjalankan proses manis...[/bold yellow]", spinner="bouncingBar") as status:
            time.sleep(3)
            status.update("[bold green]Proses selesai![/bold green]")
        
        custom_pause()
    except KeyboardInterrupt:
        console.print("\n[bold red]Proses dibatalkan.[/bold red]")

