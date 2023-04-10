(This readme is copied from [this repo](https://github.com/gavinnn101/ezflyff) so it may be slightly innacurate but I don't think so.)

# Features
* Individual profiles
* * Auto login multiple accounts (no need to manually login to an incognito browser.)
* * in-game settings unique to each profile
* * Set each profile's window position and/or size in `profiles/$PROFILE_NAME/settings.ini`
* Auto assist
* * Set hotkeys and intervals in `profiles/$PROFILE_NAME/settings.ini` (intervals are in seconds.)
* * Manually follow your main and then click the toggle hotkey for your assist/rm account to start casting

# Installation
* Install python: https://www.python.org/downloads/
* Open a terminal/shell in the ezflyff folder and run the command: `pip install -r requirements.txt`

# Running program
**First Run**
* Run `quick_start.bat` to run the program and create a default settings profile.
* * First launch will create a `profiles/default` profile for you. (You can change the name of this profile after if you want.)
* * To add a new profile you can copy the existing profile and change the name. The script program will automatically load all profiles under the profiles directory.
* * You'll want to edit the window and auto assist settings in `profiles/$PROFILE_NAME/settings.ini` for all profiles as needed.

**Every run after the first one :^)**

* After you get your profiles and settings setup you can run `quick_start.bat` every time to load your clients with their settings.
