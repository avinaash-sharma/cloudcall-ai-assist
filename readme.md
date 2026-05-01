(took help from chatgpt to get the readme up for me)

# 🎧 cloudcall-ai-assist
### Real-time AI-powered Contact Center Assistant using Google Cloud CCAI

A production-grade proof-of-concept that demonstrates a full **Contact Center AI (CCAI)** pipeline on Google Cloud Platform. Audio from a voice call flows through Speech-to-Text, Agent Assist, Pub/Sub, Firestore, and streams live to an Agent Desktop browser UI.

---

## 📐 Architecture

```
Incoming Audio
      ↓
Voice Interceptor (Cloud Run)
      ↓
Speech-to-Text API
      ↓
Agent Assist / Dialogflow CX
      ↓
Pub/Sub Topic
      ↓
PubSub Interceptor (Cloud Run)
      ↓
Firestore (Real-time Database)
      ↓
UI Connector (Cloud Run) — SSE Stream
      ↓
Agent Desktop (Browser UI)
```

---

## 🗂️ Project Structure

```
cloudcall-ai-assist/
    ├── voice-interceptor/
    │   ├── main.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── pubsub-interceptor/
    │   ├── main.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── ui-connector/
    │   ├── main.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── agent-desktop/
    │   └── index.html
    ├── sample_audio.wav
    └── README.md
```

---

## ✅ Prerequisites

Make sure you have the following installed on your machine:

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://python.org) |
| pip | Latest | Comes with Python |
| Docker | Latest | [docker.com](https://docker.com) |
| Google Cloud SDK | Latest | [cloud.google.com/sdk](https://cloud.google.com/sdk) |

Verify installations:
```bash
python --version
pip --version
docker --version
gcloud --version
```

---

## 🚀 Setup Guide

### Step 1 — GCP Project Setup

#### 1.1 Create a New Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown → **New Project**
3. Name: `ccai-poc`
4. Note down the **Project ID** (e.g. `ccai-poc-494916`)

#### 1.2 Link Billing
1. Go to **Billing** in the sidebar
2. Link a billing account to the project
3. Activate free trial if available ($300 credit for 90 days)

#### 1.3 Set Budget Alert
1. Go to **Billing → Budgets & Alerts**
2. Create budget: `₹500` or `$10`
3. Set thresholds at 50%, 90%, 100%
4. Add email notifications

---

### Step 2 — Enable Required APIs

Go to **APIs & Services → Library** and enable each of these:

| API | Purpose |
|---|---|
| Cloud Run API | Deploy containerized services |
| Cloud Speech-to-Text API | Transcribe audio |
| Dialogflow API | Agent Assist / CCAI |
| Cloud Pub/Sub API | Message bus between services |
| Cloud Firestore API | Real-time database |
| Cloud Build API | Build container images |
| Artifact Registry API | Store Docker images |
| Secret Manager API | Store secrets securely |
| IAM Service Account Credentials API | Service-to-service auth |

Or enable via terminal (replace `YOUR_PROJECT_ID`):
```bash
gcloud services enable \
  run.googleapis.com \
  speech.googleapis.com \
  dialogflow.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  --project YOUR_PROJECT_ID
```

---

### Step 3 — Configure gcloud CLI

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify
gcloud config get-value project
```

---

### Step 4 — Create Service Accounts

> 📝 We create one service account per service following the **Principle of Least Privilege** — each service only gets the permissions it absolutely needs.

#### 4.1 Voice Interceptor Service Account
```bash
# Create service account
gcloud iam service-accounts create ccai-voice-interceptor-sa \
  --description="Service account for Voice Interceptor Cloud Run service" \
  --display-name="ccai-voice-interceptor-sa"

# Grant Speech-to-Text permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-voice-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/speech.serviceAgent"

# Grant Pub/Sub Publisher permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-voice-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

# Grant Dialogflow permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-voice-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/dialogflow.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-voice-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/dialogflow.reader"
```

#### 4.2 PubSub Interceptor Service Account
```bash
# Create service account
gcloud iam service-accounts create ccai-pubsub-interceptor-sa \
  --description="Service account for PubSub Interceptor Cloud Run service" \
  --display-name="ccai-pubsub-interceptor-sa"

# Grant Pub/Sub Subscriber permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-pubsub-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

# Grant Firestore permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-pubsub-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

#### 4.3 UI Connector Service Account
```bash
# Create service account
gcloud iam service-accounts create ccai-ui-connector-sa \
  --description="Service account for UI Connector Cloud Run service" \
  --display-name="ccai-ui-connector-sa"

# Grant Firestore permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-ui-connector-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Grant Cloud Run Invoker permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ccai-ui-connector-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

---

### Step 5 — Grant Cloud Build Permissions

```bash
# Replace 'YOUR_PROJECT_NUMBER' with your GCP project number
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

> 📝 Find your project number at: **GCP Console → Project Settings → Project Number**

---

### Step 6 — Create Firestore Database

```bash
gcloud firestore databases create \
  --database="ccai-conversations" \
  --location="asia-south1" \
  --type="firestore-native"
```

Or via Console:
1. Go to **Firestore**
2. Click **Create Database**
3. Select **Native Mode**
4. Select **Standard Edition**
5. Region: `asia-south1 (Mumbai)`
6. Database ID: `ccai-conversations`

---

### Step 7 — Create Pub/Sub Topic and Subscription

```bash
# Create topic
gcloud pubsub topics create ccai-agent-assist-topic

# Create push subscription (replace YOUR_PUBSUB_INTERCEPTOR_URL)
gcloud pubsub subscriptions create ccai-agent-assist-subscription \
  --topic ccai-agent-assist-topic \
  --push-endpoint YOUR_PUBSUB_INTERCEPTOR_URL/pubsub \
  --push-auth-service-account ccai-pubsub-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

> ⚠️ You'll get the `YOUR_PUBSUB_INTERCEPTOR_URL` after deploying in Step 9. Come back and run the subscription command after deployment.

---

### Step 8 — Set Up Agent Assist / Dialogflow CX

#### 8.1 Create Dialogflow CX Agent
1. Go to [dialogflow.cloud.google.com/cx](https://dialogflow.cloud.google.com/cx)
2. Click **Create Agent** → **Build your own**
3. Fill in:
   - Display Name: `ccai-agent`
   - Location: `asia-south1`
   - Timezone: `Asia/Colombo (GMT+5:30)`
   - Language: `English`
4. Click **Create**
5. Note down the **Agent ID** from the URL

#### 8.2 Create Conversation Profile
1. Go to [agentassist.cloud.google.com](https://agentassist.cloud.google.com)
2. Set Location to `asia-south1`
3. Go to **Conversation Profiles → Create**
4. Fill in:
   - Display Name: `ccai-conversation-profile`
   - Language: `en - English`
5. Enable Suggestion Types:
   - ✅ Conversation summarization (legacy)
   - ✅ Conversation summarization (legacy voice)
   - ✅ Generative knowledge assist
   - ✅ Proactive generative knowledge assist
6. Enable Pub/Sub Notifications (all 4) with topic:
   ```
   projects/YOUR_PROJECT_ID/topics/ccai-agent-assist-topic
   ```
   Set format to **JSON** for all
7. Enable **Sentiment Analysis**
8. Enable **Virtual Agent** → select `ccai-agent`
9. Voice Configuration:
   - Model: `Telephony`
   - Language: `en - English`
   - Audio Encoding: `LINEAR16`
   - Sample Rate: `16000`
10. Click **Create**
11. Note down the **Integration ID** (Conversation Profile ID)

---

### Step 9 — Deploy Cloud Run Services

#### 9.1 Deploy Voice Interceptor
```bash
cd voice-interceptor

gcloud run deploy ccai-voice-interceptor-svc \
  --source . \
  --region asia-south1 \
  --service-account ccai-voice-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=YOUR_PROJECT_ID,PUBSUB_TOPIC_NAME=ccai-agent-assist-topic,CONVERSATION_PROFILE_ID=YOUR_CONVERSATION_PROFILE_ID \
  --no-allow-unauthenticated \
  --port 8080
```

#### 9.2 Deploy PubSub Interceptor
```bash
cd ../pubsub-interceptor

gcloud run deploy ccai-pubsub-interceptor-svc \
  --source . \
  --region asia-south1 \
  --service-account ccai-pubsub-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=YOUR_PROJECT_ID,FIRESTORE_COLLECTION=ccai-conversations \
  --no-allow-unauthenticated \
  --port 8080
```

> 📝 After this deployment, go back to Step 7 and create the Pub/Sub subscription using the service URL.

#### 9.3 Deploy UI Connector
```bash
cd ../ui-connector

gcloud run deploy ccai-ui-connector-svc \
  --source . \
  --region asia-south1 \
  --service-account ccai-ui-connector-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=YOUR_PROJECT_ID,FIRESTORE_COLLECTION=ccai-conversations \
  --allow-unauthenticated \
  --timeout 3600 \
  --port 8080
```

---

### Step 10 — Grant Pub/Sub Push Authentication

```bash
# Allow Pub/Sub to generate auth tokens
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:service-YOUR_PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

# Allow PubSub Interceptor SA to invoke Cloud Run
gcloud run services add-iam-policy-binding ccai-pubsub-interceptor-svc \
  --region asia-south1 \
  --member="serviceAccount:ccai-pubsub-interceptor-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

---

### Step 11 — Update Agent Desktop UI

Open `agent-desktop/index.html` and replace the UI Connector URL with your deployed service URL:

```javascript
const UI_CONNECTOR_URL = 'YOUR_UI_CONNECTOR_URL/stream';
```

---

## 🧪 Testing

### Health Checks
```bash
# Voice Interceptor
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  YOUR_VOICE_INTERCEPTOR_URL/health

# PubSub Interceptor
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  YOUR_PUBSUB_INTERCEPTOR_URL/health

# UI Connector
curl YOUR_UI_CONNECTOR_URL/health
```

### Prepare Test Audio
Convert any audio file to the correct format:
```bash
# Using ffmpeg
ffmpeg -i input.mp3 \
  -ar 16000 \
  -ac 1 \
  -acodec pcm_s16le \
  sample_audio.wav
```

Requirements:
- Format: WAV
- Encoding: LINEAR16 (pcm_s16le)
- Sample Rate: 16000 Hz
- Channels: Mono (1)
- Duration: Under 60 seconds

### End-to-End Test
```bash
# 1. Open Agent Desktop in browser
open agent-desktop/index.html

# 2. Send audio through pipeline
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@sample_audio.wav" \
  YOUR_VOICE_INTERCEPTOR_URL/transcribe
```

Expected response:
```json
{
  "status": "success",
  "transcription": "...",
  "conversation_id": "projects/...",
  "suggestions": [],
  "message_id": "..."
}
```

---

## 🔐 Full IAM Permissions Reference

| Service Account | Roles | Purpose |
|---|---|---|
| `ccai-voice-interceptor-sa` | `speech.serviceAgent` | Call Speech-to-Text API |
| `ccai-voice-interceptor-sa` | `pubsub.publisher` | Publish to Pub/Sub topic |
| `ccai-voice-interceptor-sa` | `dialogflow.client` | Create Agent Assist conversations |
| `ccai-voice-interceptor-sa` | `dialogflow.reader` | Read conversation profiles |
| `ccai-pubsub-interceptor-sa` | `pubsub.subscriber` | Receive Pub/Sub messages |
| `ccai-pubsub-interceptor-sa` | `datastore.user` | Write to Firestore |
| `ccai-pubsub-interceptor-sa` | `run.invoker` | Allow Pub/Sub to invoke service |
| `ccai-ui-connector-sa` | `datastore.user` | Read from Firestore |
| `ccai-ui-connector-sa` | `run.invoker` | Call other Cloud Run services |
| `Pub/Sub SA` | `iam.serviceAccountTokenCreator` | Generate auth tokens for push |
| `Compute SA` | `storage.objectAdmin` | Cloud Build storage access |
| `Compute SA` | `cloudbuild.builds.builder` | Execute Cloud Build |

---

## 🌍 Environment Variables Reference

| Service | Variable | Description |
|---|---|---|
| Voice Interceptor | `PROJECT_ID` | GCP Project ID |
| Voice Interceptor | `PUBSUB_TOPIC_NAME` | Pub/Sub topic name |
| Voice Interceptor | `CONVERSATION_PROFILE_ID` | Full Agent Assist profile resource name |
| PubSub Interceptor | `PROJECT_ID` | GCP Project ID |
| PubSub Interceptor | `FIRESTORE_COLLECTION` | Firestore collection name |
| UI Connector | `PROJECT_ID` | GCP Project ID |
| UI Connector | `FIRESTORE_COLLECTION` | Firestore collection name |

---

## 💰 Cost Estimate

| Service | Free Tier | Cost After |
|---|---|---|
| Cloud Run | 2M requests/month | $0.40/million |
| Pub/Sub | 10 GB/month | $0.04/GB |
| Firestore | 50K reads, 20K writes/day | $0.06/100K reads |
| Speech-to-Text | 60 mins/month | $0.016/min |
| Agent Assist Chat | N/A | $0.06/session (~₹5.65) |
| Firestore (Mumbai) | Free tier | Minimal |

> ⚠️ Agent Assist voice pricing requires contacting Google Cloud sales.

---

## 🔜 Roadmap

- [ ] Add Knowledge Base documents for Knowledge Assist
- [ ] Fix sentiment and summary flow from Agent Assist
- [ ] Implement Redis + WebSocket version for true real-time
- [ ] Add authentication to Agent Desktop
- [ ] Support long audio files (>60 seconds) via LongRunningRecognize
- [ ] Add multi-language support
- [ ] Deploy Agent Desktop to Cloud Run

---

## 📝 Notes

- **Region:** All services deployed in `asia-south1 (Mumbai)` for data residency and low latency
- **Smart Reply** is not available in `asia-south1` — available in `us-central1` and `europe-west1`
- **Firestore** replaces Redis for POC — swap to Memorystore for production
- **Audio format:** Must be LINEAR16, 16kHz, mono WAV under 60 seconds
- Cloud Run services use **Application Default Credentials** — no key files needed

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 |
| Web Framework | FastAPI |
| Server | Uvicorn |
| Containerization | Docker |
| Deployment | Google Cloud Run |
| Speech | Google Cloud Speech-to-Text |
| AI | Google Agent Assist / Dialogflow CX |
| Messaging | Google Cloud Pub/Sub |
| Database | Google Cloud Firestore |
| Streaming | Server Sent Events (SSE) |
| Frontend | HTML + Vanilla JavaScript |

---

## 👤 Author

Built by Avinash Sharma — [myselfavinash.com](https://myselfavinash.com)
GitHub: [@avinaash-sharma](https://github.com/avinaash-sharma)