import os
import json
import re

def validate_groq_api():
    """Validate Groq API key"""
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key or len(groq_api_key) <= 30:
        return False, "No valid Groq API key provided. Please set GROQ_API_KEY environment variable."
    return True, groq_api_key

def fix_json_response(json_str):
    """Clean and fix JSON response from API"""
    if not json_str:
        return json_str
    
    # Remove common formatting issues
    json_str = json_str.replace("\n", "\\n").replace("\r", "\\r")
    json_str = json_str.strip()
    
    # Find JSON object boundaries
    json_start = json_str.find('{')
    json_end = json_str.rfind('}')
    
    if json_start != -1 and json_end != -1:
        return json_str[json_start:json_end+1]
    
    return json_str

def generate_script(topic):
    """Generate a compelling story script for StoryForge video creation"""
    
    # Validate API key
    is_valid, result = validate_groq_api()
    if not is_valid:
        print(f"❌ {result}")
        return None
    
    groq_api_key = result
    
    try:
        from groq import Groq
        model = "llama3-70b-8192"
        client = Groq(api_key=groq_api_key)
        print("✅ Using Groq API for script generation")
    except ImportError:
        print("❌ Groq library not installed. Please install with: pip install groq")
        return None
    except Exception as e:
        print(f"❌ Error initializing Groq client: {e}")
        return None
    
    # Craft the story generation prompt
    prompt = f"""You are an expert storyteller for StoryForge, specializing in creating captivating short-form video narratives.

Create a compelling story script that is:
- 45-60 seconds when narrated (approximately 120-160 words)
- Emotionally engaging with a clear narrative arc
- Visually rich and perfect for video storytelling
- Complete with beginning, middle, and satisfying conclusion
- Relatable and memorable

The story should flow naturally when spoken aloud and be suitable for background video footage.

Topic: '{topic}'

Requirements:
- Write in a narrative voice suitable for storytelling
- Include vivid, visual descriptions
- Create emotional moments that resonate
- End with a meaningful conclusion or insight
- Use language that flows well when spoken

Output your response in this exact JSON format:
{{"script": "Your complete story script here..."}}

Only return the JSON object, nothing else."""

    try:
        print(f"🔮 Generating story for topic: '{topic}'...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Create a story about: {topic}"}
            ],
            temperature=0.8,  # Higher creativity for storytelling
            max_tokens=500   # Sufficient for story length
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        try:
            script_data = json.loads(content)
            script = script_data.get("script", "")
            
            if not script:
                raise ValueError("Empty script in response")
                
            print("✅ Story script generated successfully")
            return script
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed, attempting to fix: {e}")
            
            # Try to fix and re-parse the JSON
            fixed_content = fix_json_response(content)
            try:
                script_data = json.loads(fixed_content)
                script = script_data.get("script", "")
                
                if script:
                    print("✅ Story script generated successfully (after JSON fix)")
                    return script
                else:
                    raise ValueError("Empty script after JSON fix")
                    
            except Exception as inner_e:
                print(f"❌ Failed to parse JSON even after fixing: {inner_e}")
                print(f"Raw response: {content[:200]}...")
                
                # Last resort: extract script from raw text
                script_match = re.search(r'"script":\s*"([^"]+)"', content)
                if script_match:
                    script = script_match.group(1)
                    print("✅ Extracted story script from raw response")
                    return script
                
                return None
                
    except Exception as e:
        print(f"❌ Error generating script: {e}")
        return None
