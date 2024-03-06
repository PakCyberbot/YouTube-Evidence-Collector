import sys
from pytube import YouTube
import os
import subprocess

#-------------------- YOUTUBE Interaction --------------------------------

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

def download_video(video_url, output_path, GuiWorkerThread = None):
    """
    video url or watch id
    """
    if not ("youtube.com" in video_url or "youtu.be" in video_url ):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    try:
        # Create a YouTube object
        if not GuiWorkerThread == None:
            yt = YouTube(video_url, on_progress_callback=GuiWorkerThread.progress_func)
        else:
            yt = YouTube(video_url, on_progress_callback=progress_func)

        # Get the highest resolution stream
        stream = yt.streams.get_highest_resolution()

        # Get the total file size in bytes
        total_size = stream.filesize

        # Clean the filename
        cleaned_filename = clean_filename(yt.title)

        # Define the output file path
        output_file_path = os.path.join(output_path, cleaned_filename)

        # Download the video
        stream.download(output_path=output_path, filename=f"{cleaned_filename}.mp4")

        mb_size = f"{total_size / (1024 * 1024):.2f}"
        print(f"Video '{yt.title}' has been downloaded")
        print(f"Total size: {mb_size} MB")
        return (mb_size, yt.title)
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

