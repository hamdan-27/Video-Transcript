# import moviepy.editor as mpe
from openai import OpenAI
import streamlit as st
import tempfile
import requests
import base64
import time
import cv2
import os

client = OpenAI()

st.title("Viewit.ai | Video to Audio Transcript Demo")
st.write("Please upload a video to get started.")

vid = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

tfile = tempfile.NamedTemporaryFile(delete=False)
tfile.write(vid.read())

video = cv2.VideoCapture(tfile.name)
fps = video.get(cv2.CAP_PROP_FPS)

@st.cache_data(show_spinner=True)
def get_video_frames():
    base64Frames = []
    while video.isOpened():
        success, frame = video.read()
        if not success:
            break
        _, buffer = cv2.imencode(".jpg", frame)
        base64Frames.append(base64.b64encode(buffer).decode("utf-8"))
        duration = len(base64Frames)/fps

    video.release()
    cut_frames = base64Frames[0::50]
    # st.write(len(base64Frames), "frames read.")

    return duration, cut_frames


if video:
    duration, cut_frames = get_video_frames()
    _, container, _ = st.columns(3)
    container.video(vid)
    generate_audio = container.button("Generate Description")

words = duration*2

messages = [
    {
        "role": "user",
        "content": [
            f"These are frames from a property listing video that I want to upload. Generate a compelling description in under {words} words that describes the rooms, views, and amenities that I can upload along with the video.",
            *map(lambda x: {"image": x, "resize": 768}, cut_frames),
        ],
    },
]

if generate_audio:
    prog_bar = st.progress(7, text="Generating description...")
    
    result = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=200
    )
    
    prog_bar.progress(45, text="Generating audio...")
    
    response = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        },
        json={
            "model": "tts-1-1106",
            "input": result.choices[0].message.content,
            "voice": "onyx",
        },
    )

    audio = b""
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        audio += chunk
    
    # prog_bar.progress(90, text="Adding audio to video...")

    # my_clip = mpe.VideoFileClip(tfile.name)
    # taudio = tempfile.NamedTemporaryFile(delete=False)
    # taudio.write(audio)
    # audio_background = mpe.AudioFileClip(taudio.name)
    # final_audio = mpe.CompositeAudioClip([my_clip.audio, audio_background])
    # final_clip = my_clip.set_audio(final_audio)

    prog_bar.progress(100, text="Done!")
    
    container.audio(audio)