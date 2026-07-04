# test_embed.py
import traceback
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    v = emb.embed_documents(["hello world"])
    print("OK, got embedding:", v[:1])
except Exception:
    traceback.print_exc()