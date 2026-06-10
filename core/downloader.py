import os
import yt_dlp
import re
import unicodedata
from core.utils import get_resource_path

def sanitize_filename(name):
    """
    Remove invalid characters for Windows filenames and transliterate
    non-ASCII characters to their closest ASCII equivalents.
    """
    # Windows invalid chars: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    # Transliterate Unicode → closest ASCII (e.g. ū → u, é → e)
    nfkd = unicodedata.normalize('NFKD', sanitized)
    ascii_safe = nfkd.encode('ascii', 'ignore').decode('ascii')
    # If transliteration emptied the string entirely, keep original minus bad chars
    if not ascii_safe.strip():
        ascii_safe = sanitized
    # Strip leading/trailing spaces and dots
    return ascii_safe.strip().strip('.')

def download_track(video_id, output_dir, track_index, track_title, preferred_quality, progress_callback):
    """
    Downloads a YouTube audio stream and transcodes it to MP3.
    Uses a temporary file name based on video_id to avoid conflicts,
    which is later renamed by the orchestrator after tagging.
    
    Returns: The path to the temporary MP3 file, or raises an Exception.
    """
    # Find ffmpeg binary folder
    ffmpeg_exe = get_resource_path("ffmpeg.exe")
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    
    # Check that ffmpeg exists
    if not os.path.exists(ffmpeg_exe):
        raise FileNotFoundError(
            f"ffmpeg.exe not found at {ffmpeg_exe}. Please run download_ffmpeg.py first."
        )

    # Temporary name schema in the destination folder
    temp_filename = f"djaelyt_temp_{video_id}"
    temp_outtmpl = os.path.join(output_dir, f"{temp_filename}.%(ext)s")
    
    # Progress hook closure
    def ydl_progress_hook(d):
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', '0.0%').strip()
            # Clean ANSI sequences from string
            clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '')
            try:
                percent = float(clean_percent) / 100.0
            except ValueError:
                percent = 0.0
                
            speed_str = d.get('_speed_str', 'N/A').strip()
            clean_speed = re.sub(r'\x1b\[[0-9;]*m', '', speed_str)
            
            progress_callback(track_index, track_title, "downloading", percent, clean_speed)
            
        elif d['status'] == 'finished':
            progress_callback(track_index, track_title, "converting", 1.0, "")

    # yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_outtmpl,
        'ffmpeg_location': ffmpeg_dir,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [ydl_progress_hook],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': str(preferred_quality),
        }],
    }
    
    # Download and transcode
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        # Clean up any partial files if they exist
        partial_path = os.path.join(output_dir, f"{temp_filename}.*")
        # In case yt-dlp left any traces, they will be cleaned up
        raise Exception(f"yt-dlp download failed: {str(e)}")
        
    # After successful conversion, the output file is temp_filename.mp3
    final_temp_mp3 = os.path.join(output_dir, f"{temp_filename}.mp3")
    
    if not os.path.exists(final_temp_mp3):
        raise FileNotFoundError(
            f"Expected output file not found: {final_temp_mp3}. Conversion may have failed."
        )
        
    return final_temp_mp3
