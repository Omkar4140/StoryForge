import os
import tempfile
import requests
from moviepy.editor import (AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip, ColorClip)

def safe_unpack(data, expected_count, default_values=None):
    """
    Safely unpack data with fallback to defaults - Enhanced version
    """
    try:
        if data is None:
            print("Warning: Data is None, using defaults")
            if default_values and len(default_values) == expected_count:
                return tuple(default_values)
            else:
                return tuple([None] * expected_count)
        
        if isinstance(data, (tuple, list)):
            if len(data) == expected_count:
                return tuple(data)
            elif len(data) > expected_count:
                print(f"Warning: More values than expected ({len(data)} > {expected_count}), using first {expected_count}")
                return tuple(data[:expected_count])
            else:
                print(f"Warning: Fewer values than expected ({len(data)} < {expected_count})")
                if default_values and len(default_values) == expected_count:
                    result = list(data) + default_values[len(data):]
                    return tuple(result[:expected_count])
                else:
                    result = list(data) + [None] * (expected_count - len(data))
                    return tuple(result)
        else:
            print(f"Data is not iterable: {type(data)} - {data}")
            if default_values and len(default_values) == expected_count:
                return tuple(default_values)
            else:
                return tuple([None] * expected_count)
            
    except Exception as e:
        print(f"❌ Unpacking error: {e}")
        if default_values and len(default_values) == expected_count:
            return tuple(default_values)
        else:
            return tuple([None] * expected_count)

def create_styled_caption(text, fontsize, width, height, duration, start_time, 
                         style="modern", color="white", stroke_color="black", stroke_width=3):
    """
    Create enhanced caption with better styling for social media
    """
    try:
        # Caption styling options
        styles = {
            "modern": {
                "font": "Arial-Bold",
                "color": color,
                "stroke_color": stroke_color,
                "stroke_width": stroke_width,
                "method": "caption"
            },
            "elegant": {
                "font": "Arial",
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "method": "caption"
            },
            "bold": {
                "font": "Arial-Black",
                "color": "yellow",
                "stroke_color": "black",
                "stroke_width": 4,
                "method": "caption"
            }
        }
        
        style_config = styles.get(style, styles["modern"])
        
        # Create text clip with enhanced styling
        text_clip = TextClip(
            txt=text,
            fontsize=fontsize,
            color=style_config["color"],
            font=style_config["font"],
            stroke_color=style_config["stroke_color"],
            stroke_width=style_config["stroke_width"],
            method=style_config["method"],
            size=(width - 100, None),
            align='center',
            interline=-10  # Reduce line spacing for better readability
        )
        
        # Add background box for better readability (optional)
        if style == "boxed":
            # Create semi-transparent background
            bg_clip = ColorClip(
                size=(text_clip.w + 40, text_clip.h + 20),
                color=(0, 0, 0),
                duration=duration
            ).set_opacity(0.7)
            
            # Combine text with background
            text_with_bg = CompositeVideoClip([
                bg_clip.set_position('center'),
                text_clip.set_position('center')
            ], size=(text_clip.w + 40, text_clip.h + 20))
            
            text_clip = text_with_bg
        
        text_clip = text_clip.set_start(start_time).set_duration(duration)
        
        # Position captions in lower third but not at bottom edge
        text_clip = text_clip.set_position(('center', height - text_clip.h - 150))
        
        return text_clip
        
    except Exception as e:
        print(f"❌ Error creating styled caption: {e}")
        # Fallback to basic text clip
        basic_clip = TextClip(
            txt=text,
            fontsize=fontsize,
            color="white",
            method='caption',
            size=(width - 100, None),
            align='center'
        )
        return basic_clip.set_start(start_time).set_duration(duration).set_position(('center', 'bottom'))

def optimize_video_clip(video_clip, width, height, duration, target_fps=30):
    """
    Optimize video clip for better performance and quality
    """
    try:
        # Resize maintaining aspect ratio
        if video_clip.w / video_clip.h > width / height:
            # Video is wider - fit to height and crop width
            video_clip = video_clip.resize(height=height)
            if video_clip.w > width:
                x_center = video_clip.w // 2
                x1 = max(0, x_center - width // 2)
                x2 = min(video_clip.w, x1 + width)
                video_clip = video_clip.crop(x1=x1, x2=x2)
        else:
            # Video is taller - fit to width and crop height
            video_clip = video_clip.resize(width=width)
            if video_clip.h > height:
                y_center = video_clip.h // 2
                y1 = max(0, y_center - height // 2)
                y2 = min(video_clip.h, y1 + height)
                video_clip = video_clip.crop(y1=y1, y2=y2)
        
        # Ensure clip fills the frame
        if video_clip.w < width or video_clip.h < height:
            video_clip = video_clip.resize((width, height))
        
        # Set consistent frame rate
        if hasattr(video_clip, 'fps') and video_clip.fps != target_fps:
            video_clip = video_clip.set_fps(target_fps)
        
        # Loop if needed
        if video_clip.duration < duration:
            video_clip = video_clip.loop(duration=duration)
        elif video_clip.duration > duration:
            video_clip = video_clip.subclip(0, duration)
        
        return video_clip
        
    except Exception as e:
        print(f"❌ Error optimizing video clip: {e}")
        return video_clip

def get_output_media(audio_file_path, timed_captions, background_video_data, 
                    orientation="portrait", caption_style="modern", output_name="rendered_video.mp4"):
    """
    Enhanced video generation with better styling and optimization
    """
    
    # Optimized dimensions for 9:16 aspect ratio
    if orientation == "portrait":
        WIDTH, HEIGHT = 1080, 1920
        fontsize = 65  # Slightly larger for better readability
    else:
        WIDTH, HEIGHT = 1920, 1080
        fontsize = 80
    
    print(f"📱 Rendering {orientation} video ({WIDTH}x{HEIGHT}) with {caption_style} captions")
    
    visual_clips = []
    temp_files = []
    
    # Create background color in case no videos are available
    background = ColorClip(size=(WIDTH, HEIGHT), color=(0, 0, 0))
    
    # Process background videos
    print(f"📹 Processing {len(background_video_data)} video segments...")
    for i, video_data in enumerate(background_video_data):
        try:
            print(f"\n--- Processing video {i+1} ---")
            
            time_info, video_url = safe_unpack(video_data, 2, [(-1, -1), None])
            
            if not isinstance(time_info, (tuple, list)) or len(time_info) < 2:
                print(f"❌ Invalid time info for video {i+1}")
                continue
            
            start_time, end_time = float(time_info[0]), float(time_info[1])
            duration = end_time - start_time
            
            if video_url is None or duration <= 0:
                print(f"⚠️ Skipping video {i+1}: Invalid URL or duration")
                # Add black background for this segment
                bg_segment = background.set_start(start_time).set_duration(duration)
                visual_clips.append(bg_segment)
                continue
            
            # Download video
            video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            temp_files.append(video_file)
            
            # Download with better headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(video_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(video_file, 'wb') as f:
                f.write(response.content)
            
            # Create and optimize video clip
            video_clip = VideoFileClip(video_file)
            video_clip = optimize_video_clip(video_clip, WIDTH, HEIGHT, duration)
            video_clip = video_clip.set_start(start_time).set_duration(duration)
            
            visual_clips.append(video_clip)
            print(f"✅ Video {i+1} processed successfully")
            
        except Exception as e:
            print(f"❌ Error processing video {i+1}: {e}")
            # Add fallback background
            try:
                bg_segment = background.set_start(start_time).set_duration(duration)
                visual_clips.append(bg_segment)
            except:
                pass
            continue
    
    # Process captions with enhanced styling
    print(f"\n📝 Processing {len(timed_captions)} captions with {caption_style} style...")
    for i, caption_data in enumerate(timed_captions):
        try:
            print(f"\n--- Processing caption {i+1} ---")
            
            time_info, text = safe_unpack(caption_data, 2, [(0, 0), ""])
            
            if not isinstance(time_info, (tuple, list)) or len(time_info) < 2:
                print(f"❌ Invalid time info for caption {i+1}")
                continue
            
            start_time, end_time = float(time_info[0]), float(time_info[1])
            duration = end_time - start_time
            text_str = str(text).strip()
            
            if not text_str or duration <= 0:
                print(f"⚠️ Skipping invalid caption {i+1}")
                continue
            
            print(f"Caption {i+1}: {start_time:.1f}s - {end_time:.1f}s: '{text_str[:50]}...'")
            
            # Create styled caption
            text_clip = create_styled_caption(
                text=text_str,
                fontsize=fontsize,
                width=WIDTH,
                height=HEIGHT,
                duration=duration,
                start_time=start_time,
                style=caption_style
            )
            
            visual_clips.append(text_clip)
            print(f"✅ Caption {i+1} processed successfully")
            
        except Exception as e:
            print(f"❌ Error processing caption {i+1}: {e}")
            continue
    
    if not visual_clips:
        print("❌ No clips created! Adding default background.")
        # Add a default background for the entire duration
        try:
            audio_clip = AudioFileClip(audio_file_path)
            default_bg = background.set_duration(audio_clip.duration)
            visual_clips.append(default_bg)
        except Exception as e:
            print(f"❌ Could not create default background: {e}")
            return None
    
    # Load audio
    print("🎼 Loading audio...")
    try:
        audio_clip = AudioFileClip(audio_file_path)
    except Exception as e:
        print(f"❌ Error loading audio: {e}")
        return None
    
    # Create final video
    print("🎬 Creating final composite video...")
    try:
        final_video = CompositeVideoClip(visual_clips, size=(WIDTH, HEIGHT))
        final_video = final_video.set_audio(audio_clip)
        
        # Ensure video duration matches audio
        if final_video.duration != audio_clip.duration:
            final_video = final_video.set_duration(audio_clip.duration)
        
    except Exception as e:
        print(f"❌ Error creating composite video: {e}")
        return None
    
    # Render with optimized settings
    print(f"💾 Rendering to {output_name}...")
    try:
        final_video.write_videofile(
            output_name,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",  # Higher bitrate for better quality
            verbose=False,
            logger=None,
            preset='medium',  # Balance between speed and compression
            threads=4  # Use multiple threads for faster encoding
        )
    except Exception as e:
        print(f"❌ Error during video rendering: {e}")
        return None
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        # Close clips to free memory
        try:
            final_video.close()
            audio_clip.close()
            for clip in visual_clips:
                if hasattr(clip, 'close'):
                    clip.close()
        except:
            pass
    
    print(f"✅ Video created successfully: {output_name}")
    return output_name
