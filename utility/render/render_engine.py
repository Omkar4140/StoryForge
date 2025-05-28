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
    with open(filename, 'wb') as f:
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server):
    """
    Generate video with specified orientation
    
    Args:
        audio_file_path: Path to audio file
        timed_captions: List of timed caption segments
        background_video_data: List of timed video segments with URLs
        video_server: Video service used
        orientation: "portrait" for 9:16 (1080x1920) or "landscape" for 16:9 (1920x1080)
    """
    OUTPUT_FILE_NAME = "rendered_video.mp4"
  
    if orientation == "portrait":
      TARGET_WIDTH = 1080
      TARGET_HEIGHT = 1920
      print("📱 Rendering in PORTRAIT mode (9:16 - 1080x1920)")
    else:
      TARGET_WIDTH = 1920
      TARGET_HEIGHT = 1080
      print("🖥️ Rendering in LANDSCAPE mode (16:9 - 1920x1080)")
      
    magick_path = get_program_path("magick")
    print(magick_path)
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
    visual_clips = [] 
    temp_files = [] 
    print(f"📹 Processing {len(background_video_data)} video segments...")
    
    for i, ((t1, t2), video_url) in enumerate(background_video_data):
        print(f"\n--- Processing video segment {i+1}/{len(background_video_data)} ---")
        print(f"Time: {t1}s - {t2}s")
        print(f"URL: {video_url}")
        
        if video_url is None:
            print(f"⚠️ No video URL for segment {i+1}, skipping...")
            continue
            
        try:
            # Download the video file
            video_filename = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            temp_files.append(video_filename)
            
            print(f"⬇️ Downloading video to: {video_filename}")
            download_file(video_url, video_filename)
            
            # Check if file was downloaded successfully
            if not os.path.exists(video_filename) or os.path.getsize(video_filename) == 0:
                print(f"❌ Failed to download video for segment {i+1}")
                continue
            
            # Create VideoFileClip from the downloaded file
            print(f"🎬 Creating video clip...")
            video_clip = VideoFileClip(video_filename)
            
            # Get original video dimensions
            original_w, original_h = video_clip.w, video_clip.h
            print(f"📐 Original video: {original_w}x{original_h}")
            
            # Calculate segment duration
            segment_duration = t2 - t1
            print(f"⏱️ Segment duration: {segment_duration}s")
            
            # Resize and crop video to fit target dimensions while maintaining aspect ratio
            if orientation == "portrait":
                # For portrait videos, we want to fill 1080x1920
                # Calculate scale to fill the target dimensions
                scale_w = TARGET_WIDTH / original_w
                scale_h = TARGET_HEIGHT / original_h
                scale = max(scale_w, scale_h)  # Use larger scale to fill entire frame
                
                new_w = int(original_w * scale)
                new_h = int(original_h * scale)
                
                print(f"📏 Scaled dimensions: {new_w}x{new_h}")
                
                # Resize video
                video_clip = video_clip.resize((new_w, new_h))
                
                # Center crop to exact target dimensions
                x_center = new_w // 2
                y_center = new_h // 2
                
                x1 = max(0, x_center - TARGET_WIDTH // 2)
                y1 = max(0, y_center - TARGET_HEIGHT // 2)
                x2 = min(new_w, x1 + TARGET_WIDTH)
                y2 = min(new_h, y1 + TARGET_HEIGHT)
                
                video_clip = video_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
                
            else:
                # For landscape videos (1920x1080)
                scale_w = TARGET_WIDTH / original_w
                scale_h = TARGET_HEIGHT / original_h
                scale = max(scale_w, scale_h)
                
                new_w = int(original_w * scale)
                new_h = int(original_h * scale)
                
                video_clip = video_clip.resize((new_w, new_h))
                
                # Center crop
                x_center = new_w // 2
                y_center = new_h // 2
                
                x1 = max(0, x_center - TARGET_WIDTH // 2)
                y1 = max(0, y_center - TARGET_HEIGHT // 2)
                x2 = min(new_w, x1 + TARGET_WIDTH)
                y2 = min(new_h, y1 + TARGET_HEIGHT)
                
                video_clip = video_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
            
            # Set timing for this segment
            video_clip = video_clip.set_start(t1)
            video_clip = video_clip.set_duration(segment_duration)
            
            # Ensure the clip doesn't exceed available video duration
            if video_clip.duration < segment_duration:
                # Loop the video if it's shorter than needed
                video_clip = video_clip.loop(duration=segment_duration)
            
            print(f"✅ Video clip prepared: {video_clip.w}x{video_clip.h}, duration: {video_clip.duration}s")
            visual_clips.append(video_clip)
            
        except Exception as e:
            print(f"❌ Error processing video segment {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n📝 Processing {len(timed_captions)} caption segments...")
    
    # Process captions with improved styling for mobile viewing
    for i, ((t1, t2), text) in enumerate(timed_captions):
        try:
            print(f"Caption {i+1}: [{t1}s-{t2}s] '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Adjust font size based on orientation
            if orientation == "portrait":
                fontsize = 60  # Smaller font for portrait to fit mobile screens
                stroke_width = 2
                # Position captions in lower third for portrait
                caption_position = ('center', TARGET_HEIGHT - 300)  # 300px from bottom
            else:
                fontsize = 80  # Larger font for landscape
                stroke_width = 3
                caption_position = ('center', TARGET_HEIGHT - 200)  # 200px from bottom
            
            # Create text clip with better mobile-friendly styling
            text_clip = TextClip(
                txt=text,
                fontsize=fontsize,
                color='white',
                stroke_width=stroke_width,
                stroke_color='black',
                method='caption',  # Use caption method for better text wrapping
                size=(TARGET_WIDTH - 100, None),  # Leave 50px margin on each side
                align='center'
            )
            text_clip = text_clip.set_start(t1)
            text_clip = text_clip.set_end(t2)
            text_clip = text_clip.set_position(["center", 800])
            visual_clips.append(text_clip)

    video = CompositeVideoClip(visual_clips)
    
    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
    
    # Clean up downloaded files
    for (t1, t2), video_url in background_video_data:
        video_filename = tempfile.NamedTemporaryFile(delete=False).name
        os.remove(video_filename)

    return OUTPUT_FILE_NAME
