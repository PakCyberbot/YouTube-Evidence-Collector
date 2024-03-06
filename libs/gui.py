import re, shutil, os
from datetime import datetime
from docx2pdf import convert
from PyQt5.QtWidgets import QMainWindow, QWidget,QStatusBar, QLabel, QLineEdit,QProgressBar, QPushButton, QVBoxLayout, QCheckBox, QHBoxLayout
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from libs.vid_downloader import download_video

from libs.scraper import scrape_channel_info, scrape_video_info, download_image, api_init

from libs.ReportGenerator import reportme
#-----------------------  GUI --------------------------------
# Worker thread for performing scraping
class WorkerThread(QThread):
    finished = pyqtSignal(str)
    update_progress = pyqtSignal(int)

    def __init__(self, url, evidence_check):
        super().__init__()
        self.url = url
        self.evidence_check = evidence_check

    def run(self):
        # Perform scraping operation
        file_size, yt_title = download_video(self.url, './', self)

        # Emit signal to indicate that the operation is finished
        self.finished.emit(f"{file_size} MB - {yt_title} : Successfully downloaded video")

    def progress_func(self, stream, chunk, bytes_remaining):
        current = stream.filesize - bytes_remaining
        done = int(100 * current / stream.filesize)
        self.update_progress.emit(done)


def percentSize(object, width_percentage=100, height_percentage=100):
    # use 'app' to get desktop relative sizing, for others pass the object not string 
    if type(object) == str and  object.lower().endswith('app'):
        raise Exception("Convert 'app' string argument in percentSize() to QApplication object, because of pyside6 update!")

    if hasattr(object, "primaryScreen"):
        object = object.primaryScreen().availableGeometry()
    
    width = int(object.width() * (width_percentage/100))
    height = int(object.height() * (height_percentage/100))
    return (width, height)

class MainWindow(QMainWindow):
    def __init__(self,app):
        super().__init__()
        self.app = app
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Create widgets
        self.label1 = QLabel("Enter YT Video URL:")
        self.url_input = QLineEdit()

        self.label2 = QLabel("YT API KEY:")
        self.yt_api = QLineEdit()
        self.yt_api.setEchoMode(QLineEdit.Password)
        self.label2.setVisible(False)
        self.yt_api.setVisible(False)
        self.evdnce_chkbx = QCheckBox("Evidence Gathering")
        
        self.scrape_btn = QPushButton("Start Scraping")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Initially invisible

        # Layout
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.label1)
        hlayout1.addWidget(self.url_input)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.evdnce_chkbx)
        hlayout2.addWidget(self.label2)
        hlayout2.addWidget(self.yt_api)

        main_layout = QVBoxLayout()
        main_layout.addLayout(hlayout1)
        main_layout.addLayout(hlayout2)

        main_layout.addWidget(self.scrape_btn)
        main_layout.addWidget(self.progress_bar)

        # Set layout
        central_widget.setLayout(main_layout)

        # Connect buttons to functions
        self.evdnce_chkbx.stateChanged.connect(self.toggle_api_input_visibility)
        self.scrape_btn.clicked.connect(self.scraping)
        self.setGeometry(0,0, *percentSize(self.app,30,60))

        # Set window properties
        self.setWindowTitle("URL Checker")
        self.center()

    def toggle_api_input_visibility(self,state):
        if state == 2:
            with open("libs/yt_apikey", 'r') as file:
                # Read the content of the file
                content = file.read()
                
                if content:
                    self.label2.setVisible(True)
                    self.label2.setText("Api Key loaded from file")
                else:
                    self.label2.setVisible(True)
                    self.yt_api.setVisible(True)
        else:
            self.label2.setVisible(False)
            self.yt_api.setVisible(False)

    def scraping(self):
        if self.check_line_edit() == True:
            self.progress_bar.setVisible(True)

            # Disable the scrape button during scraping
            self.scrape_btn.setEnabled(False)
            
            # Start worker thread for scraping
            url = self.url_input.text()
            evidence_check = self.evdnce_chkbx.isChecked()
            self.worker = WorkerThread(url, evidence_check)
            self.worker.finished.connect(self.scraping_finished)
            self.worker.update_progress.connect(self.update_progress_bar)
            self.worker.start()

            if self.evdnce_chkbx.isChecked() == True:
                self.data_scrape()
    def data_scrape(self):
        # link types
        # https://www.youtube.com/watch?v=Mc_Rkzy4zuo
        # https://youtu.be/Mc_Rkzy4zuo?si=oumUfUqlP6n2gpi8
        # https://www.youtube.com/shorts/LMLBzzlvJs8

        vid_id = self.extract_watch_id(self.url_input.text())
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
                secret = self.yt_api.text()
        
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

        reportme("libs/vid_template.docx",f"Video{vid_id}.docx",dict_vals, {0:image_path,1:image_path2})
        shutil.rmtree(temp_dir)
        shutil.rmtree(temp_dir2)

        convert(f"Video{vid_id}.docx", f"Video{vid_id}.pdf")
        os.remove(f"Video{vid_id}.docx")

    def extract_watch_id(self, link):
        # Regex pattern to extract watch id from YouTube links
        pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([\w-]+)'
        
        # Search for the watch id in the link
        match = re.search(pattern, link)
        
        # Return the watch id if found, otherwise return None
        if match:
            return match.group(1)
        else:
            return None 
        
    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)  # Update progress bar value
        # if value == 100:
        #     # Enable the button when the task is finished
        #     self.scraping_finished()


    def scraping_finished(self, message):
        # Re-enable the scrape button after scraping is finished
        self.scrape_btn.setEnabled(True)
        self.progress_bar.setVisible(False) 

        self.status_bar.showMessage(message,10000)  

    def check_line_edit(self):
        if not self.url_input.text():  # Check if line edit is empty
            self.url_input.setToolTip("Please enter a URL")  # Set tooltip if line edit is empty
            return False
        else:
            self.url_input.setToolTip("")  # Clear tooltip if line edit is not empty
            return True

    def center(self):
        qRect = self.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())


