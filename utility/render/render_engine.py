# Fixed utility/render/render_engine.py

import os
import tempfile
import requests
from moviepy.editor import (AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip)

def normalize_data_format(data):
    """
    Normalize data to consistent format: ((start, end), content)
    Handles various input formats and returns consistent output
    """
    try:
        if not data:
            return None
            
        # Handle different possible formats
        if isinstance(data, (tuple, list)):
            if len(data) == 2:
                # Check if first element is time info
                first, second = data
                
                # Format: ((start, end), content) - already correct
                if isinstance(first, (tuple, list)) and len(first) == 2:
                    try:
                        # Verify times are numeric
                        float(first[0])
                        float(first[1])
                        return ((float(first[0]), float(first[1])), second)
                    except (ValueError, TypeError):
                        pass
                
                # Format: ([start, end], content)
                if isinstance(first, list) and len(first) == 2:
                    try:
                        float(first[0])
                        float(first[1])
                        return ((float(first[0]), float(first[1])), second)
                    except (ValueError, TypeError):
                        pass
                        
            elif len(data) == 3:
                # Format: (start, end, content)
                try:
                    start, end, content = data
                    return ((float(start), float(end)), content)
                except (ValueError, TypeError):
                    pass
        
        print(f"Warning: Could not normalize data format: {data}")
        return None
        
    except Exception as e:
        print(f"Error normalizing data: {e}")
        return None

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
    Generate video with captions and background videos - Enhanced with better data handling
    
    Args:
        audio_file_path: Path to audio file
        timed_captions: List of caption data in various formats
        background_video_data: List of video data in various formats
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
    
    # Process background videos with enhanced error handling
    print(f"📹 Processing {len(background_video_data)} video segments...")
    for i, video_data in enumerate(background_video_data):
        try:
            print(f"\n--- Processing video {i+1} ---")
            print(f"Raw video data: {video_data}")
            print(f"Data type: {type(video_data)}")
            
            # Normalize the video data format
            normalized = normalize_data_format(video_data)
            if normalized is None:
                print(f"❌ Could not normalize video data at index {i}")
                continue
            
            time_info, video_url = normalized
            start_time, end_time = time_info
            duration = end_time - start_time
            
            print(f"Video {i+1}: {start_time:.1f}s - {end_time:.1f}s (duration: {duration:.1f}s)")
            print(f"Video URL: {video_url}")
            
            if video_url is None:
                print(f"⚠️ Skipping video {i+1}: No URL provided")
                continue
            
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
            print(f"✅ Video {i+1} processed successfully")
            
        except Exception as e:
            print(f"❌ Error processing video {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Process captions with enhanced error handling
    print(f"\n📝 Processing {len(timed_captions)} captions...")
    for i, caption_data in enumerate(timed_captions):
        try:
            print(f"\n--- Processing caption {i+1} ---")
            print(f"Raw caption data: {caption_data}")
            print(f"Data type: {type(caption_data)}")
            
            # Handle different caption formats
            if isinstance(caption_data, (tuple, list)):
                if len(caption_data) >= 3:
                    # Format: ((start, end), text, color) or ([start, end], text, color)
                    time_info, text, color = caption_data[0], caption_data[1], caption_data[2]
                elif len(caption_data) == 2:
                    # Format: ((start, end), text) or ([start, end], text)
                    time_info, text = caption_data
                    color = "white"  # default color
                else:
                    print(f"❌ Warning: Invalid caption format at index {i}: {caption_data}")
                    continue
                    
                # Normalize time info
                if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                    try:
                        start_time = float(time_info[0])
                        end_time = float(time_info[1])
                    except (ValueError, TypeError):
                        print(f"❌ Warning: Invalid time values at index {i}: {time_info}")
                        continue
                else:
                    print(f"❌ Warning: Invalid time info at index {i}: {time_info}")
                    continue
                    
            else:
                print(f"❌ Warning: Caption data should be tuple/list at index {i}: {caption_data}")
                continue
            
            duration = end_time - start_time
            text_str = str(text).strip()
            
            if not text_str:
                print(f"⚠️ Skipping empty caption at index {i}")
                continue
            
            print(f"Caption {i+1}: {start_time:.1f}s - {end_time:.1f}s: '{text_str[:30]}...'")
            print(f"Color: {color}, Duration: {duration:.1f}s")
            
            # Create text clip
            text_clip = TextClip(
                txt=text_str,
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
            print(f"✅ Caption {i+1} processed successfully")
            
        except Exception as e:
            print(f"❌ Error processing caption {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if not visual_clips:
        print("❌ No clips created! Check your input data.")
        print(f"Captions sample: {timed_captions[:2] if timed_captions else 'None'}")
        print(f"Videos sample: {background_video_data[:2] if background_video_data else 'None'}")
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
