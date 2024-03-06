from googleapiclient.discovery import build
from pprint import pprint
import json
import os, shutil
import requests
import tempfile
from datetime import datetime

from docx2pdf import convert


from libs.ReportGenerator import reportme
# Set up the YouTube Data API client
# https://googleapis.github.io/google-api-python-client/docs/dyn/youtube_v3.html
api_key = 'AIzaSyCn91JPROinHSEw08zrWpJIshxnGpoOSI4'  # Replace with your API key
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
        "video_name": check["snippet"]["title"],
        "published_date": check["snippet"]["publishedAt"],
        "duration": check["contentDetails"]["duration"].replace("M", " minutes ").replace("H", " hours").replace("PT","").replace("S"," seconds"),
        "video_description": check["snippet"]["description"],
        "video_tags": ", ".join(check["snippet"]["tags"]),

        "views": check["statistics"]["viewCount"],
        "likes": check["statistics"]["likeCount"],
        "comments": check["statistics"]["commentCount"],

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
        "channel_creation_date": check["snippet"]["publishedAt"],

        "channel_logo": check["snippet"]["thumbnails"]["high"]["url"],
        
        "channel_views": check["statistics"]["viewCount"],
        "channel_subs": check["statistics"]["subscriberCount"],
        "channel_vids": check["statistics"]["videoCount"],
    }

    return dict_vals
    # Extract channel details
    if 'items' in response:
        channel = response['items'][0]
        title = channel['snippet']['title']
        description = channel['snippet']['description']
        thumbnails = channel['snippet']['thumbnails']
        return title, description, thumbnails
    else:
        return None, None, None
    
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

if __name__ == "__main__":
    video_id = 'lAjQr0Zq_zA'  # Replace with the ID of the video you want to scrape
    channel_id = "UCPf_eR-5vP-PDHpc9s7AFuQ"
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
    # with open("video.json", "w") as json_file:
    #     json.dump(check, json_file, indent=4)
    
    # with open("channel.json", "w") as json_file:
    #     json.dump(check2, json_file, indent=4)
    
    # with open("channelvids.json", "w") as json_file:
    #     json.dump(check3, json_file, indent=4)
    
    # print(len(check3))
    
    # with open("vidcomments.json", "w") as json_file:
    #     json.dump(check4, json_file, indent=4)
    
    # title, description, thumbnails = scrape_video_info(video_id)
    # if title:
    #     print("Title:", title)
    #     print("Description:", description)
    #     print("Thumbnails:", thumbnails)
    # else:
    #     print("Video not found or invalid API key.")
