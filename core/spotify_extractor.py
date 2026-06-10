import re

def extract_playlist_id(url_or_id):
    """
    Extracts the playlist ID from a Spotify playlist URL or returns it directly if it's already an ID.
    Supports formats like:
    - https://open.spotify.com/playlist/37i9dQZF1DXcBWIGo3712j?si=abc...
    - spotify:playlist:37i9dQZF1DXcBWIGo3712j
    - 37i9dQZF1DXcBWIGo3712j
    """
    url_or_id = url_or_id.strip()
    
    # Check for URI format spotify:playlist:ID
    if url_or_id.startswith("spotify:playlist:"):
        return url_or_id.split(":")[-1]
        
    # Check for URL format
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url_or_id)
    if match:
        return match.group(1)
        
    # Assume it's a raw ID if no pattern matched
    return url_or_id

def get_spotify_client(client_id=None, client_secret=None):
    """
    Instantiates and returns a SpotipyFree.Spotify client.
    """
    from SpotipyFree import Spotify
    return Spotify()

def get_playlist_tracks(sp, playlist_id):
    """
    Fetches all tracks from a Spotify playlist with full pagination.
    Returns a list of structured dictionaries for valid, non-local tracks.
    """
    tracks = []
    
    try:
        # Initial request
        results = sp.playlist_items(
            playlist_id,
            fields="items(track(name,duration_ms,is_local,uri,artists(name),album(name,images))),next",
            additional_types=("track",)
        )
    except Exception as e:
        raise Exception(f"Failed to fetch playlist items: {str(e)}")
        
    if not results:
        return tracks
        
    # Function to process a page of items
    def process_items(items):
        for item in items:
            if not item or not item.get("track"):
                continue
                
            track = item["track"]
            
            # Skip local files and null entries
            if track.get("is_local") or (track.get("uri") and track["uri"].startswith("spotify:local")):
                continue
                
            # Basic info
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
            
            # Duration in ms and seconds
            duration_ms = track.get("duration_ms", 0)
            duration_sec = duration_ms / 1000.0
            
            # Cover Art URL (first image is usually the highest resolution)
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
            
    # Process first page
    process_items(results.get("items", []))
    
    # Process remaining pages using pagination (next page URL)
    while results.get("next"):
        try:
            results = sp.next(results)
            if results:
                process_items(results.get("items", []))
            else:
                break
        except Exception as e:
            # If a page fails, log it and break to return what we have so far
            print(f"Error paginating playlist items: {e}")
            break
            
    return tracks
