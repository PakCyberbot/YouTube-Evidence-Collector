from googleapiclient.discovery import build
from pprint import pprint
import json
import os, shutil
import requests
import tempfile
from datetime import datetime
import locale

from docx2pdf import convert
import waybackpy
from libs.vid_downloader import extract_watch_id
from libs.ReportGenerator import reportme


locale.setlocale(locale.LC_ALL, '')

def add_to_wayback(vid_id):
    
    new_archive_url = waybackpy.Url(

        url = f"https://www.youtube.com/watch?v={vid_id}",
        user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"

    ).save()
    return new_archive_url


# Set up the YouTube Data API client
# https://googleapis.github.io/google-api-python-client/docs/dyn/youtube_v3.html
def api_init(secret):
# 'AIzaSyCn91JPROinHSEw08zrWpJIshxnGpoOSI4'
    global api_key
    api_key =  secret # Replace with your API key
    global youtube
    youtube = build('youtube', 'v3', developerKey=api_key)

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
        "video_url": f"https://www.youtube.com/watch?v={check['id']}",   
        "video_name": check["snippet"]["title"],
        "published_date": check["snippet"]["publishedAt"].replace("T"," ").replace("Z"," (UTC)"),
        "duration": check["contentDetails"]["duration"].replace("M", " minutes ").replace("H", " hours").replace("PT","").replace("S"," seconds"),
        "video_description": check["snippet"]["description"],
        "video_tags": ", ".join(check["snippet"].get("tags", ["NOT AVAILABLE"])),

        "views": "{:,}".format(int(check["statistics"]["viewCount"])),
        "likes": "{:,}".format(int(check["statistics"].get("likeCount","HIDDEN"))),
        "comments": "{:,}".format(int(check["statistics"]["commentCount"])),

        "thumbnails": check["snippet"]["thumbnails"]["maxres"]["url"],

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
   
    
def list_channel_videos(video_id):
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
    return videos

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

def data_scrape(url, api_key=None):
        # link types
        # https://www.youtube.com/watch?v=Mc_Rkzy4zuo
        # https://youtu.be/Mc_Rkzy4zuo?si=oumUfUqlP6n2gpi8
        # https://www.youtube.com/shorts/LMLBzzlvJs8

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

        # captures the video snapshot in wayback machine at the time of scraping
        wayback_machine_url = add_to_wayback(vid_id)
        dict_vals.update({"wayback_url":str(wayback_machine_url)})

        reportme("libs/vid_template.docx",f"Video{vid_id}.docx",dict_vals, {0:image_path,1:image_path2})
        
        shutil.rmtree(temp_dir)
        shutil.rmtree(temp_dir2)

        convert(f"Video{vid_id}.docx", f"Video{vid_id}.pdf")
        os.remove(f"Video{vid_id}.docx")

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
    
