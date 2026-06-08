import os
from dotenv import load_dotenv
from phoenix.otel import register
from google import genai
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

load_dotenv()

register(project_name="default")

GoogleGenAIInstrumentor().instrument()

api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise RuntimeError("GENAI_API_KEY is not set. Add it to your .env file.")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is AI?"
)

print(response.text)
