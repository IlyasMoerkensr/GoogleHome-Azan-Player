import requests
import schedule
import time
import datetime
import pychromecast
import sys

################################################
# Dynamic Azan Scheduler
# ------------------------------------------------
# This script:
#   1) Lets you set city/country/method.
#   2) Fetches daily times from AlAdhan (timingsByCity/<DD-MM-YYYY>).
#   3) Schedules Azan 1 minute earlier for each prayer.
#   4) After Isha passes, moves on to the next day.
#   5) Runs indefinitely.
#   6) Temporarily raises Google Home volume for Azan, then restores it.
#   7) Logs all key events and failures.
#   8) Supports an optional daily test time.
#
# Once you run it, it remains active:
#   - If the current time is after Isha, it immediately loads tomorrow's times.
#   - Otherwise it schedules today's remaining prayers.
#   - After Isha passes, it automatically schedules the next day.
################################################

# Flush logs immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

###################################
# USER CONFIG
###################################
CITY = "Madrid"           # City name
COUNTRY = "Spain"         # Country name
METHOD = 3                 # AlAdhan method (e.g., 3 = Muslim World League)
TEST_TIME = ""       # Set to "" if no daily test azan is needed
TARGET_DEVICE_NAME = "Parents Room speaker"  # Google Home device name to cast

# Publicly hosted Azan MP3 URL
AZAN_URL = "https://www.islamcan.com/audio/adhan/azan1.mp3"

# Volume for Azan
AZAN_VOLUME = 1.0  # 100% during Azan

################################################
# get_prayer_times_for_date
################################################
def get_prayer_times_for_date(date_obj, city, country, method=3):
    date_str = date_obj.strftime("%d-%m-%Y")
    url = (
        f"https://api.aladhan.com/v1/timingsByCity/{date_str}"  # date-specific
        f"?city={city}"  # city
        f"&country={country}"  # country
        f"&method={method}"    # method
    )
    print(f"📡 Fetching prayer times for {date_str} from: {url}")

    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        if "data" in data and "timings" in data["data"]:
            t = data["data"]["timings"]
            return {
                "Fajr": t["Fajr"],
                "Dhuhr": t["Dhuhr"],
                "Asr": t["Asr"],
                "Maghrib": t["Maghrib"],
                "Isha": t["Isha"],
            }
    print("❌ Could not retrieve valid prayer times from AlAdhan.")
    return None

################################################
# connect_to_google_home
################################################
def connect_to_google_home():
    print("🔍 Searching for Google Home devices...")
    chromecasts, _ = pychromecast.get_chromecasts()
    print(f"🔎 Found {len(chromecasts)} Chromecast devices.")

    cast = next((c for c in chromecasts if c.name == TARGET_DEVICE_NAME), None)
    if not cast:
        print(f"❌ Could not find '{TARGET_DEVICE_NAME}' on the network.")
        return None

    print(f"✅ Found target device: {cast.name} (host: {cast.socket_client.host})")
    cast.wait()
    return cast

################################################
# play_azan
################################################
def play_azan():
    print("🔊 Starting Azan sequence...")
    try:
        cast = connect_to_google_home()
        if not cast:
            print("🚫 Aborting Azan: target device not found.")
            return

        original_volume = cast.status.volume_level
        print(f"🔊 Original Volume: {original_volume * 100:.0f}%")

        # Increase volume
        try:
            cast.set_volume(AZAN_VOLUME)
            print("🔊 Volume set to 100% for Azan.")
        except Exception as e:
            print(f"⚠️ Failed to set volume to 100%: {e}")

        # Play Azan
        mc = cast.media_controller
        try:
            print("🎵 Attempting to play Azan audio...")
            mc.play_media(AZAN_URL, "audio/mp3")
            time.sleep(2)
            mc.play()
            print("✅ Azan should be playing now.")
        except Exception as e:
            print(f"⚠️ Error playing Azan: {e}")

        # Wait ~3 minutes, restore volume
        time.sleep(180)
        try:
            cast.set_volume(original_volume)
            print(f"🔊 Volume restored to {original_volume * 100:.0f}%.")
        except Exception as e:
            print(f"⚠️ Failed to restore volume: {e}")

    except Exception as e:
        print(f"⚠️ Error in play_azan: {e}")

################################################
# parse_time
################################################
def parse_time(t_str):
    # Sometimes AlAdhan returns e.g. "20:30 (CEST)" => strip parentheses.
    base = t_str.split('(')[0].strip()
    hh_str, mm_str = base.split(":")
    return int(hh_str), int(mm_str)

################################################
# schedule_test_time
################################################
def schedule_test_time(date_obj, test_time_str):
    if not test_time_str:
        return

    print(f"🛠 Checking if we should schedule a test Azan at {test_time_str}...")
    try:
        hh, mm = parse_time(test_time_str)
    except:
        print(f"⚠️ TEST_TIME '{test_time_str}' invalid format, skipping.")
        return

    dt_test = datetime.datetime(date_obj.year, date_obj.month, date_obj.day, hh, mm)
    now = datetime.datetime.now()
    if dt_test > now:
        sch_time = dt_test.strftime("%H:%M")
        schedule.every().day.at(sch_time).do(play_azan)
        print(f"🛠️ Scheduled TEST Azan at {sch_time}")
    else:
        print(f"⚠️ Test time {test_time_str} already passed today.")

################################################
# schedule_daily_prayers
################################################
def schedule_daily_prayers(date_obj, prayer_times):
    print(f"\n📅 Scheduling daily Azan times for {date_obj.strftime('%d-%m-%Y')}...")
    for p, t_str in prayer_times.items():
        print(f"   {p}: {t_str}")

    for prayer, t_str in prayer_times.items():
        hh, mm = parse_time(t_str)
        dt_prayer = datetime.datetime(date_obj.year, date_obj.month, date_obj.day, hh, mm)
        dt_one_min_early = dt_prayer - datetime.timedelta(minutes=1)
        now = datetime.datetime.now()
        if dt_one_min_early > now:
            sch_time = dt_one_min_early.strftime("%H:%M")
            schedule.every().day.at(sch_time).do(play_azan)
            print(f"⏰ Scheduled {prayer} Azan (1 min early) at {sch_time}")

            # 10-min reminder
            ten_min_before = dt_prayer - datetime.timedelta(minutes=10)
            if ten_min_before > now:
                ten_min_notice = ten_min_before.strftime("%H:%M")
                # We'll just log a reminder 10 min prior
                def reminder_closure(pr=prayer, sch=sch_time):
                    print(f"🕰️ Reminder: {pr} Azan will start in 10 minutes at {sch}")
                schedule.every().day.at(ten_min_notice).do(reminder_closure)
                print(f"🕰️ Reminder set for {prayer} at {ten_min_notice}")
        else:
            print(f"⚠️ {prayer} time ({t_str}) already passed today.")

################################################
# main_loop
################################################
def main_loop(city, country, method=3):
    current_day = datetime.date.today()

    while True:
        schedule.clear()
        prayer_times = get_prayer_times_for_date(current_day, city, country, method)
        if not prayer_times:
            print("❌ Could not fetch prayer times. Retrying in 1 hour...")
            time.sleep(3600)
            continue

        # Schedule daily prayers + test time
        schedule_daily_prayers(current_day, prayer_times)
        schedule_test_time(current_day, TEST_TIME)

        # Wait until isha passes, then move on
        isha_hh, isha_mm = parse_time(prayer_times["Isha"])
        dt_isha = datetime.datetime(current_day.year, current_day.month, current_day.day, isha_hh, isha_mm)

        while True:
            now = datetime.datetime.now()
            if now > dt_isha:
                print("\n🌙 Isha passed, scheduling next day...")
                break
            schedule.run_pending()
            time.sleep(30)

        current_day += datetime.timedelta(days=1)

################################################
# Entry point
################################################
print("✅ Dynamic Azan Scheduler Running... Press CTRL+C to stop.")
main_loop(CITY, COUNTRY, METHOD)
