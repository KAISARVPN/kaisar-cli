import requests, time
from random import randint
from app.client.engsel import get_family, get_package_details
# from app.menus.util import pause # Kita ganti dengan fungsi pause dari rich
from app.service.auth import AuthInstance
from app.type_dict import PaymentItem
from app.client.balance import settlement_balance

# --- Tambahan untuk Tampilan Keren! ---
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    SpinnerColumn,
)
from rich.text import Text

# Inisialisasi console Rich
console = Console()

def pause():
    """Gantinya app.menus.util.pause, versi lebih manis."""
    console.input(Text("\nTekan [Enter] untuk melanjutkan...", style="dim italic"))
# ----------------------------------------


# Purchase
def purchase_by_family(
    family_code: str,
    use_decoy: bool,
    pause_on_success: bool = True,
    delay_seconds: int = 0,
    start_from_option: int = 1,
):
    console.print(Panel(
        f"Mencari paket-paket terbaik di family [bold]{family_code}[/bold] untukmu! 💖",
        title="✨ Halo! Mari Kita Mulai Berburu ✨",
        style="bold magenta",
        padding=(1, 2)
    ))
    
    api_key = AuthInstance.api_key
    tokens: dict = AuthInstance.get_active_tokens() or {}
    
    if use_decoy:
        # Balance; Decoy XCP
        url = "https://me.mashu.lol/pg-decoy-xcp.json"
        
        console.print("Mengambil data decoy...", style="cyan")
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            console.print("Oops! Gagal mengambil data decoy package.", style="bold red")
            pause()
            return None
        
        decoy_data = response.json()
        decoy_package_detail = get_package_details(
            api_key,
            tokens,
            decoy_data["family_code"],
            decoy_data["variant_code"],
            decoy_data["order"],
            decoy_data["is_enterprise"],
            decoy_data["migration_type"],
        )
        
        balance_treshold = decoy_package_detail["package_option"]["price"]
        console.print(f"Pastikan sisa balance KURANG DARI [bold]Rp{balance_treshold}[/bold] ya!", style="bold yellow")
        balance_answer = console.input(Text("Apakah kamu yakin ingin melanjutkan pembelian? (y/n): ", style="bold cyan"))
        if balance_answer.lower() != "y":
            console.print("Pembelian dibatalkan olehmu. Sampai jumpa lagi!", style="bold red")
            pause()
            return None
    
    family_data = get_family(api_key, tokens, family_code)
    if not family_data:
        console.print(f"Gagal mendapatkan data family untuk kode: {family_code}.", style="bold red")
        pause()
        return None
    
    family_name = family_data["package_family"]["name"]
    variants = family_data["package_variants"]
    
    successful_purchases = []
    packages_count = 0
    for variant in variants:
        packages_count += len(variant["package_options"])
    
    purchase_count = 0
    start_buying = False
    if start_from_option <= 1:
        start_buying = True

    # --- Progress Bar Keren! ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(f"[cyan]Memburu {packages_count} paket di [bold]{family_name}[/bold]...", total=packages_count)

        for variant in variants:
            variant_name = variant["name"]
            for option in variant["package_options"]:
                tokens = AuthInstance.get_active_tokens()
                option_order = option["order"]
                if not start_buying and option_order == start_from_option:
                    start_buying = True
                
                if not start_buying:
                    progress.log(f"[dim]Melewatkan Opsi {option_order}: {option['name']}[/dim]")
                    progress.update(task, advance=1)
                    continue
                
                option_name = option["name"]
                option_price = option["price"]
                
                purchase_count += 1
                progress.log(
                    f"Mencoba membeli ({purchase_count}/{packages_count}): [bold]{variant_name} - {option_name}[/bold] (Rp{option_price})"
                )
                
                payment_items = []
                
                try:
                    if use_decoy:
                        decoy_package_detail = get_package_details(
                            api_key,
                            tokens,
                            decoy_data["family_code"],
                            decoy_data["variant_code"],
                            decoy_data["order"],
                            decoy_data["is_enterprise"],
                            decoy_data["migration_type"],
                        )
                    
                    target_package_detail = get_package_details(
                        api_key,
                        tokens,
                        family_code,
                        variant["package_variant_code"],
                        option["order"],
                        None,
                        None,
                    )
                except Exception as e:
                    progress.log(f"[bold red]Oops! Terjadi error saat ambil detail paket: {e}[/bold red]")
                    progress.log(f"Gagal mendapatkan detail untuk {variant_name} - {option_name}. Melewatkan...")
                    progress.update(task, advance=1)
                    continue
                
                payment_items.append(
                    PaymentItem(
                        item_code=target_package_detail["package_option"]["package_option_code"],
                        product_type="",
                        item_price=target_package_detail["package_option"]["price"],
                        item_name=str(randint(1000, 9999)) + " " + target_package_detail["package_option"]["name"],
                        tax=0,
                        token_confirmation=target_package_detail["token_confirmation"],
                    )
                )
                
                if use_decoy:
                    payment_items.append(
                        PaymentItem(
                            item_code=decoy_package_detail["package_option"]["package_option_code"],
                            product_type="",
                            item_price=decoy_package_detail["package_option"]["price"],
                            item_name=str(randint(1000, 9999)) + " " + decoy_package_detail["package_option"]["name"],
                            tax=0,
                            token_confirmation=decoy_package_detail["token_confirmation"],
                        )
                    )
                
                res = None
                
                overwrite_amount = target_package_detail["package_option"]["price"]
                if use_decoy or overwrite_amount == 0:
                    overwrite_amount += decoy_package_detail["package_option"]["price"]
                    
                error_msg = ""

                try:
                    res = settlement_balance(
                        api_key,
                        tokens,
                        payment_items,
                        "🤑",
                        False,
                        overwrite_amount,
                        token_confirmation_idx=1
                    )
                    
                    if res and res.get("status", "") != "SUCCESS":
                        error_msg = res.get("message", "")
                        if "Bizz-err.Amount.Total" in error_msg:
                            error_msg_arr = error_msg.split("=")
                            valid_amount = int(error_msg_arr[1].strip())
                            
                            progress.log(f"[yellow]Menyesuaikan jumlah total menjadi: {valid_amount}[/yellow]")
                            res = settlement_balance(
                                api_key,
                                tokens,
                                payment_items,
                                "SHARE_PACKAGE",
                                False,
                                valid_amount,
                                token_confirmation_idx=-1
                            )
                            if res and res.get("status", "") == "SUCCESS":
                                error_msg = ""
                                successful_purchases.append(
                                    f"{variant_name}|{option_order}. {option_name} - {option_price}"
                                )
                                progress.log(f"[bold green]🎉 Berhasil![/bold green] Paket '{option_name}' sudah jadi milikmu.")
                                if pause_on_success: pause()
                        else:
                             progress.log(f"[bold red]😥 Gagal:[/bold red] {error_msg}")
                    else:
                        successful_purchases.append(
                            f"{variant_name}|{option_order}. {option_name} - {option_price}"
                        )
                        progress.log(f"[bold green]🎉 Berhasil![/bold green] Paket '{option_name}' sudah jadi milikmu.")
                        if pause_on_success: pause()

                except Exception as e:
                    progress.log(f"[bold red]Exception terjadi saat membuat order: {e}[/bold red]")
                    res = None
                
                should_delay = error_msg == "" or "Failed call ipaas purchase" in error_msg
                if delay_seconds > 0 and should_delay:
                    progress.log(f"[cyan]Menunggu {delay_seconds} detik sebelum lanjut...[/cyan]")
                    time.sleep(delay_seconds)
                
                progress.update(task, advance=1)
    
    # --- Laporan Akhir yang Manis ---
    summary_text = Text(f"Keluarga Paket: {family_name}\n", justify="center")
    summary_text.append(f"Total Berhasil: {len(successful_purchases)} dari {packages_count}\n\n")
    
    if len(successful_purchases) > 0:
        summary_text.append("Paket yang berhasil didapatkan:\n", style="bold")
        for purchase in successful_purchases:
            summary_text.append(f"✓ {purchase}\n", style="green")
    else:
        summary_text.append("Yah, belum ada paket yang berhasil dibeli kali ini. 😔", style="dim")
    
    console.print(Panel(
        summary_text,
        title="✨ Laporan Selesai ✨",
        border_style="bold green",
        padding=(1, 2)
    ))
    pause()

def purchase_n_times(
    n: int,
    family_code: str,
    variant_code: str,
    option_order: int,
    use_decoy: bool,
    delay_seconds: int = 0,
    pause_on_success: bool = False,
    token_confirmation_idx: int = 0,
):
    api_key = AuthInstance.api_key
    tokens: dict = AuthInstance.get_active_tokens() or {}
    
    console.print(Panel(
        f"Siap-siap membeli paket spesial ini sebanyak [bold]{n}x[/bold]! 🚀",
        title="✨ Misi Pembelian Berulang ✨",
        style="bold blue",
        padding=(1, 2)
    ))
    
    if use_decoy:
        # Balance; Decoy XCP
        url = "https://me.mashu.lol/pg-decoy-xcp.json"
        
        console.print("Mengambil data decoy...", style="cyan")
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            console.print("Oops! Gagal mengambil data decoy package.", style="bold red")
            pause()
            return None
        
        decoy_data = response.json()
        decoy_package_detail = get_package_details(
            api_key,
            tokens,
            decoy_data["family_code"],
            decoy_data["variant_code"],
            decoy_data["order"],
            decoy_data["is_enterprise"],
            decoy_data["migration_type"],
        )
        
        balance_treshold = decoy_package_detail["package_option"]["price"]
        console.print(f"Pastikan sisa balance KURANG DARI [bold]Rp{balance_treshold}[/bold] ya!", style="bold yellow")
        balance_answer = console.input(Text("Apakah kamu yakin ingin melanjutkan pembelian? (y/n): ", style="bold cyan"))
        if balance_answer.lower() != "y":
            console.print("Pembelian dibatalkan olehmu. Sampai jumpa lagi!", style="bold red")
            pause()
            return None
    
    family_data = get_family(api_key, tokens, family_code)
    if not family_data:
        console.print(f"Gagal mendapatkan data family untuk kode: {family_code}.", style="bold red")
        pause()
        return None
    family_name = family_data["package_family"]["name"]
    variants = family_data["package_variants"]
    target_variant = None
    for variant in variants:
        if variant["package_variant_code"] == variant_code:
            target_variant = variant
            break
    if not target_variant:
        console.print(f"Kode varian {variant_code} tidak ditemukan di family {family_name}.", style="bold red")
        pause()
        return None
    target_option = None
    for option in target_variant["package_options"]:
        if option["order"] == option_order:
            target_option = option
            break
    if not target_option:
        console.print(f"Urutan Opsi {option_order} tidak ditemukan di varian {target_variant['name']}.", style="bold red")
        pause()
        return None
    
    option_name = target_option["name"]
    option_price = target_option["price"]
    
    successful_purchases = []
    
    # --- Progress Bar Keren! ---
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}% ({task.completed}/{task.total})"),
        TimeRemainingColumn(),
        console=console,
        transient=True
    ) as progress:
        task_description = f"[cyan]Membeli [bold]{option_name}[/bold] ({n}x)..."
        task = progress.add_task(task_description, total=n)
    
        for i in range(n):
            progress.log(f"--- Pembelian ke-[bold]{i + 1}[/bold] dari {n} ---")
            progress.log(f"Mencoba membeli: [bold]{target_variant['name']} - {option_name}[/bold] (Rp{option_price})")
            
            api_key = AuthInstance.api_key
            tokens: dict = AuthInstance.get_active_tokens() or {}
            
            payment_items = []
            
            try:
                if use_decoy:
                    decoy_package_detail = get_package_details(
                        api_key,
                        tokens,
                        decoy_data["family_code"],
                        decoy_data["variant_code"],
                        decoy_data["order"],
                        decoy_data["is_enterprise"],
                        decoy_data["migration_type"],
                    )
                
                target_package_detail = get_package_details(
                    api_key,
                    tokens,
                    family_code,
                    target_variant["package_variant_code"],
                    target_option["order"],
                    None,
                    None,
                )
            except Exception as e:
                progress.log(f"[bold red]Oops! Terjadi error saat ambil detail paket: {e}[/bold red]")
                progress.log(f"Gagal mendapatkan detail untuk {target_variant['name']} - {option_name}. Melewatkan...")
                progress.update(task, advance=1)
                continue
            
            payment_items.append(
                PaymentItem(
                    item_code=target_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=target_package_detail["package_option"]["price"],
                    item_name=str(randint(1000, 9999)) + " " + target_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=target_package_detail["token_confirmation"],
                )
            )
            
            if use_decoy:
                payment_items.append(
                    PaymentItem(
                        item_code=decoy_package_detail["package_option"]["package_option_code"],
                        product_type="",
                        item_price=decoy_package_detail["package_option"]["price"],
                        item_name=str(randint(1000, 9999)) + " " + decoy_package_detail["package_option"]["name"],
                        tax=0,
                        token_confirmation=decoy_package_detail["token_confirmation"],
                    )
                )
            
            res = None
            
            overwrite_amount = target_package_detail["package_option"]["price"]
            if use_decoy:
                overwrite_amount += decoy_package_detail["package_option"]["price"]

            try:
                res = settlement_balance(
                    api_key,
                    tokens,
                    payment_items,
                    "BUY_PACKAGE",
                    False,
                    overwrite_amount,
                )
                
                if res and res.get("status", "") != "SUCCESS":
                    error_msg = res.get("message", "Unknown error")
                    if "Bizz-err.Amount.Total" in error_msg:
                        error_msg_arr = error_msg.split("=")
                        valid_amount = int(error_msg_arr[1].strip())
                        
                        progress.log(f"[yellow]Menyesuaikan jumlah total menjadi: {valid_amount}[/yellow]")
                        res = settlement_balance(
                            api_key,
                            tokens,
                            payment_items,
                            "BUY_PACKAGE",
                            False,
                            valid_amount,
                        )
                        if res and res.get("status", "") == "SUCCESS":
                            successful_purchases.append(
                                f"{target_variant['name']}|{option_order}. {option_name} - {option_price}"
                            )
                            progress.log(f"[bold green]🎉 Berhasil![/bold green] (Pembelian {i+1})")
                            if pause_on_success: pause()
                        else:
                            error_msg = res.get("message", "Unknown error")
                            progress.log(f"[bold red]😥 Gagal (setelah penyesuaian):[/bold red] {error_msg}")
                    else:
                        progress.log(f"[bold red]😥 Gagal:[/bold red] {error_msg}")
                else:
                    successful_purchases.append(
                        f"{target_variant['name']}|{option_order}. {option_name} - {option_price}"
                    )
                    progress.log(f"[bold green]🎉 Berhasil![/bold green] (Pembelian {i+1})")
                    if pause_on_success: pause()
            except Exception as e:
                progress.log(f"[bold red]Exception terjadi saat membuat order: {e}[/bold red]")
                res = None
            
            progress.update(task, advance=1)

            if delay_seconds > 0 and i < n - 1:
                progress.log(f"[cyan]Menunggu {delay_seconds} detik sebelum lanjut...[/cyan]")
                time.sleep(delay_seconds)
    
    # --- Laporan Akhir yang Manis ---
    summary_text = Text(f"Paket: {family_name} | {target_variant['name']} | {option_name}\n", justify="center")
    summary_text.append(f"Target Pembelian: {n} kali\n", style="dim")
    summary_text.append(f"Total Berhasil: {len(successful_purchases)} kali\n\n", style="bold")

    if len(successful_purchases) > 0:
        summary_text.append(f"Hore! Berhasil {len(successful_purchases)}/{n} pembelian!", style="bold green")
    else:
        summary_text.append("Sayang sekali, tidak ada pembelian yang berhasil. 😔", style="bold red")

    console.print(Panel(
        summary_text,
        title="✨ Laporan Misi Selesai ✨",
        border_style="bold blue",
        padding=(1, 2)
    ))
    pause()
    return True

