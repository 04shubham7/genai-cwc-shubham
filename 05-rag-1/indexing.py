import getpass
import os
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

pdf_path=Path(__file__).parent / "nodejs.pdf"

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

# Vector Embeddings
embeddings_model=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# using [embeddings_model] create embeddigs of [split_docs] and store in 
# Some famous Vector DBs-> Pinecone(Cloud,Paid),Astra DB,ChromaDB(OpenSource),Milvus DB(OpenSource),PG Vector(OpenSource),Weaviate(OpenSource),Qdrant DB(OpenSource)
# QDrant DB(OpenSource) - Lightweight,Spin up time is easy,out of the box :UI,Namespaces

#search Qdrantvectorstore to get the wrapper from langchain
vectorstore=QdrantVectorStore.from_documents(
    split_docs,
    embeddings_model,
    collection_name="learning_vectors",
    host="localhost",
    port=6333,
    force_recreate=True,
) 

print("Vector store created and documents embedded successfully.")
print("You can now query the vector store for relevant information.")



