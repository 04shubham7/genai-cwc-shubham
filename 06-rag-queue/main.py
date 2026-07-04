import uvicorn

try:
    # When run as a module inside a package
    from .server import app
except Exception:
    # When executed as a script (python main.py)
    from server import app


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()