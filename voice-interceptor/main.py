import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from google.cloud import speech
from google.cloud import pubsub_v1
from google.cloud import dialogflow_v2beta1 as dialogflow
from google.api_core.client_options import ClientOptions

# Initialize FastAPI app
app = FastAPI(title="CCAI Voice Interceptor")

# Regional endpoint for asia-south1
client_options = ClientOptions(
    api_endpoint="asia-south1-dialogflow.googleapis.com"
)

# Initialize Google clients
speech_client = speech.SpeechClient()
publisher = pubsub_v1.PublisherClient()
conversations_client = dialogflow.ConversationsClient(
    client_options=client_options
)
participants_client = dialogflow.ParticipantsClient(
    client_options=client_options
)

# Get environment variables
PROJECT_ID = os.environ.get("PROJECT_ID")
TOPIC_NAME = os.environ.get("PUBSUB_TOPIC_NAME")
CONVERSATION_PROFILE_ID = os.environ.get("CONVERSATION_PROFILE_ID")

# Build full Pub/Sub topic path
TOPIC_PATH = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Cloud Run pings this to verify service is running.
    """
    return {"status": "healthy", "service": "voice-interceptor"}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Main endpoint:
    1. Receives audio file
    2. Creates Agent Assist conversation
    3. Transcribes audio
    4. Sends transcription to Agent Assist
    5. Publishes result to Pub/Sub
    """
    try:
        # Step 1 — Read the uploaded audio file
        audio_content = await file.read()

        # Step 2 — Transcribe audio using Speech-to-Text
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        response = speech_client.recognize(config=config, audio=audio)

        # Step 3 — Extract transcription
        transcription = ""
        for result in response.results:
            transcription += result.alternatives[0].transcript

        # Step 4 — Create Agent Assist Conversation
        conversation = conversations_client.create_conversation(
            parent=f"projects/{PROJECT_ID}/locations/asia-south1",
            conversation={
                "conversation_profile": CONVERSATION_PROFILE_ID,
            }
        )
        conversation_id = conversation.name

        # Step 5 — Create END_USER participant
        end_user_participant = participants_client.create_participant(
            parent=conversation_id,
            participant={"role": "END_USER"}
        )

        # Step 6 — Create HUMAN_AGENT participant
        agent_participant = participants_client.create_participant(
            parent=conversation_id,
            participant={"role": "HUMAN_AGENT"}
        )

        # Step 7 — Send transcription to Agent Assist
        analyze_response = participants_client.analyze_content(
            participant=end_user_participant.name,
            text_input={"text": transcription, "language_code": "en-US"}
        )

        # Step 8 — Extract Agent Assist suggestions
        suggestions = []
        for suggestion in analyze_response.human_agent_suggestion_results:
            suggestions.append(str(suggestion))

        # Step 9 — Build message payload
        message = {
            "transcription": transcription,
            "filename": file.filename,
            "conversation_id": conversation_id,
            "suggestions": suggestions,
            "status": "transcribed"
        }

        # Step 10 — Publish to Pub/Sub
        message_bytes = json.dumps(message).encode("utf-8")
        future = publisher.publish(TOPIC_PATH, message_bytes)
        message_id = future.result()

        # Step 11 — Complete conversation
        conversations_client.complete_conversation(name=conversation_id)

        return {
            "status": "success",
            "transcription": transcription,
            "conversation_id": conversation_id,
            "suggestions": suggestions,
            "message_id": message_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))