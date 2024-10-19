import streamlit as st
import moviepy.editor as mp
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import requests
import tempfile

# Set your Azure OpenAI configuration
AZURE_API_KEY = st.secrets["AZURE_API_KEY"]  # Store your key in secrets.toml for security
AZURE_ENDPOINT = 'https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview'

# Function to transcribe audio using Google Speech-to-Text
def transcribe_audio(file_path):
    client = speech.SpeechClient()
    with open(file_path, 'rb') as audio_file:
        content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    
    response = client.recognize(config=config, audio=audio)
    transcription = " ".join([result.alternatives[0].transcript for result in response.results])
    
    return transcription

# Function to correct transcription using GPT-4o
def correct_transcription(transcription):
    headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": f"Correct this text: {transcription}"}],
        "max_tokens": 1000
    }
    
    response = requests.post(AZURE_ENDPOINT, headers=headers, json=data)
    
    if response.status_code != 200:
        st.error("Error with GPT-4 API: " + response.text)
        return transcription  # Return original transcription in case of an error
    
    corrected_text = response.json()['choices'][0]['message']['content']
    
    return corrected_text

# Function to generate audio from text using Google Text-to-Speech
def generate_audio(text):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-D"  # You can change the voice model here
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )
    
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as audio_file:
        audio_file.write(response.audio_content)
        return audio_file.name

# Function to replace audio in the original video
def replace_audio(video_path, audio_path):
    video = mp.VideoFileClip(video_path)
    audio = mp.AudioFileClip(audio_path)
    video = video.set_audio(audio)
    
    output_path = 'output_video.mp4'
    video.write_videofile(output_path, codec='libx264', audio_codec='aac')
    
    return output_path

# Streamlit app
st.title("Video Audio Replacement with AI")
st.write("Upload a video file, and we'll replace the audio with corrected transcription from Google Speech-to-Text!")

# Video uploader
uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video_file:
        temp_video_file.write(uploaded_file.read())
        st.video(temp_video_file.name)
        
        st.write("Transcribing audio...")
        transcription = transcribe_audio(temp_video_file.name)
        st.write("Transcription:", transcription)
        
        st.write("Correcting transcription...")
        corrected_text = correct_transcription(transcription)
        st.write("Corrected Text:", corrected_text)
        
        st.write("Generating new audio...")
        audio_file_path = generate_audio(corrected_text)
        
        st.write("Replacing audio in video...")
        output_video_path = replace_audio(temp_video_file.name, audio_file_path)
        
        st.video(output_video_path)
        st.success("Audio replacement completed!")
