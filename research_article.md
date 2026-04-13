# CeriBot: An AI-Powered Humanoid Robot System for Intelligent Hotel Reception and Guest Management

**Authors**: M1 Computer Science — Avignon Université
**Date**: April 2026
**Keywords**: humanoid robot, hotel automation, face recognition, RAG, large language model, speech recognition, QR code, Pepper robot, conversational AI, service robotics

---

## Abstract

This paper presents **CeriBot**, an intelligent hotel reception and guest management system built around the **Pepper humanoid robot** (SoftBank Robotics). The system integrates state-of-the-art artificial intelligence technologies — including large language models (LLM), retrieval-augmented generation (RAG), automatic speech recognition (ASR), and computer vision — into a modular multi-service architecture. CeriBot handles four core hotel workflows: personalized facial recognition and greeting, intelligent conversational assistance, voice-driven reservation management, and QR-code-based check-in verification. The system targets measurable improvements in guest experience while validating the acceptability and operational viability of deploying advanced robotics in a real hotel environment. Evaluation targets include ≥85% face recognition accuracy, ≥90% speech transcription word accuracy, and ≤5-second chatbot response times, with user satisfaction goals of ≥4.0/5.0.

---

## 1. Introduction

The hospitality industry faces growing pressure to balance personalized guest experiences with operational efficiency. Humanoid social robots have emerged as a promising interface between AI capabilities and human-centered service environments. Unlike kiosk-based automation, robots such as Pepper can engage guests through natural language, gestures, and a tablet interface, offering a more intuitive and memorable interaction.

Previous deployments of Pepper in hospitality contexts have demonstrated the potential of social robots for greeting and information provision [1], but rarely have they integrated the full spectrum of AI capabilities required for end-to-end service workflows: from biometric recognition and contextual dialogue to voice-driven reservation creation and contactless check-in.

This project addresses that gap by designing, implementing, and evaluating a complete AI stack deployed on and around a Pepper robot, named **CeriBot**, operating in a hotel reception scenario. The system is structured as two cooperating REST APIs — a primary Flask application (port 5000) and a dedicated FastAPI reservation microservice (port 8000) — backed by SQLite databases and an optional Redis memory store.

The contributions of this paper are:

1. A modular multi-service architecture integrating LLM, RAG, ASR, face recognition, and QR code verification for hotel automation.
2. A voice-driven reservation workflow using Whisper ASR and Llama 3.1 for intent extraction and structured data validation.
3. A conversational memory system with session-scoped context and Redis persistence.
4. A Streamlit-based administrative dashboard for robot and database management.
5. An empirical evaluation framework targeting both technical performance and user experience metrics.

---

## 2. Related Work

### 2.1 Social Robots in Hospitality

The deployment of robots in hotels has been explored since the early 2010s. Henn-na Hotel in Japan pioneered robot-staffed reception using ACTROID androids [2]. Pepper has been trialed in retail, banking, and healthcare for customer-facing roles [3]. However, most deployments are limited to scripted interactions and do not leverage modern generative AI.

### 2.2 Retrieval-Augmented Generation (RAG)

RAG [4] combines dense retrieval with generative language models to ground responses in domain-specific documents. LlamaIndex [5] provides a high-level framework for indexing and querying document corpora, enabling the chatbot to access hotel-specific information (floor plans, regulations, services) without fine-tuning the base model.

### 2.3 Automatic Speech Recognition

Whisper [6] (OpenAI) is a transformer-based ASR model trained on 680,000 hours of multilingual speech. The `faster-whisper` implementation [7] provides GPU-accelerated inference with float16 quantization, making real-time transcription feasible on consumer hardware. The system also handles format conversion (WebM, Opus → WAV) for browser-originating audio.

### 2.4 Face Recognition

YOLOv8 [8] delivers real-time object and face detection via a single-shot convolutional architecture. Combined with the `face_recognition` library (dlib-based 128-dimensional face encodings), the system achieves robust recognition against a stored database of guest and staff encodings.

### 2.5 Large Language Models for Service Tasks

Llama 3.1-8B-Instruct [9] is an open-weight instruction-tuned model capable of natural dialogue, structured information extraction, and multilingual response generation. Accessed via the HuggingFace router API, it serves as the backbone of both the chatbot and the reservation intent extraction pipeline.

---

## 3. System Architecture

### 3.1 Overview

CeriBot follows a **distributed microservice architecture** (Figure 1):

```
Guest ←→ Pepper Robot (tablet UI / voice / camera)
              ↓
     Flask API — robot_hotel (port 5000)
       ├── Chat Service (LLM + RAG + Memory)
       ├── ASR Service (Whisper)
       ├── Face Detection Service (YOLOv8 + face_recognition)
       ├── Reservation Orchestration Service
       ├── QR Code Service (OpenCV)
       └── Email Service (SMTP)
              ↓
     FastAPI — ams_project_llm (port 8000)
       ├── Client Database (SQLite via SQLAlchemy)
       └── Reservation Database (SQLite)
              ↓
     Streamlit Admin Dashboard
```

The two APIs communicate over HTTP, with the Flask layer acting as the orchestrator and the FastAPI layer providing persistent storage and business logic for client and reservation management.

### 3.2 Primary API — robot_hotel (Flask)

The Flask application exposes route groups organized by functional domain:

| Route Group | Endpoints | Responsibility |
|---|---|---|
| `/chat` | POST /chat, POST /chat/voice | LLM chatbot with RAG |
| `/face` | POST /face/detect, POST /face/register | Face recognition |
| `/record` | POST /transcribe, POST /record/start | ASR pipeline |
| `/make_reservation` | POST, GET /validate | Reservation creation |
| `/scan_qr` | POST /scan_qr | QR code verification |
| `/email` | GET/PUT /email/config | Email configuration |
| `/tablet` | GET /tablet | Pepper tablet UI |

API documentation is auto-generated via Flasgger (Swagger/OpenAPI).

### 3.3 Reservation Microservice — ams_project_llm (FastAPI)

The FastAPI service manages two SQLAlchemy ORM models:

**Client**:
```
id_client (String, PK), nom, prenom,
langue_pref (default: "fr"),
preferences (JSON), nb_visites (Integer),
derniere_visite (DateTime)
```

**Reservation**:
```
id_res (String, PK, format: "R-C-001-YYYY-MM-DD"),
id_client (FK), type_chambre ("Simple"|"Double"|"Suite"),
date_arrivee (Date), date_depart (Date),
statut ("prévue"|"arrivée"|"conflit")
```

A temporary SQLite database (`temp_reservations.db`) stores unconfirmed reservations with automatic 1-hour expiration.

---

## 4. Core AI Components

### 4.1 Conversational AI with RAG

The chat service combines Llama 3.1-8B-Instruct with a LlamaIndex RAG pipeline. At startup, the hotel documentation corpus (room types, floor plans, regulations, services) is indexed using `sentence-transformers/all-MiniLM-L6-v2` embeddings and persisted to disk for fast subsequent startups.

For each guest query:
1. The RAG retriever fetches the top-2 most relevant document chunks (capped at 2,500 characters to respect the LLM token budget).
2. A system prompt enriched with the retrieved context, current date/time, and hotel identity is constructed.
3. The last 8 message pairs from session memory are prepended as conversation history.
4. Llama 3.1 generates the response via the HuggingFace inference API.

**Session Memory**: Each session maintains up to 10 question-answer pairs. Redis is used as the primary store (key format: `chat:{session_id}`), with automatic fallback to an in-memory Python dictionary if Redis is unavailable. Sessions expire after 1 hour of inactivity.

**Reservation Intent Detection**: The chat service monitors for reservation-related keywords. When triggered, it enters a structured multi-step collection flow, extracting guest name, dates, and room type before invoking the reservation workflow.

### 4.2 Automatic Speech Recognition

The ASR pipeline uses `faster-whisper` with the `medium` multilingual model:

- **GPU path**: float16 quantization for maximum throughput.
- **CPU path**: int8 quantization for compatibility.
- **Format normalization**: WebM and Opus streams (from browser/Pepper microphone) are converted to WAV via subprocess before inference.
- **Fallback**: If the `medium` model fails to load, the system downgrades to `base`.

Transcription is exposed at `POST /transcribe` accepting WAV, MP3, OGG, M4A, and FLAC. The Pepper-specific endpoint (`POST /record/pepper_mode`) handles the robot's native audio stream format.

### 4.3 Computer Vision — Face Recognition

The face recognition pipeline operates in two stages:

1. **Detection** (YOLOv8n): A lightweight YOLO model identifies face bounding boxes in the captured image frame. The model runs on GPU when available.
2. **Recognition** (`face_recognition`): Each detected face is encoded into a 128-dimensional vector and compared against stored encodings in `friends.pkl` using Euclidean distance with a configurable tolerance threshold.

Thread safety is enforced via Python locks to support concurrent API requests. A real-time streaming mode exposes detected faces via WebSocket for the admin dashboard.

### 4.4 QR Code Management

QR codes encode reservation IDs generated by the FastAPI service. The `qrcode[pil]` library generates PNG QR images that are:
- Attached to confirmation emails sent via SMTP.
- Displayed on Pepper's tablet screen.

At check-in, `POST /scan_qr` decodes the QR image using OpenCV's `QRCodeDetector`, retrieves the reservation from FastAPI, updates the arrival status, and increments the client visit counter.

---

## 5. Workflows

### 5.1 Workflow 1: Facial Recognition and Personalized Greeting

```
Guest arrives → Camera captures frame
→ /face/detect (YOLOv8 + face_recognition)
→ Match in friends.pkl?
   YES → Personalized greeting via Pepper TTS
   NO  → Generic welcome message
```

Target: <3 seconds end-to-end, ≥85% recognition accuracy.

### 5.2 Workflow 2: Intelligent Conversational Assistance

```
Guest speaks/types → ASR transcription (if voice)
→ /chat endpoint
→ RAG retrieval (LlamaIndex)
→ Memory context retrieval (Redis)
→ Llama 3.1 inference (HuggingFace API)
→ Response delivered via Pepper TTS or tablet display
→ Memory updated
```

Target: <5 seconds response time, ≥85% response relevance.

### 5.3 Workflow 3: Voice-Driven Reservation Creation

This is the most complex workflow, involving six coordinated services:

```
Guest speaks reservation request
→ Pepper microphone / browser recording
→ /transcribe (faster-whisper)
→ Transcription text
→ Llama 3.1 information extraction:
     {name, first_name, arrival_date, departure_date, room_type}
→ Validation:
     - Room type ∈ {"Simple", "Double", "Suite"}
     - Dates valid and not in past
     - Relative dates converted to absolute (e.g., "next Friday")
→ Store in temp_reservations.db (TTL: 1 hour)
→ Send validation email with confirmation link (HTML + SMTP)
→ Guest clicks link → /validate
→ POST /confirm_reservation
→ FastAPI: create_client + create_reservation
→ QR code generated (PNG)
→ Confirmation email with QR attachment sent
```

Target: ≥90% transcription accuracy, ≥85% extraction success rate, end-to-end <2 minutes.

### 5.4 Workflow 4: QR Code Check-in Verification

```
Guest presents QR code (printed / on phone)
→ Camera captures image → /scan_qr (OpenCV QRCodeDetector)
→ Reservation ID extracted
→ FastAPI /verify_qr → Reservation lookup
→ Details displayed on Pepper tablet
→ /confirm_arrival: statut = "arrivée", nb_visites += 1
```

Target: <1 second verification, contactless and reliable.

---

## 6. Administrative Interface

The Streamlit-based admin dashboard provides operators with five functional panels:

1. **Face Management**: Upload face images to register guests/staff; delete entries from `friends.pkl`; view registered persons.
2. **Video Streaming**: Real-time face detection preview with detection overlay; start/stop control.
3. **Chat & Audio**: Test chatbot with session management; upload audio files for transcription; test voice call pipeline.
4. **Reservations**: Browse client and reservation records; view statuses and preferences; monitor temp reservation expiration.
5. **Email Configuration**: Set SMTP server, port, credentials; send test emails; view current configuration.

An API health check widget shows the live status of both the Flask and FastAPI services at startup.

---

## 7. Pepper Robot Integration

Pepper (SoftBank Robotics, NAOQi OS) is integrated through a Python 2.7 compatibility layer connecting to the robot's SDK. Key integration points:

- **Tablet UI** (`routes/tablet.py`, `ui/tablet_html.py`): An HTML interface rendered on Pepper's 10.1-inch chest tablet with a microphone recording button, a "Call" button for real-time voice interaction, and a QR code display for chat access.
- **Text-to-Speech**: Robot speech is triggered by the Flask backend, passing generated text to Pepper's TTS engine.
- **Choreography** (`pepper_test/choreographe.py`): Scripted gestures and movements that accompany greetings and interactions.
- **Wake Word Detection**: The ASR pipeline supports a wake-word trigger mode via `POST /record/wake_word/start`, enabling hands-free activation.
- **Voice Call Mode**: Real-time bi-directional voice communication via WebSocket. Three seconds of silence triggers automatic message sending; the guest taps "Hang up" to end the session.

---

## 8. Performance Targets and Evaluation Framework

### 8.1 Technical KPIs

| Metric | Target |
|---|---|
| Face recognition accuracy | ≥85% |
| Face detection latency | ≤3 seconds |
| ASR Word Error Rate | ≤10% (≥90% correct) |
| Reservation extraction success | ≥85% |
| API response time (P95) | ≤2 seconds |
| Chatbot response time | ≤5 seconds |
| QR verification time | ≤1 second |
| System availability | ≥95% |

### 8.2 User Experience KPIs

| Metric | Target |
|---|---|
| Task success rate | ≥80% |
| User satisfaction score | ≥4.0/5.0 |
| Reservation completion time | ≤2 minutes |
| Net Promoter Score (NPS) | ≥50 |

### 8.3 Evaluation Methodology

Technical evaluation uses automated test suites structured in:
- **Unit tests** (`tests/unit/`): Component-level tests for each service.
- **Integration tests** (`tests/integration/`): End-to-end workflow tests across both APIs.
- **Security tests** (`tests/security/`): Input validation, injection prevention, authentication checks.

User experience evaluation is conducted through structured user studies with hotel guests and staff, using Likert-scale questionnaires, task completion timing, and NPS surveys.

---

## 9. System Configuration and Deployment

### 9.1 Environment

- **Python**: 3.12+ (Flask API), Python 2.7 compatibility shim (Pepper NAOQi)
- **Database**: SQLite (clients, reservations, temp reservations)
- **Memory Store**: Redis (primary), in-memory dict (fallback)
- **LLM Access**: HuggingFace Inference API (Llama 3.1-8B-Instruct)
- **Embeddings**: HuggingFace (sentence-transformers/all-MiniLM-L6-v2)

### 9.2 Key Dependencies

| Component | Library | Version |
|---|---|---|
| Primary API | Flask | 3.1.2 |
| Reservation API | FastAPI | 0.127.0 |
| ORM | SQLAlchemy | 2.0.44 |
| ASR | faster-whisper | latest |
| LLM RAG | LlamaIndex | latest |
| Face Detection | YOLOv8 (ultralytics) | latest |
| Face Recognition | face-recognition | latest |
| Image Processing | OpenCV | latest |
| Admin UI | Streamlit | latest |
| Data Validation | Pydantic | v2 |

### 9.3 Planned Future Improvements

**Short-term (3–6 months)**:
- Docker containerization for consistent deployment.
- Analytics dashboard for usage monitoring.
- Customizable email templates.

**Medium-term (6–12 months)**:
- PostgreSQL migration for production scalability.
- Mobile guest app.
- Chatbot fine-tuning on hotel-specific dialogue data.
- SMS/WhatsApp notification integration.

**Long-term (12+ months)**:
- Sentiment analysis for guest feedback.
- Multi-robot support and coordination.
- Integration with commercial Property Management Systems (PMS) and CRM platforms.
- Predictive analytics for service personalization.

---

## 10. Discussion

### 10.1 Strengths

**Modularity**: The separation between the Flask orchestration layer and the FastAPI persistence layer allows independent scaling and replacement of components. Each AI service (ASR, LLM, face recognition) is encapsulated in its own service module with a clean interface.

**Resilience**: Fallback mechanisms are implemented at multiple levels: Redis → in-memory memory, GPU inference → CPU inference, `medium` Whisper model → `base` model. This ensures the system degrades gracefully under resource constraints.

**Multilingual Support**: Whisper's multilingual model and Llama 3.1's multilingual capabilities allow the system to serve non-French-speaking guests without additional configuration.

**Contactless Design**: The QR-code-based check-in workflow eliminates physical contact at the reception desk, a hygiene consideration relevant post-pandemic.

### 10.2 Limitations and Challenges

**Latency**: While the system targets <5 seconds for chatbot responses, cloud-based LLM inference via the HuggingFace API introduces network-dependent latency variability. Local inference would improve consistency but requires significant GPU hardware.

**Face Recognition in Crowds**: YOLOv8n's performance degrades with occlusion, extreme lighting, and multiple simultaneous faces. Higher-capacity models (YOLOv8l, YOLOv8x) would improve accuracy at the cost of latency.

**Information Extraction Reliability**: Llama 3.1's ability to reliably parse complex or ambiguous spoken reservations (e.g., "I want a room for me and my husband from next Monday to the weekend after") depends on prompt engineering quality and may fail on edge cases without a structured validation and retry loop.

**Python 2.7 Dependency**: The Pepper NAOQi SDK requires Python 2.7, introducing a compatibility boundary that limits direct integration with modern Python 3 libraries. The current architecture mitigates this through HTTP API boundaries.

**Privacy and GDPR**: Biometric data (face encodings) and guest personal data stored in the system require careful consideration of GDPR compliance, consent management, and data retention policies — areas requiring further development for production deployment.

---

## 11. Conclusion

CeriBot demonstrates the feasibility of integrating a full-stack AI pipeline — combining large language models, retrieval-augmented generation, automatic speech recognition, computer vision, and humanoid robotics — into a coherent hotel reception system. The modular microservice architecture allows each AI component to be developed, tested, and replaced independently, while the four core workflows cover the essential touchpoints of a hotel guest journey: arrival recognition, information retrieval, reservation creation, and check-in.

The system's design prioritizes both technical robustness (fallback mechanisms, async processing, session persistence) and user experience (personalized greetings, natural language dialogue, contactless check-in). The defined evaluation framework provides clear, measurable targets against which real-world deployment can be assessed.

Future work will focus on improving information extraction reliability, reducing LLM inference latency through local deployment, achieving GDPR compliance for biometric data handling, and extending the system to support multi-robot coordination in larger hospitality environments.

---

## References

[1] Ivanov, S., & Webster, C. (2019). Robots in tourism: A research agenda for tourism economics. *Tourism Economics*, 25(6), 954–976.

[2] Tung, V. W. S., & Law, R. (2017). The potential for tourism and hospitality experience research in human-robot interactions. *International Journal of Contemporary Hospitality Management*, 29(10), 2518–2535.

[3] Pandey, A. K., & Gelin, R. (2018). A mass-produced sociable humanoid robot: Pepper: The first machine of its kind. *IEEE Robotics & Automation Magazine*, 25(3), 40–48.

[4] Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems*, 33, 9459–9474.

[5] Liu, J. (2022). LlamaIndex. GitHub. https://github.com/run-llama/llama_index

[6] Radford, A., et al. (2023). Robust speech recognition via large-scale weak supervision. *Proceedings of ICML 2023*.

[7] Bain, M., et al. (2023). Faster Whisper — CTranslate2-based implementation of OpenAI's Whisper. GitHub.

[8] Jocher, G., et al. (2023). Ultralytics YOLOv8. GitHub. https://github.com/ultralytics/ultralytics

[9] Meta AI. (2024). Llama 3.1: Open Foundation and Fine-Tuned Chat Models. *Meta AI Blog*.

---

*This article was produced as part of the M1 Applied Mathematics and Computer Science (AMS) curriculum at Avignon Université.*
