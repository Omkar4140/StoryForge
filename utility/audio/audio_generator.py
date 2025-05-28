import edge_tts
import asyncio

async def generate_audio(text, filename):
    """Generate audio from text using edge-tts"""
    
    # Validate input
    if not text or not isinstance(text, str):
        print(f"❌ Invalid text input: {text}")
        fallback_text = "Sorry, there was an issue generating the script content."
        print(f"Using fallback text: {fallback_text}")
        text = fallback_text
    
    # Clean and validate text
    text = str(text).strip()
    if len(text) == 0:
        text = "Hello, this is a test audio message."
        print(f"Empty text detected, using default: {text}")
    
    try:
        print(f"🔊 Generating audio for: {text[:50]}...")
        
        # Create the TTS communication
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        
        # Generate and save the audio
        await communicate.save(filename)
        
        print(f"✅ Audio saved as: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating audio: {e}")
        
        # Try with a simple fallback
        try:
            fallback_text = "Audio generation encountered an error."
            communicate = edge_tts.Communicate(fallback_text, "en-US-GuyNeural")
            await communicate.save(filename)
            print(f"✅ Fallback audio saved as: {filename}")
            return True
        except Exception as e2:
            print(f"❌ Fallback audio generation also failed: {e2}")
            return False
