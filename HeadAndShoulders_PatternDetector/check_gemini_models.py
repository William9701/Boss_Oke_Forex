"""Check available Gemini models"""
import google.generativeai as genai
import os

API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=API_KEY)

print("Available Gemini Models:")
print("=" * 70)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported: {model.supported_generation_methods}")
        print()
