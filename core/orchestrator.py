import os
from core.playlist_extractor import detect_platform, get_playlist_tracks_general
from core.yt_matcher import find_best_match
from core.downloader import download_track, sanitize_filename
from core.tagger import apply_metadata
from core.utils import scan_local_mp3s, clean_text, get_similarity_ratio

def orchestrate_download(playlist_url, output_dir, bitrate, client_id=None, client_secret=None, log_cb=None, progress_cb=None, stop_check_cb=None):
    """
    Orchestrates the playlist extraction, YouTube Music matching,
    audio downloading, and metadata tagging processes.
    
    Can be run from either GUI (background thread) or CLI (main thread).
    """
    def log(message):
        if log_cb:
            log_cb(message)
        else:
            # Safely handle non-ASCII characters on Windows consoles with limited encoding
            try:
                print(message)
            except UnicodeEncodeError:
                print(message.encode('ascii', 'replace').decode('ascii'))

    platform = detect_platform(playlist_url)
    log(f"[PLATFORM] Detected playlist platform: {platform}")
    
    log(f"[{platform.upper()}] Retrieving playlist tracks...")
    tracks = get_playlist_tracks_general(playlist_url, client_id, client_secret)
    total_tracks = len(tracks)
    
    log(f"[{platform.upper()}] {total_tracks} tracks detected (excluding local files).")
    if total_tracks == 0:
        raise ValueError("No valid tracks found in this playlist.")
        
    log("[LOCAL] Scanning output directory for duplicates...")
    local_tracks = scan_local_mp3s(output_dir)
    log(f"[LOCAL] {len(local_tracks)} existing files identified.")
    
    for index, track in enumerate(tracks):
        if stop_check_cb and stop_check_cb():
            log("[STOP] Download process interrupted.")
            return False
            
        track_title = f"{track['primary_artist']} - {track['title']}"
        log(f"\n----------------------------------------\n[TRACK {index+1}/{total_tracks}] {track_title}")
        
        if progress_cb:
            progress_cb(index, total_tracks, f"Processing {index+1}/{total_tracks} : {track['title']}", 0.0)
            
        # Clean terms for matching
        clean_sp_title = clean_text(track['title'])
        clean_sp_artist = clean_text(track['primary_artist'])
        clean_sp_artists = clean_text(track['all_artists'])
        
        matching_local_track = None
        for lt in local_tracks:
            clean_lt_title = clean_text(lt['title'])
            clean_lt_artist = clean_text(lt['artist'])
            
            title_match = get_similarity_ratio(clean_sp_title, clean_lt_title) >= 0.85
            artist_match = (
                get_similarity_ratio(clean_sp_artist, clean_lt_artist) >= 0.85 or
                clean_sp_artist in clean_lt_artist or
                clean_lt_artist in clean_sp_artists
            )
            
            if title_match and artist_match:
                matching_local_track = lt
                break
                
        if matching_local_track:
            target_bitrate = int(bitrate)
            local_bitrate = matching_local_track['bitrate']
            
            if local_bitrate >= target_bitrate:
                log(f"[LOCAL] Match found with equal or better quality ({local_bitrate} kbps >= {target_bitrate} kbps). Skipped.")
                if progress_cb:
                    progress_cb(index + 1, total_tracks, f"Skipped: {track['title']}", 1.0)
                continue
            else:
                log(f"[LOCAL] Upgrade requested ({target_bitrate} kbps > {local_bitrate} kbps). Overwriting local file...")
                try:
                    if os.path.exists(matching_local_track['filepath']):
                        os.remove(matching_local_track['filepath'])
                        local_tracks.remove(matching_local_track)
                except Exception as e:
                    log(f"[WARNING] Failed to remove local file: {e}")
                    
        # Match on YouTube Music
        log("[SEARCH] Searching for corresponding track on YouTube Music...")
        video_id, match_msg = find_best_match(track)
        log(f"[SEARCH] Result: {match_msg}")
        
        if not video_id:
            log(f"[WARNING] No match found on YouTube Music. Skipping track.")
            continue
            
        # Download progress callback closure
        def dl_progress(t_idx, t_title, state, percent, speed=""):
            if progress_cb:
                progress_cb(t_idx, total_tracks, f"Track {t_idx+1}/{total_tracks} : {t_title} ({state} {int(percent*100)}% {speed})", percent)
                
        log("[DOWNLOAD] Acquiring audio stream via yt-dlp...")
        try:
            temp_mp3 = download_track(
                video_id=video_id,
                output_dir=output_dir,
                track_index=index,
                track_title=track["title"],
                preferred_quality=bitrate,
                progress_callback=dl_progress
            )
        except Exception as dl_err:
            log(f"[WARNING] Download failed: {dl_err}")
            continue
            
        log("[METADATA] Applying Spotify ID3 metadata & cover art...")
        try:
            apply_metadata(temp_mp3, track)
        except Exception as tag_err:
            log(f"[WARNING] Failed to write ID3 tags: {tag_err}")
            
        # Sanitize and rename
        final_filename = f"{track['all_artists']} - {track['title']}"
        sanitized_filename = sanitize_filename(final_filename) + ".mp3"
        final_path = os.path.join(output_dir, sanitized_filename)
        
        if os.path.exists(final_path):
            try:
                os.remove(final_path)
            except Exception:
                pass
                
        try:
            os.rename(temp_mp3, final_path)
            log(f"[SUCCESS] Saved '{sanitized_filename}'")
        except Exception as e:
            log(f"[ERROR] Failed to save file: {e}")
            
    return True
