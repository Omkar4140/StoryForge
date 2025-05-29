import whisper_timestamped as whisper
import re
import os
import librosa
import numpy as np
import soundfile as sf
from pathlib import Path

def generate_timed_captions(audio_filename, model_size="base", max_caption_size=15, caption_color="white"):
    """
    Generate timed captions from audio file using Whisper with enhanced error handling
    
    Args:
        audio_filename (str): Path to the audio file
        model_size (str): Whisper model size ("tiny", "base", "small", "medium", "large")
        max_caption_size (int): Maximum words per caption segment
        caption_color (str): Color for captions (white, yellow, red, blue, green, etc.)
    
    Returns:
        list: List of ((start_time, end_time), caption_text, color) tuples
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
    print(f"🎨 Caption color: {caption_color}")
    
    try:
        # Preprocess audio file to ensure compatibility
        print("🔧 Preprocessing audio file...")
        processed_audio_path = preprocess_audio_file(audio_filename)
        
        if not processed_audio_path:
            print("❌ Failed to preprocess audio file")
            return []
        
        # Load Whisper model
        print("📥 Loading Whisper model...")
        model = whisper.load_model(model_size)
        
        # Transcribe with timestamps
        print("🔍 Transcribing audio with timestamps...")
        transcription = whisper.transcribe_timestamped(
            model, 
            processed_audio_path, 
            verbose=False, 
            fp16=False,
            language="en",  # Specify English for better accuracy
            beam_size=1,   # Reduce beam size for stability
            best_of=1      # Use single best transcription
        )
        
        # Clean up temporary file if it was created
        if processed_audio_path != audio_filename:
            try:
                os.remove(processed_audio_path)
                print("🧹 Cleaned up temporary audio file")
            except:
                pass
        
        # Enhanced error checking for transcription result
        if transcription is None:
            print("❌ Transcription returned None")
            return fallback_transcription(audio_filename, model_size, max_caption_size, caption_color)
        
        if not isinstance(transcription, dict):
            print(f"❌ Transcription is not a dictionary, got: {type(transcription)}")
            return fallback_transcription(audio_filename, model_size, max_caption_size, caption_color)
        
        if 'segments' not in transcription:
            print("❌ No 'segments' key in transcription")
            print(f"Available keys: {list(transcription.keys()) if isinstance(transcription, dict) else 'N/A'}")
            return fallback_transcription(audio_filename, model_size, max_caption_size, caption_color)
        
        segments = transcription.get('segments', [])
        if not segments:
            print("❌ No transcription segments found")
            return fallback_transcription(audio_filename, model_size, max_caption_size, caption_color)
        
        print(f"✅ Transcription completed!")
        print(f"📊 Found {len(segments)} segments")
        
        # Generate timed captions with color
        captions = create_timed_captions(transcription, max_caption_size, caption_color)
        
        print(f"✅ Generated {len(captions)} caption segments")
        
        # Preview captions
        print("📋 Caption preview:")
        for i, ((start, end), text, color) in enumerate(captions[:3]):
            print(f"   {i+1}. [{start:.1f}s - {end:.1f}s] ({color}): {text}")
        if len(captions) > 3:
            print(f"   ... and {len(captions) - 3} more")
        
        return captions
        
    except Exception as e:
        print(f"❌ Error generating timed captions: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        # Try alternative approach with basic whisper
        print("🔄 Attempting fallback transcription...")
        try:
            return fallback_transcription(audio_filename, model_size, max_caption_size, caption_color)
        except Exception as fallback_error:
            print(f"❌ Fallback transcription also failed: {fallback_error}")
            return []

def preprocess_audio_file(audio_filename):
    """
    Preprocess audio file to ensure compatibility with Whisper
    
    Args:
        audio_filename (str): Path to original audio file
    
    Returns:
        str: Path to processed audio file (may be same as input if no processing needed)
    """
    try:
        print("🔍 Analyzing audio file...")
        
        # Get audio info
        try:
            # Try to load with librosa first
            audio_data, sample_rate = librosa.load(audio_filename, sr=None)
            print(f"📊 Audio info: {len(audio_data)} samples, {sample_rate} Hz, {len(audio_data)/sample_rate:.1f}s duration")
            
            # Check if audio data is valid
            if len(audio_data) == 0:
                print("❌ Audio file contains no data")
                return None
                
            if np.all(audio_data == 0):
                print("❌ Audio file contains only silence")
                return None
            
        except Exception as e:
            print(f"❌ Failed to analyze audio with librosa: {e}")
            
            # Try with soundfile
            try:
                audio_data, sample_rate = sf.read(audio_filename)
                print(f"📊 Audio info (soundfile): {len(audio_data)} samples, {sample_rate} Hz")
            except Exception as sf_error:
                print(f"❌ Failed to read audio with soundfile: {sf_error}")
                return None
        
        # Check if we need to convert the audio
        needs_conversion = False
        temp_file_path = None
        
        # Whisper works best with 16kHz mono audio
        target_sr = 16000
        
        if sample_rate != target_sr:
            print(f"🔄 Converting sample rate from {sample_rate}Hz to {target_sr}Hz")
            needs_conversion = True
        
        if len(audio_data.shape) > 1:
            print("🔄 Converting to mono")
            needs_conversion = True
        
        if needs_conversion:
            # Resample and convert to mono
            if len(audio_data.shape) > 1:
                audio_data = librosa.to_mono(audio_data.T)  # Convert to mono
            
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)
            
            # Create temporary file
            temp_file_path = audio_filename.rsplit('.', 1)[0] + '_processed.wav'
            sf.write(temp_file_path, audio_data, target_sr)
            print(f"💾 Saved processed audio to: {temp_file_path}")
            
            return temp_file_path
        else:
            print("✅ Audio file is already in compatible format")
            return audio_filename
            
    except Exception as e:
        print(f"❌ Error preprocessing audio: {e}")
        return None

def fallback_transcription(audio_filename, model_size, max_caption_size, caption_color):
    """
    Fallback transcription method using basic whisper without timestamps
    """
    print("🔄 Using fallback transcription without detailed timestamps...")
    
    try:
        import whisper as basic_whisper
        
        # Load basic whisper model
        model = basic_whisper.load_model(model_size)
        
        # Basic transcription
        result = model.transcribe(audio_filename, language="en")
        
        if not result or 'text' not in result:
            print("❌ Fallback transcription failed")
            return []
        
        # Create simple timed segments (estimate timing)
        text = result['text'].strip()
        words = text.split()
        
        # Group words into segments
        segments = []
        current_segment = []
        
        for word in words:
            if len(current_segment) >= max_caption_size:
                segments.append(' '.join(current_segment))
                current_segment = [word]
            else:
                current_segment.append(word)
        
        if current_segment:
            segments.append(' '.join(current_segment))
        
        # Estimate timing (rough approximation)
        total_duration = len(words) * 0.5  # Assume ~0.5 seconds per word
        segment_duration = total_duration / len(segments) if segments else 1.0
        
        timed_captions = []
        for i, segment in enumerate(segments):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            timed_captions.append(((start_time, end_time), segment, caption_color))
        
        print(f"✅ Fallback generated {len(timed_captions)} caption segments")
        return timed_captions
        
    except Exception as e:
        print(f"❌ Fallback transcription error: {e}")
        return []

def create_timed_captions(whisper_result, max_caption_size=15, caption_color="white"):
    """
    Convert Whisper transcription to timed caption segments with color
    
    Args:
        whisper_result (dict): Whisper transcription result
        max_caption_size (int): Maximum words per caption
        caption_color (str): Color for captions
    
    Returns:
        list: Timed caption segments with color
    """
    
    if not whisper_result or 'text' not in whisper_result:
        return []
    
    # Create word-to-timestamp mapping
    word_timestamps = create_word_timestamp_mapping(whisper_result)
    
    if not word_timestamps:
        print("⚠️  No word timestamps available, using segment-level timing")
        return create_segment_based_captions(whisper_result, max_caption_size, caption_color)
    
    # Split text into caption-sized chunks
    full_text = whisper_result['text'].strip()
    words = full_text.split()
    
    # Clean words (remove excessive punctuation but keep basic punctuation)
    cleaned_words = [clean_word(word) for word in words]
    
    # Group words into caption segments
    caption_segments = group_words_by_size(cleaned_words, max_caption_size)
    
    # Assign timestamps to caption segments
    timed_captions = assign_timestamps_to_captions(caption_segments, word_timestamps, full_text, caption_color)
    
    return timed_captions

def create_segment_based_captions(whisper_result, max_caption_size, caption_color):
    """Create captions based on segment-level timestamps when word-level isn't available"""
    captions = []
    
    try:
        segments = whisper_result.get('segments', [])
        
        for segment in segments:
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            end = segment.get('end', start + 1)
            
            if not text:
                continue
            
            words = text.split()
            
            # Split long segments into smaller captions
            if len(words) <= max_caption_size:
                captions.append(((start, end), text, caption_color))
            else:
                # Split segment into smaller parts
                segment_duration = end - start
                word_count = len(words)
                
                current_words = []
                current_start = start
                
                for i, word in enumerate(words):
                    current_words.append(word)
                    
                    if len(current_words) >= max_caption_size or i == len(words) - 1:
                        # Calculate end time for this sub-segment
                        progress = (i + 1) / word_count
                        current_end = start + (segment_duration * progress)
                        
                        caption_text = ' '.join(current_words)
                        captions.append(((current_start, current_end), caption_text, caption_color))
                        
                        current_words = []
                        current_start = current_end
        
    except Exception as e:
        print(f"⚠️  Error creating segment-based captions: {e}")
    
    return captions

def create_word_timestamp_mapping(whisper_result):
    """Create mapping from text positions to timestamps with enhanced error handling"""
    word_to_time = {}
    text_position = 0
    
    try:
        segments = whisper_result.get('segments', [])
        
        for segment in segments:
            # Check if segment has words with timestamps
            words = segment.get('words', [])
            
            if not words:
                # Fallback: use segment-level timing
                text = segment.get('text', '').strip()
                if text:
                    start_time = segment.get('start', 0)
                    end_time = segment.get('end', start_time + 1)
                    word_to_time[(text_position, text_position + len(text))] = end_time
                    text_position += len(text) + 1
                continue
            
            for word_info in words:
                if not isinstance(word_info, dict):
                    continue
                    
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

def assign_timestamps_to_captions(caption_segments, word_timestamps, full_text, caption_color):
    """Assign start and end timestamps to caption segments with color"""
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
        
        timed_captions.append(((start_time, end_time), segment_text.strip(), caption_color))
        
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

def diagnose_audio_file(audio_filename):
    """
    Diagnose audio file issues
    """
    print(f"🔍 Diagnosing audio file: {audio_filename}")
    
    if not os.path.exists(audio_filename):
        print("❌ File does not exist")
        return False
    
    file_size = os.path.getsize(audio_filename)
    print(f"📁 File size: {file_size} bytes")
    
    if file_size == 0:
        print("❌ File is empty")
        return False
    
    try:
        # Try different audio libraries
        print("🔍 Testing with librosa...")
        audio_data, sr = librosa.load(audio_filename, sr=None)
        print(f"✅ Librosa: {len(audio_data)} samples, {sr}Hz, {len(audio_data)/sr:.1f}s")
        
        print("🔍 Testing with soundfile...")
        sf_data, sf_sr = sf.read(audio_filename)
        print(f"✅ Soundfile: {len(sf_data)} samples, {sf_sr}Hz")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio diagnosis failed: {e}")
        return False
