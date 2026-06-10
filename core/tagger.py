import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, error

def apply_metadata(file_path, spotify_track):
    """
    Applies Spotify metadata (Title, Artist, Album, Cover Art) to the MP3 file.
    Uses ID3v2.4 specification.
    """
    title = spotify_track.get("title", "")
    artists = spotify_track.get("all_artists", "")
    album = spotify_track.get("album", "")
    cover_url = spotify_track.get("cover_url")
    
    # Initialize ID3 tags
    try:
        audio = MP3(file_path, ID3=ID3)
    except error:
        audio = MP3(file_path)
        audio.add_tags()
        
    # Delete existing/residual tags to start with a clean state
    try:
        audio.delete()
        audio.save()
    except Exception as e:
        print(f"Warning during tag deletion: {e}")
        
    # Re-initialize to write new tags
    audio = MP3(file_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
        
    # Inject standard text frames (using encoding=3 which corresponds to UTF-8 in ID3v2.4)
    audio.tags.add(TIT2(encoding=3, text=title))
    audio.tags.add(TPE1(encoding=3, text=artists))
    audio.tags.add(TALB(encoding=3, text=album))
    
    # Download and inject cover art
    if cover_url:
        try:
            # Synchrounous request to fetch the image bytes
            response = requests.get(cover_url, timeout=10)
            if response.status_code == 200:
                # Add Attached Picture (APIC) frame
                audio.tags.add(
                    APIC(
                        encoding=0,           # LATIN1/ISO-8859-1 for maximum compatibility
                        mime="image/jpeg",    # Spotify covers are standard JPEG files
                        type=3,               # 3 means Cover (front)
                        desc="Cover",
                        data=response.content
                    )
                )
            else:
                print(f"Failed to fetch cover art from {cover_url}, status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching/embedding cover art: {e}")
            
    # Save the modified file
    audio.save()
