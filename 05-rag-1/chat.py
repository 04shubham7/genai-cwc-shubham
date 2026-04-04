from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import sys
import getpass
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")

DRY_RUN = "--dry-run" in sys.argv
# Vector Embeddings
embeddings_model=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


vector_db=QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="learning_vectors",
    embedding=embeddings_model,
)

#Take User Input/Query

query=input(">> Enter your query: ")

#Vector Similarity Search in Vector DB
search_results=vector_db.similarity_search(query, k=3)

context = "\n\n\n".join(
    [
        f"Page Content: {result.page_content}\n"
        f"Page Number: {result.metadata.get('page_label', 'N/A')}\n"
        f"File Location: {result.metadata.get('source', 'N/A')}"
        for result in search_results
    ]
)
print("Context retrieved from vector store:")   

if DRY_RUN:
    print("Dry run mode enabled. Retrieved context preview:")
    print(context[:1500] if context else "No context found.")
    raise SystemExit(0)
 

SYSTEM_PROMPT = f"""You are a helpful assistant for answering questions related to available content. Use the following retrieved information to answer
the user's question. If the user's question is not related to available content, politely respond that you are
unable to help with that. If you are unsure and the user seeks clarification, politely respond that
you do not have the information available to answer the question.

You should only answer based on the retrieved information and not make up any answer. Always use all the retrieved information to answer the question and guide the user to the right page number to know more.
context: {context}
"""

chat_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

try:
    response = chat_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]
    )
    print(f"Assistant: {response.content}")
except Exception as exc:
    print("LLM call failed. If this is a quota issue, run with '--dry-run' to validate retrieval without API usage.")
    print(f"Details: {exc}")