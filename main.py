import os
import sys
import threading
import queue
import argparse
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Adjust sys.path to find core packages if run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import load_config, save_config, get_resource_path
from core.orchestrator import orchestrate_download

class DjaelYTPlaylistDWNLD(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load local configuration (from Windows Temp)
        self.config = load_config()
        
        # Appearance config
        theme = self.config.get("theme", "Dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("green")  # Spotify green vibe
        
        # Window configuration
        self.title("DjaelYTPlaylistDWNLD")
        self.geometry("780x620")
        self.resizable(True, True)
        self.minsize(700, 560)
        
        # Set app window icon
        logo_ico = get_resource_path("logo.ico")
        logo_png = get_resource_path("logo.png")
        if os.path.exists(logo_ico):
            try:
                self.iconbitmap(logo_ico)
            except Exception:
                pass
        elif os.path.exists(logo_png):
            try:
                from PIL import Image, ImageTk
                icon_image = ImageTk.PhotoImage(Image.open(logo_png))
                self.iconphoto(False, icon_image)
            except Exception:
                pass
                
        # Queue for background thread communication
        self.gui_queue = queue.Queue()
        self.download_thread = None
        self.stop_requested = False
        self.last_detected_platform = None
        
        self.build_ui()
        self.load_settings_into_ui()
        
        # Start checking the message queue
        self.after(100, self.check_queue)
        
    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header title
        header = ctk.CTkLabel(
            self, 
            text="DjaelYTPlaylistDWNLD", 
            font=("Segoe UI", 24, "bold"),
            text_color="#1DB954"
        )
        header.grid(row=0, column=0, pady=(15, 5), sticky="n")
        
        # Minimalist Tab View
        self.tabview = ctk.CTkTabview(
            self, 
            segmented_button_selected_color="#1DB954", 
            segmented_button_selected_hover_color="#1aa34a"
        )
        self.tabview.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")
        
        self.tabview.add("Downloader")
        self.tabview.add("Settings")
        
        self.build_downloader_tab(self.tabview.tab("Downloader"))
        self.build_settings_tab(self.tabview.tab("Settings"))
        
    def build_downloader_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(4, weight=1)  # Log box row takes available height
        
        # Playlist URL Input
        ctk.CTkLabel(tab, text="Playlist URL/ID:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.playlist_entry = ctk.CTkEntry(tab, placeholder_text="Enter Spotify, SoundCloud, YouTube, Deezer, or Apple Music link", font=("Segoe UI", 11))
        self.playlist_entry.grid(row=0, column=1, columnspan=2, padx=(0, 15), pady=10, sticky="ew")
        self.playlist_entry.bind("<KeyRelease>", self.on_playlist_input_changed)
        
        # Output directory
        ctk.CTkLabel(tab, text="Output Folder:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.dest_entry = ctk.CTkEntry(tab, placeholder_text="Select directory to store MP3s", font=("Segoe UI", 11))
        self.dest_entry.grid(row=1, column=1, padx=(0, 5), pady=10, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            tab, 
            text="Browse", 
            width=90, 
            fg_color="#1DB954", 
            hover_color="#1aa34a",
            command=self.browse_directory
        )
        browse_btn.grid(row=1, column=2, padx=(0, 15), pady=10, sticky="e")
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        self.start_btn = ctk.CTkButton(
            btn_frame, 
            text="Start Download", 
            font=("Segoe UI", 13, "bold"),
            fg_color="#1DB954", 
            hover_color="#1aa34a",
            height=35,
            command=self.start_extraction
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            btn_frame, 
            text="Stop Process", 
            font=("Segoe UI", 13, "bold"),
            fg_color="#A31A1A", 
            hover_color="#7A1313",
            state="disabled",
            height=35,
            command=self.request_stop
        )
        self.stop_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Progress section
        progress_frame = ctk.CTkFrame(tab, fg_color="transparent")
        progress_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(progress_frame, text="Ready.", font=("Segoe UI", 12, "bold"))
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=8, progress_color="#1DB954")
        self.progress_bar.grid(row=1, column=0, pady=(5, 5), sticky="ew")
        self.progress_bar.set(0.0)
        
        # Console output / logs
        self.log_box = ctk.CTkTextbox(tab, font=("Consolas", 11), fg_color="#121212", text_color="#E0E0E0")
        self.log_box.grid(row=4, column=0, columnspan=3, padx=15, pady=(5, 15), sticky="nsew")
        self.log_box.configure(state="disabled")
        
    def build_settings_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)
        
        # Theme Selector
        ctk.CTkLabel(tab, text="Interface Theme:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.theme_combo = ctk.CTkComboBox(
            tab, 
            values=["System", "Dark", "Light"], 
            font=("Segoe UI", 11),
            command=self.change_theme
        )
        self.theme_combo.grid(row=0, column=1, padx=15, pady=15, sticky="w")
        
        # Quality Selector
        ctk.CTkLabel(tab, text="Preferred Quality (Bitrate):", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=15, sticky="w")
        self.quality_combo = ctk.CTkComboBox(
            tab, 
            values=["320", "256", "192", "128"], 
            font=("Segoe UI", 11),
            command=self.save_settings_from_gui
        )
        self.quality_combo.grid(row=1, column=1, padx=15, pady=15, sticky="w")
        
        # Custom Spotify Credentials Frame
        credentials_frame = ctk.CTkFrame(tab)
        credentials_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=15, sticky="ew")
        credentials_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            credentials_frame, 
            text="Optional Custom Spotify API Credentials", 
            font=("Segoe UI", 13, "bold"), 
            text_color="#1DB954"
        ).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        
        ctk.CTkLabel(credentials_frame, text="Client ID:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.client_id_entry = ctk.CTkEntry(credentials_frame, placeholder_text="Enter custom Client ID (optional)", font=("Segoe UI", 11))
        self.client_id_entry.grid(row=1, column=1, padx=(0, 15), pady=5, sticky="ew")
        self.client_id_entry.bind("<KeyRelease>", lambda event: self.save_settings_from_gui())
        
        ctk.CTkLabel(credentials_frame, text="Client Secret:", font=("Segoe UI", 12)).grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.client_secret_entry = ctk.CTkEntry(credentials_frame, placeholder_text="Enter custom Client Secret (optional)", show="*", font=("Segoe UI", 11))
        self.client_secret_entry.grid(row=2, column=1, padx=(0, 15), pady=5, sticky="ew")
        self.client_secret_entry.bind("<KeyRelease>", lambda event: self.save_settings_from_gui())
        
        # Logo display
        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                from PIL import Image
                logo_img = ctk.CTkImage(Image.open(logo_path), size=(60, 60))
                logo_label = ctk.CTkLabel(tab, image=logo_img, text="")
                logo_label.grid(row=3, column=0, columnspan=2, pady=10)
            except Exception:
                pass
                
        # Credits
        credits_label = ctk.CTkLabel(
            tab, 
            text="Developer: djael-ml | GitHub: github.com/djael-ml", 
            font=("Segoe UI", 11, "italic"),
            text_color="#888888"
        )
        credits_label.grid(row=4, column=0, columnspan=2, pady=(10, 15))
        
    def load_settings_into_ui(self):
        if self.config.get("spotify_client_id"):
            self.client_id_entry.insert(0, self.config["spotify_client_id"])
        if self.config.get("spotify_client_secret"):
            self.client_secret_entry.insert(0, self.config["spotify_client_secret"])
        if self.config.get("output_directory"):
            self.dest_entry.insert(0, self.config["output_directory"])
            
        quality = self.config.get("preferred_quality", "320")
        if quality in ["320", "256", "192", "128"]:
            self.quality_combo.set(quality)
            
        theme = self.config.get("theme", "Dark")
        if theme in ["System", "Dark", "Light"]:
            self.theme_combo.set(theme)
            
    def save_settings_from_gui(self, event=None):
        self.config["spotify_client_id"] = self.client_id_entry.get().strip()
        self.config["spotify_client_secret"] = self.client_secret_entry.get().strip()
        self.config["output_directory"] = self.dest_entry.get().strip()
        self.config["preferred_quality"] = self.quality_combo.get()
        self.config["theme"] = self.theme_combo.get()
        save_config(self.config)
        
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.save_settings_from_gui()
        
    def browse_directory(self):
        selected = filedialog.askdirectory()
        if selected:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, selected)
            self.save_settings_from_gui()
            
    def on_playlist_input_changed(self, event=None):
        url = self.playlist_entry.get().strip()
        if not url:
            return
        from core.playlist_extractor import detect_platform
        platform = detect_platform(url)
        if platform != "Unknown" and platform != self.last_detected_platform:
            self.last_detected_platform = platform
            self.append_log(f"[PLATFORM] Detected playlist platform: {platform}")
            
    def append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        
    def request_stop(self):
        if self.download_thread and self.download_thread.is_alive():
            self.stop_requested = True
            self.append_log("[INFO] Requesting download cancellation... Finalizing current track.")
            self.status_label.configure(text="Cancelling...")
            self.stop_btn.configure(state="disabled")
            
    def start_extraction(self):
        playlist_url = self.playlist_entry.get().strip()
        output_dir = self.dest_entry.get().strip()
        preferred_quality = self.quality_combo.get()
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()
        
        if not playlist_url:
            messagebox.showerror("Validation Error", "Please provide a Spotify playlist URL or ID.")
            return
            
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showerror("Validation Error", "Selected output directory is invalid.")
            return
            
        ffmpeg_exe = get_resource_path("ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            messagebox.showerror(
                "FFmpeg Missing", 
                "ffmpeg.exe was not found. Please run the 'download_ffmpeg.py' script first."
            )
            return
            
        self.save_settings_from_gui()
        
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0.0)
        self.status_label.configure(text="Initializing extraction...")
        
        self.log_box.configure(state="normal")
        self.log_box.delete("0.0", "end")
        self.log_box.configure(state="disabled")
        
        self.append_log("[START] Initializing DjaelYTPlaylistDWNLD extraction process...")
        self.stop_requested = False
        
        self.download_thread = threading.Thread(
            target=self.run_download_orchestrator,
            args=(playlist_url, output_dir, preferred_quality, client_id, client_secret),
            daemon=True
        )
        self.download_thread.start()
        
    def run_download_orchestrator(self, playlist_url, output_dir, bitrate, client_id, client_secret):
        def log_cb(msg):
            self.gui_queue.put({"type": "log", "content": msg})
            
        def progress_cb(index, total, status, percent):
            overall = (index + percent) / total if total > 0 else 0.0
            self.gui_queue.put({"type": "progress", "value": overall, "status": status})
            
        def stop_check_cb():
            return self.stop_requested
            
        try:
            success = orchestrate_download(
                playlist_url=playlist_url,
                output_dir=output_dir,
                bitrate=bitrate,
                client_id=client_id if client_id else None,
                client_secret=client_secret if client_secret else None,
                log_cb=log_cb,
                progress_cb=progress_cb,
                stop_check_cb=stop_check_cb
            )
            if success:
                self.gui_queue.put({"type": "finish"})
            else:
                self.gui_queue.put({"type": "stopped"})
        except Exception as e:
            self.gui_queue.put({"type": "error", "content": str(e)})
            
    def check_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                msg_type = msg.get("type")
                
                if msg_type == "log":
                    self.append_log(msg["content"])
                elif msg_type == "progress":
                    self.progress_bar.set(msg["value"])
                    self.status_label.configure(text=msg["status"])
                elif msg_type == "finish":
                    self.status_label.configure(text="Finished successfully!")
                    self.progress_bar.set(1.0)
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.append_log("[END] Extraction completed successfully.")
                    messagebox.showinfo("Success", "Spotify playlist extraction completed!")
                elif msg_type == "error":
                    self.status_label.configure(text="Extraction failed.")
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.append_log(f"[FATAL ERROR] {msg['content']}")
                    messagebox.showerror("Error", f"Process failed: {msg['content']}")
                elif msg_type == "stopped":
                    self.status_label.configure(text="Cancelled.")
                    self.progress_bar.set(0.0)
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.append_log("[STOP] Extraction process cancelled by user.")
                    messagebox.showwarning("Cancelled", "Process was stopped.")
                    
                self.gui_queue.task_done()
        except queue.Empty:
            pass
            
        self.after(100, self.check_queue)

def attach_to_console():
    """Attaches stdout and stderr streams to the parent console on Windows."""
    if sys.platform == "win32":
        import ctypes
        try:
            # Attach to parent process console
            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        except Exception:
            pass

def run_cli(args):
    """Executes the downloader in headless CLI mode."""
    attach_to_console()
    if not args.playlist:
        print("Error: Spotify playlist URL or ID must be specified using --playlist or -p.")
        sys.exit(1)
        
    if not args.output:
        print("Error: Output directory must be specified using --output or -o.")
        sys.exit(1)
        
    if not os.path.isdir(args.output):
        print(f"Error: Output directory '{args.output}' does not exist.")
        sys.exit(1)
        
    ffmpeg_exe = get_resource_path("ffmpeg.exe")
    if not os.path.exists(ffmpeg_exe):
        print(f"Error: FFmpeg was not found at '{ffmpeg_exe}'. Please run 'download_ffmpeg.py' first.")
        sys.exit(1)
        
    print("DjaelYTPlaylistDWNLD (CLI Mode)")
    print(f"Playlist: {args.playlist}")
    print(f"Output Directory: {args.output}")
    print(f"Preferred Quality: {args.quality} kbps")
    print("Starting download process...\n")
    
    # Load optional API config
    config = load_config()
    client_id = config.get("spotify_client_id")
    client_secret = config.get("spotify_client_secret")
    
    try:
        success = orchestrate_download(
            playlist_url=args.playlist,
            output_dir=args.output,
            bitrate=args.quality,
            client_id=client_id if client_id else None,
            client_secret=client_secret if client_secret else None
        )
        if success:
            print("\nDownload process completed successfully!")
        else:
            print("\nDownload process was interrupted.")
    except Exception as e:
        print(f"\nFatal Error: {e}")
        sys.exit(1)

def run_gui():
    """Executes the application in windowed GUI mode."""
    app = DjaelYTPlaylistDWNLD()
    app.mainloop()

def main():
    parser = argparse.ArgumentParser(description="DjaelYTPlaylistDWNLD - Spotify to MP3 Downloader")
    parser.add_argument("--playlist", "-p", help="Spotify playlist URL or ID")
    parser.add_argument("--output", "-o", help="Output directory path to store downloaded MP3s")
    parser.add_argument("--quality", "-q", choices=["320", "256", "192", "128"], default="320", help="Preferred download quality in kbps")
    parser.add_argument("--cli", action="store_true", help="Force CLI execution mode (run headlessly)")
    args = parser.parse_args()
    
    # Run in CLI mode if forced or if arguments are supplied
    if args.cli or args.playlist or args.output:
        run_cli(args)
    else:
        run_gui()

if __name__ == "__main__":
    main()
