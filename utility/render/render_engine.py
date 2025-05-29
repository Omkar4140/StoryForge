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

def safe_unpack_caption_data(caption_data, index):
    """
    Safely unpack caption data in various formats to avoid 'too many values to unpack' errors.
    
    Returns:
        tuple: (time_info, text, color) or None if invalid format
    """
    try:
        print(f"🔍 Debug: Processing caption {index}: {caption_data} (type: {type(caption_data)})")
        
        # Initialize defaults
        time_info = None
        text = None
        color = "white"
        
        if isinstance(caption_data, (tuple, list)):
            length = len(caption_data)
            print(f"🔍 Debug: Caption is tuple/list with {length} elements")
            
            if length == 0:
                print(f"❌ Caption {index} is empty")
                return None
            elif length == 1:
                # Single element - might be nested data
                element = caption_data[0]
                if isinstance(element, (tuple, list)) and len(element) >= 2:
                    # Nested format: (((start, end), text, color),)
                    return safe_unpack_caption_data(element, index)
                else:
                    print(f"❌ Caption {index} has single element that's not a valid caption: {element}")
                    return None
            elif length == 2:
                # Standard format: (time_info, text)
                time_info, text = caption_data[0], caption_data[1]
            elif length == 3:
                # Extended format: (time_info, text, color)
                time_info, text, color = caption_data[0], caption_data[1], caption_data[2]
            elif length > 3:
                # Too many elements - take first 3
                print(f"⚠️ Warning: Caption {index} has {length} elements, using first 3")
                time_info, text, color = caption_data[0], caption_data[1], caption_data[2]
                
        elif isinstance(caption_data, dict):
            # Dictionary format
            time_info = caption_data.get('time_info') or caption_data.get('timing') or caption_data.get('time')
            text = caption_data.get('text') or caption_data.get('caption') or caption_data.get('content')
            color = caption_data.get('color', "white")
            
        else:
            print(f"❌ Caption {index} has unsupported format: {type(caption_data)}")
            return None
        
        # Validate extracted data
        if not time_info:
            print(f"❌ Caption {index} missing time_info")
            return None
        if not text:
            print(f"❌ Caption {index} missing text")
            return None
        if not color:
            color = "white"
            
        return (time_info, text, color)
        
    except Exception as e:
        print(f"❌ Error unpacking caption {index}: {e}")
        import traceback
        traceback.print_exc()
        return None

def safe_unpack_time_info(time_info, index):
    """
    Safely extract start and end times from time_info in various formats.
    
    Returns:
        tuple: (start_time, end_time) as floats or None if invalid
    """
    try:
        start_time, end_time = None, None
        
        if isinstance(time_info, (tuple, list)):
            if len(time_info) >= 2:
                start_time, end_time = time_info[0], time_info[1]
            else:
                print(f"❌ Time info for caption {index} has insufficient elements: {time_info}")
                return None
                
        elif isinstance(time_info, dict):
            start_time = time_info.get('start') or time_info.get('t1') or time_info.get('begin')
            end_time = time_info.get('end') or time_info.get('t2') or time_info.get('finish')
            
        else:
            print(f"❌ Time info for caption {index} has invalid format: {type(time_info)}")
            return None
        
        # Convert to float and validate
        try:
            start_time = float(start_time)
            end_time = float(end_time)
        except (ValueError, TypeError) as e:
            print(f"❌ Invalid timestamp values for caption {index}: start={start_time}, end={end_time}")
            return None
        
        if start_time >= end_time:
            print(f"❌ Invalid time range for caption {index}: {start_time}s >= {end_time}s")
            return None
            
        return (start_time, end_time)
        
    except Exception as e:
        print(f"❌ Error processing time info for caption {index}: {e}")
        return None

def safe_unpack_video_data(video_data, index):
    """
    Safely unpack video data in various formats.
    
    Returns:
        tuple: (time_info, video_url) or None if invalid format
    """
    try:
        print(f"🔍 Debug: Processing video {index}: {video_data} (type: {type(video_data)})")
        
        time_info = None
        video_url = None
        
        if isinstance(video_data, (tuple, list)):
            length = len(video_data)
            print(f"🔍 Debug: Video data is tuple/list with {length} elements")
            
            if length >= 2:
                time_info, video_url = video_data[0], video_data[1]
                if length > 2:
                    print(f"⚠️ Warning: Video data {index} has {length} elements, using first 2")
            else:
                print(f"❌ Video data {index} has insufficient elements: {length}")
                return None
                
        elif isinstance(video_data, dict):
            time_info = video_data.get('time_info') or video_data.get('timing')
            video_url = video_data.get('url') or video_data.get('video_url')
            
        else:
            print(f"❌ Video data {index} has unsupported format: {type(video_data)}")
            return None
        
        if not time_info or not video_url:
            print(f"❌ Video data {index} missing required fields: time_info={bool(time_info)}, video_url={bool(video_url)}")
            return None
            
        return (time_info, video_url)
        
    except Exception as e:
        print(f"❌ Error unpacking video data {index}: {e}")
        return None

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server, orientation="portrait"):
    """
    Generate video with specified orientation - FIXED VERSION
    
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
    
    # FIXED: Safe video data processing
    for i, video_data in enumerate(background_video_data):
        try:
            # Use safe unpacking function
            unpacked_data = safe_unpack_video_data(video_data, i)
            if not unpacked_data:
                continue
                
            time_info, video_url = unpacked_data
            
            # Use safe time extraction
            time_result = safe_unpack_time_info(time_info, i)
            if not time_result:
                continue
                
            t1, t2 = time_result
            print(f"Processing video segment {i}: {t1}s - {t2}s")
            
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
    
    # FIXED: Safe caption processing
    for i, caption_data in enumerate(timed_captions):
        try:
            # Use safe unpacking function
            unpacked_data = safe_unpack_caption_data(caption_data, i)
            if not unpacked_data:
                continue
                
            time_info, text, color = unpacked_data
            
            # Use safe time extraction
            time_result = safe_unpack_time_info(time_info, i)
            if not time_result:
                continue
                
            start_time, end_time = time_result
            duration = end_time - start_time
            
            print(f"Caption {i+1}: [{start_time:.2f}s-{end_time:.2f}s] ({duration:.2f}s) '{str(text)[:50]}{'...' if len(str(text)) > 50 else ''}' [{color}]")
            
            # Create text clip with error handling
            try:
                text_clip = TextClip(
                    txt=str(text).strip(),  # Ensure text is string and strip whitespace
                    fontsize=fontsize,
                    color=color or 'white',
                    stroke_width=stroke_width,
                    stroke_color='black',  # Add stroke for better readability
                    method='caption',  # Use caption method for better text wrapping
                    size=(TARGET_WIDTH - 100, None),  # Leave 50px margin on each side
                    align='center'
                )
                
                text_clip = text_clip.set_start(start_time)
                text_clip = text_clip.set_duration(duration)
                text_clip = text_clip.set_position(caption_position)

                visual_clips.append(text_clip)
                print(f"✅ Successfully created text clip for caption {i+1}")

            except Exception as text_error:
                print(f"❌ Error creating text clip for caption {i+1}: {text_error}")
                print(f"   Text: '{str(text)[:100]}...'")
                print(f"   Parameters: fontsize={fontsize}, color={color}, duration={duration}")
                continue

        except Exception as e:
            print(f"❌ Error processing caption {i+1}: {e}")
            print(f"Caption data: {caption_data}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n✅ Successfully processed {len([clip for clip in visual_clips if hasattr(clip, 'txt')])} caption clips")
    print(f"✅ Successfully processed {len([clip for clip in visual_clips if not hasattr(clip, 'txt')])} video clips")
    print(f"📊 Total visual clips: {len(visual_clips)}")

    if not visual_clips:
        print("❌ No visual clips were created! Check your input data.")
        return None

    # Load audio
    print("🎼 Processing audio track...")
    try:
        audio_clip = AudioFileClip(audio_file_path)
        print(f"✅ Audio loaded: {audio_clip.duration:.2f}s")
        
        # Normalize audio
        audio_clip = audio_normalize(audio_clip)
        print(f"✅ Audio normalized")
    except Exception as e:
        print(f"❌ Error loading audio: {e}")
        return None

    # Combine visual clips
    print("🎬 Combining video elements...")
    try:
        final_video = CompositeVideoClip(visual_clips, size=(TARGET_WIDTH, TARGET_HEIGHT))
        print(f"✅ Video composite created: {final_video.w}x{final_video.h}")
        
        # Add audio to final video
        final_video = final_video.set_audio(audio_clip)
        print(f"✅ Audio added to video")
        
    except Exception as e:
        print(f"❌ Error creating composite video: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Render final output
    print(f"💾 Saving final video to {OUTPUT_FILE_NAME}...")
    try:
        final_video.write_videofile(
            OUTPUT_FILE_NAME, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            verbose=False,  # Reduce console output
            logger=None  # Disable moviepy progress bar
        )
        print("✅ Video rendering complete!")
        
    except Exception as e:
        print(f"❌ Error rendering final video: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Clean up temporary files
    print("🧹 Cleaning up temporary files...")
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                print(f"🗑️ Cleaned up: {os.path.basename(temp_file)}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up {temp_file}: {e}")
    
    print(f"🎉 Successfully created: {OUTPUT_FILE_NAME}")
    return OUTPUT_FILE_NAME
