import os
import re
import librosa
import numpy as np
import soundfile as sf
from pathlib import Path
import json

def generate_timed_captions(audio_filename, model_size="base", max_caption_size=15, caption_color="white", method="faster-whisper"):
    """
    Generate timed captions using multiple alternative methods
    
    Args:
        audio_filename (str): Path to the audio file
        model_size (str): Model size
        max_caption_size (int): Maximum words per caption segment
        caption_color (str): Color for captions
        method (str): Method to use ("faster-whisper", "wav2vec2", "basic-whisper", "vosk")
    
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
    print(f"🔧 Using method: {method}")
    print(f"📏 Max caption size: {max_caption_size} words")
    print(f"🎨 Caption color: {caption_color}")
    
    # Try different methods in order of preference
    methods = [
        ("faster-whisper", try_faster_whisper),
        ("wav2vec2", try_wav2vec2_with_alignment),
        ("vosk", try_vosk),
        ("basic-whisper", try_basic_whisper_with_vad),
    ]
    
    # If specific method requested, try it first
    if method != "faster-whisper":
        methods = [(m, f) for m, f in methods if m == method] + [(m, f) for m, f in methods if m != method]
    
    for method_name, method_func in methods:
        try:
            print(f"\n🔍 Trying {method_name}...")
            captions = method_func(audio_filename, model_size, max_caption_size, caption_color)
            
            if captions:
                print(f"✅ {method_name} succeeded with {len(captions)} captions!")
                preview_captions(captions)
                # Validate caption format before returning
                validated_captions = validate_caption_format(captions)
                return validated_captions
            else:
                print(f"⚠️  {method_name} returned no captions")
                
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("❌ All methods failed")
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

def try_faster_whisper(audio_filename, model_size, max_caption_size, caption_color):
    """
    Method 1: Use faster-whisper (most recommended)
    Install: pip install faster-whisper
    """
    try:
        from faster_whisper import WhisperModel
        
        print("📥 Loading faster-whisper model...")
        # Use CPU or GPU based on availability
        device = "cpu"  # Change to "cuda" if you have GPU
        model = WhisperModel(model_size, device=device, compute_type="int8")
        
        print("🔍 Transcribing with faster-whisper...")
        segments, info = model.transcribe(
            audio_filename,
            language="en",
            beam_size=1,
            word_timestamps=True,
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        
        # Convert segments to our format
        captions = []
        current_words = []
        current_start = None
        current_end = None
        
        print(f"📝 Processing segments...")
        
        for segment in segments:
            print(f"Segment: {segment.start:.1f}s - {segment.end:.1f}s: {segment.text}")
            
            if hasattr(segment, 'words') and segment.words:
                # Use word-level timestamps
                for word_info in segment.words:
                    try:
                        # Handle different word object formats
                        if hasattr(word_info, 'word'):
                            word_text = word_info.word.strip()
                            word_start = float(word_info.start)
                            word_end = float(word_info.end)
                        else:
                            # Alternative format handling
                            word_text = str(word_info).strip()
                            word_start = segment.start
                            word_end = segment.end
                        
                        if not word_text:
                            continue
                            
                        if current_start is None:
                            current_start = word_start
                        
                        current_words.append(word_text)
                        current_end = word_end
                        
                        # Create caption when we reach max size
                        if len(current_words) >= max_caption_size:
                            caption_text = ' '.join(current_words).strip()
                            if caption_text:
                                captions.append(((current_start, current_end), caption_text, caption_color))
                            current_words = []
                            current_start = None
                            current_end = None
                            
                    except Exception as e:
                        print(f"⚠️  Error processing word: {e}")
                        continue
            else:
                # Use segment-level timestamps as fallback
                words = segment.text.strip().split()
                if words:
                    segment_captions = split_segment_into_captions(
                        words, segment.start, segment.end, max_caption_size, caption_color
                    )
                    captions.extend(segment_captions)
        
        # Add remaining words
        if current_words and current_start is not None:
            if current_end is None:
                current_end = current_start + len(current_words) * 0.5
            caption_text = ' '.join(current_words).strip()
            if caption_text:
                captions.append(((current_start, current_end), caption_text, caption_color))
        
        print(f"✅ Generated {len(captions)} captions with faster-whisper")
        return captions
        
    except ImportError:
        print("❌ faster-whisper not installed. Install with: pip install faster-whisper")
        return []
    except Exception as e:
        print(f"❌ faster-whisper error: {e}")
        import traceback
        traceback.print_exc()
        return []

def try_wav2vec2_with_alignment(audio_filename, model_size, max_caption_size, caption_color):
    """
    Method 2: Use Wav2Vec2 + forced alignment
    Install: pip install transformers torch torchaudio
    """
    try:
        import torch
        import torchaudio
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer, Wav2Vec2Processor
        
        print("📥 Loading Wav2Vec2 model...")
        model_name = "facebook/wav2vec2-base-960h"
        processor = Wav2Vec2Processor.from_pretrained(model_name)
        model = Wav2Vec2ForCTC.from_pretrained(model_name)
        
        # Load and preprocess audio
        print("🔧 Loading audio...")
        audio_input, sample_rate = torchaudio.load(audio_filename)
        
        # Resample if necessary
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            audio_input = resampler(audio_input)
        
        # Convert to mono if stereo
        if audio_input.shape[0] > 1:
            audio_input = torch.mean(audio_input, dim=0, keepdim=True)
        
        # Process in chunks to avoid memory issues
        chunk_length = 16000 * 30  # 30 seconds chunks
        audio_length = audio_input.shape[1]
        captions = []
        
        for start_idx in range(0, audio_length, chunk_length):
            end_idx = min(start_idx + chunk_length, audio_length)
            chunk = audio_input[:, start_idx:end_idx]
            chunk_start_time = start_idx / 16000
            
            # Process chunk
            input_values = processor(chunk.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_values
            
            with torch.no_grad():
                logits = model(input_values).logits
            
            # Decode
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = processor.batch_decode(predicted_ids)[0].lower()
            
            if transcription.strip():
                # Simple time alignment (can be improved)
                words = transcription.split()
                chunk_duration = chunk.shape[1] / 16000
                word_duration = chunk_duration / len(words) if words else 1.0
                
                current_words = []
                current_start = chunk_start_time
                
                for i, word in enumerate(words):
                    current_words.append(word)
                    
                    if len(current_words) >= max_caption_size or i == len(words) - 1:
                        word_end_time = chunk_start_time + (i + 1) * word_duration
                        caption_text = ' '.join(current_words)
                        captions.append(((current_start, word_end_time), caption_text, caption_color))
                        current_words = []
                        current_start = word_end_time
        
        return captions
        
    except ImportError:
        print("❌ Required libraries not installed. Install with: pip install transformers torch torchaudio")
        return []
    except Exception as e:
        print(f"❌ Wav2Vec2 error: {e}")
        return []

def try_vosk(audio_filename, model_size, max_caption_size, caption_color):
    """
    Method 3: Use Vosk for offline speech recognition
    Install: pip install vosk
    Download model: https://alphacephei.com/vosk/models
    """
    try:
        import vosk
        import wave
        
        # Convert audio to WAV format if needed
        wav_file = convert_to_wav(audio_filename)
        if not wav_file:
            return []
        
        # Try to find Vosk model
        model_paths = [
            "./vosk-model",
            "./vosk-model-en-us-0.22",
            "./vosk-model-small-en-us-0.15",
            "/opt/vosk-model",
        ]
        
        model_path = None
        for path in model_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            print("❌ Vosk model not found. Download from: https://alphacephei.com/vosk/models")
            print("   Extract to current directory or ./vosk-model/")
            return []
        
        print(f"📥 Loading Vosk model from {model_path}...")
        model = vosk.Model(model_path)
        
        # Process audio
        wf = wave.open(wav_file, "rb")
        rec = vosk.KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)  # Enable word-level timestamps
        
        captions = []
        current_words = []
        current_start = None
        
        print("🔍 Transcribing with Vosk...")
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
                
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if 'result' in result:
                    for word_info in result['result']:
                        word = word_info['word']
                        start_time = word_info['start']
                        end_time = word_info['end']
                        
                        if current_start is None:
                            current_start = start_time
                        
                        current_words.append(word)
                        
                        if len(current_words) >= max_caption_size:
                            caption_text = ' '.join(current_words)
                            captions.append(((current_start, end_time), caption_text, caption_color))
                            current_words = []
                            current_start = None
        
        # Final result
        final_result = json.loads(rec.FinalResult())
        if 'result' in final_result and current_words:
            # Add remaining words
            last_end = captions[-1][0][1] if captions else 0
            estimated_end = last_end + len(current_words) * 0.5
            caption_text = ' '.join(current_words)
            captions.append(((current_start or last_end, estimated_end), caption_text, caption_color))
        
        wf.close()
        
        # Clean up temporary WAV file
        if wav_file != audio_filename:
            try:
                os.remove(wav_file)
            except:
                pass
        
        return captions
        
    except ImportError:
        print("❌ Vosk not installed. Install with: pip install vosk")
        return []
    except Exception as e:
        print(f"❌ Vosk error: {e}")
        return []

def try_basic_whisper_with_vad(audio_filename, model_size, max_caption_size, caption_color):
    """
    Method 4: Basic Whisper with Voice Activity Detection for better timing
    """
    try:
        import whisper
        
        print("📥 Loading basic Whisper model...")
        model = whisper.load_model(model_size)
        
        # Add VAD (Voice Activity Detection) using librosa
        print("🔍 Performing Voice Activity Detection...")
        audio_data, sr = librosa.load(audio_filename, sr=16000)
        
        # Simple VAD using energy-based detection
        frame_length = 2048
        hop_length = 512
        
        # Compute short-time energy
        energy = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Find voice segments
        energy_threshold = np.percentile(energy, 30)  # Adjust threshold as needed
        voice_frames = energy > energy_threshold
        
        # Convert frame indices to time
        times = librosa.frames_to_time(np.arange(len(voice_frames)), sr=sr, hop_length=hop_length)
        
        # Find continuous voice segments
        voice_segments = []
        in_voice = False
        segment_start = 0
        
        for i, is_voice in enumerate(voice_frames):
            if is_voice and not in_voice:
                segment_start = times[i]
                in_voice = True
            elif not is_voice and in_voice:
                voice_segments.append((segment_start, times[i]))
                in_voice = False
        
        # Add final segment if needed
        if in_voice:
            voice_segments.append((segment_start, times[-1]))
        
        # Merge short gaps
        merged_segments = []
        for start, end in voice_segments:
            if merged_segments and start - merged_segments[-1][1] < 0.5:  # Merge if gap < 0.5s
                merged_segments[-1] = (merged_segments[-1][0], end)
            else:
                merged_segments.append((start, end))
        
        print(f"🔍 Found {len(merged_segments)} voice segments")
        
        # Transcribe full audio
        print("🔍 Transcribing with basic Whisper...")
        result = model.transcribe(audio_filename, language="en", fp16=False)
        
        if not result or 'text' not in result:
            return []
        
        # Split transcription into timed segments
        full_text = result['text'].strip()
        words = full_text.split()
        
        if not words:
            return []
        
        # Distribute words across voice segments
        captions = []
        word_idx = 0
        
        for segment_start, segment_end in merged_segments:
            segment_duration = segment_end - segment_start
            words_in_segment = max(1, int(len(words) * (segment_duration / times[-1])))
            
            segment_words = words[word_idx:word_idx + words_in_segment]
            word_idx += len(segment_words)
            
            if segment_words:
                # Split segment words into caption-sized chunks
                segment_captions = split_segment_into_captions(
                    segment_words, segment_start, segment_end, max_caption_size, caption_color
                )
                captions.extend(segment_captions)
            
            if word_idx >= len(words):
                break
        
        # Add any remaining words
        if word_idx < len(words):
            remaining_words = words[word_idx:]
            last_end = captions[-1][0][1] if captions else 0
            estimated_end = last_end + len(remaining_words) * 0.5
            
            remaining_captions = split_segment_into_captions(
                remaining_words, last_end, estimated_end, max_caption_size, caption_color
            )
            captions.extend(remaining_captions)
        
        return captions
        
    except ImportError:
        print("❌ Basic whisper not available")
        return []
    except Exception as e:
        print(f"❌ Basic whisper with VAD error: {e}")
        return []

def split_segment_into_captions(words, start_time, end_time, max_caption_size, caption_color):
    """Helper function to split a segment into caption-sized chunks"""
    captions = []
    duration = end_time - start_time
    
    # Group words into caption-sized chunks
    word_groups = []
    current_group = []
    
    for word in words:
        current_group.append(word)
        if len(current_group) >= max_caption_size:
            word_groups.append(current_group)
            current_group = []
    
    if current_group:
        word_groups.append(current_group)
    
    # Assign timestamps to groups
    for i, group in enumerate(word_groups):
        group_start = start_time + (i / len(word_groups)) * duration
        group_end = start_time + ((i + 1) / len(word_groups)) * duration
        
        caption_text = ' '.join(group)
        captions.append(((group_start, group_end), caption_text, caption_color))
    
    return captions

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
