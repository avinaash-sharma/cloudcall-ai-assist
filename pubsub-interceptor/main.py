import os
import json
import base64
from fastapi import FastAPI, Request, HTTPException
from google.cloud import firestore
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(title="CCAI PubSub Interceptor")

# Initialize Firestore client
# New
db = firestore.Client(database="ccai-conversations")

# Get environment variables
PROJECT_ID = os.environ.get("PROJECT_ID")
COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION", "ccai-conversations")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Cloud Run pings this to verify service is running.
    """
    return {"status": "healthy", "service": "pubsub-interceptor"}


@app.post("/pubsub")
async def receive_pubsub_message(request: Request):
    """
    Main endpoint:
    1. Receives Pub/Sub push message
    2. Decodes it
    3. Writes to Firestore
    """
    try:
        # Step 1 — Parse the incoming Pub/Sub message
        body = await request.json()

        # Step 2 — Extract and decode the message data
        # Pub/Sub encodes message data in base64
        pubsub_message = body.get("message", {})
        message_data = pubsub_message.get("data", "")

        # Step 3 — Decode base64 to get actual message
        decoded_data = base64.b64decode(message_data).decode("utf-8")
        message = json.loads(decoded_data)

        # Step 4 — Extract transcription from message
        transcription = message.get("transcription", "")
        filename = message.get("filename", "unknown")

        # Step 5 — Build Firestore document
        conversation_data = {
            "transcription": transcription,
            "filename": filename,
            "status": "transcribed",
            "timestamp": datetime.utcnow(),
            "sentiment": "pending",
            "summary": "pending",
        }

        # Step 6 — Write to Firestore
        # Each conversation gets its own document
        doc_ref = db.collection(COLLECTION_NAME).document()
        doc_ref.set(conversation_data)

        # Step 7 — Return 200 OK to acknowledge message
        # IMPORTANT: If we don't return 200, Pub/Sub will
        # keep retrying the same message
        return {"status": "success", "document_id": doc_ref.id}

    except Exception as e:
        # Return 500 so Pub/Sub knows to retry
        raise HTTPException(status_code=500, detail=str(e))