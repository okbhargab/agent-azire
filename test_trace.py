import os
import time
from dotenv import load_dotenv
from phoenix.otel import register

load_dotenv()

# Get the target project name (defaults to phoenixguard)
PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT_NAME", "phoenixguard")

print(f"Registering trace provider for project: {PHOENIX_PROJECT}")
tracer_provider = register(
    project_name=PHOENIX_PROJECT
)

tracer = tracer_provider.get_tracer(__name__)

# Standard traced function
@tracer.chain
def simulated_agent_call(query: str):
    print(f"Processing query: {query}")
    time.sleep(0.5)
    return f"Response for: {query}"

# Running this generates a trace on Phoenix Cloud
if __name__ == "__main__":
    print("Sending simulated trace to Phoenix...")
    res = simulated_agent_call("Hello PhoenixGuard!")
    print(f"Result: {res}")
    print("Trace sent successfully (0 Gemini tokens consumed).")