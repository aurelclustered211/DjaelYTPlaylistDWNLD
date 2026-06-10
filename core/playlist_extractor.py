import re
import yt_dlp
from SpotipyFree import Spotify

def detect_platform(url):
    """
    Detects the platform of the playlist from the URL.
    Returns: 'Spotify', 'SoundCloud', 'Apple Music', 'Deezer', 'YouTube Music', 'YouTube', or 'Unknown'.
    """
    url_lower = url.lower().strip()
    if "spotify.com" in url_lower or url_lower.startswith("spotify:"):
        return "Spotify"
    elif "soundcloud.com" in url_lower:
        return "SoundCloud"
    elif "apple.com" in url_lower or "music.apple.com" in url_lower:
        return "Apple Music"
    elif "deezer.com" in url_lower:
        return "Deezer"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        if "music.youtube.com" in url_lower:
            return "YouTube Music"
        return "YouTube"
    return "Unknown"

def extract_playlist_id(url_or_id):
    """
    Extracts the playlist ID from a Spotify playlist URL or returns it directly.
    """
    url_or_id = url_or_id.strip()
    
    # Check for URI format spotify:playlist:ID
    if url_or_id.startswith("spotify:playlist:"):
        return url_or_id.split(":")[-1]
        
    # Check for URL format
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url_or_id)
    if match:
        return match.group(1)
        
    return url_or_id

def get_spotify_client(client_id=None, client_secret=None):
    """
    Returns a SpotipyFree.Spotify client.
    """
    return Spotify()

def get_spotify_playlist_tracks(sp, playlist_id):
    """
    Fetches all tracks from a Spotify playlist with full pagination.
    """
    tracks = []
    try:
        results = sp.playlist_items(
            playlist_id,
            fields="items(track(name,duration_ms,is_local,uri,artists(name),album(name,images))),next",
            additional_types=("track",)
        )
    except Exception as e:
        raise Exception(f"Failed to fetch Spotify playlist items: {str(e)}")
        
    if not results:
        return tracks
        
    def process_items(items):
        for item in items:
            if not item or not item.get("track"):
                continue
            track = item["track"]
            
            if track.get("is_local") or (track.get("uri") and track["uri"].startswith("spotify:local")):
                continue
                
            name = track.get("name")
            if not name:
                continue
                
            artists_list = track.get("artists", [])
            if not artists_list:
                continue
                
            artists = [a.get("name") for a in artists_list if a.get("name")]
            if not artists:
                continue
                
            primary_artist = artists[0]
            all_artists_str = ", ".join(artists)
            album_name = track.get("album", {}).get("name", "Unknown Album")
            
            duration_ms = track.get("duration_ms", 0)
            duration_sec = duration_ms / 1000.0
            
            images = track.get("album", {}).get("images", [])
            cover_url = images[0].get("url") if images else None
            
            tracks.append({
                "title": name,
                "primary_artist": primary_artist,
                "all_artists": all_artists_str,
                "album": album_name,
                "duration_ms": duration_ms,
                "duration_sec": duration_sec,
                "cover_url": cover_url
            })
            
    process_items(results.get("items", []))
    
    while results.get("next"):
        try:
            results = sp.next(results)
            if results:
                process_items(results.get("items", []))
            else:
                break
        except Exception as e:
            print(f"Error paginating Spotify playlist items: {e}")
            break
            
    return tracks

def get_yt_dlp_playlist_tracks(url):
    """
    Fetches playlist tracks from platforms like YouTube, SoundCloud, Deezer, Apple Music, etc.
    Uses yt-dlp flat extraction.
    """
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    tracks = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    if not info:
        raise ValueError("Could not extract playlist information.")
        
    entries = info.get("entries", [])
    for entry in entries:
        if not entry:
            continue
            
        title = entry.get("title", "Unknown Title")
        artist = entry.get("artist") or entry.get("uploader") or entry.get("channel") or "Unknown Artist"
        
        # Heuristic: split artist and title if title is in "Artist - Title" format
        if " - " in title:
            parts = title.split(" - ", 1)
            possible_artist = parts[0].strip()
            possible_title = parts[1].strip()
            if possible_artist and possible_title:
                artist = possible_artist
                title = possible_title
                
        duration_sec = entry.get("duration", 0)
        duration_ms = duration_sec * 1000.0
        
        cover_url = entry.get("thumbnail")
        if not cover_url and entry.get("thumbnails"):
            cover_url = entry.get("thumbnails")[0].get("url")
            
        album = entry.get("album") or "Unknown Album"
        
        tracks.append({
            "title": title,
            "primary_artist": artist,
            "all_artists": artist,
            "album": album,
            "duration_ms": duration_ms,
            "duration_sec": duration_sec,
            "cover_url": cover_url
        })
        
    return tracks

def get_playlist_tracks_general(url_or_id, client_id=None, client_secret=None):
    """
    Extracts tracks from any supported platform playlist.
    """
    platform = detect_platform(url_or_id)
    if platform == "Spotify":
        sp = get_spotify_client(client_id, client_secret)
        playlist_id = extract_playlist_id(url_or_id)
        return get_spotify_playlist_tracks(sp, playlist_id)
    else:
        # Fallback to general yt-dlp extraction for SoundCloud, YouTube, Deezer, Apple Music, etc.
        return get_yt_dlp_playlist_tracks(url_or_id)
