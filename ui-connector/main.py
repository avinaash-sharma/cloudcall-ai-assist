import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore
from datetime import datetime
import asyncio

# Initialize FastAPI app
app = FastAPI(title="CCAI UI Connector")

# Initialize Firestore client
# New
db = firestore.Client(database="ccai-conversations")

# Get environment variables
COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION", "ccai-conversations")

# Add CORS middleware
# This allows the browser (Agent Desktop) to connect to this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Cloud Run pings this to verify service is running.
    """
    return {"status": "healthy", "service": "ui-connector"}


@app.get("/stream")
async def stream_conversations(request: Request):
    """
    SSE endpoint:
    1. Browser connects here
    2. We listen to Firestore for changes
    3. Push updates to browser in real time
    """

    async def event_generator():
        """
        Generator function that yields events to browser.
        Runs continuously until browser disconnects.
        """
        try:
            # Send initial connection confirmation to browser
            yield {
                "event": "connected",
                "data": json.dumps({
                    "status": "connected",
                    "service": "ui-connector",
                    "timestamp": datetime.utcnow().isoformat()
                })
            }

            # Keep track of documents we've already sent
            # so we don't send duplicates
            sent_docs = set()

            # Continuously poll Firestore for new documents
            while True:
                # Check if browser is still connected
                if await request.is_disconnected():
                    break

                # Query latest 10 conversations from Firestore
                docs = db.collection(COLLECTION_NAME)\
                         .order_by("timestamp",
                                   direction=firestore.Query.DESCENDING)\
                         .limit(10)\
                         .stream()

                # Check each document
                for doc in docs:
                    # Only send documents we haven't sent yet
                    if doc.id not in sent_docs:
                        sent_docs.add(doc.id)
                        data = doc.to_dict()

                        # Convert timestamp to string for JSON
                        if "timestamp" in data:
                            data["timestamp"] = data["timestamp"].isoformat()

                        # Push to browser as SSE event
                        yield {
                            "event": "conversation",
                            "data": json.dumps({
                                "id": doc.id,
                                "transcription": data.get("transcription", ""),
                                "sentiment": data.get("sentiment", "pending"),
                                "summary": data.get("summary", "pending"),
                                "status": data.get("status", ""),
                                "timestamp": data.get("timestamp", "")
                            })
                        }

                # Wait 2 seconds before checking again
                await asyncio.sleep(2)

        except Exception as e:
            # Send error to browser
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())