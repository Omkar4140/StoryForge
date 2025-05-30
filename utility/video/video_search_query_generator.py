import os
import json
import re
from datetime import datetime
from utility.utils import log_response, LOG_TYPE_GPT

# Initialize client
if os.environ.get("GROQ_API_KEY") and len(os.environ.get("GROQ_API_KEY")) > 30:
    from groq import Groq
    model = "meta-llama/llama-4-scout-17b-16e-instruct"
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    print("Using Groq API")
else:
    print("Use another API - GROQ_API_KEY not found or invalid")
    exit(1)

log_directory = ".logs/gpt_logs"

prompt = """# Instructions for Topic-Aware Visual Search

You are generating video search queries for a story/content with a specific TOPIC/THEME. Given the story script, topic context, and timed captions, create three highly relevant and visually specific search terms for each time segment.

CRITICAL REQUIREMENTS:
1. ALL search terms must be directly related to the MAIN TOPIC/THEME
2. Keywords should be visually concrete and searchable on stock video platforms
3. Prioritize topic-relevant imagery over generic visuals
4. Each keyword should be 1-3 words maximum
5. Focus on what would actually appear in the video frame

Topic Categories & Approach:
- TECHNOLOGY/AI: Focus on modern tech, digital interfaces, coding, robotics, futuristic elements
- BUSINESS/FINANCE: Corporate environments, meetings, charts, money, professional settings
- HEALTH/WELLNESS: Medical equipment, exercise, healthy food, nature, peaceful environments
- EDUCATION: Learning environments, books, students, teaching, academic settings
- TRAVEL/LIFESTYLE: Destinations, transportation, cultural elements, adventures
- FOOD/COOKING: Ingredients, cooking processes, restaurants, food presentation
- NATURE/ENVIRONMENT: Natural landscapes, wildlife, weather, outdoor scenes
- SPORTS/FITNESS: Athletic activities, equipment, training, competitions
- FAMILY/RELATIONSHIPS: People interactions, home environments, emotional moments
- ART/CREATIVITY: Artistic processes, creative tools, galleries, performances

Search Strategy:
1. Identify the main topic from the script
2. For each caption segment, find topic-relevant visual elements
3. Create search terms that combine the topic with the specific content
4. Prioritize searchable stock video terms

Examples by Topic:
TECHNOLOGY Script: "AI is changing the world"
→ ["artificial intelligence", "digital transformation", "tech innovation"]

COOKING Script: "The recipe was perfect"
→ ["cooking preparation", "kitchen ingredients", "food plating"]

BUSINESS Script: "The meeting was successful"
→ ["corporate meeting", "business handshake", "office presentation"]

CRITICAL: Return ONLY the JSON array. No explanations, no markdown formatting, no extra text.

Format: [[[t1, t2], ["topic-keyword1", "topic-keyword2", "topic-keyword3"]], [[t2, t3], ["topic-keyword4", "topic-keyword5", "topic-keyword6"]], ...]
"""

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

def clean_json_response(response_text):
    """
    Removes extra text from API responses and extracts only the valid JSON portion.
    Enhanced to handle the specific format from your API.
    """
    if not response_text:
        return None
        
    # Remove common markdown formatting
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    # Remove any explanatory text before or after the JSON
    # Look for the pattern that starts with [[ and ends with ]]
    lines = response_text.split('\n')
    json_lines = []
    in_json = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('[[') or in_json:
            in_json = True
            json_lines.append(line)
            if line.endswith(']]') and not line.endswith(',]]'):
                break
    
    if json_lines:
        json_text = '\n'.join(json_lines)
        # Ensure proper array wrapping
        if not json_text.startswith('['):
            json_text = '[' + json_text
        if not json_text.endswith(']'):
            json_text = json_text + ']'
        return json_text
    
    # Fallback: find the first [ and last ]
    json_start_index = response_text.find("[")
    json_end_index = response_text.rfind("]")
    
    if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
        return response_text[json_start_index:json_end_index+1]
    
    return response_text

def fix_json(json_str):
    """
    Fixes common JSON formatting issues - Enhanced for your specific format.
    """
    if not json_str:
        return json_str
        
    # Replace smart quotes with regular quotes
    json_str = json_str.replace("'", "'").replace("'", "'")
    json_str = json_str.replace(""", "\"").replace(""", "\"")
    
    # Fix common quote issues
    json_str = json_str.replace('"you didn"t"', '"you didn\'t"')
    json_str = json_str.replace('""', '"')
    
    # Remove markdown formatting
    json_str = json_str.replace("```json", "").replace("```", "").strip()
    
    # Fix the specific pattern from your logs
    # Convert the comma-separated array format to proper JSON array
    if not json_str.startswith('[') or not json_str.endswith(']'):
        # Split by lines and reconstruct
        segments = []
        lines = json_str.strip().split('\n')
        
        for line in lines:
            line = line.strip().rstrip(',')
            if line.startswith('[[') and line.endswith(']]'):
                segments.append(line)
        
        if segments:
            json_str = '[' + ',\n'.join(segments) + ']'
    
    # Ensure proper commas between segments
    json_str = re.sub(r'\]\],\s*\[\[', ']],\n[[', json_str)
    
    return json_str

def advanced_json_parse(content):
    """
    Advanced JSON parsing specifically designed for your API response format
    """
    if not content or not content.strip():
        print("❌ Empty content provided to JSON parser")
        return None
    
    print(f"🔍 Attempting to parse JSON content (length: {len(content)})")
    print(f"📝 Content preview: {content[:200]}...")
    
    # Method 1: Parse as-is (the content might already be valid JSON)
    try:
        # The API response appears to be already in the correct format, just add brackets
        if not content.strip().startswith('['):
            content_wrapped = '[' + content.strip() + ']'
        else:
            content_wrapped = content.strip()
        
        result = json.loads(content_wrapped)
        print("✅ Method 1: Direct parsing with wrapping successful")
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Method 1 failed: {e}")
    
    # Method 2: Clean and parse
    try:
        cleaned = clean_json_response(content)
        if cleaned:
            result = json.loads(cleaned)
            print("✅ Method 2: Cleaned JSON parsing successful")
            return result
    except json.JSONDecodeError as e:
        print(f"❌ Method 2 failed: {e}")
    
    # Method 3: Fix and parse
    try:
        fixed = fix_json(content)
        result = json.loads(fixed)
        print("✅ Method 3: Fixed JSON parsing successful")
        return result
    except json.JSONDecodeError as e:
        print(f"❌ Method 3 failed: {e}")
    
    # Method 4: Parse line by line and reconstruct
    try:
        print("🔧 Attempting line-by-line reconstruction...")
        
        lines = content.strip().split('\n')
        segments = []
        
        for line in lines:
            line = line.strip().rstrip(',')
            if line and line.startswith('[[') and line.endswith(']]'):
                try:
                    # Parse individual segment
                    parsed_line = json.loads(line)
                    segments.append(parsed_line)
                except json.JSONDecodeError:
                    # Manual parsing for this specific format
                    # Extract time range and keywords using regex
                    match = re.match(r'\[\[(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\], \[(.*)\]\]', line)
                    if match:
                        start_time = float(match.group(1))
                        end_time = float(match.group(2))
                        keywords_str = match.group(3)
                        
                        # Extract keywords
                        keywords = []
                        for keyword in re.findall(r'"([^"]*)"', keywords_str):
                            keywords.append(keyword)
                        
                        if keywords:
                            segments.append([[start_time, end_time], keywords])
        
        if segments:
            print(f"✅ Method 4: Line-by-line reconstruction successful with {len(segments)} segments")
            return segments
    except Exception as e:
        print(f"❌ Method 4 failed: {e}")
    
    # Method 5: Regex-based extraction for your specific format
    try:
        print("🔧 Attempting regex-based extraction...")
        
        # Pattern specifically for your format: [[0.0-3.9], ["keyword1", "keyword2", "keyword3"]]
        pattern = r'\[\[(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\],\s*\[([^\]]+)\]\]'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        if matches:
            segments = []
            for start_str, end_str, keywords_str in matches:
                start_time = float(start_str)
                end_time = float(end_str)
                
                # Extract keywords
                keywords = re.findall(r'"([^"]*)"', keywords_str)
                
                if keywords:
                    segments.append([[start_time, end_time], keywords])
            
            if segments:
                print(f"✅ Method 5: Regex extraction successful with {len(segments)} segments")
                return segments
    except Exception as e:
        print(f"❌ Method 5 failed: {e}")
    
    print(f"❌ All JSON parsing methods failed. Content: {content}")
    return None

def getVideoSearchQueriesTimed(script, captions_timed):
    """
    Get video search queries with improved error handling and retry logic
    """
    if not captions_timed:
        print("❌ Warning: No captions provided")
        return None
    
    print(f"🎯 Processing {len(captions_timed)} caption segments")
    
    # Get the end time for validation
    try:
        last_caption = captions_timed[-1]
        if isinstance(last_caption, (list, tuple)) and len(last_caption) >= 1:
            time_info = last_caption[0]
            if isinstance(time_info, (list, tuple)) and len(time_info) >= 2:
                end_time = float(time_info[1])
            else:
                end_time = 60.0  # Default fallback
        else:
            end_time = 60.0  # Default fallback
    except Exception as e:
        print(f"⚠️ Could not determine end time: {e}")
        end_time = 60.0
    
    print(f"📊 Expected end time: {end_time}")
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"🚀 Attempt {attempt + 1}/{max_retries}")
            
            # Call the API
            raw_response = call_OpenAI(script, captions_timed)
            
            if not raw_response or not raw_response.strip():
                print("❌ Empty response from API")
                continue
            
            print(f"📨 Received response length: {len(raw_response)}")
            
            # Parse the response
            parsed_result = advanced_json_parse(raw_response)
            
            if parsed_result is None:
                print(f"❌ Failed to parse JSON on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    print("🔄 Retrying...")
                    continue
                else:
                    print("❌ Max retries reached, returning None")
                    return None
            
            # Validate the result
            if not isinstance(parsed_result, list):
                print(f"❌ Result is not a list: {type(parsed_result)}")
                continue
            
            # Check if we have valid time segments
            if len(parsed_result) == 0:
                print("❌ Empty result list")
                continue
            
            print(f"✅ Parsed {len(parsed_result)} segments successfully")
            
            # Validate structure
            valid_segments = 0
            for i, segment in enumerate(parsed_result):
                if isinstance(segment, list) and len(segment) >= 2:
                    time_info, keywords = segment[0], segment[1]
                    if (isinstance(time_info, list) and len(time_info) >= 2 and
                        isinstance(keywords, list) and len(keywords) > 0):
                        valid_segments += 1
                    else:
                        print(f"⚠️ Invalid segment structure at index {i}: {segment}")
                else:
                    print(f"⚠️ Invalid segment at index {i}: {segment}")
            
            print(f"✅ Found {valid_segments}/{len(parsed_result)} valid segments")
            
            if valid_segments > 0:
                print("✅ Returning valid result")
                return parsed_result
            
            if attempt < max_retries - 1:
                print("🔄 Retrying due to validation issues...")
                continue
            
        except Exception as e:
            print(f"❌ Error in getVideoSearchQueriesTimed (attempt {attempt + 1}): {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                continue
    
    print("❌ Failed to get valid video search queries after all attempts")
    return None

def call_OpenAI(script, captions_timed):
    """
    Call the API with improved formatting and error handling
    """
    # Create more concise input to avoid token limits
    captions_summary = []
    for caption in captions_timed[:10]:  # Limit to first 10 for context
        try:
            time_info, text = safe_unpack(caption, 2, [[-1, -1], ""])
            if isinstance(time_info, (list, tuple)) and len(time_info) >= 2:
                captions_summary.append(f"[{time_info[0]:.1f}-{time_info[1]:.1f}]: {text[:50]}")
        except:
            continue
    
    user_content = f"""Script: {script[:1000]}...

Timed Captions (sample): {'; '.join(captions_summary)}

Total caption segments: {len(captions_timed)}

Please generate video search queries for ALL {len(captions_timed)} segments."""
    
    try:
        print("📞 Calling API...")
        
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,  # Lower temperature for more consistent JSON output
            max_tokens=4000,  # Increased token limit
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        text = response.choices[0].message.content.strip()
        
        print(f"📨 API Response length: {len(text)}")
        print(f"📝 Response preview: {text[:300]}...")
        
        # Log the response
        try:
            log_response(LOG_TYPE_GPT, script[:200], text)
        except Exception as log_error:
            print(f"⚠️ Failed to log response: {log_error}")
        
        return text
        
    except Exception as e:
        print(f"❌ Error calling API: {e}")
        import traceback
        traceback.print_exc()
        return None

def merge_empty_intervals(segments):
    """
    Merge empty intervals with improved error handling using safe_unpack
    """
    if segments is None:
        print("⚠️ Warning: Received None for segments, returning empty list.")
        return []
    
    if not isinstance(segments, list):
        print("⚠️ Warning: Segments is not a list, returning empty list.")
        return []
    
    if len(segments) == 0:
        print("⚠️ Warning: Empty segments list.")
        return []
    
    print(f"🔗 Merging intervals for {len(segments)} segments")
    
    merged = []
    i = 0
    while i < len(segments):
        try:
            # Safely check segment structure
            if not isinstance(segments[i], (list, tuple)):
                print(f"⚠️ Warning: Segment at index {i} is not a list/tuple: {segments[i]}")
                i += 1
                continue
            
            # Use safe_unpack to handle variable segment lengths
            interval, url = safe_unpack(segments[i], 2, default_values=[[-1, -1], None])
            
            if url is None:
                # Find consecutive None intervals
                j = i + 1
                while j < len(segments):
                    if not isinstance(segments[j], (list, tuple)):
                        break
                    
                    next_interval, next_url = safe_unpack(segments[j], 2, default_values=[[-1, -1], None])
                    if next_url is not None:
                        break
                    j += 1
                
                # Merge consecutive None intervals with the previous valid URL
                if i > 0 and len(merged) > 0:
                    prev_interval, prev_url = merged[-1]
                    if (prev_url is not None and 
                        len(prev_interval) >= 2 and 
                        len(interval) >= 2 and 
                        abs(prev_interval[1] - interval[0]) <= 0.1):  # Allow small time gaps
                        
                        # Get the last interval's end time
                        last_end_time = interval[1]
                        if j - 1 < len(segments):
                            last_segment = segments[j-1]
                            if isinstance(last_segment, (list, tuple)):
                                last_interval, _ = safe_unpack(last_segment, 2, default_values=[[-1, -1], None])
                                if len(last_interval) >= 2:
                                    last_end_time = last_interval[1]
                        
                        merged[-1] = [[prev_interval[0], last_end_time], prev_url]
                        print(f"🔗 Extended previous segment to cover empty intervals")
                    else:
                        merged.append([interval, prev_url if len(merged) > 0 else None])
                        print(f"➕ Added segment with fallback URL")
                else:
                    merged.append([interval, None])
                    print(f"➕ Added segment with no URL (first segment)")
                
                i = j
            else:
                merged.append([interval, url])
                print(f"➕ Added segment with URL")
                i += 1
                
        except Exception as e:
            print(f"❌ Error processing segment {i}: {e}")
            print(f"Segment data: {segments[i] if i < len(segments) else 'Index out of range'}")
            i += 1
    
    print(f"✅ Merged into {len(merged)} final segments")
    return merged
