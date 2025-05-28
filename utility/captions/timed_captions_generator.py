import whisper_timestamped as whisper
import re
import os

def generate_timed_captions(audio_filename, model_size="base", max_caption_size=15):
    """
    Generate timed captions from audio file using Whisper
    
    Args:
        audio_filename (str): Path to the audio file
        model_size (str): Whisper model size ("tiny", "base", "small", "medium", "large")
        max_caption_size (int): Maximum words per caption segment
    
    Returns:
        list: List of ((start_time, end_time), caption_text) tuples
    """
    
    # Validate input file
    if not os.path.exists(audio_filename):
        print(f"❌ Audio file not found: {audio_filename}")
        return []
    
    if os.path.getsize(audio_filename) == 0:
        print(f"❌ Audio file is empty: {audio_filename}")
        return []
    
    print(f"🎧 Processing audio file: {audio_filename}")
    print(f"🧠 Using Whisper model: {model_size}")
    print(f"📏 Max caption size: {max_caption_size} words")
    
    try:
        # Load Whisper model
        print("📥 Loading Whisper model...")
        model = whisper.load_model(model_size)
        
        # Transcribe with timestamps
        print("🔍 Transcribing audio with timestamps...")
        transcription = whisper.transcribe_timestamped(
            model, 
            audio_filename, 
            verbose=False, 
            fp16=False,
            language="en"  # Specify English for better accuracy
        )
        
        if not transcription or 'segments' not in transcription:
            print("❌ No transcription segments found")
            return []
        
        print(f"✅ Transcription completed!")
        print(f"📊 Found {len(transcription['segments'])} segments")
        
        # Generate timed captions
        captions = create_timed_captions(transcription, max_caption_size)
        
        print(f"✅ Generated {len(captions)} caption segments")
        
        # Preview captions
        print("📋 Caption preview:")
        for i, ((start, end), text) in enumerate(captions[:3]):
            print(f"   {i+1}. [{start:.1f}s - {end:.1f}s]: {text}")
        if len(captions) > 3:
            print(f"   ... and {len(captions) - 3} more")
        
        return captions
        
    except Exception as e:
        print(f"❌ Error generating timed captions: {e}")
        return []

def create_timed_captions(whisper_result, max_caption_size=15):
    """
    Convert Whisper transcription to timed caption segments
    
    Args:
        whisper_result (dict): Whisper transcription result
        max_caption_size (int): Maximum words per caption
    
    Returns:
        list: Timed caption segments
    """
    
    if not whisper_result or 'text' not in whisper_result:
        return []
    
    # Create word-to-timestamp mapping
    word_timestamps = create_word_timestamp_mapping(whisper_result)
    
    if not word_timestamps:
        print("⚠️  No word timestamps available")
        return []
    
    # Split text into caption-sized chunks
    full_text = whisper_result['text'].strip()
    words = full_text.split()
    
    # Clean words (remove excessive punctuation but keep basic punctuation)
    cleaned_words = [clean_word(word) for word in words]
    
    # Group words into caption segments
    caption_segments = group_words_by_size(cleaned_words, max_caption_size)
    
    # Assign timestamps to caption segments
    timed_captions = assign_timestamps_to_captions(caption_segments, word_timestamps, full_text)
    
    return timed_captions

def create_word_timestamp_mapping(whisper_result):
    """Create mapping from text positions to timestamps"""
    word_to_time = {}
    text_position = 0
    
    try:
        for segment in whisper_result.get('segments', []):
            for word_info in segment.get('words', []):
                word_text = word_info.get('text', '').strip()
                word_end_time = word_info.get('end', 0)
                
                if word_text and word_end_time:
                    # Find word position in full text
                    start_pos = text_position
                    end_pos = text_position + len(word_text)
                    word_to_time[(start_pos, end_pos)] = word_end_time
                    text_position = end_pos + 1  # +1 for space
                    
    except Exception as e:
        print(f"⚠️  Error creating word timestamp mapping: {e}")
    
    return word_to_time

def clean_word(word):
    """Clean word while preserving essential punctuation for readability"""
    if not word:
        return ""
    
    # Remove excessive punctuation but keep basic sentence structure
    # Keep: periods, commas, question marks, exclamation points, apostrophes
    cleaned = re.sub(r'[^\w\s\-_.,!?\'"]+', '', word)
    return cleaned.strip()

def group_words_by_size(words, max_size):
    """Group words into caption-sized segments"""
    if not words:
        return []
    
    segments = []
    current_segment = []
    
    for word in words:
        # Check if adding this word would exceed the limit
        if len(current_segment) >= max_size:
            # Save current segment and start new one
            if current_segment:
                segments.append(' '.join(current_segment))
            current_segment = [word]
        else:
            current_segment.append(word)
    
    # Add the last segment
    if current_segment:
        segments.append(' '.join(current_segment))
    
    return segments

def assign_timestamps_to_captions(caption_segments, word_timestamps, full_text):
    """Assign start and end timestamps to caption segments"""
    timed_captions = []
    text_position = 0
    start_time = 0
    
    for segment_text in caption_segments:
        if not segment_text.strip():
            continue
        
        # Find the position of this segment in the full text
        segment_start_pos = text_position
        segment_end_pos = text_position + len(segment_text)
        
        # Find the end timestamp for this segment
        end_time = find_timestamp_for_position(segment_end_pos, word_timestamps)
        
        if end_time is None:
            # Estimate based on previous segments or use start_time + duration estimate
            estimated_duration = len(segment_text.split()) * 0.5  # ~0.5 seconds per word
            end_time = start_time + estimated_duration
        
        # Ensure end_time is greater than start_time
        if end_time <= start_time:
            end_time = start_time + 1.0  # Minimum 1 second duration
        
        timed_captions.append(((start_time, end_time), segment_text.strip()))
        
        # Update position and start time for next segment
        text_position = segment_end_pos + 1  # +1 for space
        start_time = end_time
    
    return timed_captions

def find_timestamp_for_position(position, word_timestamps):
    """Find the timestamp for a given text position"""
    for (start_pos, end_pos), timestamp in word_timestamps.items():
        if start_pos <= position <= end_pos:
            return timestamp
    
    # If exact match not found, find the closest one
    closest_timestamp = None
    min_distance = float('inf')
    
    for (start_pos, end_pos), timestamp in word_timestamps.items():
        distance = min(abs(start_pos - position), abs(end_pos - position))
        if distance < min_distance:
            min_distance = distance
            closest_timestamp = timestamp
    
    return closest_timestamp

def test_caption_generation():
    """Test function for caption generation"""
    print("🧪 Testing timed caption generation...")
    
    # This would require an actual audio file to test
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        captions = generate_timed_captions(test_audio)
        if captions:
            print("✅ Caption generation test passed!")
            return True
        else:
            print("❌ Caption generation test failed!")
            return False
    else:
        print(f"⚠️  Test audio file not found: {test_audio}")
        return False

if __name__ == "__main__":
    test_caption_generation()
