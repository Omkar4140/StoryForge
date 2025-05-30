import os
import asyncio
import argparse
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals

def safe_unpack(data, expected_count, default_values=None):
    """
    Safely unpack data with fallback to defaults - Enhanced version
    
    Args:
        data: Data to unpack (tuple, list, etc.)
        expected_count: Number of values expected
        default_values: List of default values if unpacking fails
    
    Returns:
        tuple: Unpacked values or defaults
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
                    # Fill missing values with defaults
                    result = list(data) + default_values[len(data):]
                    return tuple(result[:expected_count])
                else:
                    # Pad with None values
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

def main():
    """Main function to orchestrate the StoryForge video creation process"""
    parser = argparse.ArgumentParser(description="StoryForge - Generate compelling story videos from topics")
    parser.add_argument("topic", type=str, help="The topic/theme for the story video")
    parser.add_argument("--video-server", type=str, default="pexel", choices=["pexel"], 
                       help="Video source server (default: pexel)")
    parser.add_argument("--audio-file", type=str, default="story_audio.wav",
                       help="Output audio filename (default: story_audio.wav)")
    parser.add_argument("--orientation", type=str, default="portrait", choices=["portrait", "landscape"], 
                   help="Video orientation (default: portrait for mobile fullscreen)")
    
    args = parser.parse_args()
    
    print("🎬 Welcome to StoryForge - Creating your story video...")
    print(f"📝 Topic: {args.topic}")
    print("=" * 50)
    
    try:
        # Step 1: Generate the story script
        print("🔮 Step 1: Generating story script...")
        script = generate_script(args.topic)
        if not script:
            print("❌ Failed to generate script. Please check your GROQ_API_KEY.")
            return
        
        print(f"✅ Script generated successfully!")
        print(f"📖 Script preview: {script[:100]}...")
        print()
        
        # Step 2: Generate audio narration
        print("🎵 Step 2: Generating audio narration...")
        audio_success = asyncio.run(generate_audio(script, args.audio_file))
        if not audio_success:
            print("❌ Failed to generate audio narration.")
            return
        
        print(f"✅ Audio narration saved as: {args.audio_file}")
        print()
        
        # Step 3: Generate timed captions
        print("📝 Step 3: Generating timed captions...")
        timed_captions = generate_timed_captions(args.audio_file)
        if not timed_captions:
            print("❌ Failed to generate timed captions.")
            return
        
        print(f"✅ Generated {len(timed_captions)} timed caption segments")
        print("📋 Caption preview:")
        
        # Use safe_unpack for caption preview
        for i, caption_data in enumerate(timed_captions[:3]):
            try:
                time_info, text = safe_unpack(caption_data, 2, default_values=[(0, 0), ""])
                if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                    start, end = time_info[0], time_info[1]
                    print(f"   {i+1}. [{start:.1f}s - {end:.1f}s]: {text}")
                else:
                    print(f"   {i+1}. Invalid caption format: {caption_data}")
            except Exception as e:
                print(f"   {i+1}. Error displaying caption: {e}")
        
        if len(timed_captions) > 3:
            print(f"   ... and {len(timed_captions) - 3} more segments")
        print()
        
        # Step 4: Generate video search queries
        print("🔍 Step 4: Generating video search queries...")
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)
        if not search_terms:
            print("⚠️  Warning: No video search queries generated. Proceeding with audio only.")
            background_video_urls = None
        else:
            print(f"✅ Generated search queries for {len(search_terms)} segments")
            print("🔎 Search query preview:")
            
            # Use safe_unpack for search terms preview
            for i, search_data in enumerate(search_terms[:3]):
                try:
                    time_segment, queries = safe_unpack(search_data, 2, default_values=[(0, 0), []])
                    if isinstance(time_segment, (tuple, list)) and len(time_segment) >= 2:
                        start, end = time_segment[0], time_segment[1]
                        print(f"   {i+1}. [{start:.1f}s - {end:.1f}s]: {queries}")
                    else:
                        print(f"   {i+1}. Invalid search format: {search_data}")
                except Exception as e:
                    print(f"   {i+1}. Error displaying search query: {e}")
            
            if len(search_terms) > 3:
                print(f"   ... and {len(search_terms) - 3} more segments")
            print()
            
            # Step 5: Find background videos
            print("🎥 Step 5: Finding background videos...")
            background_video_urls = generate_video_url(search_terms, args.video_server)
            if not background_video_urls:
                print("⚠️  Warning: No background videos found. Proceeding with audio only.")
            else:
                # Count successful videos using safe_unpack
                successful_videos = 0
                for entry in background_video_urls:
                    try:
                        time_info, url = safe_unpack(entry, 2, default_values=[None, None])
                        if url is not None:
                            successful_videos += 1
                    except:
                        continue
                
                print(f"✅ Found background videos for {successful_videos}/{len(background_video_urls)} segments")
                
                # Merge empty intervals
                background_video_urls = merge_empty_intervals(background_video_urls)
                print(f"📐 Merged intervals: {len(background_video_urls)} final segments")
        
        print()
        
        # Step 6: Render the final video
        print("🎬 Step 6: Rendering final video...")
        if background_video_urls:
    # Pass orientation parameter to ensure portrait rendering
            output_video = get_output_media(
                audio_file=args.audio_file, 
                timed_captions=timed_captions, 
                background_video_data=background_video_urls, 
                video_server=args.video_server,
                orientation=args.orientation  # Add this line
            )
            if output_video:
                print(f"🎉 SUCCESS! Your StoryForge video has been created: {output_video}")
                print(f"📊 Video specs:")
                print(f"   • Resolution: {'1080x1920 (9:16 Portrait)' if args.orientation == 'portrait' else '1920x1080 (16:9 Landscape)'}")
                print(f"   • Optimized for: {'Mobile Fullscreen' if args.orientation == 'portrait' else 'Desktop/TV'}")
                print(f"   • Story narration audio")
                print(f"   • Synchronized captions")
                print(f"   • Background video footage")
            else:
                print("❌ Failed to render the final video.")
        else:
            print("⚠️  Creating audio-only version due to missing background videos.")
            print("💡 Tip: Check your PEXELS_KEY and internet connection for video footage.")
        
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        print("💡 Please check your API keys and internet connection.")
        
        # Add debug information
        import traceback
        print("🔍 Debug traceback:")
        traceback.print_exc()
    
    print("\n🎬 StoryForge process completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
