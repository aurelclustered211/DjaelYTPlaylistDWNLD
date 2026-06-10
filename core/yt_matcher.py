import re
from ytmusicapi import YTMusic
from core.utils import get_similarity_ratio, clean_text

# Global instance of YTMusic
_yt = None

def get_yt_client():
    global _yt
    if _yt is None:
        _yt = YTMusic()
    return _yt

def parse_duration_to_seconds(duration_str):
    """
    Parses a duration string (e.g. "3:45", "1:02:15") into seconds.
    """
    if not duration_str:
        return 0
    try:
        parts = str(duration_str).split(":")
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + int(part)
        return seconds
    except ValueError:
        return 0

def find_best_match(spotify_track, similarity_threshold=0.75, max_time_delta=4):
    """
    Searches YouTube Music for the Spotify track and applies double-factor verification.
    Returns: (videoId, match_status_message)
    """
    yt = get_yt_client()
    
    title = spotify_track["title"]
    artist = spotify_track["primary_artist"]
    spotify_duration = spotify_track["duration_sec"]
    
    # Formulate search query
    query = f"{artist} {title}"
    
    try:
        # Limit to 5 results as requested
        search_results = yt.search(query, filter="songs", limit=5)
    except Exception as e:
        return None, f"Search failed: {str(e)}"
        
    if not search_results:
        # Fallback search without filter in case no "songs" filter returns results
        try:
            search_results = yt.search(query, limit=5)
        except Exception:
            return None, "No results found on YouTube Music"
            
    if not search_results:
        return None, "No results found on YouTube"
        
    best_candidate = None
    best_similarity = 0.0
    
    for item in search_results:
        video_id = item.get("videoId")
        if not video_id:
            continue
            
        yt_title = item.get("title", "")
        
        # Get duration in seconds
        yt_duration = item.get("duration_seconds")
        if yt_duration is None:
            # Try to parse string duration
            yt_duration = parse_duration_to_seconds(item.get("duration", ""))
            
        # Get artist string (ytmusicapi returns artist list or dict)
        yt_artists = item.get("artists", [])
        yt_artist_name = ""
        if isinstance(yt_artists, list) and yt_artists:
            yt_artist_name = yt_artists[0].get("name", "")
        elif isinstance(yt_artists, dict):
            yt_artist_name = yt_artists.get("name", "")
            
        # 1. Calculate Title similarity on cleaned titles
        clean_sp_title = clean_text(title)
        clean_yt_title = clean_text(yt_title)
        
        title_similarity = get_similarity_ratio(clean_sp_title, clean_yt_title)
        
        # 2. Calculate time delta
        time_delta = abs(spotify_duration - yt_duration)
        
        # Check matching criteria
        has_good_similarity = (title_similarity >= similarity_threshold) or (clean_sp_title in clean_yt_title) or (clean_yt_title in clean_sp_title)
        has_good_duration = (time_delta <= max_time_delta)
        
        if has_good_similarity and has_good_duration:
            # We found a verified match!
            return video_id, f"Verified match (similarity={title_similarity:.2f}, delta={time_delta:.1f}s)"
            
        # Keep track of the best candidate so far as fallback
        # Score is combined similarity and duration match
        if title_similarity > best_similarity:
            best_similarity = title_similarity
            best_candidate = (video_id, yt_title, time_delta)
            
    # If no verified match found, fallback to best candidate if it's reasonably similar
    if best_candidate and best_similarity >= 0.50:
        video_id, yt_title, time_delta = best_candidate
        return video_id, f"Fallback match: '{yt_title}' (similarity={best_similarity:.2f}, delta={time_delta:.1f}s)"
        
    # Absolute fallback: first item
    first_item = search_results[0]
    first_video_id = first_item.get("videoId")
    first_title = first_item.get("title", "Unknown")
    return first_video_id, f"Unverified fallback match: '{first_title}' (first search result)"
