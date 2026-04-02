from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import getpass
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")
# Vector Embeddings
embeddings_model=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


vector_db=QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="learning_vectors",
    embeddings_model=embeddings_model,
    force_recreate=True,
)

#Take User Input/Query

query=input(">> Enter your query: ")

#Vector Similarity Search in Vector DB
search_results=vector_db.similarity_search(query, k=3)

 

SYSTEM_PROMPT="""You are a helpful assistant for answering questions related to available content. Use the following retrieved information to answer
the user's question. If the user's question is not related to availabe content, politely respond that you are
unable to help with that. If you are unsure and the user seeks clarification, politely respond that
you do not have the information available to answer the question. 

you should onlyy answer based on the retrieved information and not make up any answer. Always use all the retrieved information to answer the question and navigate the user to open the right page number to know more.
"""