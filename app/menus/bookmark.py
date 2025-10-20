# Impor library standar aplikasi Anda
from app.menus.package import show_package_details
from app.service.auth import AuthInstance
from app.service.bookmark import BookmarkInstance
from app.client.engsel import get_family

# Impor library RICH untuk tampilan keren!
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt # Untuk input yang lebih baik

# Inisialisasi console Rich
console = Console()

def pause():
    """Fungsi helper untuk menjeda layar, versi Rich."""
    console.input("\n[italic dim]Tekan [Enter] untuk melanjutkan...[/italic dim]")

def show_bookmark_menu():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    
    in_bookmark_menu = True
    while in_bookmark_menu:
        # Gunakan console.clear() dari Rich
        console.clear()

        # Gunakan Panel untuk judul yang keren
        console.print(Panel(
            "[bold cyan]🌟 Bookmark Paket Favoritmu 🌟[/bold cyan]",
            title="Menu Bookmark",
            subtitle="Pilih paket andalanmu dengan cepat!",
            expand=False,
            border_style="magenta"
        ))
        
        bookmarks = BookmarkInstance.get_bookmarks()
        if not bookmarks or len(bookmarks) == 0:
            console.print("\n[bold yellow]Wah, kamu belum punya bookmark. 💔[/bold yellow]")
            console.print("Kamu bisa menambahkan bookmark dari menu pembelian paket.")
            pause()
            return None
        
        console.print("\n[bold]Ini dia daftar paket andalanmu:[/bold]\n")
        for idx, bm in enumerate(bookmarks):
            # Gunakan objek Text untuk mencampur gaya
            text = Text()
            text.append(f"{idx + 1}. ", style="bold green")
            text.append(f"{bm['family_name']} ", style="cyan")
            text.append("-> ", style="dim")
            text.append(f"{bm['variant_name']} ", style="bold magenta")
            text.append(f"({bm['option_name']})", style="yellow")
            console.print(text)
        
        # Opsi menu yang lebih rapi
        console.print("\n" + "—" * 50)
        console.print("[bold yellow]00.[/bold yellow]  Kembali ke Menu Utama")
        console.print("[bold red]000.[/bold red] Hapus Bookmark")
        console.print("—" * 50)
        
        # Gunakan Prompt dari Rich untuk input
        choice = Prompt.ask("[bold]Silakan pilih paket (nomor) [/bold]")

        if choice == "00":
            console.print("\n[italic blue]Oke, sampai jumpa lagi! 👋[/italic blue]")
            in_bookmark_menu = False
            return None
        elif choice == "000":
            del_choice = Prompt.ask("[bold yellow]Masukkan nomor bookmark yang ingin dihapus: [/bold yellow]")
            if del_choice.isdigit() and 1 <= int(del_choice) <= len(bookmarks):
                del_bm = bookmarks[int(del_choice) - 1]
                
                # Tambahkan konfirmasi
                konfirmasi = Prompt.ask(
                    f"Yakin ingin menghapus '[italic]{del_bm['variant_name']}[/italic]'? (y/n)", 
                    choices=["y", "n"], 
                    default="n"
                )
                
                if konfirmasi.lower() == 'y':
                    BookmarkInstance.remove_bookmark(
                        del_bm["family_code"],
                        del_bm["is_enterprise"],
                        del_bm["variant_name"],
                        del_bm["order"],
                    )
                    console.print(f"\n[bold green]Sukses![/bold green] Bookmark '[italic]{del_bm['variant_name']}[/italic]' telah dihapus.")
                else:
                    console.print("\n[italic]Penghapusan dibatalkan.[/italic]")
                pause()
            else:
                console.print("\n[bold red]Input tidak valid.[/bold red] Mohon masukkan nomor yang ada di daftar.")
                pause()
            continue
            
        if choice.isdigit() and 1 <= int(choice) <= len(bookmarks):
            selected_bm = bookmarks[int(choice) - 1]
            family_code = selected_bm["family_code"]
            is_enterprise = selected_bm["is_enterprise"]
            
            # --- Ini adalah "PROSES" yang diubah ---
            # Gunakan 'status' untuk menampilkan spinner loading
            family_data = None
            with console.status("[bold green]Mencari data paket pilihanmu, mohon tunggu...[/bold green]", spinner="dots4") as status:
                family_data = get_family(api_key, tokens, family_code, is_enterprise)
                if not family_data:
                    status.stop()
                    console.print("\n[bold red]Oops! Gagal mengambil data paket. 😵[/bold red]")
                    console.print("Mungkin ada gangguan jaringan. Coba lagi nanti ya.")
                    pause()
                    continue
            
            # Jika berhasil, data diproses di sini
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
                console.print(f"\n[bold green]Paket ditemukan![/bold green] (Kode: {option_code})")
                console.print("Mempersiapkan detail paket untukmu...")
                pause()
                # Panggil fungsi detail (diasumsikan sudah rapi juga)
                show_package_details(api_key, tokens, option_code, is_enterprise)            
            else:
                # Menangani jika bookmark ada tapi data API tidak valid
                console.print("\n[bold red]Error aneh terjadi.[/bold red]")
                console.print("Bookmark-mu tersimpan, tapi data paket tidak ditemukan di server.")
                pause()
            
        else:
            console.print("\n[bold red]Pilihan tidak dikenal.[/bold red] Mohon masukkan nomor yang benar dari daftar.")
            pause()
            continue

