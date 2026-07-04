"""
Windows-friendly RQ worker using SimpleWorker (no os.fork).

Usage:
    (.venv) PS> python run_worker.py

Note: RQ's scheduler uses forking on Unix; for scheduling on Windows consider using a separate scheduler
process or run workers inside WSL/Linux.
"""
import os
from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker


def get_redis_connection():
    url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_HOST")
    if url:
        if url.startswith("redis://"):
            return Redis.from_url(url)
        parts = url.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 6379
        return Redis(host=host, port=port)
    return Redis(host="localhost", port=6379)


def main():
    conn = get_redis_connection()
    q = Queue(connection=conn)
    worker = SimpleWorker([q], connection=conn)
    # blocking worker; exits only on keyboard interrupt
    worker.work()


if __name__ == "__main__":
    main()
