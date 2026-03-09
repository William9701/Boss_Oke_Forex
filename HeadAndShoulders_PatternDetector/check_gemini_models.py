"""Check available Gemini models"""
import google.generativeai as genai

API_KEY = "AIzaSyB347Qy8qcOx5q5SAPGe1547xS1jLMhC4g"
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
