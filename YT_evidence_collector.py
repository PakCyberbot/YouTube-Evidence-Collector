import sys, argparse
from PyQt5.QtWidgets import QApplication
import qdarktheme

from libs.gui import MainWindow
from libs.vid_downloader import download_video

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # GUI version
        app = QApplication(sys.argv)
        qdarktheme.setup_theme()

        window = MainWindow(app)
        window.show()
        sys.exit(app.exec_())
    else:
        #CLI Version
        parser = argparse.ArgumentParser(description="Download YouTube video in high resolution.")
        parser.add_argument("url", help="URL of the YouTube video or  the path to mp4 video")
    
        args = parser.parse_args()
        try:
            _ , video_title = download_video(args.url, "./")
            print(f'>>>>>>>>>>>>>>>> {video_title} <<<<<<<<<<<<<<<<"')
        except:
            print(f'Error - Error - Error {args.url} Error - Error - Error')
