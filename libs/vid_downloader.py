import sys, re, shutil
# from pytube import YouTube
import os
import subprocess
import yt_dlp
import json
from pathlib import Path

#-------------------- YOUTUBE Interaction --------------------------------
def extract_watch_id(link):
        # Regex pattern to extract watch id from YouTube links
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([\w-]+)'
        
        # Search for the watch id in the link
        match = re.search(pattern, link)
        
        # Return the watch id if found, otherwise return None
        if match:
            return match.group(1)
        else:
            return None 
        
def clean_filename(filename):
    # Replace characters that are not allowed in Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '-')
    return filename

def progress_func(stream, chunk, bytes_remaining):
    current = stream.filesize - bytes_remaining
    done = int(50 * current / stream.filesize)

    sys.stdout.write(
        "\r[{}{}] {} MB / {} MB".format('=' * done, ' ' * (50 - done), "{:.2f}".format(bytes_to_megabytes(current)),
                                        "{:.2f}".format(bytes_to_megabytes(stream.filesize))))
    sys.stdout.flush()

def bytes_to_megabytes(bytes_size):
    megabytes_size = bytes_size / (1024 ** 2)
    return megabytes_size

def download_video(video_url, output_path="./", GuiWorkerThread = None):
    """
    video url or watch id
    """
    # _default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID"]

    if not ("youtube.com" in video_url or "youtu.be" in video_url ):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    try:
        #------------------- Old downloader --------------------
        # # Create a YouTube object
        # if not GuiWorkerThread == None:
        #     yt = YouTube(video_url, on_progress_callback=GuiWorkerThread.progress_func)
        # else:
        #     yt = YouTube(video_url, on_progress_callback=progress_func)

        # # Get the highest resolution stream
        # stream = yt.streams.get_highest_resolution()

        # # Get the total file size in bytes
        # total_size = stream.filesize

        # # Clean the filename
        # cleaned_filename = clean_filename(yt.title)

        # # Define the output file path
        # output_file_path = os.path.join(output_path, cleaned_filename)

        # # Download the video
        # stream.download(output_path=output_path, filename=f"{cleaned_filename}.mp4")
        
        #---------------------------- New Downloader --------------------------------
        ydl_opts = {
            'format': 'mp4/bestaudio/best'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            with open('check.json', 'w') as f:
                json.dump(ydl.sanitize_info(info), f, indent=4)
            yttitle  = ydl.sanitize_info(info)['title']
            ytid = ydl.sanitize_info(info)['id']
            total_size = int(ydl.sanitize_info(info)['filesize_approx'])

        # debug
        print(f'filename moving {yttitle} [{ytid}].mp4')
        if not output_path == './':
            matching_file = next((file for file in Path('./').iterdir() if file.is_file() and ytid in file.name), None)
            shutil.move(str(matching_file),output_path)

        mb_size = f"{total_size / (1024 * 1024):.2f}"
        print(f"Video '{yttitle}' has been downloaded")
        print(f"Total size: {mb_size} MB")
        return (mb_size, yttitle)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def time_to_seconds(time_str):
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds

def cut_video(input_file, output_file, start_time, end_time):
    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)

    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-ss', str(start_seconds),
        '-to', str(end_seconds),
        '-c', 'copy',
        output_file
    ]

    subprocess.run(cmd)

