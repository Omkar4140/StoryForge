import os
import re
import librosa
import numpy as np
import soundfile as sf
from pathlib import Path
import json

def generate_timed_captions(audio_filename, model_size="base", max_caption_size=15, caption_color="white"):
    """
    Generate timed captions using Whisper
    
    Args:
        audio_filename (str): Path to the audio file
        model_size (str): Whisper model size ("tiny", "base", "small", "medium", "large")
        max_caption_size (int): Maximum words per caption segment
        caption_color (str): Color for captions
    
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
    
    print(f"🎧 Processing: {audio_filename}")
    print(f"🔧 Model: {model_size}, Max words: {max_caption_size}")
    
    try:
        # Load Whisper model
        print("📥 Loading Whisper model...")
        model = whisper.load_model(model_size)
        
        # Transcribe with word timestamps
        print("🔍 Transcribing...")
        result = model.transcribe(audio_filename, word_timestamps=True)
        
        if not result.get('segments'):
            print("❌ No speech detected")
            return []
        
        # Process segments into captions
        captions = []
        current_words = []
        current_start = None
        current_end = None
        
        for segment in result['segments']:
            words = segment.get('words', [])
            
            for word_data in words:
                word = word_data.get('word', '').strip()
                start = word_data.get('start', 0)
                end = word_data.get('end', 0)
                
                if not word:
                    continue
                
                if current_start is None:
                    current_start = start
                
                current_words.append(word)
                current_end = end
                
                # Create caption when reaching max size
                if len(current_words) >= max_caption_size:
                    caption_text = ' '.join(current_words).strip()
                    captions.append(((current_start, current_end), caption_text, caption_color))
                    current_words = []
                    current_start = None
        
        # Add remaining words
        if current_words and current_start is not None:
            caption_text = ' '.join(current_words).strip()
            captions.append(((current_start, current_end), caption_text, caption_color))
        
        print(f"✅ Generated {len(captions)} captions")
        preview_captions(captions)
        return captions
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def validate_caption_format(captions):
    """Ensure all captions have the correct format: ((start, end), text, color)"""
    validated = []
    
    for i, caption in enumerate(captions):
        try:
            if isinstance(caption, (tuple, list)) and len(caption) >= 2:
                time_info = caption[0]
                text = caption[1]
                color = caption[2] if len(caption) > 2 else "white"
                
                # Ensure time_info is a tuple of two numbers
                if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                    start_time = float(time_info[0])
                    end_time = float(time_info[1])
                    
                    # Ensure text is a string
                    text = str(text).strip()
                    
                    if text:  # Only add non-empty captions
                        validated.append(((start_time, end_time), text, color))
                else:
                    print(f"⚠️  Skipping caption {i}: invalid time format {time_info}")
            else:
                print(f"⚠️  Skipping caption {i}: invalid format {caption}")
                
        except Exception as e:
            print(f"⚠️  Error validating caption {i}: {e}")
            continue
    
    print(f"✅ Validated {len(validated)} captions out of {len(captions)}")
    return validated




def convert_to_wav(audio_filename):
    """Convert audio file to WAV format if needed"""
    if audio_filename.lower().endswith('.wav'):
        return audio_filename
    
    try:
        # Load audio and save as WAV
        audio_data, sr = librosa.load(audio_filename, sr=16000)
        wav_filename = audio_filename.rsplit('.', 1)[0] + '_temp.wav'
        sf.write(wav_filename, audio_data, sr)
        return wav_filename
    except Exception as e:
        print(f"❌ Error converting to WAV: {e}")
        return None

def preview_captions(captions):
    """Preview generated captions"""
    print("📋 Caption preview:")
    for i, caption_data in enumerate(captions[:3]):
        try:
            if isinstance(caption_data, (tuple, list)) and len(caption_data) >= 2:
                time_info = caption_data[0]
                text = caption_data[1]
                color = caption_data[2] if len(caption_data) > 2 else "white"
                
                if isinstance(time_info, (tuple, list)) and len(time_info) >= 2:
                    start, end = time_info[0], time_info[1]
                    print(f"   {i+1}. [{start:.1f}s - {end:.1f}s] ({color}): {text}")
                else:
                    print(f"   {i+1}. Invalid time format: {caption_data}")
            else:
                print(f"   {i+1}. Invalid caption format: {caption_data}")
        except Exception as e:
            print(f"   {i+1}. Error displaying caption: {e}")
    
    if len(captions) > 3:
        print(f"   ... and {len(captions) - 3} more")
