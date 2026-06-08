from phoenix.otel import register
from google import genai

from phoenix.otel import register
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

register(project_name="default")

GoogleGenAIInstrumentor().instrument()

client = genai.Client(
    api_key="AQ.Ab8RN6IvHrRSI4GaWcphwCmIp0MavRHee3cqVjAyR6QHVT62Hw"
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is AI?"
)

print(response.text)
