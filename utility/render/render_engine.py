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

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server, orientation="portrait"):
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
    
    # Set target resolution based on orientation
    if orientation == "portrait":
        TARGET_WIDTH = 1080
        TARGET_HEIGHT = 1920
        print("📱 Rendering in PORTRAIT mode (9:16 - 1080x1920)")
        fontsize = 60
        stroke_width = 3
        caption_position = ('center', 'bottom')
    else:
        TARGET_WIDTH = 1920
        TARGET_HEIGHT = 1080
        print("🖥️ Rendering in LANDSCAPE mode (16:9 - 1920x1080)")
        fontsize = 80
        stroke_width = 4
        caption_position = ('center', 'bottom')
    
    magick_path = get_program_path("magick")
    print(f"ImageMagick path: {magick_path}")
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
    visual_clips = []
    temp_files = []  # Track temporary files for cleanup
    
    print(f"📹 Processing {len(background_video_data)} video segments...")
    
    for i, video_data in enumerate(background_video_data):
        try:
            print(f"🔍 Debug: Video data {i}: {video_data} (type: {type(video_data)})")
            
            # FIXED: More robust handling of video data formats
            time_info = None
            video_url = None
            
            if isinstance(video_data, (tuple, list)):
                print(f"🔍 Debug: Video data length: {len(video_data)}")
                
                if len(video_data) >= 2:
                    # Extract first two elements as time_info and video_url
                    time_info = video_data[0]
                    video_url = video_data[1]
                    
                    if len(video_data) > 2:
                        print(f"Warning: Video data {i} has extra elements: {video_data[2:]}")
                else:
                    print(f"❌ Invalid video data format at {i}: not enough elements")
                    continue
            elif isinstance(video_data, dict):
                # Handle dictionary format if needed
                time_info = video_data.get('time_info') or video_data.get('timing')
                video_url = video_data.get('url') or video_data.get('video_url')
            else:
                print(f"❌ Video data {i} is not a supported format: {type(video_data)}")
                continue
            
            if not time_info or not video_url:
                print(f"❌ Missing time_info or video_url at index {i}")
                continue
                    
            print(f"🔍 Debug: Time info: {time_info} (type: {type(time_info)})")
            print(f"🔍 Debug: Video URL: {str(video_url)[:100]}...")
            
            # FIXED: More robust time info validation
            t1, t2 = None, None
            
            if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                t1, t2 = time_info[0], time_info[1]
            elif isinstance(time_info, dict):
                t1 = time_info.get('start') or time_info.get('t1')
                t2 = time_info.get('end') or time_info.get('t2')
            else:
                print(f"❌ Invalid time format at {i}: {time_info}")
                continue
            
            if t1 is None or t2 is None:
                print(f"❌ Could not extract valid timestamps from {time_info}")
                continue
                
            # Convert to float if needed
            try:
                t1, t2 = float(t1), float(t2)
                print(f"Processing video segment {i}: {t1}s - {t2}s")
            except (ValueError, TypeError):
                print(f"❌ Invalid timestamp values: t1={t1}, t2={t2}")
                continue
                    
        except Exception as e:
            print(f"❌ Error parsing video data {i}: {e}")
            print(f"Data: {video_data}")
            import traceback
            traceback.print_exc()
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
    
    # FIXED: More robust caption processing
    for i, caption_data in enumerate(timed_captions):
        try:
            print(f"🔍 Debug: Caption data {i}: {caption_data} (type: {type(caption_data)})")
            
            # Initialize variables
            time_info = None
            text = None
            color = "white"  # default
            
            # Handle different caption formats more robustly
            if isinstance(caption_data, (tuple, list)):
                print(f"🔍 Debug: Caption data length: {len(caption_data)}")
                
                if len(caption_data) >= 2:
                    time_info = caption_data[0]
                    text = caption_data[1]
                    
                    # Optional third element for color
                    if len(caption_data) >= 3:
                        color = caption_data[2] or "white"
                else:
                    print(f"❌ Caption data {i} doesn't have enough elements")
                    continue
                    
            elif isinstance(caption_data, dict):
                # Handle dictionary format
                time_info = caption_data.get('time_info') or caption_data.get('timing')
                text = caption_data.get('text') or caption_data.get('caption')
                color = caption_data.get('color', "white")
            else:
                print(f"❌ Unsupported caption format at index {i}: {type(caption_data)}")
                continue
            
            if not time_info or not text:
                print(f"❌ Missing time_info or text at caption {i}")
                continue
                
            print(f"🔍 Debug: Time info: {time_info}, Text: '{text[:50]}...', Color: {color}")
            
            # FIXED: More robust time extraction
            t1, t2 = None, None
            
            if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                t1, t2 = time_info[0], time_info[1]
            elif isinstance(time_info, dict):
                t1 = time_info.get('start') or time_info.get('t1')
                t2 = time_info.get('end') or time_info.get('t2')
            else:
                print(f"❌ Invalid time info format: {time_info}")
                continue
            
            if t1 is None or t2 is None:
                print(f"❌ Could not extract valid timestamps from {time_info}")
                continue
            
            # Convert to float if needed
            try:
                t1, t2 = float(t1), float(t2)
            except (ValueError, TypeError):
                print(f"❌ Invalid timestamp values: t1={t1}, t2={t2}")
                continue
                
            print(f"Caption {i+1}: [{t1}s-{t2}s] '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Create text clip with better mobile-friendly styling
            text_clip = TextClip(
                txt=str(text),  # Ensure text is string
                fontsize=fontsize,
                color=color or 'white',
                stroke_width=stroke_width,
                method='caption',  # Use caption method for better text wrapping
                size=(TARGET_WIDTH - 100, None),  # Leave 50px margin on each side
                align='center'
            )
            
            text_clip = text_clip.set_start(t1)
            text_clip = text_clip.set_duration(t2 - t1)
            text_clip = text_clip.set_position(caption_position)

            visual_clips.append(text_clip)

        except Exception as e:
            print(f"❌ Error processing caption {i+1}: {e}")
            print(f"Caption data: {caption_data}")
            import traceback
            traceback.print_exc()
            continue

    # Load audio
    print("🎼 Processing audio track...")
    audio_clip = AudioFileClip(audio_file_path)

    # Normalize audio
    audio_clip = audio_normalize(audio_clip)

    # Combine visual clips
    print("🎬 Combining video elements...")
    final_video = CompositeVideoClip(visual_clips, size=(TARGET_WIDTH, TARGET_HEIGHT))

    # Add audio to final video
    final_video = final_video.set_audio(audio_clip)

    # Render final output
    print(f"💾 Saving final video to {OUTPUT_FILE_NAME}...")
    final_video.write_videofile(OUTPUT_FILE_NAME, fps=30, codec="libx264", audio_codec="aac")

    print("✅ Video rendering complete!")
    
    # Clean up temporary files
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                print(f"🗑️ Cleaned up temporary file: {temp_file}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up {temp_file}: {e}")
            
    return OUTPUT_FILE_NAME
