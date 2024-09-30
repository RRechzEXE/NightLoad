import os
import subprocess
import threading
import queue
import re
import psutil
import time
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox, QComboBox, QMenu, QMenuBar, QAction, QHBoxLayout, QSizePolicy, QFrame, QInputDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
import sys

log_file_path = "download_logs.txt"
github_repo_url = "https://github.com/RRechzEXE/NightLoad/"  # GitHub repo URL

def write_to_log(message):
    with open(log_file_path, "a") as log_file:
        log_file.write(message + "\n")

def download_with_aria2(url, options=[]):
    aria2_path = r"C:\BasicDownload\aria2-1.37.0-win-64bit-build1\aria2c.exe"
    command = [aria2_path] + options + [url]
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process
    except Exception as e:
        write_to_log(f"Failed to start download: {str(e)}")
        return None

def monitor_download(process, output_queue):
    try:
        for line in iter(process.stdout.readline, ''):
            output_queue.put(line)
            write_to_log(f"stdout: {line.strip()}")

        process.stdout.close()
        process.wait()
        output_queue.put("done")
    except Exception as e:
        output_queue.put(f"error: {str(e)}")
        write_to_log(f"Error: {str(e)}")

    for err_line in iter(process.stderr.readline, ''):
        output_queue.put(f"error: {err_line.strip()}")
        write_to_log(f"stderr: {err_line.strip()}")

    process.stderr.close()

def get_latest_release_info():
    try:
        response = requests.get(github_repo_url)
        response.raise_for_status()
        release_data = response.json()
        tag_name = release_data['Version-414']
        download_url = release_data['assets'][0]['https://github.com/RRechzEXE/NightLoad/releases/tag/Version-414']
        return tag_name, download_url
    except Exception as e:
        write_to_log(f"Failed to get latest release info: {str(e)}")
        return None, None

def download_file(url, local_filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(local_filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    except Exception as e:
        write_to_log(f"Failed to download file: {str(e)}")

class DownloadManager(QWidget):
    def __init__(self):
        super().__init__()

        self.aria2_path = r"C:\BasicDownload\aria2-1.37.0-win-64bit-build1\aria2c.exe"
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Project NightLoad: Open Source Project with Aria2')
        self.setGeometry(100, 100, 800, 400)
        self.setFixedSize(800, 400)

        layout = QVBoxLayout()

        # Menü çubuğunu oluştur
        self.menubar = QMenuBar(self)
        self.settings_menu = QMenu('Settings', self)
        self.help_menu = QMenu('Help', self)

        self.theme_action = QAction('Theme', self)
        self.theme_action.triggered.connect(self.show_theme_selector)
        self.settings_menu.addAction(self.theme_action)

        self.update_action = QAction('Update', self)
        self.update_action.triggered.connect(self.check_for_updates)
        self.settings_menu.addAction(self.update_action)

        self.about_action = QAction('About', self)
        self.about_action.triggered.connect(self.show_about_me)
        self.support_action = QAction('Support', self)
        self.support_action.triggered.connect(self.open_support_link)
        self.wallpapers_action = QAction('Wallpapers', self)
        self.wallpapers_action.triggered.connect(self.open_wallpapers_link)
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.support_action)
        self.help_menu.addAction(self.wallpapers_action)

        self.menubar.addMenu(self.settings_menu)
        self.menubar.addMenu(self.help_menu)

        layout.setMenuBar(self.menubar)

        self.url_label = QLabel('Download URL:')
        self.url_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.url_label)

        self.url_input = QLineEdit(self)
        self.url_input.setFont(QFont('Arial', 12))
        layout.addWidget(self.url_input)

        self.thread_label = QLabel('Threads:')
        self.thread_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.thread_label)

        self.thread_entry = QLineEdit(self)
        self.thread_entry.setFont(QFont('Arial', 12))
        self.thread_entry.setText("4")
        layout.addWidget(self.thread_entry)

        self.download_button = QPushButton('Download', self)
        self.download_button.setFont(QFont('Arial', 12))
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        status_frame = QFrame(self)
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setLayout(QVBoxLayout())

        self.download_about_label = QLabel('Download About', self)
        self.download_about_label.setFont(QFont('Arial', 12, QFont.Bold))
        status_frame.layout().addWidget(self.download_about_label)

        self.download_status_label = QLabel('Download Status | 0%', self)
        self.network_speed_label = QLabel('Network Speed | 0.00 MB/s', self)
        status_frame.layout().addWidget(self.download_status_label)
        status_frame.layout().addWidget(self.network_speed_label)

        layout.addWidget(status_frame)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('', self)
        self.status_label.setFont(QFont('Arial', 5))
        self.status_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_label)

        self.text_label = QLabel('❤️ Thank you for choosing NightLoad ❤️\n#Updated | v4.1.3', self)
        self.text_label.setFont(QFont('Canva Sans', 8))
        self.text_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        layout.addWidget(self.text_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(spacer)

        self.setLayout(layout)
        self.set_dark_theme()

        self.process = None
        self.output_queue = None
        self.last_bytes_sent = 0
        self.last_check_time = time.time()

    def start_download(self):
        url = self.url_input.text()
        if not url:
            QMessageBox.critical(self, "Error", "Please enter a URL to download.")
            return

        if not os.path.exists(self.aria2_path):
            QMessageBox.critical(self, "Error", "Aria2 not found. Please ensure that aria2 is installed at the specified path.")
            return

        thread_count = self.thread_entry.text()
        if not thread_count.isdigit() or int(thread_count) < 1:
            QMessageBox.critical(self, "Error", "Please enter a valid number for threads.")
            return

        options = ["-s", thread_count, "-x", thread_count]

        self.download_button.setEnabled(False)
        self.download_button.setText("Your file is downloading...")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #7F8C8D;
                color: #BDC3C7;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
        """)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Downloading...")
        
        self.download_about_label.setVisible(True)
        self.download_status_label.setVisible(True)
        self.network_speed_label.setVisible(True)

        self.process = download_with_aria2(url, options)
        if not self.process:
            return
        
        self.output_queue = queue.Queue()
        
        self.download_thread = threading.Thread(target=monitor_download, args=(self.process, self.output_queue))
        self.download_thread.start()

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_progress)
        self.monitor_timer.start(1000)

        self.speedtest_thread = threading.Thread(target=self.update_speed)
        self.speedtest_thread.start()

    def update_progress(self):
        if self.process is None:
            return
        
        while not self.output_queue.empty():
            line = self.output_queue.get_nowait()

            if line.startswith("error"):
                self.status_label.setText("An error occurred.")
                self.download_button.setEnabled(True)
                self.download_button.setText("Download")
                self.download_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB;
                        color: #FFFFFF;
                        padding: 10px;
                        border-radius: 5px;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #2980B9;
                    }
                """)
                self.progress_bar.setVisible(False)
                self.monitor_timer.stop()
                return

            if "download complete" in line.lower():
                self.status_label.setText("Download completed!")
                self.download_button.setEnabled(True)
                self.download_button.setText("Download")
                self.download_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2ECC71;
                        color: #FFFFFF;
                        padding: 10px;
                        border-radius: 5px;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #27AE60;
                    }
                """)
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
                self.monitor_timer.stop()
                return

            match = re.search(r'\[(\d+\.\d+)%\]', line)
            if match:
                progress = float(match.group(1))
                self.progress_bar.setValue(int(progress))
                self.download_status_label.setText(f'Download Status | {progress:.2f}%')

    def update_speed(self):
        while True:
            net_io_counters = psutil.net_io_counters()
            bytes_sent = net_io_counters.bytes_sent
            bytes_recv = net_io_counters.bytes_recv

            current_time = time.time()
            time_diff = current_time - self.last_check_time

            upload_speed = (bytes_sent - self.last_bytes_sent) / time_diff
            download_speed = (bytes_recv - self.last_bytes_recv) / time_diff

            upload_speed_mbps = upload_speed / (1024 * 1024)
            download_speed_mbps = download_speed / (1024 * 1024)

            self.network_speed_label.setText(f'Network Speed | {download_speed_mbps:.2f} MB/s')

            self.last_bytes_sent = bytes_sent
            self.last_bytes_recv = bytes_recv
            self.last_check_time = current_time

            time.sleep(1)

    def show_theme_selector(self):
        themes = ["Dark", "Light", "Auto"]
        selected_theme, ok = QInputDialog.getItem(self, "Select Theme", "Choose a theme:", themes, 0, False)

        if ok and selected_theme:
            if selected_theme == "Dark":
                self.set_dark_theme()
            elif selected_theme == "Light":
                self.set_light_theme()
            elif selected_theme == "Auto":
                self.set_auto_theme()

    def set_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2C3E50;
                color: #ECF0F1;
            }
            QLabel {
                color: #ECF0F1;
            }
            QLineEdit {
                background-color: #34495E;
                color: #ECF0F1;
                padding: 5px;
                border-radius: 5px;
                border: 1px solid #7F8C8D;
            }
            QPushButton {
                background-color: #3498DB;
                color: #FFFFFF;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QProgressBar {
                background-color: #7F8C8D;
                color: #FFFFFF;
                border: 1px solid #BDC3C7;
                border-radius: 5px;
            }
        """)

    def set_light_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #ECF0F1;
                color: #2C3E50;
            }
            QLabel {
                color: #2C3E50;
            }
            QLineEdit {
                background-color: #BDC3C7;
                color: #2C3E50;
                padding: 5px;
                border-radius: 5px;
                border: 1px solid #7F8C8D;
            }
            QPushButton {
                background-color: #3498DB;
                color: #FFFFFF;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QProgressBar {
                background-color: #BDC3C7;
                color: #2C3E50;
                border: 1px solid #7F8C8D;
                border-radius: 5px;
            }
        """)

    def set_auto_theme(self):
        current_hour = time.localtime().tm_hour
        if 8 <= current_hour <= 19:
            self.set_light_theme()
        else:
            self.set_dark_theme()

    def check_for_updates(self):
        latest_version, download_url = get_latest_release_info()
        if latest_version:
            QMessageBox.information(self, "Update Available", f"Latest version: {latest_version}")
        else:
            QMessageBox.information(self, "No Updates", "You are using the latest version.")

    def show_about_me(self):
        QMessageBox.information(self, "About App", "Project NightLoad: Open Source Project with Aria2\n\nApp: The Project NightLoad\nVersion: v4.1.3-Stable\nBuild: PNL29092024-V4.1-Offical\nDeveloped by @RRechzEXE & @Rescci\n\n*Present by WallsHunter Media")

    def open_support_link(self):
        QDesktopServices.openUrl(QUrl("https://discord.gg/WXr4j6Cr"))

    def open_wallpapers_link(self):
        QDesktopServices.openUrl(QUrl("https://t.me/WallsHunterHQ"))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    download_manager = DownloadManager()
    download_manager.show()
    sys.exit(app.exec_())
