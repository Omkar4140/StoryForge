import os
import tempfile
import requests
from moviepy.editor import (AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip)

def download_file(url, filename):
    """Download file from URL"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    with open(filename, 'wb') as f:
        f.write(response.content)

def get_output_media(audio_file_path, timed_captions, background_video_data, orientation="portrait"):
    """
    Generate video with captions and background videos
    
    Args:
        audio_file_path: Path to audio file
        timed_captions: List of ((start, end), text, color) tuples
        background_video_data: List of ((start, end), video_url) tuples
        orientation: "portrait" or "landscape"
    """
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    
    # Set dimensions based on orientation
    if orientation == "portrait":
        WIDTH, HEIGHT = 1080, 1920
        fontsize = 60
    else:
        WIDTH, HEIGHT = 1920, 1080
        fontsize = 80
    
    print(f"📱 Rendering {orientation} video ({WIDTH}x{HEIGHT})")
    
    visual_clips = []
    temp_files = []
    
    # Process background videos
    print(f"📹 Processing {len(background_video_data)} video segments...")
    for i, video_data in enumerate(background_video_data):
        try:
            # Simple unpacking - expect ((start, end), url) format
            (start_time, end_time), video_url = video_data
            duration = end_time - start_time
            
            print(f"Video {i+1}: {start_time:.1f}s - {end_time:.1f}s")
            
            # Download video
            video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            temp_files.append(video_file)
            download_file(video_url, video_file)
            
            # Create video clip
            video_clip = VideoFileClip(video_file)
            
            # Resize to fill screen (crop if needed)
            video_clip = video_clip.resize(height=HEIGHT)
            if video_clip.w > WIDTH:
                # Center crop if too wide
                x_center = video_clip.w // 2
                x1 = x_center - WIDTH // 2
                x2 = x1 + WIDTH
                video_clip = video_clip.crop(x1=x1, x2=x2)
            
            # Set timing
            video_clip = video_clip.set_start(start_time).set_duration(duration)
            
            # Loop if video is shorter than needed
            if video_clip.duration < duration:
                video_clip = video_clip.loop(duration=duration)
            
            visual_clips.append(video_clip)
            print(f"✅ Video {i+1} processed")
            
        except Exception as e:
            print(f"❌ Error processing video {i+1}: {e}")
            continue
    
    # Process captions
    print(f"📝 Processing {len(timed_captions)} captions...")
    for i, caption_data in enumerate(timed_captions):
        try:
            # Simple unpacking - expect ((start, end), text, color) format
            (start_time, end_time), text, color = caption_data
            duration = end_time - start_time
            
            print(f"Caption {i+1}: {start_time:.1f}s - {end_time:.1f}s: '{str(text)[:30]}...'")
            
            # Create text clip
            text_clip = TextClip(
                txt=str(text),
                fontsize=fontsize,
                color=color,
                stroke_width=3,
                stroke_color='black',
                method='caption',
                size=(WIDTH - 100, None),
                align='center'
            )
            
            text_clip = text_clip.set_start(start_time).set_duration(duration)
            text_clip = text_clip.set_position(('center', 'bottom'))
            
            visual_clips.append(text_clip)
            print(f"✅ Caption {i+1} processed")
            
        except Exception as e:
            print(f"❌ Error processing caption {i+1}: {e}")
            continue
    
    if not visual_clips:
        print("❌ No clips created!")
        return None
    
    # Load audio
    print("🎼 Loading audio...")
    audio_clip = AudioFileClip(audio_file_path)
    
    # Create final video
    print("🎬 Creating final video...")
    final_video = CompositeVideoClip(visual_clips, size=(WIDTH, HEIGHT))
    final_video = final_video.set_audio(audio_clip)
    
    # Render
    print(f"💾 Rendering to {OUTPUT_FILE_NAME}...")
    final_video.write_videofile(
        OUTPUT_FILE_NAME,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        verbose=False,
        logger=None
    )
    
    # Cleanup
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except:
            pass
    
    print(f"✅ Video created: {OUTPUT_FILE_NAME}")
    return OUTPUT_FILE_NAME
