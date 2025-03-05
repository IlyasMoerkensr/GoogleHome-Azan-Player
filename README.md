# GoogleHome-Azan-Player

This application automatically fetches prayer times from AlAdhan and plays the Azan on a Google Home device. It:
1) Let’s you set your city, country, and calculation method.
2) Fetches fresh prayer times daily.
3) Schedules the Azan 1 minute ahead of each prayer time and runs indefinitely.
4) Raises the device volume for the Azan, then restores it.

## Setup
1. Ensure Python 3 is installed.
2. Install dependencies:
   - `pip install requests schedule pychromecast`
3. Update settings in `azan_google_home.py` (e.g., CITY, COUNTRY, METHOD).

## Usage
Run the script in the background:
```
nohup /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 "/Users/nafislord/Documents/Programming Projects/Python/Azan Player/azan_google_home.py" > azan.log 2>&1 &
```
To kill the process:
```
pkill -f azan_google_home.py
```
To check running instances:
```
ps aux | grep azan_google_home.py
```
Logs are written to `azan.log`.

## Contributing
Feel free to open pull requests with new ideas or improvements.

## License
MIT