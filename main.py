import configparser
import os
import random
import sys
import time
import win32api
import win32con
from win32gui import FindWindow, SendMessage
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSignal, QThread
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile, QWebEngineView
from PyQt5.QtWidgets import QApplication, QWidget

from loguru import logger
from key_codes import KEY_MAP


# https://stackoverflow.com/questions/67599432/setting-the-same-icon-as-application-icon-in-task-bar-for-pyqt5-application
# Get taskbar to display the correct icon
import ctypes
myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Full path to directory where the script is launched from.
ezflyff_dir = sys.path[0]


class FlyffClient(QWidget):
    auto_assist_stop_signal = pyqtSignal()
    def __init__(self, profile_name, *args, **kwargs):
        super(FlyffClient, self).__init__(*args, **kwargs)
        self.setWindowTitle("ezFlyff")
        self.url = "https://universe.flyff.com/play"
        self.ezflyff_dir = "C:\\Users\\Gavin\\Desktop\\ezflyff"
        self.profile_name = profile_name
        self.profile_settings = get_profile_settings(self.profile_name)

        # Initialize toggle listener for Auto Assist
        self.toggle_listener_thread = QThread()
        self.toggle_listener = ToggleListener(self.profile_name, self.profile_settings)
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
            self.auto_assist = AutoAssist(self.profile_name, self.profile_settings)
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


    def create_new_window(self, profile_name):
        logger.info("create_new_window called")
        browser = QWebEngineView()
        browser.setAttribute(Qt.WA_DeleteOnClose)
        browser.setWindowTitle(f"ezFlyff - {profile_name}")

        # Apply user settings from profile_settings.ini
        width_setting = int(self.profile_settings["window"]["window_width"])
        height_setting = int(self.profile_settings["window"]["window_height"])
        logger.debug(f"Window width: {width_setting} | Window height: {height_setting}")

        # Set window x,y position
        x_setting = int(self.profile_settings["window"]["window_x_pos"])
        y_setting = int(self.profile_settings["window"]["window_y_pos"])
        logger.debug(f"Window x: {x_setting} | Window y: {y_setting}")

        browser.resize(width_setting, height_setting)
        browser.move(x_setting, y_setting)

        profile = QWebEngineProfile(profile_name, browser)
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"
        )
        profile.setCachePath(f"{self.ezflyff_dir}\\profiles\\{profile_name}\\cache")
        profile.setPersistentStoragePath(f"{self.ezflyff_dir}\\profiles\\{profile_name}")
        page = QWebEnginePage(profile, browser)

        browser.setPage(page)
        browser.load(QUrl(self.url))
        browser.show()
        return browser


#################
# Auto Assist
#################

class AutoAssist(QObject):
    finished = pyqtSignal()
    def __init__(self, profile_name, profile_settings, *args, **kwargs):
        super(AutoAssist, self).__init__(*args, **kwargs)
        self.profile_name = profile_name
        self.profile_settings = profile_settings
        self.heal_hotkey = self.profile_settings["assist"]["heal_hotkey"]
        self.heal_interval = int(self.profile_settings["assist"]["heal_interval"])
        self.buff_hotkey = self.profile_settings["assist"]["buff_hotkey"]
        self.buff_interval = int(self.profile_settings["assist"]["buff_interval"])

        self.game_handle = get_game_handle(self.profile_name)
        self.running = False

    def stop(self):
        logger.info(f"Auto Assist is stopping on profile {self.profile_name}")
        self.running = False

    def press_key(self, handle, hotkey):
        """Gets key map for hotkey, presses the hotkey, and waits a randomized fraction of a second."""
        hotkey = KEY_MAP[hotkey]
        SendMessage(handle, win32con.WM_KEYDOWN, hotkey, 0)
        time.sleep(0.5 + random.random())
        SendMessage(handle, win32con.WM_KEYUP, hotkey, 0)
     
    def assist_loop(self):
        def buff_character(self):
            """Presses the buff hotkey and waits for the buff interval."""
            logger.info(f"pressing buff hotkey {self.buff_hotkey} on {self.profile_name}")
            self.press_key(self.game_handle, self.buff_hotkey)
            logger.info("Sleeping 5 seconds while character buffs")
            time.sleep(5 + random.random())  # To make sure buffs arent interrupted by a heal
            buff_timer = time.perf_counter()  # Reset buff timer
            return buff_timer

        def heal_character(self):
            """Presses the heal hotkey and sleeps for the heal interval."""
            logger.info(f"Sleeping {self.heal_interval} seconds...")
            time.sleep(self.heal_interval + random.random())
            logger.info(f"pressing heal hotkey {self.heal_hotkey} on {self.profile_name}.")
            self.press_key(self.game_handle, self.heal_hotkey)

        self.running = True
        logger.info(f"Auto Assist is running on profile {self.profile_name}")
        buff_timer = buff_character(self)
        while self.running:
            heal_character(self)
            buff_timer_check = time.perf_counter()
            if buff_timer_check - buff_timer > self.buff_interval:
                buff_timer = buff_character(self)
        self.finished.emit()



#################
# Toggle Listener
#################

class ToggleListener(QObject):
    toggle_signal = pyqtSignal(bool)
    def __init__(self, profile_name, profile_settings, *args, **kwargs):
        super(ToggleListener, self).__init__(*args, **kwargs)
        self.profile_name = profile_name
        self.profile_settings = profile_settings
        logger.debug(type(self.profile_settings))
        self.toggle_key = self.profile_settings["assist"]["toggle_key"]
        self.toggle_state = False


    def toggle_key_listener(self):
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


def create_settings_dir(profile_name):
    """Creates the profile directory and subdirectories if they don't exist."""
    logger.info("create_settings_dir called")
    dir_path = f"{ezflyff_dir}\\profiles\\{profile_name}"

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logger.info(f"Created directory {dir_path}")
    else:
        logger.info(f"Directory {dir_path} already exists")


def get_profile_settings(profile_name):
    """Loads profile settings from profile_settings.ini or creates a default if it doesn't exist."""
    logger.info("get_profile_settings called")
    config = configparser.ConfigParser()
    settings_path = f"{ezflyff_dir}\\profiles\\{profile_name}\\settings.ini"
    if not os.path.isfile(settings_path):
        logger.info(f"Creating settings.ini for profile {profile_name}")
        # Add window settings to settings.ini
        config.add_section("window")
        config.set("window", "window_width", "800")
        config.set("window", "window_height", "600")
        config.set("window", "window_x_pos", "0")
        config.set("window", "window_y_pos", "0")
        # Add assist settings to settings.ini
        config.add_section("assist")
        config.set("assist", "toggle_key", "-")
        config.set("assist", "heal_hotkey", "3")
        config.set("assist", "heal_interval", "2")
        config.set("assist", "buff_hotkey", "4")
        config.set("assist", "buff_interval", "300")
        with open(settings_path, "w") as config_file:
            config.write(config_file)
    config.read(settings_path)
    return config


def load_profiles():
    """Loads profiles from profiles directory or creates a 'default' if none exist."""
    profile_list = []
    profiles_path = f"{ezflyff_dir}\\profiles"
    if not os.path.exists(profiles_path):
        os.makedirs(profiles_path)
        logger.info(f"Created directory {profiles_path}")

    profiles = os.listdir(profiles_path)
    if len(profiles) == 0:
        logger.info("No profiles found. Creating default profile.")
        create_settings_dir("default")
        profiles.append("default")
    else:
        for profile in profiles:
            profile_list.append(profile)
    return profiles


def get_game_handle(profile_name):
    """Gets handle to game window."""
    logger.debug("get_game_handle called")
    game_window_name = f"ezFlyff - {profile_name}"
    game_window_class = "Qt5152QWindowIcon"
    return FindWindow(game_window_class, game_window_name)


#################
# Main
#################

clients = []
game_windows = []
profiles = ['main', 'fullsupport']

app = QApplication(sys.argv)
app.setApplicationName("ezFlyff")

for profile in profiles:
    create_settings_dir(profile)
    client = FlyffClient(profile)
    window = client.create_new_window(client.profile_name)

    # Keep reference open so windows don't close.
    clients.append(client)
    game_windows.append(window)


sys.exit(app.exec_())