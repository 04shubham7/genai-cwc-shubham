import os
import sys
import uvicorn

# Ensure the package folder is importable even with an invalid package name
pkg_path = os.path.join(os.path.dirname(__file__), "06-rag-queue")
sys.path.insert(0, pkg_path)

from server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
