import getpass
import os
import sys
import time
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

RUN_INDEXING = "--run" in sys.argv
FORCE_RECREATE = "--force-recreate" in sys.argv

pdf_path=Path(__file__).parent / "nodejs.pdf"

if not pdf_path.exists():
    raise FileNotFoundError(f"PDF file not found: {pdf_path}")

# Load PDF file as a single document to keep the embedding request count manageable.
loader=PyPDFLoader(str(pdf_path), mode="single")
documents=loader.load()   #read the PDF file and load its content into documents
# print(f"Loaded {len(documents)} documents from the PDF.")
# print("Docs[0]",documents[5])

# Chunking
text_splitter=RecursiveCharacterTextSplitter(chunk_size=3000,chunk_overlap=200)
# texts=text_splitter.split_documents(documents)

split_docs=text_splitter.split_documents(documents)
# print(f"Split into {len(split_docs)} chunks.")

print(f"Prepared {len(split_docs)} chunks from {pdf_path.name}.")

if not RUN_INDEXING:
    print("Dry run complete. No embeddings were generated and no data was written to Qdrant.")
    print("To perform indexing, run: python indexing.py --run")
    print("To recreate the collection, run: python indexing.py --run --force-recreate")
    raise SystemExit(0)

# Vector Embeddings
embeddings_model=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# Process in batches of 10 to stay safely under the Gemini RPM limit.
batch_size = 10
sleep_seconds = 60

# using [embeddings_model] create embeddigs of [split_docs] and store in 
# Some famous Vector DBs-> Pinecone(Cloud,Paid),Astra DB,ChromaDB(OpenSource),Milvus DB(OpenSource),PG Vector(OpenSource),Weaviate(OpenSource),Qdrant DB(OpenSource)
# QDrant DB(OpenSource) - Lightweight,Spin up time is easy,out of the box :UI,Namespaces

vectorstore = None

try:
    for start_index in range(0, len(split_docs), batch_size):
        batch = split_docs[start_index : start_index + batch_size]
        end_index = start_index + len(batch)
        print(f"Processing batch {start_index} to {end_index}...")

        if vectorstore is None:
            vectorstore = QdrantVectorStore.from_documents(
                batch,
                embeddings_model,
                collection_name="learning_vectors",
                host="localhost",
                port=6333,
                force_recreate=FORCE_RECREATE,
            )
        else:
            vectorstore.add_documents(batch)

        if end_index < len(split_docs):
            print(f"Sleeping for {sleep_seconds} seconds to respect rate limits...")
            time.sleep(sleep_seconds)
except Exception as exc:
    print("Indexing failed during embedding/upload.")
    print("If you see RESOURCE_EXHAUSTED, switch to another API key/project or wait for quota reset.")
    print(f"Details: {exc}")
    raise SystemExit(1)

print("Vector store created and documents embedded successfully.")
print("You can now query the vector store for relevant information.")



