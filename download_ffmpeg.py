import os
import zipfile
import requests

FFMPEG_URL = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip"
FFPROBE_URL = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip"

def download_and_extract(url, target_name):
    """
    Downloads zip file from url and extracts the target binary (e.g. ffmpeg.exe).
    """
    zip_path = target_name + ".zip"
    print(f"Downloading {target_name} from {url}...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    print(f"Extracting {target_name}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Check files in zip
        for file_info in zip_ref.infolist():
            if file_info.filename.lower() == target_name.lower() or file_info.filename.lower().endswith(target_name.lower()):
                # Extract file
                data = zip_ref.read(file_info.filename)
                with open(target_name, "wb") as out_f:
                    out_f.write(data)
                break
                
    os.remove(zip_path)
    print(f"Successfully downloaded and extracted {target_name}!")

def main():
    dest_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(dest_dir, "ffmpeg.exe")
    ffprobe_path = os.path.join(dest_dir, "ffprobe.exe")
    
    if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
        print("ffmpeg.exe and ffprobe.exe are already present in the project folder.")
        return
        
    try:
        if not os.path.exists(ffmpeg_path):
            download_and_extract(FFMPEG_URL, "ffmpeg.exe")
        if not os.path.exists(ffprobe_path):
            download_and_extract(FFPROBE_URL, "ffprobe.exe")
        print("FFmpeg setup completed successfully!")
    except Exception as e:
        print(f"Error while downloading FFmpeg: {e}")
        print("Please download ffmpeg.exe and ffprobe.exe manually and place them in the project root.")

if __name__ == "__main__":
    main()
