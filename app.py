from flask import Flask, render_template, request, jsonify
import cv2
from fer import FER
import webbrowser
from googleapiclient.discovery import build
import speech_recognition as sr
import pyttsx3
from datetime import datetime

app = Flask(__name__)

YOUTUBE_API_KEY = 'AIzaSyDTGJTN9GVlTSp9SGY0Z6XMwGBx45JWFvs'
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

detector = FER(mtcnn=True)
recognizer = sr.Recognizer()
tts = pyttsx3.init()

voices = tts.getProperty('voices')
for voice in voices:
    if 'female' in voice.name:
        tts.setProperty('voice', voice.id)
        break

def speak(text):
    tts.say(text)
    tts.runAndWait()

def listen(language="en-IN"):
    attempts = 0
    while attempts < 3:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening...")
            audio = None
            try:
                audio = recognizer.listen(source, timeout=10)
            except sr.WaitTimeoutError:
                return "I didn't hear anything. Please try again."
        try:
            text = recognizer.recognize_google(audio, language=language)
            print(f"You said: {text}")
            return text.lower()
        except sr.UnknownValueError:
            return "Sorry, I did not understand that. Please try again."
        except sr.RequestError:
            return "Sorry, my speech service is down. Please try again later."
    return "Please type your response."

def search_songs_on_youtube(query):
    request = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        maxResults=10
    )
    response = request.execute()
    
    if response['items']:
        videos = [(item['snippet']['title'], item['id']['videoId']) for item in response['items']]
        return videos
    else:
        return []

def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_mood', methods=['POST'])
def get_mood():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({"status": "error", "message": "Error: Could not open video stream."})

    detected_mood = None
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        result = detector.detect_emotions(frame)
        if result:
            emotions = result[0]['emotions']
            mood = max(emotions, key=emotions.get)
            print("Detected mood:", mood)
            detected_mood = mood
            break

    cap.release()

    if detected_mood:
        return jsonify({"status": "success", "mood": detected_mood})
    else:
        return jsonify({"status": "error", "message": "Sorry, I couldn't detect your mood. Please try again later."})

@app.route('/search_songs', methods=['POST'])
def search_songs():
    data = request.json
    mood = data.get('mood')
    singer = data.get('singer')
    query = f"{mood} songs by {singer}" if singer else f"{mood} songs"

    songs = search_songs_on_youtube(query)
    if songs:
        return jsonify({"status": "success", "songs": songs})
    else:
        return jsonify({"status": "error", "message": "No songs found."})

if __name__ == "__main__":
    app.run(debug=True)