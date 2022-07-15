import sys
import time
import win32api
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSignal, pyqtSlot, QThread, QMutex, QMutexLocker, QTimer
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile, QWebEngineView
from PyQt5.QtWidgets import QApplication, QWidget

from loguru import logger


class FlyffClient(QWidget):
    auto_assist_stop_signal = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super(FlyffClient, self).__init__(*args, **kwargs)
        self.setWindowTitle("ezFlyff")
        self.flyff_url = "https://universe.flyff.com/play"
        self.ezflyff_dir = "C:\\Users\\Gavin\\Desktop\\ezflyff"
        self.profile_name = "test_profile"
        self.toggle_key = "`"


        # Initialize toggle listener for Auto Assist
        self.toggle_listener_thread = QThread()
        self.toggle_listener = ToggleListener(self.profile_name)
        self.toggle_listener.moveToThread(self.toggle_listener_thread)
        # Connect toggle key signal to on_toggle_key_pressed
        self.toggle_listener.toggle_signal.connect(self.on_toggle_key_pressed)
        # Start the toggle listener thread
        self.toggle_listener_thread.started.connect(self.toggle_listener.toggle_key_listener)
        self.toggle_listener_thread.start()


    def on_toggle_key_pressed(self, key_state):
        logger.debug("on_toggle_key_pressed called")
        if key_state == True:
            logger.debug('Starting Auto Assist thread')
            # Initialize Auto Assist thread
            self.auto_assist_thread = QThread()
            self.auto_assist = AutoAssist(self.profile_name)
            self.auto_assist_stop_signal.connect(self.auto_assist.stop)
            self.auto_assist.moveToThread(self.auto_assist_thread)
            # https://stackoverflow.com/questions/49886313/how-to-run-a-while-loop-with-pyqt5
            self.auto_assist.finished.connect(self.auto_assist_thread.quit)  # connect the workers finished signal to stop thread
            self.auto_assist.finished.connect(self.auto_assist.deleteLater)  # connect the workers finished signal to clean up worker
            self.auto_assist_thread.finished.connect(self.auto_assist_thread.deleteLater)  # connect threads finished signal to clean up thread
            self.auto_assist_thread.started.connect(self.auto_assist.assist_loop)  # On thread start, exec assist_loop()
            self.auto_assist_thread.finished.connect(self.auto_assist.stop)  # On thread finish, stop the assist loop
            # Start thread
            self.auto_assist_thread.start()
        else:
            logger.debug('Stopping Auto Assist thread')
            self.auto_assist_stop_signal.emit()


    def closeEvent(self, event):
        logger.info("closeEvent called")
        self.toggle_listener.stop()
        self.auto_assist.stop()
        self.toggle_listener_thread.quit()
        self.toggle_listener_thread.wait()
        self.toggle_listener_thread.terminate()
        self.auto_assist_thread.quit()
        self.auto_assist_thread.wait()
        self.auto_assist_thread.terminate()
        event.accept()


    def create_new_window(self, url, profile_name):
        logger.info("create_new_window called")
        browser = QWebEngineView()
        browser.setAttribute(Qt.WA_DeleteOnClose)

        profile = QWebEngineProfile(profile_name, browser)
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"
        )
        profile.setCachePath(f"{self.ezflyff_dir}\\profiles\\{profile_name}\\cache")
        profile.setPersistentStoragePath(f"{self.ezflyff_dir}\\profiles\\{profile_name}")
        page = QWebEnginePage(profile, browser)

        browser.setPage(page)
        browser.load(QUrl(url))
        browser.show()
        return browser


#################
# Auto Assist
#################

class AutoAssist(QObject):
    finished = pyqtSignal()
    def __init__(self, profile_name, *args, **kwargs):
        super(AutoAssist, self).__init__(*args, **kwargs)
        self.profile_name = profile_name
        self.toggle_key = "`"
        self.running = False

    def stop(self):
        logger.info(f"Auto Assist is stopping on profile {self.profile_name}")
        self.running = False

     
    def assist_loop(self):
        self.running = True
        logger.info(f"Auto Assist is running on profile {self.profile_name}")
        while self.running:
            logger.info('pressing heal')
            time.sleep(2)
            logger.success('heal pressed')
        self.finished.emit()



#################
# Toggle Listener
#################

class ToggleListener(QObject):
    toggle_signal = pyqtSignal(bool)
    def __init__(self, profile_name, *args, **kwargs):
        super(ToggleListener, self).__init__(*args, **kwargs)
        self.profile_name = profile_name
        self.toggle_key = 'z'
        self.toggle_state = False


    def toggle_key_listener(self):
        from key_codes import KEY_MAP
        """Toggles key listener."""
        logger.debug(f"Toggle key listener started for profile {self.profile_name}")
        self.toggle_state = False
        key_code = KEY_MAP[self.toggle_key]
        logger.debug(f'Using toggle key {self.toggle_key} | key code {key_code}')

        while True:
            # logger.debug("Checking for key press")
            if win32api.GetAsyncKeyState(key_code):
                if self.toggle_state == True:
                    logger.info(f"{self.profile_name} - Assist mode disabled")
                    self.toggle_state = False
                    self.toggle_signal.emit(self.toggle_state)
                    time.sleep(2)
                else:
                    logger.info(f"{self.profile_name} - Assist mode enabled")
                    self.toggle_state = True
                    self.toggle_signal.emit(self.toggle_state)
                    time.sleep(2)


#################
# Main
#################

game_windows = []
profiles = ['main', 'alt']

app = QApplication(sys.argv)
app.setApplicationName("ezFlyff")

client = FlyffClient()
client.profile_name = 'main'
window = client.create_new_window(client.flyff_url, client.profile_name)
game_windows.append(window)


sys.exit(app.exec_())