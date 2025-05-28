import os
import asyncio
import argparse
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals

def main():
    """Main function to orchestrate the StoryForge video creation process"""
    parser = argparse.ArgumentParser(description="StoryForge - Generate compelling story videos from topics")
    parser.add_argument("topic", type=str, help="The topic/theme for the story video")
    parser.add_argument("--video-server", type=str, default="pexel", choices=["pexel"], 
                       help="Video source server (default: pexel)")
    parser.add_argument("--audio-file", type=str, default="story_audio.wav",
                       help="Output audio filename (default: story_audio.wav)")
    
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
        for i, ((start, end), text) in enumerate(timed_captions[:3]):
            print(f"   {i+1}. [{start:.1f}s - {end:.1f}s]: {text}")
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
            for i, (time_segment, queries) in enumerate(search_terms[:3]):
                print(f"   {i+1}. [{time_segment[0]:.1f}s - {time_segment[1]:.1f}s]: {queries}")
            if len(search_terms) > 3:
                print(f"   ... and {len(search_terms) - 3} more segments")
            print()
            
            # Step 5: Find background videos
            print("🎥 Step 5: Finding background videos...")
            background_video_urls = generate_video_url(search_terms, args.video_server)
            if not background_video_urls:
                print("⚠️  Warning: No background videos found. Proceeding with audio only.")
            else:
                successful_videos = sum(1 for entry in background_video_urls if len(entry) >= 2 and entry[1] is not None)
                print(f"✅ Found background videos for {successful_videos}/{len(background_video_urls)} segments")
                
                # Merge empty intervals
                background_video_urls = merge_empty_intervals(background_video_urls)
                print(f"📐 Merged intervals: {len(background_video_urls)} final segments")
        
        print()
        
        # Step 6: Render the final video
        print("🎬 Step 6: Rendering final video...")
        if background_video_urls:
            output_video = get_output_media(args.audio_file, timed_captions, background_video_urls, args.video_server)
            if output_video:
                print(f"🎉 SUCCESS! Your StoryForge video has been created: {output_video}")
                print(f"📊 Video includes:")
                print(f"   • Story narration audio")
                print(f"   • Synchronized captions")
                print(f"   • Background video footage")
            else:
                print("❌ Failed to render the final video.")
        else:
            print("⚠️  Creating audio-only version due to missing background videos.")
            # Could implement audio-only video creation here
            print("💡 Tip: Check your PEXELS_KEY and internet connection for video footage.")
        
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        print("💡 Please check your API keys and internet connection.")
    
    print("\n🎬 StoryForge process completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
