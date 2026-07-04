import os
from redis import Redis
from rq import Queue

# Read Redis connection from env var `REDIS_URL`, fall back to localhost
REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("REDIS_HOST")
if REDIS_URL:
	# allow either full URL (redis://...) or host:port
	if REDIS_URL.startswith("redis://"):
		redis_conn = Redis.from_url(REDIS_URL)
	else:
		# if provided only host or host:port
		parts = REDIS_URL.split(":")
		host = parts[0]
		port = int(parts[1]) if len(parts) > 1 else 6379
		redis_conn = Redis(host=host, port=port)
else:
	redis_conn = Redis(host="localhost", port=6379)

queue = Queue(connection=redis_conn)


