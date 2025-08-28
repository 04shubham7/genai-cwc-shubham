
from google import genai
import os
import sys
from dotenv import load_dotenv


# Expect an API key in env var GOOGLE_API_KEY
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
        print("ERROR: Set GOOGLE_API_KEY environment variable or pass api_key to genai.Client(...)", file=sys.stderr)
        sys.exit(1)

client = genai.Client(api_key=api_key)

result = client.models.embed_content(
        model="text-embedding-004",
        contents="Dog Chases Cat",
)

# result.embeddings is a list of ContentEmbedding; the vector is in .values (a list of floats)
print("Embedding:", result.embeddings)
vec = result.embeddings[0].values
print(f"Length of embedding: {len(vec)}")  # text-embedding-004 returns 768 dimensions
print("First 8 values:", vec[:8])