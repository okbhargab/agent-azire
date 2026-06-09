from dotenv import load_dotenv
from google import genai
import os

print("1. Starting")

load_dotenv()

key = os.getenv("GENAI_API_KEY")
print("2. Key found:", key[:15] if key else None)

client = genai.Client(api_key=key)

print("3. Client created")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello"
)

print("4. Response received")
print(response)
print("5. Text:")
print(response.text)