import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                            TextClip, VideoFileClip)
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
import requests

def download_file(url, filename):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    with open(filename, 'wb') as f:
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    return search_program(program_name)

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server, orientation):
    """
    Generate video with specified orientation.
    """
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    TARGET_WIDTH, TARGET_HEIGHT = (1080, 1920) if orientation == "portrait" else (1920, 1080)
    
    os.environ['IMAGEMAGICK_BINARY'] = get_program_path("magick") or '/usr/bin/convert'
    
    visual_clips = []  
    temp_files = []  

    for (t1, t2), video_url in background_video_data:
        if not video_url:
            continue
        
        video_filename = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        temp_files.append(video_filename)
        download_file(video_url, video_filename)

        if not os.path.exists(video_filename) or os.path.getsize(video_filename) == 0:
            continue

        video_clip = VideoFileClip(video_filename).subclip(t1, t2)
        original_w, original_h = video_clip.w, video_clip.h

        scale = max(TARGET_WIDTH / original_w, TARGET_HEIGHT / original_h)
        new_w, new_h = int(original_w * scale), int(original_h * scale)

        video_clip = video_clip.resize((new_w, new_h)).crop(
            x1=(new_w - TARGET_WIDTH) // 2, 
            y1=(new_h - TARGET_HEIGHT) // 2, 
            x2=((new_w - TARGET_WIDTH) // 2) + TARGET_WIDTH,
            y2=((new_h - TARGET_HEIGHT) // 2) + TARGET_HEIGHT
        )

        if video_clip.duration < (t2 - t1):
            video_clip = audio_loop(video_clip, duration=(t2 - t1))

        visual_clips.append(video_clip)

    for (t1, t2), text in timed_captions:
        fontsize, stroke_width = (60, 2) if orientation == "portrait" else (80, 3)
        text_clip = TextClip(txt=text, fontsize=fontsize, color='white', stroke_width=stroke_width,
                             stroke_color='black', method='caption', size=(TARGET_WIDTH - 100, None), 
                             align='center').set_start(t1).set_end(t2).set_position(("center", 800))
        visual_clips.append(text_clip)

    video = CompositeVideoClip(visual_clips)
    
    if os.path.exists(audio_file_path):
        audio_clip = AudioFileClip(audio_file_path)
        video.audio = audio_clip
    
    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
    
    for temp_file in temp_files:
        os.remove(temp_file)

    return OUTPUT_FILE_NAME
