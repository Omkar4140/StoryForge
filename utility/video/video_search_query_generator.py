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
    """
    # Remove common markdown formatting
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    # Find the first [ and last ]
    json_start_index = response_text.find("[")
    json_end_index = response_text.rfind("]")
    
    if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
        return response_text[json_start_index:json_end_index+1]
    
    return None

def fix_json(json_str):
    """
    Fixes common JSON formatting issues such as incorrect quotes or escape characters.
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
    
    # Fix missing commas between array elements
    json_str = re.sub(r'\]\s*\[', '], [', json_str)
    
    # Fix missing commas between object elements
    json_str = re.sub(r'}\s*{', '}, {', json_str)
    
    # Ensure proper brackets
    if not json_str.startswith("["):
        json_str = "[" + json_str
    if not json_str.endswith("]"):
        json_str = json_str + "]"

    return json_str

def advanced_json_parse(content):
    """
    Advanced JSON parsing with multiple fallback methods
    """
    if not content or not content.strip():
        return None
    
    # Method 1: Direct parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Method 2: Clean and parse
    try:
        cleaned = clean_json_response(content)
        if cleaned:
            return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Method 3: Fix common issues and parse
    try:
        fixed = fix_json(content)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Method 4: Extract JSON with regex
    try:
        # Look for array patterns
        json_pattern = r'\[\s*\[.*?\]\s*\]'
        matches = re.findall(json_pattern, content, re.DOTALL)
        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
    except:
        pass
    
    # Method 5: Try to construct valid JSON from content
    try:
        # Look for time segments and keywords pattern
        segment_pattern = r'\[\[(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\],\s*\[(.*?)\]\]'
        segments = re.findall(segment_pattern, content, re.DOTALL)
        
        if segments:
            result = []
            for start_time, end_time, keywords_str in segments:
                # Extract keywords
                keywords = re.findall(r'"([^"]*)"', keywords_str)
                if keywords:
                    result.append([[float(start_time), float(end_time)], keywords[:3]])  # Limit to 3 keywords
            
            if result:
                return result
    except:
        pass
    
    print(f"Failed to parse JSON: {content[:200]}...")
    return None

def getVideoSearchQueriesTimed(script, captions_timed):
    """
    Get video search queries with improved error handling and retry logic
    """
    if not captions_timed:
        print("Warning: No captions provided")
        return None
    
    end_time = captions_timed[-1][0][1]
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}")
            
            # Call the API
            raw_response = call_OpenAI(script, captions_timed)
            
            if not raw_response or not raw_response.strip():
                print("Empty response from API")
                continue
            
            # Parse the response
            parsed_result = advanced_json_parse(raw_response)
            
            if parsed_result is None:
                print(f"Failed to parse JSON on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                else:
                    print("Max retries reached, returning None")
                    return None
            
            # Validate the result
            if not isinstance(parsed_result, list):
                print("Result is not a list")
                continue
            
            # Check if we have valid time segments
            if len(parsed_result) == 0:
                print("Empty result list")
                continue
            
            # Validate time coverage
            if len(parsed_result) > 0:
                last_segment = parsed_result[-1]
                if isinstance(last_segment, list) and len(last_segment) >= 2:
                    if isinstance(last_segment[0], list) and len(last_segment[0]) >= 2:
                        if abs(last_segment[0][1] - end_time) <= 1.0:  # Allow 1 second tolerance
                            print("✅ Successfully parsed video search queries")
                            return parsed_result
            
            print(f"Time coverage validation failed. Expected end: {end_time}")
            if attempt < max_retries - 1:
                continue
            
        except Exception as e:
            print(f"Error in getVideoSearchQueriesTimed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue
    
    print("Failed to get valid video search queries after all attempts")
    return None

def call_OpenAI(script, captions_timed):
    """
    Call the API with improved formatting and error handling
    """
    user_content = f"""Script: {script}
Timed Captions: {captions_timed}"""
    
    try:
        print("Calling API...")
        
        response = client.chat.completions.create(
            model=model,
            temperature=0.7,  # Reduced temperature for more consistent output
            max_tokens=2000,  # Increased token limit
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        text = response.choices[0].message.content.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        print(f"API Response (first 200 chars): {text[:200]}...")
        
        # Log the response
        try:
            log_response(LOG_TYPE_GPT, script, text)
        except Exception as log_error:
            print(f"Warning: Failed to log response: {log_error}")
        
        return text
        
    except Exception as e:
        print(f"Error calling API: {e}")
        return None

def merge_empty_intervals(segments):
    """
    Merge empty intervals with improved error handling using safe_unpack
    """
    if segments is None:
        print("Warning: Received None for segments, returning empty list.")
        return []
    
    if not isinstance(segments, list):
        print("Warning: Segments is not a list, returning empty list.")
        return []
    
    if len(segments) == 0:
        print("Warning: Empty segments list.")
        return []
    
    merged = []
    i = 0
    while i < len(segments):
        try:
            # Safely check segment structure
            if not isinstance(segments[i], list):
                print(f"Warning: Segment at index {i} is not a list: {segments[i]}")
                i += 1
                continue
            
            # Use safe_unpack to handle variable segment lengths
            interval, url = safe_unpack(segments[i], 2, default_values=[[-1, -1], None])
            
            if url is None:
                # Find consecutive None intervals
                j = i + 1
                while j < len(segments):
                    if not isinstance(segments[j], list) or len(segments[j]) < 2:
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
                        prev_interval[1] == interval[0]):
                        
                        # Get the last interval's end time
                        last_end_time = interval[1]
                        if j - 1 < len(segments):
                            last_segment = segments[j-1]
                            if isinstance(last_segment, list) and len(last_segment) >= 1:
                                last_interval, _ = safe_unpack(last_segment, 2, default_values=[[-1, -1], None])
                                if len(last_interval) >= 2:
                                    last_end_time = last_interval[1]
                        
                        merged[-1] = [[prev_interval[0], last_end_time], prev_url]
                    else:
                        merged.append([interval, prev_url if len(merged) > 0 else None])
                else:
                    merged.append([interval, None])
                
                i = j
            else:
                merged.append([interval, url])
                i += 1
                
        except Exception as e:
            print(f"❌ Error processing segment {i}: {e}")
            print(f"Segment data: {segments[i] if i < len(segments) else 'Index out of range'}")
            i += 1
    
    return merged
