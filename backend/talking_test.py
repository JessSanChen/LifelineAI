import pyttsx3
import speech_recognition as sr

def text_to_speech(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Could not understand the audio."
        except sr.RequestError:
            return "Could not request results, check your internet connection."
        except sr.WaitTimeoutError:
            return "Listening timed out."

if __name__ == "__main__":
    # Convert text to speech
    text_to_speech("Hello! I can convert text to speech and speech to text.")

    # Convert speech to text
    print("Say something:")
    recognized_text = speech_to_text()
    print("You said:", recognized_text)
    text_to_speech(recognized_text)
