from googleapiclient.discovery import build
from pprint import pprint
import json
import os, shutil, re
import requests
import tempfile
from datetime import datetime
import locale
import hashlib
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup


# from docx2pdf import convert
# from spire.doc import *
# from spire.doc.common import *

import waybackpy
# import asyncio
# from pyppeteer import launch
from libs.vid_downloader import extract_watch_id, download_video
from libs.ReportGenerator import reportme


locale.setlocale(locale.LC_ALL, '')

def extract_channel_name(url):
    # Define the regex pattern to extract the channel name
    pattern = r"https://www\.youtube\.com/(@[^\s/]+)"

    # Use re.search() to find the match in the URL
    match = re.search(pattern, url)

    # If a match is found, extract and return the channel name
    if match:
        return match.group(1)
    else:
        return None
    
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

async def take_screenshot(url, screenshot_path):
    # Launch a headless browser
    browser = await launch()
    page = await browser.newPage()
    
    # Open the webpage
    await page.goto(url)

    # Take a screenshot of the whole webpage
    await page.screenshot({'path': screenshot_path, 'fullPage': True})

    # Close the browser
    await browser.close()

# Set up the YouTube Data API client
# https://googleapis.github.io/google-api-python-client/docs/dyn/youtube_v3.html
def api_init(secret, gui_statusbar=None):
    global api_key
    api_key =  secret # Replace with your API key
    global youtube
    youtube = build('youtube', 'v3', developerKey=api_key)

    global gui_status
    gui_status = gui_statusbar
def download_image(url, location=None):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

        if location is None:
            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()

            # Create a temporary file to save the image
            temp_file_path = os.path.join(temp_dir, 'image.jpg')

            # Write the image content to the temporary file
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)

            # Return the path of the downloaded image and the temporary directory
            return temp_file_path, temp_dir
        else:
            with open(location, 'wb') as f:
                f.write(response.content)

            return None, None
        
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
        "likes": "{:,}".format(int(check["statistics"].get("likeCount","-1"))),
        "comments": "{:,}".format(int(check["statistics"].get("commentCount","0"))),

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
        "channel_name": check["snippet"]["title"],
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
        if "@" in channel_id:
            channel_response = youtube.channels().list(
                part='id',
                forHandle=channel_id.replace("@", "")
            ).execute()
            # Extract the channel ID from the response
            channel_id = channel_response['items'][0]['id']

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
    
    return channel_id, filtered_array_video

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

def data_scrape(url, api_key=None, channel_dump=False, wayback=False, only_channel=False, bulk_vid_down=False):
        
        with open("libs/yt_apikey", 'r') as file:
                # Read the content of the file
            content = file.read()
            
            if content:
                # If the file is not empty, remove the newline at the end
                secret = content.rstrip('\n')
            else:
                secret = api_key
        
        hashfile_content = ""
        api_init(secret)
        
        if only_channel == False:
            # link types
            # https://www.youtube.com/watch?v=<watch_id>
            # https://youtu.be/<watch_id>?si=oumUfUqlP6n2gpi8
            # https://www.youtube.com/shorts/<watch_id>
            vid_id = extract_watch_id(url)
            # Right now, exception handling isn't implemented so no need to take just watch id
            # if vid_id == None:
            #     # then the watch id is already given
            #     vid_id = self.url_input.text()
            

            dict_vals = scrape_video_info(vid_id)
            dict_vals2 = scrape_channel_info(dict_vals["channel_id"])
            dict_vals.update(dict_vals2)

            # Get current date and time
            current_datetime = datetime.utcnow()
            formatted_datetime = current_datetime.strftime("%Y-%m-%d at %H:%M:%S (UTC)")
            dict_vals.update({"scrape_datetime":formatted_datetime})

            image_path, temp_dir = download_image(dict_vals['thumbnails'])
            image_path2, temp_dir2 = download_image(dict_vals['channel_logo'])
            print('1. tempdir2 ', temp_dir2)

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
            # md5 hash addition    
            video_doc_hash =  calculate_md5(f"Video{vid_id}.docx")
            hashfile_content += f"Video{vid_id}.docx: {video_doc_hash}\n"
            
            custom_url = dict_vals["custom_url"]

            shutil.rmtree(temp_dir)

        
        if only_channel == True:
            custom_url = extract_channel_name(url)
            dict_vals = {}

            
        
        if channel_dump == True:
            vids_dir_path = Path(f'./{custom_url}')
            if not vids_dir_path.exists():
                vids_dir_path.mkdir()
            print("Channel Dumping started...")
            if only_channel == True:
                channel_id, videos_array = list_channel_videos(custom_url)
                dict_vals.update(scrape_channel_info(channel_id))
                dict_vals.update({"channel_id":channel_id})
                image_path2, temp_dir2 = download_image(dict_vals['channel_logo'])
                print('2. tempdir2 ', temp_dir2)
            else:
                _, videos_array = list_channel_videos(dict_vals["channel_id"])

            if wayback:
                # captures the video snapshot in wayback machine at the time of scraping
                wayback_machine_url = add_to_wayback(ch_id=custom_url)
                dict_vals.update({"wayback_url":str(wayback_machine_url)})

            sorted_videos_list = sorted(videos_array, key=lambda x: x['published_date'])

            total_videos = len(videos_array)
            for idx in range(total_videos):
                sorted_videos_list[idx]['video_number'] = str(idx + 1) 

            print("Now creating docx report of the channel")            
            reportme("libs/ch_template.docx",f"./{custom_url}/Channel{custom_url}.docx",dict_vals, {0:image_path2},sorted_videos_list)
            print("completed channel report")
            channel_doc_hash = calculate_md5(f"./{custom_url}/Channel{custom_url}.docx")
            hashfile_content += f"Channel{custom_url}.docx: {channel_doc_hash}\n"
            # document = Document()
            # # Load a Word DOCX file
            # document.LoadFromFile(f"Channel{custom_url}.docx")

            # # Save the file to a PDF file
            # document.SaveToFile(f"Channel{custom_url}.pdf", FileFormat.PDF)
            # document.Close()

            # convert(f"Channel{custom_url}.docx", f"Channel{custom_url}.pdf")
            # os.remove(f"Channel{custom_url}.docx")
            if bulk_vid_down == True:
                print(f"Starting to download {len(sorted_videos_list)} videos{'.' if len(sorted_videos_list) <= 5 else ', Please be patient as it might take a lot of time.'}")
                vids_dir_path = Path(f'./{custom_url}/videos')
                if not vids_dir_path.exists():
                    vids_dir_path.mkdir()
                pages_dir_path = Path(f'./{custom_url}/pages')
                if not pages_dir_path.exists():
                    pages_dir_path.mkdir()
                try:
                    for video in tqdm(sorted_videos_list, desc="Downloading Channel Videos"):
                        # Checks for already downloaded videos so it can continue where the downloading left/discontinued
                        result = any(video["video_id"] in file_name for file_name in os.listdir(vids_dir_path))
                        # if not Path(f'./{custom_url}/videos/{video["video_name"]} [{video["video_id"]}].mp4').exists():
                        if not result:
                            download_video(video['video_url'],f'./{custom_url}/videos')
                except Exception as e:
                    None

                if len(os.listdir(vids_dir_path)) < len(sorted_videos_list):
                    print(f"{len(sorted_videos_list) - len(os.listdir(vids_dir_path))} videos failed to download")
                    print("Restart scraping of the same channel; failed videos will be attempted for download again")
                else:
                    print(f"All {len(sorted_videos_list)} videos downloaded successfully")
                
                # Generating youtube clone webpage for better visualization of videos
                # shutil.copytree('./libs/web_template', f'./{custom_url}/')
                source_directory = './libs/web_template'
                destination_directory = f'./{custom_url}/'
                contents = os.listdir(source_directory)
                try:
                    # Move each item in the source directory to the destination directory
                    for item in contents:
                        if 'video.html' in item:
                            continue 
                        source_path = os.path.join(source_directory, item)
                        destination_path = os.path.join(destination_directory, item)
                        if os.path.isdir(source_path):
                            shutil.copytree(source_path, destination_path)
                        else:
                            shutil.copy(source_path, destination_path)
                except Exception as e:
                    print(e)
                    print("File already exists")

                print("Generating HTML file for easier visualization of downloaded videos...")
                
                with open(f'./libs/web_template/video.html', 'r') as f:
                    vid_html_content = f.read()
                video_soup = BeautifulSoup(vid_html_content, 'html.parser')

                with open(f'./{custom_url}/index.html', 'r') as f:
                    html_content = f.read()

                soup = BeautifulSoup(html_content, 'html.parser')
                # placing data in placeholders
                placeholders = {
                    '[channel_name]': dict_vals['channel_name'],
                    '[custom_url]': dict_vals['custom_url'],
                    '[sub_count]': dict_vals['channel_subs'],
                    '[channel_description]': dict_vals['channel_description']
                }

                # Replace placeholders in the entire HTML content
                html_text = str(soup)  # Get the HTML content as text
                for placeholder, replacement in placeholders.items():
                    html_text = html_text.replace(placeholder, replacement)
                
                soup = BeautifulSoup(html_text, 'html.parser')

                # placing channel logo
                shutil.copy(image_path2, f'{custom_url}/images/channel_logo.png')
                
                div_tag = soup.find('div', class_='list-container')
                # Adding videos sorted by time
                for video in sorted_videos_list:
                    matching_file = next((file for file in Path(vids_dir_path).iterdir() if file.is_file() and video['video_id'] in file.name), None)

                    # setting up for individual video page
                    vid_placeholders = {
                    '[channel_name]': dict_vals['channel_name'],
                    '[sub_count]': dict_vals['channel_subs'],
                    '[video_name]': video['video_name'],
                    '[video_description]': video['video_description'],
                    '[video_file]': os.path.basename(matching_file),
                    '[video_id]': video['video_id'],
                    '[video_views]': video['views'],
                    '[video_likes]': video['likes'],
                    '[video_published_date]': video['published_date'],
                    '[video_description]': video['video_description'],
                    '[thumbnail]': f'{video["video_id"]}.jpg'
                    }
                    video_html = str(video_soup)
                    for placeholder, replacement in vid_placeholders.items():
                        video_html = video_html.replace(placeholder, replacement)
                    with open(f'{custom_url}/pages/{video["video_id"]}.html', 'w',encoding='utf-8') as fh:
                        fh.write(video_html)

                    # setting up for index.html
                    download_image(video['Picture'],f'{custom_url}/images/{video["video_id"]}.jpg')
                    
                    
                    
                    # Write content inside the <div> tag
                    div_tag.append(BeautifulSoup(f'<div class="vid-list"><a href="pages/{video["video_id"]}.html"><div class="video"><video class="thevideo" loop muted poster="images/{video["video_id"]}.jpg"><source src="videos/{str(os.path.basename(matching_file))}" type="video/mp4"></video></div></a><div class="flex-div"><img src="images/channel_logo.png" alt=""><div class="vid-info"><a href="">{video["video_name"]}</a><p>{dict_vals["channel_name"]}</p><p>{str(video["views"])} Views &bull; {str(video["published_date"])}</p></div></div></div>', 'html.parser'))

                with open(f'./{custom_url}/index.html', 'w',encoding='utf-8') as file:
                    file.write(str(soup.prettify()))
                    print("HTML generated successfully")

            write_md5_to_file(f"./{custom_url}/Channel{custom_url}", hashfile_content)
        
        shutil.rmtree(temp_dir2)

def html_vidlist_gen():
    None

if __name__ == "__main__":

    global youtube
    # expired key
    youtube = build('youtube', 'v3', developerKey="AIzaSyCn91JPROinHSEw08zrWpJIshxnGpoOSI4")

    video_id = '<watch-id>'  # Replace with the ID of the video you want to scrape
    channel_id = "<channel-id>" # Replace with the ID of the channel you want to scrape
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
    
