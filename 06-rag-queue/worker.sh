# export GOOGLE_API_KEY=REDACTED
# python 06-rag-queue/worker.py

export $(grep -v '^#' .env | xargs -d '\n')
rq worker --with-scheduler --url redis://localhost:6379
