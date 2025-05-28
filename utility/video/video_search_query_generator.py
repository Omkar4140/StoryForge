import os
import json
import re
from datetime import datetime
from utility.utils import log_response, LOG_TYPE_GPT

# Initialize client
if os.environ.get("GROQ_API_KEY") and len(os.environ.get("GROQ_API_KEY")) > 30:
    from groq import Groq
    model = "llama3-70b-8192"
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    print("Using Groq API")
else:
    print("Use another API - GROQ_API_KEY not found or invalid")
    exit(1)

log_directory = ".logs/gpt_logs"

"""# Instructions for StoryForge Visual Search
Given the following story script and timed captions, extract three visually concrete and specific keywords for each time segment that can be used to search for background videos. The keywords should capture the visual essence of the story moments and emotions being portrayed.

Important Guidelines for StoryForge:
- Focus on visual storytelling elements (characters, settings, actions, emotions)
- Keywords should evoke the mood and atmosphere of the story
- Use cinematic and narrative-focused search terms
- Each keyword should be 1-3 words and highly visual
- Consider emotional visual cues (facial expressions, body language, lighting)
- Include setting and environment details
- Think about what viewers would see on screen

For story segments, prioritize:
- Character actions and expressions
- Environmental storytelling
- Emotional moments with visual impact
- Symbolic or metaphorical visuals
- Atmospheric elements (lighting, weather, mood)

Example transformations:
'She felt sad remembering her friend' → ['woman crying', 'nostalgic moment', 'old photograph']
'The old house stood empty' → ['abandoned house', 'empty rooms', 'dusty interior']
'He ran through the forest' → ['man running', 'dense forest', 'sunlight trees']

Time segments should be 2-4 seconds each, covering the entire story duration consecutively.

Use only English in your text queries.
Each search string must depict something visually concrete and cinematic.
Focus on what the audience would actually see in the video.

CRITICAL: Return ONLY the JSON array. No explanations, no markdown formatting, no extra text. Just the raw JSON array starting with [ and ending with ].

Format: [[[t1, t2], ["keyword1", "keyword2", "keyword3"]], [[t2, t3], ["keyword4", "keyword5", "keyword6"]], ...]
"""

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
    Merge empty intervals with improved error handling
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
            if not isinstance(segments[i], list) or len(segments[i]) < 2:
                print(f"Warning: Invalid segment format at index {i}: {segments[i]}")
                i += 1
                continue
                
            interval, url = segments[i]
            
            if url is None:
                # Find consecutive None intervals
                j = i + 1
                while j < len(segments) and len(segments[j]) >= 2 and segments[j][1] is None:
                    j += 1
                
                # Merge consecutive None intervals with the previous valid URL
                if i > 0 and len(merged) > 0:
                    prev_interval, prev_url = merged[-1]
                    if prev_url is not None and len(prev_interval) >= 2 and len(interval) >= 2 and prev_interval[1] == interval[0]:
                        merged[-1] = [[prev_interval[0], segments[j-1][0][1]], prev_url]
                    else:
                        merged.append([interval, prev_url if len(merged) > 0 else None])
                else:
                    merged.append([interval, None])
                
                i = j
            else:
                merged.append([interval, url])
                i += 1
                
        except Exception as e:
            print(f"Error processing segment {i}: {e}")
            i += 1
    
    return merged

# Test function for debugging
def test_json_parsing():
    """Test the JSON parsing functions"""
    test_cases = [
        '[[[0, 5], ["test keyword", "another keyword", "third keyword"]]]',
        '```json\n[[[0, 5], ["test", "keyword", "example"]]]\n```',
        '[[[0 5] ["broken" "json" "format"]]]',  # Missing comma
        'Some text before [[[0, 5], ["keyword"]]] some text after',
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest case {i + 1}: {test_case}")
        result = advanced_json_parse(test_case)
        print(f"Result: {result}")

if __name__ == "__main__":
    test_json_parsing()
