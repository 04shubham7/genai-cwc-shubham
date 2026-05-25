#pip freeze > requirements.txt
#pip install -r requirements.txt

from fastapi import FastAPI, Query
from task_queue.connection import queue
from task_queue.worker import process_query
import asyncio
import time
app = FastAPI()


@app.get("/")
def chat():
    return {"message": "Server is up and running!"}

@app.post('/chat')
def chat(
      query: str = Query(..., description="Chat Message")
):  

    #query ko queue me daal do, 
    job=queue.enqueue(process_query, query)
    #and user ko bolo you job/task is recieved, we will process it and get back to you with the answer.
    return {"status": "queued","job_id":job.id}
