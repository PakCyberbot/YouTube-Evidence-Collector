from PyQt5.QtWidgets import QMainWindow, QWidget,QStatusBar, QLabel, QLineEdit,QProgressBar, QPushButton, QVBoxLayout, QCheckBox, QHBoxLayout
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from libs.vid_downloader import download_video
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
        self.clear_button = QPushButton("Clear")
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
        main_layout.addWidget(self.clear_button)
        main_layout.addWidget(self.progress_bar)

        # Set layout
        central_widget.setLayout(main_layout)

        # Connect buttons to functions
        self.evdnce_chkbx.stateChanged.connect(self.toggle_api_input_visibility)
        self.scrape_btn.clicked.connect(self.scraping)
        self.clear_button.clicked.connect(self.clear_clicked)
        self.setGeometry(0,0, *percentSize(app,30,60))

        # Set window properties
        self.setWindowTitle("URL Checker")
        self.center()

    def toggle_api_input_visibility(self,state):
        if state == 2:
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
    
    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)  # Update progress bar value
        if value == 100:
            # Enable the button when the task is finished
            self.scraping_finished()


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
        
    def clear_clicked(self):
        self.url_input.clear()

    def center(self):
        qRect = self.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())


