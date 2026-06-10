# DjaelYTPlaylistDWNLD

A sleek, portable, and zero-configuration playlist downloader that extracts and saves tracks as high-quality MP3s by matching audio on YouTube Music and downloading via `yt-dlp`.

It supports extracting playlists from **Spotify, SoundCloud, Apple Music, Deezer, YouTube Music, and YouTube**, and runs fully independently without requiring any Spotify Developer API credentials, Premium subscriptions, or complicated user configurations.

Developed by **djael-ml** (GitHub: [github.com/djael-ml](https://github.com/djael-ml)).

---

## Features

- **Multi-Platform Support**: Extract and download playlists from Spotify, SoundCloud, Apple Music, Deezer, YouTube Music, and YouTube.
- **No API Credentials Required**: Built-in unauthenticated Spotify Web API bypass.
- **Live Platform Detection**: Instantly detects and prints the source platform in the logs in real time as soon as you paste the URL.
- **Smart Duplicate Matching**: Automatically scans your target output folder, checks ID3 tags (or filenames) of existing tracks, and compares bitrates.
- **Dynamic Quality Upgrades**: If a local file has a lower bitrate than your target quality (e.g. 128 kbps vs 320 kbps), it is automatically replaced. Otherwise, the track is skipped to save bandwidth.
- **Modern Minimalist GUI**: Fully custom interface with Light/Dark/System theme selector, Settings tab, progress indicators, and an embedded log window.
- **Dual Mode (GUI & CLI)**: Can be run as a windowed desktop app or headlessly from the command line.
- **ID3 Metadata Integration**: Automatically injects artist names, track title, album name, and front-cover artwork into downloaded MP3s.

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/djael-ml/DjaelYTPlaylistDWNLD.git
   cd DjaelYTPlaylistDWNLD
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Acquire FFmpeg Binaries**:
   Download and unpack the required `ffmpeg.exe` and `ffprobe.exe` binaries into the root directory:
   ```bash
   python download_ffmpeg.py
   ```

---

## Usage

### 1. GUI Mode (Default)
Double-click the compiled executable or run:
```bash
python main.py
```
This opens the windowed application with two tabs:
- **Downloader**: Paste any playlist URL or ID, select the output folder, and start the extraction.
- **Settings**: Change the appearance theme (Dark / Light / System), target quality bitrate, and configure optional Spotify credentials if you prefer to use your own Developer Client ID.

*Note: The configuration file is stored cleanly in Windows temporary files (`%TEMP%\DjaelYTPlaylistDWNLD_config.json`).*

### 2. CLI Mode (Headless)
Run the application with parameters in your console to execute headlessly:
```bash
python main.py --playlist "PLAYLIST_URL_OR_ID" --output "C:\Path\To\Save\Music" --quality 320
```

#### CLI Parameters:
- `--playlist`, `-p` (Required): Playlist URL or Spotify unique ID.
- `--output`, `-o` (Required): Path to the folder where MP3 files will be stored.
- `--quality`, `-q` (Optional): Target quality in kbps. Choose from `320`, `256`, `192`, or `128` (Default is `320`).
- `--cli` (Optional): Forces headless console mode even if other arguments are omitted.

---

## Building Standalone Executable

To compile DjaelYTPlaylistDWNLD into a single executable `.exe` containing all DLLs and data assets, use PyInstaller:
```bash
.venv\Scripts\pyinstaller.exe DjaelYTPlaylistDWNLD.spec --clean
```
The standalone executable will be generated at `dist/DjaelYTPlaylistDWNLD.exe`.
