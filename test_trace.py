from dotenv import load_dotenv
from phoenix.otel import register

load_dotenv()

tracer_provider = register(
    project_name="default"
)

tracer = tracer_provider.get_tracer(__name__)

@tracer.chain
def hello():
    return "Hello"

print(hello())