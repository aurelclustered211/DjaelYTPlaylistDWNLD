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

def get_soundcloud_playlist_tracks(url):
    """
    Fetches SoundCloud playlist tracks using yt-dlp flat extraction and
    SoundCloud v2 API batch track resolution. This is fast and resolves full metadata.
    """
    import urllib.request
    import json
    from urllib.parse import urlparse

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    if not info:
        raise ValueError("Could not extract SoundCloud playlist information.")
        
    entries = info.get("entries", [])
    playlist_title = info.get("title") or "Unknown Album"
    
    # If no entries are found or if it's a single track, try standard extraction
    if not entries:
        ydl_opts_single = {
            'extract_flat': False,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts_single) as ydl_s:
            single_info = ydl_s.extract_info(url, download=False)
        if single_info:
            title = single_info.get("title", "Unknown Title")
            artist = single_info.get("artist") or single_info.get("uploader") or "Unknown Artist"
            duration_sec = single_info.get("duration", 0)
            cover_url = single_info.get("thumbnail")
            album = single_info.get("album") or "Unknown Album"
            return [{
                "title": title,
                "primary_artist": artist,
                "all_artists": artist,
                "album": album,
                "duration_ms": duration_sec * 1000.0,
                "duration_sec": duration_sec,
                "cover_url": cover_url
            }]
        return []

    track_ids = []
    for entry in entries:
        if not entry:
            continue
        tid = entry.get("id")
        if tid:
            track_ids.append(str(tid))

    client_id = None
    try:
        ydl_sc = yt_dlp.YoutubeDL()
        sc_ie = ydl_sc.get_info_extractor('Soundcloud')
        sc_ie._update_client_id()
        client_id = sc_ie._CLIENT_ID
    except Exception as e:
        print(f"Warning: Failed to extract SoundCloud client_id: {e}")

    resolved_tracks = {}
    if client_id and track_ids:
        batch_size = 50
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i + batch_size]
            ids_str = ','.join(batch)
            api_url = f"https://api-v2.soundcloud.com/tracks?ids={ids_str}&client_id={client_id}"
            try:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    for track_data in res_json:
                        if isinstance(track_data, dict) and track_data.get("id"):
                            resolved_tracks[str(track_data["id"])] = track_data
            except Exception as e:
                print(f"Warning: Failed to fetch metadata batch {i//batch_size + 1}: {e}")

    tracks = []
    for entry in entries:
        if not entry:
            continue
            
        tid = str(entry.get("id", ""))
        track_data = resolved_tracks.get(tid)
        
        if track_data:
            title = track_data.get("title", "Unknown Title")
            user = track_data.get("user", {})
            artist = (track_data.get("publisher_metadata") or {}).get("artist") or user.get("username", "Unknown Artist")
            duration_ms = track_data.get("duration", 0)
            duration_sec = duration_ms / 1000.0
            
            cover_url = track_data.get("artwork_url") or user.get("avatar_url")
            if cover_url and "-large." in cover_url:
                cover_url = cover_url.replace("-large.", "-t500x500.")
                
            album = playlist_title
        else:
            title = entry.get("title", "Unknown Title")
            artist = entry.get("artist") or entry.get("uploader") or entry.get("channel") or "Unknown Artist"
            
            url = entry.get("url") or entry.get("webpage_url")
            if (artist == "Unknown Artist" or artist == "Tracks") and url:
                try:
                    parsed_url = urlparse(url)
                    path_parts = [p for p in parsed_url.path.split('/') if p]
                    if len(path_parts) >= 2 and path_parts[0] != "tracks":
                        artist_slug = path_parts[0].replace('-', ' ').replace('_', ' ').title()
                        track_slug = path_parts[1].replace('-', ' ').replace('_', ' ').title()
                        artist = artist_slug
                        if title == "Unknown Title" or title == track_slug or title.isdigit():
                            title = track_slug
                except Exception:
                    pass

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
                
            album = entry.get("album") or playlist_title
            
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
    elif platform == "SoundCloud":
        return get_soundcloud_playlist_tracks(url_or_id)
    else:
        # Fallback to general yt-dlp extraction for YouTube, Deezer, Apple Music, etc.
        return get_yt_dlp_playlist_tracks(url_or_id)
