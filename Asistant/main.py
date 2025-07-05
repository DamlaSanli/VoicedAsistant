import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import re
import uuid
import smtplib
import subprocess
import sys
import webbrowser
import pyautogui
import pyttsx3
import speech_recognition as sr
import json
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import random
import numpy as np
import psutil 
import requests
from urllib.parse import quote
import os
import uuid
from playsound import playsound
from google.cloud import texttospeech
import dateparser
import difflib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import spotify_credentials
from spotify_credentials import CLIENT_ID, REDIRECT_URI, SCOPE
from spotify_credentials import CLIENT_SECRET
import spotipy
from spotipy.oauth2 import SpotifyOAuth



# OpenWeatherMap API Key (Buraya kendi API key'inizi girin)
WEATHER_API_KEY = "XXX"
NEWS_API_KEY = "XXX"
YOUTUBE_API_KEY ="XXX"
TMDB_API_KEY = "XXX"
SENDER_EMAIL = "XXX"
SENDER_PASSWORD = "XXX"

GENRE_MAP = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "sci-fi": 878,
    "science fiction": 878,
    "tv movie": 10770,
    "thriller": 53,
    "war": 10752,
    "western": 37
}


with open("intents.json") as file:
    data = json.load(file)

model = load_model("chat_model.h5")

with open("tokenizer.pkl", "rb") as f:
    tokenizer = pickle.load(f)

with open("label_encoder.pkl", "rb") as encoder_file:
    label_encoder = pickle.load(encoder_file)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_tts_credentials.json"


def speak(text, lang_code="en-US"):
    print(f"\033[1;34mAssistant replied:\033[0m {text}")

    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name="en-US-Wavenet-D"  # Erkek, doğal sesli Wavenet sesi
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.8,  # pyttsx3'teki rate-50 karşılığı
            pitch=0.0,          # Sesin tonu (pyttsx3 pitch ayarı yoksa 0.0 kullanılabilir)
            effects_profile_id=["telephony-class-application"]
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        file_name = f"temp_audio_{uuid.uuid4()}.mp3"
        with open(file_name, "wb") as out:
            out.write(response.audio_content)

        playsound(file_name)
        os.remove(file_name)

    except Exception as e:
        print("TTS Hatası:", e)
    
def command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            # Gürültü ayarı
            r.adjust_for_ambient_noise(source, duration=0.3)
            print("Listening........", end="", flush=True)
            
            # Dinleme parametreleri

            r.pause_threshold = 1.0
            r.phrase_threshold = 0.3
            r.sample_rate = 48000
            r.dynamic_energy_threshold = True
            r.operation_timeout = 5
            r.non_speaking_duration = 0.5
            r.dynamic_energy_adjustment = 2
            r.energy_threshold = 4000
            r.phrase_time_limit = 10

            # Dinleme işlemi
            audio = r.listen(
                source, 
                timeout=4,  # 4 saniye ses gelmezse timeout
                phrase_time_limit=8  # Maks 8 saniyelik ses
            )
        except sr.WaitTimeoutError:
            print("\rNo speech detected       ")
            return "no_speech"
        except Exception as e:
            print(f"\rMicrophone error: {str(e)}")
            return "error"

    try:
        print("\rRecognizing......", end="", flush=True)
        query = r.recognize_google(audio, language='en').strip().lower()
        print(f"\r\033[1;32mUser:\033[0m {query}")
        return query
    except sr.UnknownValueError:
        print("\rGoogle Speech Recognition could not understand audio")
        return "not_understood"
    except sr.RequestError as e:
        print(f"\rCould not request results from Google: {e}")
        return "api_error"
    except Exception as e:
        print(f"\rUnexpected error: {e}")
        return "error"

def handle_weather(query):
    city = None
    if " in " in query:
        city = query.split(" in ")[1].strip()
    else:
        speak("Which city's weather would you like to know?")
        city = command().lower()
    
    if not city or city == "none":
        return

    try:
        base_url = f"xxx"
        response = requests.get(base_url)
        data = response.json()

        if data.get("cod") == 200:
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]

            temp = main.get("temp", "N/A")
            humidity = main.get("humidity", "N/A")
            feels_like = main.get("feels_like", "N/A")
            weather_desc = weather.get("description", "N/A")

            speak(f"Weather in {city}:")
            speak(f"Temperature: {temp}°C, feels like {feels_like}°C")
            speak(f"Humidity: {humidity}%")
            speak(f"Description: {weather_desc}")
        else:
            error_message = data.get("message", "Unknown error")
            speak(f"Sorry, I couldn't get the weather. {error_message}")
    except Exception as e:
        print(f"Weather API error: {e}")
        speak("Sorry, I couldn't fetch the weather information. Please check your internet connection or try again later.")

def handle_news(query):
    valid_categories = ["business", "entertainment", "general", "health", "science", "sports", "technology"]
    category = next((cat for cat in valid_categories if cat in query.lower()), None)

    if not category:
        speak("Which category of news would you like? For example: technology, sports, business, health.")
        category = command().lower()
        if category == "none":
            return

    if category not in valid_categories:
        speak(f"Sorry, {category} is not a valid category. Showing general news instead.")
        category = "general"

    url = f"xx"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get("status") == "ok":
            articles = data.get("articles", [])
            if articles:
                speak(f"Here are some {category} headlines:")
                for article in articles[:3]:
                    speak(article.get("title", "No title"))
            else:
                speak("No news articles found.")
        else:
            speak("Sorry, I couldn't fetch the news.")
    except Exception as e:
        print(f"News API error: {e}")
        speak("An error occurred while fetching the news.")

def handle_youtube(query):


    try:
        search_term = ""

        # Eğer sadece "open youtube" varsa ve ek bir şey yoksa
        if query.strip().lower() == "open youtube":
            speak("Opening YouTube")
            webbrowser.open("https://www.youtube.com")
            return

        # Arama terimini belirle
        if "search" in query:
            parts = query.split("search", 1)
            if len(parts) > 1:
                search_term = parts[1].strip()
        elif "play" in query:
            parts = query.split("play", 1)
            if len(parts) > 1:
                search_term = parts[1].strip()
        elif "youtube" in query:
            parts = query.split("youtube", 1)
            if len(parts) > 1:
                search_term = parts[1].strip()

        # Arama terimi hâlâ boşsa kullanıcıdan al
        if not search_term:
            speak("What would you like me to search on YouTube?")
            search_term = command()
            if not search_term or search_term.lower() == "none":
                return

        # API isteği için parametreler
        params = {
            'part': 'snippet',
            'maxResults': 1,
            'q': search_term,
            'type': 'video',
            'key': YOUTUBE_API_KEY
        }

        # API isteği gönder
        response = requests.get(
            "xxx",
            params=params
        )
        data = response.json()

        # Hata kontrolü
        if response.status_code != 200:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            speak(f"YouTube API error: {error_msg}")
            return

        # Sonuçları işleme
        if data.get('items'):
            video_id = data['items'][0]['id']['videoId']
            video_title = data['items'][0]['snippet']['title']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            speak(f"Found: {video_title}")
            webbrowser.open(video_url)
        else:
            speak("No results found for your search")

    except Exception as e:
        print(f"YouTube Error: {str(e)}")
        speak("Failed to process YouTube command.")

def handle_social(query):
    query = query.lower()  # Küçük harfe çevir

    sites = {
        'facebook': 'https://www.facebook.com/',
        'whatsapp': 'https://web.whatsapp.com/',
        'instagram': 'https://www.instagram.com/'
    }

    # Alternatif yazımları da kapsayacak şekilde kontrol
    social_aliases = {
        'facebook': ['facebook', 'face book'],
        'whatsapp': ['whatsapp', 'whats app', 'what\'s app'],
        'instagram': ['instagram', 'insta gram', 'insta']
    }

    for site, keywords in social_aliases.items():
        for keyword in keywords:
            if keyword in query:
                speak(f"Opening your {site}")
                webbrowser.open(sites[site])
                return

    speak("No result found for social media command.")

def increase_volume(_):
    pyautogui.press("volumeup")

def decrease_volume(_):
    pyautogui.press("volumedown")

def mute_volume(_):
    pyautogui.press("volumemute")

def unmute_volume(_):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    # Eğer sessizdeyse aç
    if volume.GetMute():
        volume.SetMute(0, None) 

def open_app(query):
    apps = {
        "calculator": 'x',
        "calculate": 'x',
        "paint": 'x',
        "visual studio code": 'x',
        "notepad": 'x',
        "code": 'x',
    }

    for name, path in apps.items():
        if name in query.lower():
            os.startfile(path)
            return

def close_app(query):
    processes = {
        "calculator": "CalculatorApp.exe",
        "paint": "mspaint.exe",
        "visual studio code": "Code.exe",
        "notepad": "notepad.exe"
    }

    for name, process in processes.items():
        if name in query.lower():
            try:
                if name == "calculator":
                    subprocess.run([
                        'powershell', '-command',
                        'Get-Process CalculatorApp | Stop-Process -Force'
                    ], shell=True)
                else:
                    subprocess.run(['taskkill', '/f', '/im', process], shell=True)
            except Exception as e:
                print(f"Error: {e}")
                speak(f"Could not close {name}")
            return

def cal_day():
    day = datetime.datetime.today().weekday() + 1
    day_dict = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday"
    }
    return day_dict.get(day, "Unknown day")

def Time(_=None): 
    now = datetime.datetime.now()
    hour = now.hour
    t = now.strftime("%I:%M %p")
    day = cal_day()

    if 0 <= hour < 12:
        speak(f"Good Morning, it's {day} and the time is {t}")
    elif 12 <= hour < 16:
        speak(f"Good Afternoon, it's {day} and the time is {t}")
    else:
        speak(f"Good evening, it's {day} and the time is {t}")

def browsing(query_input=None):
    if "open" in query_input:
        speak("What should I search on Google?")
        search_query = command()  # kullanıcıdan sesli komut alır
        if search_query and search_query.lower() != "none":
            webbrowser.open(f"https://www.google.com/search?q={search_query}")
    elif "close" in query_input:
        speak("Closing browser")
        os.system("taskkill /f /im msedge.exe")

def condition(_=None):
    usage = str(psutil.cpu_percent())
    speak(f"CPU is at {usage} percent")
    battery = psutil.sensors_battery()
    percentage = battery.percent
    speak(f"Your system has {percentage} percent battery")


def suggest_movie(query):
    genre_input = command().lower()

    genre_id = None
    for name, gid in GENRE_MAP.items():
        if name in genre_input:
            genre_id = gid
            break

    if not genre_id:
        speak("Sorry, I couldn't identify the genre. Try saying action, comedy, horror, etc.")
        return

    url = f"xx"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or not data.get("results"):
        speak("I couldn't find any movies in that genre right now.")
        return

    movies = data["results"][:5]
    titles = [movie.get("title", "Unknown Title") for movie in movies]

    speak(f"Here are some {genre_input} movies you might like:")
    for i, title in enumerate(titles, 1):
        speak(f"{i}. {title}")

    speak("Do you want to watch one of them?")
    reply = command().lower()

    if "yes" in reply:
        speak("Which one would you like to watch?")
        selection = command().lower()

        index_map = {
            "first": 0, "the first": 0, "number one": 0, "1": 0,
            "second": 1, "the second": 1, "number two": 1, "2": 1,
            "third": 2, "the third": 2, "number three": 2, "3": 2,
            "fourth": 3, "the fourth": 3, "number four": 3, "4": 3,
            "fifth": 4, "the fifth": 4, "number five": 4, "5": 4
        }

        selected_index = next((idx for phrase, idx in index_map.items() if phrase in selection), None)

        if selected_index is not None and selected_index < len(titles):
            movie_title = titles[selected_index]
            speak(f"Opening {movie_title}. Enjoy!")
            webbrowser.open(f"https://www.google.com/search?q=watch+{movie_title.replace(' ', '+')}+full+movie")
        else:
            matched_title = next((title for title in titles if title.lower() in selection), None)
            if matched_title:
                speak(f"Opening {matched_title}. Enjoy!")
                webbrowser.open(f"https://www.google.com/search?q=watch+{matched_title.replace(' ', '+')}+full+movie")
            else:
                speak("Sorry, I couldn't find the movie you mentioned.")
    else:
        speak("Okay, let me know if you'd like suggestions later.")

def movie_info(query):

    movie_name = command().lower()

    search_url = f"xx"
    search_response = requests.get(search_url)
    search_data = search_response.json()

    if not search_data.get("results"):
        speak("Sorry, I couldn't find any information about that movie.")
        return

    first_result = search_data["results"][0]
    title = first_result.get("title", "Unknown Title")
    overview = first_result.get("overview", "No description available.")
    rating = first_result.get("vote_average", "No rating")
    release_date = first_result.get("release_date", "Unknown date")
    release_year = release_date.split("-")[0] if "-" in release_date else release_date

    info = f"{title} was released in {release_year}. It has a rating of {rating} out of 10. Here's a brief overview: {overview}"
    speak(info)

def normalize_email_address(text):
    text = text.lower()
    replacements = {
        " at ": "@", " dot ": ".", " underscore ": "_", " dash ": "-",
        " hyphen ": "-", " space ": "", " gmail com": "@gmail.com",
        " hotmail com": "@hotmail.com", " outlook com": "@outlook.com"
    }
    turkish_chars = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u" }

    for turkish, ascii_version in turkish_chars.items():
        text = text.replace(turkish, ascii_version)
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text.replace(" ", "").strip()

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def send_email(query=None):
    try:
        # 1. Alıcı e-posta adresini sesli al
        speak("Please tell me the recipient's email address.")
        recipient_raw = command()
        if not recipient_raw or recipient_raw == "none":
            speak("Recipient address not understood. Cancelling.")
            return

        recipient_email = normalize_email_address(recipient_raw)

        # 2. Adresin geçerliliğini kontrol et
        if not is_valid_email(recipient_email):
            speak("This doesn't seem like a valid email address. Please try again.")
            return

        # 3. E-posta konusu
        speak("What is the subject of the email?")
        subject = command()
        if not subject or subject == "none":
            speak("I need a subject to send your email.")
            return

        # 4. Mesaj içeriği
        speak("What would you like to say in the email?")
        message = command()
        if not message or message == "none":
            speak("I need a message to send your email.")
            return

        # 5. Onay iste
        speak(f"You're about to send an email to {recipient_email} with subject '{subject}' and message '{message}'. Should I go ahead and send it?")
        confirmation = command().lower()
        if "yes" not in confirmation:
            speak("Okay, the email was not sent.")
            return

        # 6. E-posta nesnesi oluştur
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        # 7. SMTP üzerinden gönder
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        speak("Your email has been sent successfully.")
        print(f"[DEBUG] Email sent to {recipient_email} | Subject: {subject}")

    except Exception as e:
        print(f"[ERROR] send_email: {e}")
        speak("Sorry, I couldn't send the email. Please check your internet connection and try again.")



def add_event(query=None):
    try:
        speak("When is the event?")
        date_str = command().lower()

        speak("What time is the event?")
        time_str = command().lower()

        speak("What is the event about?")
        description = command().lower()

        print(f"[DEBUG] Received: {date_str}, {time_str}, {description}")

        # Doğal dil tarihi yorumla
        event_datetime = dateparser.parse(f"{date_str} {time_str}")
        if not event_datetime:
            speak("I couldn't understand the date or time. Please try again.")
            return

        # Google Calendar bağlantısı
        SCOPES = ['xx']
        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)

                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)


        event = {
            'summary': description,
            'start': {
                'dateTime': event_datetime.isoformat(),
                'timeZone': 'Europe/Istanbul',
            },
            'end': {
                'dateTime': (event_datetime + datetime.timedelta(hours=1)).isoformat(),
                'timeZone': 'Europe/Istanbul',
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()

        speak(f"Your event '{description}' has been added on {event_datetime.strftime('%A, %B %d at %I:%M %p')}.")

    except Exception as e:
        print(f"[ERROR] add_event: {e}")
        speak("Sorry, something went wrong while adding the event.")

def list_events(query=None):
    try:
        speak("Let me check your upcoming events...")

        SCOPES = ['xx']
        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)

                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)

        # Şu andan itibaren gelecekteki etkinlikleri getir
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True,
            orderBy='startTime').execute()

        events = events_result.get('items', [])

        if not events:
            speak("You have no upcoming events.")
            return

        # Sohbet tarzında listeleme
        if len(events) == 1:
            response = "You have one upcoming event. "
        else:
            response = f"You have {len(events)} upcoming events. "

        for idx, event in enumerate(events, 1):
            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            try:
                start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', ''))
                start_formatted = start_dt.strftime("%A, %B %d at %I:%M %p")
            except Exception:
                start_formatted = start_raw

            summary = event.get('summary', 'No title')

            if idx == 1:
                response += f"The first is {summary} on {start_formatted}. "
            else:
                response += f"Then, {summary} on {start_formatted}. "

        speak(response.strip())

    except Exception as e:
        print(f"[ERROR] list_events: {e}")
        speak("Sorry, I couldn't fetch your events right now.")

def delete_event(query=None):
    try:
        speak("Which event would you like to delete? You can say the event name or the date.")
        event_query = command()

        SCOPES = ['xx']
        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)

                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)


        # Sadece gelecekteki etkinlikleri al
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=20, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            speak("There are no upcoming events to delete.")
            return

        # Kullanıcının söylediği tarih varsa çözümle
        parsed_date = dateparser.parse(event_query, languages=['en'])
        query_date = parsed_date.date() if parsed_date else None

        for event in events:
            summary = event.get('summary', '').lower()
            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', ''))
            start_date = start_dt.date()

            similarity = difflib.SequenceMatcher(None, event_query.lower(), summary).ratio()
            print(f"[DEBUG] Comparing '{event_query.lower()}' with '{summary}' → similarity: {similarity}")

            if similarity > 0.7 or (query_date and query_date == start_date):
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                speak(f"The event '{summary}' on {start_date.strftime('%A, %B %d')} has been deleted.")
                return

        speak("I couldn't find a matching event to delete.")

    except Exception as e:
        print(f"[ERROR] delete_event: {e}")
        speak("Something went wrong while trying to delete the event.")

def update_event(query=None):
    try:
        speak("Which event would you like to update? You can say the event name or the date.")
        event_query = command()

        SCOPES = ['xx']
        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)

                with open('token.json', 'w') as token:
                    token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)

        # Geçmiş ve gelecek tüm etkinlikleri al (1 yıl aralık)
        now = datetime.datetime.utcnow()
        time_min = (now - datetime.timedelta(days=365)).isoformat() + 'Z'
        time_max = (now + datetime.timedelta(days=365)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=time_min, timeMax=time_max,
            maxResults=50, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            speak("You have no events to update.")
            return

        parsed_query_date = dateparser.parse(event_query, languages=['en'])
        query_date = parsed_query_date.date() if parsed_query_date else None

        matched_event = None
        for event in events:
            summary = event.get('summary', '').lower()
            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', ''))
            start_date = start_dt.date()

            similarity = difflib.SequenceMatcher(None, event_query.lower(), summary).ratio()
            if similarity > 0.7 or (query_date and query_date == start_date):
                matched_event = event
                break

        if not matched_event:
            speak("I couldn't find a matching event to update.")
            return

        updated_event = matched_event.copy()
        original_start = matched_event['start'].get('dateTime', matched_event['start'].get('date'))
        original_dt = datetime.datetime.fromisoformat(original_start.replace('Z', ''))

        # Yeni tarih
        speak("Do you want to change the date?")
        if "yes" in command().lower():
            speak("Please tell me the new date.")
            new_date_str = command()
            new_date = dateparser.parse(new_date_str, languages=['en'])
        else:
            new_date = original_dt

        # Yeni saat
        speak("Do you want to change the time?")
        if "yes" in command().lower():
            speak("Please tell me the new time.")
            new_time_str = command()
            new_time = dateparser.parse(new_time_str, languages=['en'])
        else:
            new_time = original_dt

        # Yeni açıklama
        speak("Do you want to change the description?")
        if "yes" in command().lower():
            speak("Please tell me the new description.")
            new_desc = command()
            updated_event['summary'] = new_desc
            updated_event['description'] = new_desc

        # Yeni tarih-saat birleştir
        new_dt = datetime.datetime.combine(new_date.date(), new_time.time())
        updated_event['start']['dateTime'] = new_dt.isoformat()
        updated_event['end']['dateTime'] = (new_dt + datetime.timedelta(hours=1)).isoformat()

        # Güncelleme işlemi
        service.events().update(
            calendarId='primary',
            eventId=matched_event['id'],
            body=updated_event
        ).execute()

        speak(f"Your event has been updated to {updated_event.get('summary')} on {new_dt.strftime('%A, %B %d at %I:%M %p')}.")

    except Exception as e:
        print(f"[ERROR] update_event: {e}")
        speak("Something went wrong while updating the event.")


def get_responses_by_tag(tag):
    for intent in data['intents']:
        if intent['tag'] == tag:
            return intent['responses']
    return ["I'm not sure how to respond to that."]

def process_query(query):
    # Ön filtreleme
    if len(query.split()) < 1 or any(c.isdigit() for c in query):
        speak("I need proper words to understand you")
        return

    # Tokenizasyon
    sequences = tokenizer.texts_to_sequences([query])
    if not sequences or sum(sequences[0]) == 0:
        print("Those words don't make sense to me")
        return

    # Model tahmini
    padded = pad_sequences(sequences, maxlen=20, truncating='post')


    predictions = model.predict(padded, verbose=0)[0]
    

    
    confidence = np.max(predictions)
    
    # Güven kontrolü
    if confidence < 0.70: 
        print(f"Low confidence: {confidence:.2f}")
        print(random.choice([
            "I'm not quite sure, could you rephrase?",
            "Can you say that differently?",
            "I didn't catch that clearly"
        ]))
        return

    # Etiket belirleme
    predicted_index = np.argmax(predictions)
    tag = label_encoder.inverse_transform([predicted_index])[0]
    
    # Cevap verme
    responses = get_responses_by_tag(tag)
    if not responses:
        print("I'm not sure how to respond")
        return
    
    speak(random.choice(responses))
    
    # Handler çalıştırma
    if tag in TAG_HANDLERS:
        try:
            TAG_HANDLERS[tag](query)
        except Exception as e:
            print(f"Handler error: {e}")
            speak("Something went wrong with that action")


def current_music(query=None):
    try:
    
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices()
        if not devices['devices']:
            speak("I couldn't find an active device on Spotify.")
            print("[DEBUG] No active Spotify device found.")
            return

        current_track = sp.current_playback(market="US")

        if current_track and current_track.get('item'):
            track_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            speak(f"The song that's playing right now is {track_name} by {artist_name}.")
            print(f"[DEBUG] Now Playing: {track_name} - {artist_name}")
        else:
            speak("There is no song playing right now.")
            print("[DEBUG] Nothing is currently playing on Spotify.")

    except Exception as e:
        print(f"[ERROR] Spotify current_music: {e}")
        speak("Sorry, I encountered an error while checking the current song on Spotify.")

def play_music_spotify(query=None):
    try:
    
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices()
        if not devices['devices']:
            speak("I couldn't find an active device on Spotify.")
            print("[DEBUG] No active Spotify device found.")
            return

        current_playback = sp.current_playback()
        if current_playback and current_playback.get('item'):
            last_song = current_playback['item']['name']
            artist_name = current_playback['item']['artists'][0]['name']
            speak(f"Your last song was {last_song} by {artist_name}. Would you like to continue listening?")
            print(f"[DEBUG] Last track: {last_song} - {artist_name}")

            user_response = command().lower()
            if "yes" in user_response:
                sp.start_playback(device_id=devices['devices'][0]['id'])
                speak("Playing your last song.")
                print("[DEBUG] Resumed last playback.")
                return

        # Yeni şarkı iste
        speak("What song would you like to listen to?")
        song_name = command()

        speak("Who is the artist?")
        artist_name = command()

        query = f'track:"{song_name}" artist:"{artist_name}"'
        result = sp.search(q=query, type='track', limit=1)

        if result['tracks']['items']:
            track = result['tracks']['items'][0]
            sp.start_playback(device_id=devices['devices'][0]['id'], uris=[track['uri']])
            speak(f"Now playing {track['name']} by {track['artists'][0]['name']}")
            print(f"[DEBUG] Playing: {track['name']} - {track['artists'][0]['name']}")
        else:
            speak("Sorry, I couldn't find that song on Spotify.")
            print("[DEBUG] No matching track found.")

    except Exception as e:
        print(f"[ERROR] Spotify play_music_spotify: {e}")
        speak("Sorry, I encountered an error while trying to play music on Spotify.")

def play_playlist_or_album(query=None):
    try:
       
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices()
        if not devices['devices']:
            speak("I couldn't find an active device on Spotify.")
            print("[DEBUG] No active Spotify device found.")
            return

        speak("Do you want to play a playlist or an album?")
        choice = command().lower()

        if "playlist" in choice:
            speak("What is the name of the playlist?")
            playlist_name = command()

            results = sp.search(q=playlist_name, type='playlist', limit=1)
            if results['playlists']['items']:
                playlist = results['playlists']['items'][0]
                sp.start_playback(
                    device_id=devices['devices'][0]['id'],
                    context_uri=playlist['uri']
                )
                speak(f"Playing playlist: {playlist['name']}")
                print(f"[DEBUG] Playing playlist: {playlist['name']}")
            else:
                speak("I couldn't find that playlist on Spotify.")
                print("[DEBUG] Playlist not found.")

        elif "album" in choice:
            speak("What is the name of the album?")
            album_name = command()

            results = sp.search(q=album_name, type='album', limit=1)
            if results['albums']['items']:
                album = results['albums']['items'][0]
                sp.start_playback(
                    device_id=devices['devices'][0]['id'],
                    context_uri=album['uri']
                )
                speak(f"Playing album: {album['name']}")
                print(f"[DEBUG] Playing album: {album['name']}")
            else:
                speak("I couldn't find that album on Spotify.")
                print("[DEBUG] Album not found.")

        else:
            speak("I didn't understand your choice. Please say playlist or album.")
            print("[DEBUG] Invalid choice input.")

    except Exception as e:
        print(f"[ERROR] Spotify play_playlist_or_album: {e}")
        speak("Sorry, I encountered an error while trying to play a playlist or album.")

def skip_music(query=None):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices()
        if not devices['devices']:
            speak("I couldn't find an active device on Spotify.")
            print("[DEBUG] No active Spotify device found.")
            return

        device_id = devices['devices'][0]['id']
        sp.next_track(device_id=device_id)
        speak("Skipping to the next song.")
        print("[DEBUG] Skipped to the next track.")

    except Exception as e:
        print(f"[ERROR] Spotify skip_music: {e}")
        speak("Sorry, I encountered an error while skipping the song.")

def pause_music(query=None):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices()
        if not devices['devices']:
            speak("I couldn't find an active device on Spotify.")
            print("[DEBUG] No active Spotify device found.")
            return

        device_id = devices['devices'][0]['id']
        sp.pause_playback(device_id=device_id)
        speak("Music paused.")
        print("[DEBUG] Playback paused.")

    except Exception as e:
        print(f"[ERROR] Spotify pause_music: {e}")
        speak("Sorry, I encountered an error while pausing the music.")

def resume_music(query=None):
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))

        devices = sp.devices().get('devices', [])
        if not devices:
            speak("No active Spotify device found.")
            return

        device_id = devices[0]['id']
        playback = sp.current_playback()

        if not playback or not playback.get('item'):
            speak("There's nothing to resume right now. You can play a new song instead.")
            return

        sp.start_playback(device_id=device_id)
        speak("Resuming music.")
        speak("Sorry it is not possible")
        
    except Exception as e:
        speak("Sorry it is not possible")




TAG_HANDLERS = {
    "get_weather": handle_weather,
    "breaking_news": handle_news,
    "youtube": handle_youtube,
    "social": handle_social,
    "decrease_volume": decrease_volume,
    "increase_volume": increase_volume,
    "mute_volume": mute_volume,
    "open_app": lambda query: open_app(query),
    "close_app": lambda query: close_app(query),
    "get_time": Time,
    "web_search": browsing,
    "system": condition,
    "send_email":send_email,
    "unmute_volume":unmute_volume,
    "resume_music":resume_music,
    "pause_music":pause_music,
    "skip_music":skip_music,
    "general_play_music":play_music_spotify,
    "current_playing_music":current_music,
    "play_playlist_or_album":play_playlist_or_album,
    "movie_suggestion": suggest_movie,
    "movie_info": movie_info,
    "add_event":add_event,
    "list_events":list_events,
    "delete_event":delete_event,
    "update_event":update_event,
   "exit": lambda _: sys.exit()

    
}

if __name__ == "__main__":
    Time()
    
    while True:
        try:
            query = command()
            
            # Geçersiz durumlar
            if query in ["no_speech", "not_understood", "api_error", "error"]:
                print("I couldn't detect any input ")
                continue
                
            if not query or len(query.strip()) < 2:
                speak("I didn't catch that")
                continue
                

                
            process_query(query)
            
        except KeyboardInterrupt:
            speak("Goodbye!")
            sys.exit()
        except Exception as e:
            print(f"Critical error: {e}")
            speak("Let me try that again...")
