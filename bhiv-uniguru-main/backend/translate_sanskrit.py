import os
import sys
import argparse
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Try importing Groq
try:
    from groq import Groq
except ImportError:
    print("Error: The 'groq' library is not installed. Please install it using 'pip install groq'")
    exit(1)

def translate(text: str, direction: str) -> str:
    """
    Translates text between English and Sanskrit using Groq API.
    direction: 'en-to-sa' or 'sa-to-en'
    """
    # Load env variables to get the Groq API key
    base_dir = os.path.dirname(os.path.abspath(__file__))
    _env_path = os.path.join(base_dir, ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)

    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("UNIGURU_LLM_API_KEY")
    if not groq_key:
        return "Error: GROQ_API_KEY or UNIGURU_LLM_API_KEY environment variable not found."

    client = Groq(api_key=groq_key)

    if direction == "en-to-sa":
        system_prompt = (
            "You are an expert translator specializing in translating English text to Sanskrit. "
            "Please translate the user's English text into accurate Sanskrit (Devanagari script). "
            "Provide only the translated Sanskrit text without any extra conversational filler."
        )
    elif direction == "sa-to-en":
        system_prompt = (
            "You are an expert translator specializing in translating Sanskrit text to English. "
            "Please translate the user's Sanskrit text into accurate English. "
            "Provide only the translated English text without any extra conversational filler."
        )
    else:
        return "Invalid translation direction specified."

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error during translation: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate between English and Sanskrit using Groq LLM.")
    parser.add_argument("text", type=str, help="The text to translate")
    parser.add_argument(
        "--direction", 
        type=str, 
        choices=["en-to-sa", "sa-to-en"], 
        default="en-to-sa",
        help="Translation direction: 'en-to-sa' (English to Sanskrit) or 'sa-to-en' (Sanskrit to English)"
    )

    args = parser.parse_args()
    
    print(f"Translating ({args.direction}):\n'{args.text}'\n")
    result = translate(args.text, args.direction)
    print("Translation Result:")
    print("-" * 40)
    print(result)
    print("-" * 40)
