import edge_tts
import asyncio
import os

async def generate_audio(text, filename):
    """
    Generate high-quality audio narration from text using edge-tts
    
    Args:
        text (str): The story script to convert to speech
        filename (str): Output audio filename
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Input validation and sanitization
    if not text or not isinstance(text, str):
        print(f"❌ Invalid text input: {text}")
        text = "Sorry, there was an issue with the story content."
        print(f"🔄 Using fallback text")
    
    # Clean and validate text
    text = str(text).strip()
    if len(text) == 0:
        text = "This is a StoryForge audio test message."
        print(f"⚠️  Empty text detected, using default message")
    
    # Remove any problematic characters that might cause TTS issues
    text = text.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())  # Normalize whitespace
    
    print(f"🎵 Generating narration audio...")
    print(f"📝 Text length: {len(text)} characters")
    print(f"📖 Preview: {text[:80]}{'...' if len(text) > 80 else ''}")
    
    try:
        # Use a high-quality, storytelling-appropriate voice
        voice = "en-US-GuyNeural"  # Clear, engaging male voice for storytelling
        
        # Alternative voices for different story types:
        # "en-US-JennyNeural" - Warm female voice
        # "en-US-AriaNeural" - Expressive female voice
        # "en-US-DavisNeural" - Deep male voice
        
        print(f"🎤 Using voice: {voice}")
        
        # Create TTS communication object
        communicate = edge_tts.Communicate(
            text=text, 
            voice=voice,
            rate="+0%",     # Normal speaking rate
            volume="+0%",   # Normal volume
            pitch="+0Hz"    # Normal pitch
        )
        
        # Generate and save the audio
        await communicate.save(filename)
        
        # Verify the file was created and has content
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            file_size = os.path.getsize(filename)
            print(f"✅ Audio narration saved successfully!")
            print(f"📁 File: {filename}")
            print(f"📊 Size: {file_size:,} bytes")
            return True
        else:
            print(f"❌ Audio file was not created or is empty")
            return False
        
    except Exception as e:
        print(f"❌ Error generating audio: {e}")
        
        # Attempt with fallback settings
        try:
            print(f"🔄 Attempting with fallback configuration...")
            fallback_text = "StoryForge encountered an audio generation error. Please check your internet connection."
            
            communicate = edge_tts.Communicate(
                text=fallback_text, 
                voice="en-US-AriaNeural"  # Different voice as fallback
            )
            
            await communicate.save(filename)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"✅ Fallback audio saved successfully")
                return True
            else:
                print(f"❌ Fallback audio creation also failed")
                return False
                
        except Exception as fallback_error:
            print(f"❌ Fallback audio generation failed: {fallback_error}")
            return False

def get_available_voices():
    """Get list of available voices for TTS"""
    return [
        "en-US-GuyNeural",      # Clear male voice (default)
        "en-US-JennyNeural",    # Warm female voice
        "en-US-AriaNeural",     # Expressive female voice
        "en-US-DavisNeural",    # Deep male voice
        "en-US-SaraNeural",     # Professional female voice
        "en-US-TonyNeural"      # Confident male voice
    ]

async def test_audio_generation():
    """Test function for audio generation"""
    test_script = """Once upon a time, in a small village nestled between rolling hills, there lived a young girl named Luna who discovered that every star in the night sky held a secret wish from someone in the world. Each evening, she would climb to her rooftop and listen carefully to the whispers carried by the wind, collecting these dreams in a small golden jar that glowed brighter with each wish it contained."""
    
    print("🧪 Testing audio generation...")
    print(f"📝 Test script: {test_script[:100]}...")
    
    success = await generate_audio(test_script, "test_audio.wav")
    
    if success:
        print("✅ Audio generation test passed!")
    else:
        print("❌ Audio generation test failed!")
    
    return success

if __name__ == "__main__":
    asyncio.run(test_audio_generation())
