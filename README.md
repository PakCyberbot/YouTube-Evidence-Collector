# YT Evidence Collector

![banner](https://github.com/PakCyberbot/YouTube-Evidence-Collector/assets/93365275/63d39ab6-6fe4-4508-9b4e-4bc84b9c14a5)

**The purpose of the tool is to gather evidence from YouTube.**

![ytevidencecollector](https://github.com/PakCyberbot/YouTube-Evidence-Collector/assets/93365275/8a3e27e1-3c81-4bea-a7fa-da2843799dab)
# Table of Contents

- [YT Evidence Collector](#yt-evidence-collector)
- [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Features](#features)
      - [Upcoming Features](#upcoming-features)
  - [Setting Up Your YouTube API Key](#setting-up-your-youtube-api-key)
    - [Input Methods for Your API Key](#input-methods-for-your-api-key)
  - [GUI / CLI modes](#gui--cli-modes)
    - [CLI Arguments](#cli-arguments)
  - [Example Usage in CLI mode](#example-usage-in-cli-mode)
  - [Disclaimer:](#disclaimer)



## Installation
Before running the tool, type the following command
```bash
pip install -r requirements.txt
```
## Features
- Downloads YouTube videos
- Collects data about videos and their channels
- Collects data about all videos in a channel
- Takes snapshots of videos/channels in the Wayback Machine
- Generates a DOCX file with the collected data
- Ability to download age-restricted videos \[**NEW**\]
- Bulk video download during channel dump \[**NEW**\]
  

#### Upcoming Features
- Collect comments for videos
- Collect additional information about channels such as playlists, community posts, and separate shorts, live streams, and playlists in their own sections in the DOCX file
- Take screenshots of entire YouTube video/channel pages
- Implement Google API quota check before channel dump
- Generate PDF files

## Setting Up Your YouTube API Key

1. Begin by creating your project [here](https://console.cloud.google.com/projectcreate).

2. Next, enable the YouTube Data API by visiting [this link](https://console.cloud.google.com/apis/library/youtube.googleapis.com).

3. Create your API key by navigating to [API Credentials](https://console.cloud.google.com/apis/credentials) and clicking on "CREATE CREDENTIALS".

### Input Methods for Your API Key

- You can directly input your API key temporarily through an input box in the GUI or using the `-k <apikey>` option in CLI mode.
  
- Alternatively, you can add your API key to the "**_yt_apikey_**" file located in the "libs" folder.

## GUI / CLI modes
You can utilize this tool in GUI mode by simply executing it without specifying any arguments.
```
python YT_evidence_collector.py
```
### CLI Arguments

The tool supports the following command-line arguments:

| Argument              | Description                                                          |
|-----------------------|----------------------------------------------------------------------|
| `url`                 | URL of the YouTube video or channel url.               |
| `-k`, `--apikey`      | API key for scraping data.                                           |
| `-e`, `--evidence`    | Enable evidence collection.                                           |
| `-d`, `--dump`        | Dump the whole channel of the selected video.                        |
| `-n`, `--nodownload`  | Disable video downloading.                                           |
| `-w`, `--wayback`     | Take a snapshot in Wayback Machine.                                  |
| `-b`, `--bulkvideos`     | Download all channel videos                               |

## Example Usage in CLI mode

Here are some examples of how to use the tool with different options:

1. Download a YouTube video:
   
   ```bash
   python YT_evidence_collector.py <video/channel url>
   ```

2. Download a YouTube video with API key and Enable evidence collection:
   
   ```bash
   python YT_evidence_collector.py https://www.youtube.com/watch?v=your_video_id -k your_api_key -e
   ```
3. : Download a YouTube video with evidence collection, if the api key is provided in the file.
   
   ```bash
   python YT_evidence_collector.py https://www.youtube.com/watch?v=your_video_id -e
   ```

4. Dump the whole channel of the selected video:
   
   ```bash
   python YT_evidence_collector.py https://www.youtube.com/watch?v=your_video_id -d
   ```

5. Disable video downloading:
   
   ```bash
   python YT_evidence_collector.py https://www.youtube.com/watch?v=your_video_id -n
   ```

6. Take a snapshot in Wayback Machine:
   
   ```bash
   python YT_evidence_collector.py https://www.youtube.com/watch?v=your_video_id -w
   ```

## Disclaimer:

This tool, the YouTube Evidence Collector, is intended for educational, research, and investigative purposes only. It is not to be used for any illegal activities. Users are responsible for ensuring compliance with all applicable laws and regulations. The creator of this tool does not condone misuse or unauthorized use. By using this tool, you agree to use it responsibly and hold harmless the creators from any liability.
