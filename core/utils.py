import os
import sys
import json
import re
import tempfile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Normal python execution: project root folder (since utils.py is in core/)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_config_path():
    """
    Get path to the config file stored in the Windows temp directory.
    """
    return os.path.join(tempfile.gettempdir(), "DjaelYTPlaylistDWNLD_config.json")

def load_config():
    """
    Load settings from config.json.
    """
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "spotify_client_id": "",
        "spotify_client_secret": "",
        "output_directory": "",
        "preferred_quality": "320"
    }

def save_config(config):
    """
    Save settings to config.json.
    """
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def levenshtein_distance(s1, s2):
    """
    Compute the Levenshtein distance between two strings.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def get_similarity_ratio(s1, s2):
    """
    Compute similarity ratio between two strings using Levenshtein distance.
    Returns a float between 0.0 and 1.0.
    """
    if not s1 or not s2:
        return 0.0
    s1 = s1.strip().lower()
    s2 = s2.strip().lower()
    dist = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - (dist / max_len)

def clean_text(text):
    """
    Cleans track titles by converting to lowercase, removing common suffixes
    (e.g., remastered, radio edit, feat), and removing non-word characters.
    """
    if not text:
        return ""
    text = text.lower()
    # Remove contents inside parentheses/brackets containing common suffixes
    text = re.sub(r"\s*[\(\[][^\]\)]*(remaster|edit|version|mix|live|mono|stereo|single|feat|ft|lyrics|official)[^\]\)]*[\)\]]", "", text)
    # Remove common standalone suffix patterns
    text = re.sub(r"\s*-\s*(remastered|radio edit|official video|video|single version|mix).*", "", text)
    # Remove non-alphanumeric/non-space chars
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse double spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def scan_local_mp3s(directory):
    """
    Scans the directory for all .mp3 files and extracts their title, artist, and bitrate.
    Returns a list of dictionaries with:
    {
        'filepath': str,
        'title': str,
        'artist': str,
        'bitrate': int
    }
    """
    local_tracks = []
    if not os.path.isdir(directory):
        return local_tracks
        
    for filename in os.listdir(directory):
        if not filename.lower().endswith(".mp3"):
            continue
            
        filepath = os.path.join(directory, filename)
        title = ""
        artist = ""
        bitrate = 0
        
        try:
            audio = MP3(filepath)
            # Get bitrate
            if audio.info and audio.info.bitrate:
                bitrate = audio.info.bitrate // 1000  # In kbps
                
            # Get ID3 tags
            if audio.tags:
                if 'TIT2' in audio.tags:
                    title = str(audio.tags['TIT2'])
                if 'TPE1' in audio.tags:
                    artist = str(audio.tags['TPE1'])
        except Exception:
            pass
            
        # Fallback to filename parsing if ID3 tags are missing or empty
        if not title or not artist:
            # Assumes format: "Artist - Title.mp3" or similar
            name_without_ext = os.path.splitext(filename)[0]
            parts = name_without_ext.split(" - ", 1)
            if len(parts) == 2:
                if not artist:
                    artist = parts[0].strip()
                if not title:
                    title = parts[1].strip()
            else:
                if not title:
                    title = name_without_ext.strip()
                    
        local_tracks.append({
            'filepath': filepath,
            'title': title,
            'artist': artist,
            'bitrate': bitrate
        })
        
    return local_tracks
