import os
import json
import re

try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
        Image.NEAREST = Image.NEAREST
        Image.BILINEAR = Image.BILINEAR
        Image.BICUBIC = Image.BICUBIC
except ImportError:
    pass
def fix_json(json_str):
    # Replace newline and carriage return characters with their escaped counterparts.
    json_str = json_str.replace("\n", "\\n")
    json_str = json_str.replace("\r", "\\r")
    return json_str
    
# Check for a valid Groq API key. Exit if not found.
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key or len(groq_api_key) <= 30:
    print("No valid Groq API key provided.")
    exit(1)

from groq import Groq
model = "llama3-70b-8192"  # Use your desired model.
client = Groq(api_key=groq_api_key)
print("Using Groq API")
    
def generate_script(topic):
    """
    Generate a compelling story script for StoryForge video creation
    """
    prompt = (
        f"""You are a master storyteller for StoryForge, a platform that creates captivating short-form videos. 
Your specialty is crafting engaging narratives that are perfect for visual storytelling. 
Each story should be concise, lasting 45-60 seconds (approximately 120-160 words), and designed to keep viewers hooked from start to finish.

When given a topic, you create stories that are:
- Emotionally engaging with clear narrative arcs
- Visually rich and cinematic
- Perfect for short-form video content
- Complete stories with beginning, middle, and end
- Relatable and memorable

For example, if the topic is "Lost friendship":
You would create:
"Sarah found the old letter tucked between pages of her childhood diary. It was from Emma, her best friend who moved away ten years ago. The faded ink read: 'Promise we'll always stay in touch.' Sarah smiled sadly, remembering how they'd sworn nothing would change. Life had other plans. She picked up her phone, hesitated, then typed: 'Hey Em, been thinking about you.' Three dots appeared immediately. 'Sarah?! I was just looking at our old photos!' Sometimes the best friendships just need a single message to reignite the spark that time couldn't extinguish."

For topic "{topic}":
Create a compelling, complete story that would work perfectly as a short video. Make it emotionally resonant, visually engaging, and memorable.

Strictly output the script in JSON format like:
{{"script": "Your complete story script here..."}}
"""
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )
    content = response.choices[0].message.content
    try:
        # Attempt to decode the JSON response.
        script = json.loads(content, strict=False)["script"]
    except Exception as e:
        print("First JSON decoding failed:", e)
        print("Raw content:", content)
        # Extract the JSON object by locating the first '{' and the last '}'.
        json_start_index = content.find('{')
        json_end_index = content.rfind('}')
        if json_start_index != -1 and json_end_index != -1:
            content_fixed = fix_json(content[json_start_index:json_end_index+1])
            try:
                script = json.loads(content_fixed, strict=False)["script"]
            except Exception as inner_e:
                print("ERROR: Failed to decode JSON after fixing:", inner_e)
                script = ""
        else:
            print("ERROR: No valid JSON object found in response.")
            script = ""
    return script
