import sys, argparse
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import qdarktheme

from libs.gui import MainWindow
from libs.vid_downloader import download_video, extract_watch_id
from libs.scraper import data_scrape

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # GUI version
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon("libs/toollogo.png"))
        qdarktheme.setup_theme()

        window = MainWindow(app)
        window.show()
        sys.exit(app.exec_())
    else:
        #CLI Version
        parser = argparse.ArgumentParser(description="Download YouTube video in high resolution.")
        parser.add_argument("url", help="URL of the YouTube video or the channel url")
        parser.add_argument('-k', '--apikey', type=str, help='API key for scraping data')
        parser.add_argument('-e', '--evidence', action='store_true', help='Enable evidence collection')
        parser.add_argument('-d', '--dump', action='store_true', help='dumps the whole channel of the selected video')
        parser.add_argument('-n', '--nodownload', action='store_true', help='video downloading disabled')
        parser.add_argument('-w', '--wayback', action='store_true', help='Take snapshot in wayback machine')
        
        args = parser.parse_args()
        
        if args.evidence:
        
            with open("libs/yt_apikey", 'r') as file:
                content = file.read()
                if not content and args.apikey == None:
                    print("provide youtube api key using --api-key argument")
                    exit()

            data_scrape(args.url, args.apikey, channel_dump=args.dump, wayback=args.wayback)
        
        try:
            if not args.nodownload:
                _ , video_title = download_video(args.url, "./")
                print(f'>>>>>>>>>>>>>>>> {video_title} <<<<<<<<<<<<<<<<"')
        except:
            print(f'Error - Error - Error {args.url} Error - Error - Error')
