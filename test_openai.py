import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAI_APIKEY"),
)
response = client.responses.create(
    model="gpt-5-nano",
    # instructions="You are a coding assistant that talks like a pirate.",
    input="Hi?",
)

print(response.output_text)