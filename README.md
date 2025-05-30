# StoryForge 🎬
 
StoryForge is a Python-based pipeline that transforms a simple topic into a fully-rendered, narrated short video — complete with background visuals, synchronized captions, and voiceover narration. It is built to run seamlessly on Google Colab using Python 3.11 and leverages the power of modern AI services and media tools.

# Features 🚀
 
✍️ Script Generation using Groq API

🎤 Narration using edge-tts voices

⏱ Timed Captions generated with OpenAI's Whisper

🎞 Stock Video Integration via Pexels API

🧠 Search Query Generator powered by LLMs

🪄 Video Rendering using MoviePy and ImageMagick

🔄 Auto-orchestration of the full pipeline via app.py

# Workflow Overview 🧠
 
Input Topic → e.g., "AI in Education"

Script Generation → Uses Groq LLM to create a 35-50 sec story

Audio Narration → Uses edge-tts to generate .wav file

Captioning → Whisper model adds word-aligned subtitle timing

Search Queries → LLM suggests visual search terms per segment

Background Videos → Pulled from Pexels using API and matched to timing

Video Rendering → Merges audio, video, and captions into a final .mp4
