from googleapiclient.discovery import build
from pprint import pprint
import json
import os, shutil
import requests
import tempfile
from datetime import datetime
import locale
import hashlib
from tqdm import tqdm


from docx2pdf import convert
from spire.doc import *
from spire.doc.common import *

import waybackpy
from libs.vid_downloader import extract_watch_id
from libs.ReportGenerator import reportme


locale.setlocale(locale.LC_ALL, '')

def calculate_md5(file_path):
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)

    return md5_hash.hexdigest()

def write_md5_to_file(file_path, content):
    md5_file_name = f"{file_path}.md5hash"

    if os.path.exists(md5_file_name):
        with open(md5_file_name, "a") as md5_file:
            md5_file.write(content)
    else:
        with open(md5_file_name, "w") as md5_file:
            md5_file.write(content)

def add_to_wayback(vid_id="",ch_id=""):
    if vid_id != "":
        print(f"Creating snapshot in wayback machine of video {vid_id }, It takes some time")

        new_archive_url = waybackpy.Url(

            url = f"https://www.youtube.com/watch?v={vid_id}",
            user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"

        ).save()
    if ch_id != "":
        print(f"Creating snapshot in wayback machine of channel {ch_id}, It takes some time")
        new_archive_url = waybackpy.Url(
            url = f"https://www.youtube.com/{ch_id}",
            user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
        ).save()
        
        # for page in ["videos","shorts","streams","playlists","community"]:
        #     # all channel pages
        #     print(f"Taking snapshot for the path /{page}")
        #     waybackpy.Url(
        #         url = f"https://www.youtube.com/{ch_id}/{page}",
        #         user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
        #     ).save()

    print(f"Completed wayback snapshot")

    return new_archive_url


# Set up the YouTube Data API client
# https://googleapis.github.io/google-api-python-client/docs/dyn/youtube_v3.html
def api_init(secret, gui_statusbar=None):
# 'AIzaSyCn91JPROinHSEw08zrWpJIshxnGpoOSI4'
    global api_key
    api_key =  secret # Replace with your API key
    global youtube
    youtube = build('youtube', 'v3', developerKey=api_key)

    global gui_status
    gui_status = gui_statusbar
def download_image(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Create a temporary file to save the image
        temp_file_path = os.path.join(temp_dir, 'image.jpg')

        # Write the image content to the temporary file
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)

        # Return the path of the downloaded image and the temporary directory
        return temp_file_path, temp_dir
    except requests.exceptions.RequestException as e:
        print("Error downloading image:", e)
        return None, None
    
def scrape_video_info(video_id):
    # Make a request to get video details
    request = youtube.videos().list(
        part='snippet,contentDetails,statistics,status',
        id=video_id
    )
    response = request.execute()
    check = response['items'][0]
    dict_vals = {
        "video_id": check['id'],
        "video_url": f"https://www.youtube.com/watch?v={check['id']}",   
        "video_name": check["snippet"]["title"],
        "published_date": check["snippet"]["publishedAt"].replace("T"," ").replace("Z"," (UTC)"),
        "duration": check["contentDetails"]["duration"].replace("M", " minutes ").replace("H", " hours").replace("PT","").replace("S"," seconds"),
        "video_description": check["snippet"]["description"],
        "video_tags": ", ".join(check["snippet"].get("tags", ["NOT AVAILABLE"])),

        "views": "{:,}".format(int(check["statistics"]["viewCount"])),
        "likes": "{:,}".format(int(check["statistics"].get("likeCount","HIDDEN"))),
        "comments": "{:,}".format(int(check["statistics"]["commentCount"])),

        "thumbnails": check["snippet"]["thumbnails"]["high"]["url"],

        "channel_id": check["snippet"]["channelId"],
        "channel_name": check["snippet"]["channelTitle"]
    }

    return dict_vals
    
def scrape_channel_info(channel_id):
    # Make a request to get channel details
    request = youtube.channels().list(
        part='snippet,contentDetails,statistics,status',
        id=channel_id
    )
    response = request.execute()
    check = response['items'][0]
    dict_vals = {
        "channel_description": check["snippet"]["description"],
        "custom_url": check["snippet"]["customUrl"],
        "channel_creation_date": check["snippet"]["publishedAt"].replace("T"," ").replace("Z"," (UTC)"),

        "channel_logo": check["snippet"]["thumbnails"]["high"]["url"],
        
        "channel_views": "{:,}".format(int(check["statistics"]["viewCount"])),
        "channel_subs": "{:,}".format(int(check["statistics"]["subscriberCount"])),
        "channel_vids": "{:,}".format(int(check["statistics"]["videoCount"])),
    }

    return dict_vals
   
    
def list_channel_videos(channel_id):
    videos = []
    next_page_token = None
    while True:
        request = youtube.search().list(
            part='snippet',
            channelId=channel_id,
            maxResults=140,  # Maximum number of results per page
            pageToken=next_page_token
        )
        response = request.execute()

        videos.extend(response['items'])
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    filtered_array_video = []
    for i, video_dict in enumerate(tqdm(videos, desc="Scraping each videos info", total=len(videos))):
        if video_dict['id']['kind'] == "youtube#video":
            
            video_info = scrape_video_info(video_dict['id']['videoId'])
            filtered_array_video.append(
                {  
                    "video_id": video_dict['id']['videoId'],
                    "video_url": f"https://www.youtube.com/watch?v={video_dict['id']['videoId']}",   
                    "video_name": video_dict["snippet"]["title"],
                    "published_date": video_dict["snippet"]["publishedAt"].replace("T"," ").replace("Z"," (UTC)"),
                    "duration": video_info["duration"],
                    "video_description": video_dict["snippet"]["description"],
                    "video_tags": video_info["video_tags"],

                    "views": video_info["views"],
                    "likes": video_info["likes"],
                    "comments": video_info["comments"],
                    
                    "Picture": video_dict["snippet"]["thumbnails"]["high"]["url"]
                }
                
            )
    
    return filtered_array_video

def vid_comments(video_id):
    # Make a request to get channel details
    request = youtube.comments().list(
        part='snippet,contentDetails,statistics,status',
        id=video_id
    )
    response = request.execute()
    return response
def get_video_comments(video_id):
    # Build the YouTube Data API service

    # Call the comments.list method to retrieve the comments of the video
    comments_request = youtube.commentThreads().list(
        part='snippet',
        videoId=video_id,
        maxResults=100  # You can adjust this number to specify the maximum number of comments to retrieve
    )

    # Execute the request and get the response
    response = comments_request.execute()
    return response
    # Extract the comments from the response
    comments = []
    for item in response['items']:
        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
        comments.append(comment)

    return comments

def data_scrape(url, api_key=None, channel_dump=False, wayback=False):
        # link types
        # https://www.youtube.com/watch?v=Mc_Rkzy4zuo
        # https://youtu.be/Mc_Rkzy4zuo?si=oumUfUqlP6n2gpi8
        # https://www.youtube.com/shorts/LMLBzzlvJs8
        hashfile_content = ""
        vid_id = extract_watch_id(url)
        # Right now, exception handling isn't implemented so no need to take just watch id
        # if vid_id == None:
        #     # then the watch id is already given
        #     vid_id = self.url_input.text()
        
        with open("libs/yt_apikey", 'r') as file:
            # Read the content of the file
            content = file.read()
            
            if content:
                # If the file is not empty, remove the newline at the end
                secret = content.rstrip('\n')
            else:
                secret = api_key
        
        api_init(secret)

        dict_vals = scrape_video_info(vid_id)
        dict_vals2 = scrape_channel_info(dict_vals["channel_id"])
        dict_vals.update(dict_vals2)

        # Get current date and time
        current_datetime = datetime.utcnow()
        formatted_datetime = current_datetime.strftime("%Y-%m-%d at %H:%M:%S (UTC)")
        dict_vals.update({"scrape_datetime":formatted_datetime})

        image_path, temp_dir = download_image(dict_vals['thumbnails'])
        image_path2, temp_dir2 = download_image(dict_vals['channel_logo'])

        if wayback:
            # captures the video snapshot in wayback machine at the time of scraping
            wayback_machine_url = add_to_wayback(vid_id=vid_id)
            dict_vals.update({"wayback_url":str(wayback_machine_url)})

        reportme("libs/vid_template.docx",f"Video{vid_id}.docx",dict_vals, {0:image_path,1:image_path2})
        print(f"Video{vid_id}.docx generated for the video")
        
        # document = Document()
        # # Load a Word DOCX file
        # document.LoadFromFile(f"Video{vid_id}.docx")

        # # Save the file to a PDF file
        # document.SaveToFile(f"Video{vid_id}.pdf", FileFormat.PDF)
        # document.Close()

        # convert(f"Video{vid_id}.docx", f"Video{vid_id}.pdf")
        # os.remove(f"Video{vid_id}.docx")
        custom_url = dict_vals["custom_url"]

        if channel_dump == True:
            print("Channel Dumping started...")
            videos_array = list_channel_videos(dict_vals["channel_id"])

            if wayback:
                # captures the video snapshot in wayback machine at the time of scraping
                wayback_machine_url = add_to_wayback(ch_id=custom_url)
                dict_vals.update({"wayback_url":str(wayback_machine_url)})

            sorted_videos_list = sorted(videos_array, key=lambda x: x['published_date'])

            total_videos = len(videos_array)
            for idx in range(total_videos):
                sorted_videos_list[idx]['video_number'] = str(idx + 1) 

            print("Now creating docx report of the channel")            
            reportme("libs/ch_template.docx",f"Channel{custom_url}.docx",dict_vals, {0:image_path2},sorted_videos_list)
            print("completed channel report")
            channel_doc_hash = calculate_md5(f"Channel{custom_url}.docx")
            hashfile_content += f"Channel{custom_url}.docx: {channel_doc_hash}\n"
            # document = Document()
            # # Load a Word DOCX file
            # document.LoadFromFile(f"Channel{custom_url}.docx")

            # # Save the file to a PDF file
            # document.SaveToFile(f"Channel{custom_url}.pdf", FileFormat.PDF)
            # document.Close()

            # convert(f"Channel{custom_url}.docx", f"Channel{custom_url}.pdf")
            # os.remove(f"Channel{custom_url}.docx")

        # md5 hash addition    
        video_doc_hash =  calculate_md5(f"Video{vid_id}.docx")
        hashfile_content += f"Video{vid_id}.docx: {video_doc_hash}\n"
        write_md5_to_file(f"Channel{custom_url}", hashfile_content)

        shutil.rmtree(temp_dir)
        shutil.rmtree(temp_dir2)

if __name__ == "__main__":

    global youtube
    youtube = build('youtube', 'v3', developerKey="AIzaSyCn91JPROinHSEw08zrWpJIshxnGpoOSI4")

    video_id = 'lAjQr0Zq_zA'  # Replace with the ID of the video you want to scrape
    channel_id = "UCPf_eR-5vP-PDHpc9s7AFuQ"
    test  = get_video_comments(video_id)
    pprint(test)
    
    with open("video_comments.json", "w") as f:
        json.dump(test, f, indent=4)
    exit()
    dict_vals = scrape_video_info(video_id)
    dict_vals2 = scrape_channel_info(dict_vals["channel_id"])
    # check3 = list_channel_videos(channel_id)
    # check4 = vid_comments(video_id)
    
    dict_vals.update(dict_vals2)

    # Get current date and time
    current_datetime = datetime.utcnow()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d at %H:%M:%S (UTC)")
    dict_vals.update({"scrape_datetime":formatted_datetime})

    image_path, temp_dir = download_image(dict_vals['thumbnails'])
    image_path2, temp_dir2 = download_image(dict_vals['channel_logo'])

    reportme("wpscreated.docx",f"{video_id}.docx",dict_vals, {0:image_path,1:image_path2})
    shutil.rmtree(temp_dir)
    shutil.rmtree(temp_dir2)

    convert(f"{video_id}.docx", f"{video_id}.pdf")
    os.remove(f"{video_id}.docx")
    
