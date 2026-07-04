from fastapi import FastAPI, Query
from task_queue.connection import queue
from task_queue.worker import process_query

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Server is up and running!"}


@app.post("/chat")
def enqueue_chat(query: str = Query(..., description="Chat Message")):
    """Enqueue `process_query` with the provided query and return the job id."""
    job = queue.enqueue(process_query, query)
    return {"status": "queued", "job_id": job.id}


@app.get("/results/{job_id}")
def get_results(job_id: str):
    """Get the result of a job by its ID."""
    job = queue.fetch_job(job_id)
    if job is None:
        return {"status": "not_found", "job_id": job_id}

    # Prefer boolean attributes when available, fall back to status string
    if getattr(job, "is_finished", False):
        return {"status": "complete", "job_id": job_id, "result": job.result}
    if getattr(job, "is_failed", False):
        return {"status": "failed", "job_id": job_id, "error": job.exc_info}

    return {"status": "pending", "job_id": job_id}
