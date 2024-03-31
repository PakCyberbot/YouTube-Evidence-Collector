import re, shutil, os

from time import sleep
from datetime import datetime
from docx2pdf import convert
from PyQt5.QtWidgets import QMainWindow, QWidget,QStatusBar,QSizePolicy,QSpacerItem, QLabel, QLineEdit,QProgressBar, QPushButton, QVBoxLayout, QCheckBox, QHBoxLayout, QFrame
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QIcon, QFont, QFontMetrics, QPixmap

from libs.vid_downloader import download_video, extract_watch_id

from libs.scraper import data_scrape, extract_channel_name

from libs.ReportGenerator import reportme

#-----------------------  GUI --------------------------------
# Worker thread for performing scraping
class DownloadThread(QThread):
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
        self.only_channel = False

        self.setWindowIcon(QIcon("libs/toollogo.png"))
        self.init_ui()

    def init_ui(self):
        font = QFont("Arial", 10)
        font_metrics = QFontMetrics(font)
        preferred_height = font_metrics.height() + 6  # Add some padding


        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        bannerlabel = QLabel(self)

        # Load the image from file
        pixmap = QPixmap("libs/banner.png")  # Replace "image.jpg" with the path to your image file
        
        scaleed_pixmap = pixmap.scaled(*percentSize(self.app,35,70), aspectRatioMode=True)

        # Set the pixmap to the label
        bannerlabel.setPixmap(scaleed_pixmap)
        bannerlabel.setContentsMargins(50, 50, 50, 50)
        # Create widgets
        self.label1 = QLabel("Enter YT Video URL:")
        self.label1.setFont(font)
        self.url_input = QLineEdit()
        self.url_input.setMinimumHeight(preferred_height)
        self.url_input.setFont(font)

        self.label2 = QLabel("YT API KEY:")
        self.label2.setFont(font)
        self.yt_api = QLineEdit()
        self.yt_api.setFont(font)
        self.yt_api.setEchoMode(QLineEdit.Password)
        self.label2.setVisible(False)
        self.yt_api.setVisible(False)
        self.evdnce_chkbx = QCheckBox("Evidence Gathering")
        self.evdnce_chkbx.setFont(font)
        self.chdump_chkbox = QCheckBox("Channel Dump")
        self.chdump_chkbox.setFont(font)
        self.viddown_chkbox = QCheckBox("Video/s Download")
        self.viddown_chkbox.setFont(font)
        self.viddown_chkbox.setChecked(True)
        self.wayback_chkbox = QCheckBox("Wayback Snapshot")
        self.wayback_chkbox.setFont(font)

        
        self.scrape_btn = QPushButton("Start Downloading")
        self.scrape_btn.setFont(font)
        self.donate_btn = QPushButton("Donate @PakCyberbot to support for more projects")
        self.donate_btn.setFont(font)
        self.donate_btn.clicked.connect(self.openLink)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Initially invisible

        # Layout
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.label1)
        hlayout1.addWidget(self.url_input)
        hlayout1.addWidget(self.evdnce_chkbx)


        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.label2)
        hlayout2.addWidget(self.yt_api)

        self.addon_frame = QWidget()

        hlayout_addons = QHBoxLayout()
        hlayout_addons.addWidget(self.chdump_chkbox)
        hlayout_addons.addWidget(self.wayback_chkbox)
        hlayout_addons.addWidget(self.viddown_chkbox)
        self.addon_frame.setLayout(hlayout_addons)
        self.addon_frame.hide()
        top_spacer = QSpacerItem(50, 50, QSizePolicy.Minimum, QSizePolicy.Expanding)
        
        main_layout = QVBoxLayout()
        # main_layout.addItem(top_spacer)
        main_layout.addStretch(1)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.addWidget(bannerlabel)
        main_layout.addLayout(hlayout1)
        main_layout.addSpacing(50)
        main_layout.addLayout(hlayout2)
        main_layout.addSpacing(50)
        main_layout.addWidget(self.addon_frame )
        main_layout.addSpacing(50)
        main_layout.addWidget(self.scrape_btn)
        main_layout.addSpacing(50)
        main_layout.addWidget(self.donate_btn)
        main_layout.addSpacing(50)
        main_layout.addWidget(self.progress_bar)
        main_layout.addStretch(1)    
        # Set layout
        central_widget.setLayout(main_layout)
        # Connect buttons to functions
        self.evdnce_chkbx.stateChanged.connect(self.toggle_api_input_visibility)
        self.scrape_btn.clicked.connect(self.scraping)
        self.url_input.editingFinished.connect(self.urlcheck)

        self.chdump_chkbox.stateChanged.connect(self.toggle_vid_down)

        self.setGeometry(0,0, *percentSize(self.app,40,70))

        # Set window properties
        self.setWindowTitle("YT Evidence Collector")
        self.center()

    def openLink(self):
        url = QUrl('https://www.buymeacoffee.com/pakcyberbot')
        QDesktopServices.openUrl(url)
    
    def toggle_api_input_visibility(self,state):
        if state == 2:
            self.scrape_btn.setText("Start Scraping")
            self.addon_frame.show()
            with open("libs/yt_apikey", 'r') as file:
                # Read the content of the file
                content = file.read()
                
                if content:
                    self.label2.setVisible(True)
                    self.label2.setText("Api Key loaded from file")
                else:
                    self.label2.setText("YT API KEY:")
                    self.label2.setVisible(True)
                    self.yt_api.setVisible(True)
        else:
            self.scrape_btn.setText("Start Downloading")
            self.addon_frame.hide()
            self.label2.setVisible(False)
            self.yt_api.setVisible(False)
 
    def toggle_vid_down(self,state):
        if state == 2:
            self.viddown_chkbox.setText("Bulk Video Download")
            self.viddown_chkbox.setChecked(False)
        else:
            self.viddown_chkbox.setText("Video Download")
            self.viddown_chkbox.setChecked(True)


    def scraping(self):

        bulk_vids = False
        if self.viddown_chkbox.text() == "Bulk Video Download":
            bulk_vids = self.viddown_chkbox.isChecked()

        if self.check_line_edit() == True:
            # Disable the scrape button during scraping
            self.scrape_btn.setEnabled(False)

            wayback_enabled = False
            if self.wayback_chkbox.isChecked() == True:
                wayback_enabled = True

            if self.evdnce_chkbx.isChecked() == True:
                if self.chdump_chkbox.isChecked() == True:
                    self.status_bar.showMessage("Scraping for the collection of evidences...")  
                    data_scrape(self.url_input.text(),self.yt_api.text(),channel_dump=True, wayback=wayback_enabled, only_channel= self.only_channel, bulk_vid_down=bulk_vids)
                else:
                    self.status_bar.showMessage("Scraping for the collection of evidences...")  
                    data_scrape(self.url_input.text(),self.yt_api.text(), wayback=wayback_enabled, only_channel= self.only_channel, bulk_vid_down=bulk_vids)

                

            self.status_bar.showMessage("Downloading the video...")  

            self.progress_bar.setVisible(True)

            
            if self.viddown_chkbox.isChecked() == True and self.viddown_chkbox.text() != "Bulk Video Download":
                # Start worker thread for downloading
                url = self.url_input.text()
                evidence_check = self.evdnce_chkbx.isChecked()
                self.worker = DownloadThread(url, evidence_check)
                self.worker.finished.connect(self.scraping_finished)
                self.worker.update_progress.connect(self.update_progress_bar)
                self.worker.start()
            else:
                self.scraping_finished("Scraping Completed")

                
            
            

    

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
            # self.url_input.setToolTip("Please enter a URL")  # Set tooltip if line edit is empty
            return False
        else:
            # self.url_input.setToolTip("")  # Clear tooltip if line edit is not empty
            return True

    def center(self):
        qRect = self.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())


    def urlcheck(self):
        channel_name = extract_channel_name(self.url_input.text())
        if channel_name is not None:   
            self.toggle_vid_down(2)
            self.chdump_chkbox.setChecked(True)
            self.chdump_chkbox.setDisabled(True)
            self.evdnce_chkbx.setChecked(True)
            self.evdnce_chkbx.setDisabled(True)
            self.only_channel = True
        else:
            self.toggle_vid_down(1)
            self.chdump_chkbox.setDisabled(False)
            self.chdump_chkbox.setChecked(False)
            self.evdnce_chkbx.setDisabled(False)
            self.only_channel = False

            
            


