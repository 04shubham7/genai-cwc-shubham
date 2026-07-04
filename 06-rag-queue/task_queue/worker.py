"""
Worker helpers for the RQ task queue.

This module exposes `process_query(query)` which is imported by the FastAPI
server and executed by RQ workers. The module avoids performing heavy
initialization at import-time (so importing it from the web server is safe).

Key behaviors:
- Load `GOOGLE_API_KEY` from environment or prompt interactively.
- Support `--dry-run` to validate retrieval without calling LLMs.
- Lazily create the Qdrant vector store client when processing a query.
"""

from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import sys
import getpass
from dotenv import load_dotenv

# Load environment variables from a .env file when present.
load_dotenv()

# Ensure a Google API key is available. If not present and the process is
# interactive, prompt the user (useful when running the worker manually).
if not os.getenv("GOOGLE_API_KEY"):
    try:
        os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")
    except Exception:
        # In non-interactive environments (e.g. deployment) we require the key
        # to be set ahead of time to avoid blocking the process.
        raise RuntimeError("GOOGLE_API_KEY not set in environment")

# Allow running in a "dry run" mode for testing retrieval without LLM calls.
DRY_RUN = "--dry-run" in sys.argv

# Embedding model instance (cheap to construct). We reuse it for vector ops.
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def _get_vector_db() -> QdrantVectorStore:
    """Create and return a `QdrantVectorStore` connected to the collection.

    This is intentionally created on-demand so importing this module does not
    attempt to connect to Qdrant when the web server imports `process_query`.
    """
    return QdrantVectorStore.from_existing_collection(
        url="http://localhost:6333",
        collection_name="learning_vectors",
        embedding=embeddings_model,
    )


def process_query(query: str) -> str | None:
    """Process a user query and return the assistant's answer.

    Steps:
    1. Connect to the Qdrant vector store (lazy).
    2. Perform a similarity search to retrieve top-k context chunks.
    3. Format the retrieved context into a prompt for the chat model.
    4. If `DRY_RUN` is enabled, print a preview and return without calling the LLM.
    5. Invoke the chat model and return the generated content.

    Returns the assistant answer string on success, or `None` on error.
    """
    # Log the incoming query for debugging when running the worker manually.
    print(f"Searching Chunks: {query}")

    # 1) Connect to the vector DB. Catch connection errors and return None
    # so the worker can record the failure instead of crashing the importer.
    try:
        vector_db = _get_vector_db()
    except Exception as exc:
        print(f"Failed to connect to vector DB: {exc}")
        return None

    # 2) Retrieve similar documents (top-k).
    search_results = vector_db.similarity_search(query, k=3)

    # 3) Build a human-readable context string from the search results. Each
    # result contains `page_content` and `metadata` fields used for attribution.
    context = "\n\n\n".join(
        [
            f"Page Content: {result.page_content}\n"
            f"Page Number: {result.metadata.get('page_label', 'N/A')}\n"
            f"File Location: {result.metadata.get('source', 'N/A')}"
            for result in search_results
        ]
    )
    print("Context retrieved from vector store:")

    # 4) If dry-run is requested, show a preview and skip LLM usage.
    if DRY_RUN:
        print("Dry run mode enabled. Retrieved context preview:")
        print(context[:1500] if context else "No context found.")
        return None

    # 5) Prepare the system prompt that instructs the LLM to only use the
    # retrieved context when answering. We keep the prompt compact and
    # deterministic to minimize hallucination risk.
    SYSTEM_PROMPT = (
        "You are a helpful assistant for answering questions related to available content. "
        "Use the following retrieved information to answer the user's question. "
        "You should only answer based on the retrieved information and not make up any answer. "
        "Always use the retrieved information to answer the question and guide the user to the right page number to know more."
        f"\n\nContext:\n{context}"
    )

    # Create the chat model instance. We create it here (inside the function)
    # so importing this module remains side-effect free.
    chat_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    try:
        # Invoke the chat model with a system message and the user's query.
        response = chat_model.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)]
        )
        print(f"Assistant: {response.content}")
        return response.content
    except Exception as exc:
        # If the LLM call fails (quota, auth, network), print details and
        # return None so the worker can mark the job as failed.
        print("LLM call failed. If this is a quota issue, run with '--dry-run' to validate retrieval without API usage.")
        print(f"Details: {exc}")
        return None

# Entry point for RQ workers: `process_query` is importable and side-effect free.