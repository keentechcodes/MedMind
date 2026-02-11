# MedMind API

RESTful API for the MedMind AI-powered medical education platform.

## Overview

The MedMind API provides endpoints for:
- **Chat** - Conversational AI with multi-agent coordination
- **Query** - Direct RAG (Retrieval-Augmented Generation) queries
- **Quiz** - Personalized quiz generation and submission
- **Progress** - Learning analytics and progress tracking
- **Documents** - Document upload and management

## Architecture

- **Framework**: FastAPI
- **Authentication**: JWT tokens with session persistence
- **State Management**: Stateless REST API with session tokens
- **Streaming**: SSE (Server-Sent Events) for real-time responses
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## Installation

All API dependencies are included in the project. Simply run:

```bash
# Install all dependencies (including API)
uv sync

# Optional: For production deployment
# Production server dependencies are already included
```

## Running the API

### Development

```bash
# Run with auto-reload
python -m physiology_rag.api.main

# Or with uvicorn directly
uvicorn physiology_rag.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
# With gunicorn
gunicorn physiology_rag.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

### Authentication

All protected endpoints require a Bearer token in the Authorization header.

#### Create Session
```http
POST /auth/login
Content-Type: application/json

{
  "user_id": "optional_user_id"  // If not provided, creates anonymous session
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "anon_a1b2c3d4",
  "expires_in": 86400
}
```

#### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer <token>

Response:
{
  "access_token": "new_token...",
  "token_type": "bearer",
  "user_id": "anon_a1b2c3d4",
  "expires_in": 86400
}
```

### Chat

#### Send Message
```http
POST /chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Explain how synaptic transmission works",
  "stream": false
}

Response:
{
  "message_id": "uuid",
  "response": "Synaptic transmission is the process by which...",
  "intent": "explanation",
  "agent_used": "tutor",
  "sources": [
    {
      "document": "Neurophysiology_Chapter1",
      "title": "Synaptic Transmission",
      "score": 0.89,
      "chunk_index": 3,
      "page_id": 12
    }
  ],
  "new_session_token": "updated_token...",
  "metadata": {
    "topics": ["synapse", "neurotransmission"],
    "interactions": 5
  }
}
```

#### Stream Response (SSE)
```http
GET /chat/stream-alt?message=Explain+action+potentials
Authorization: Bearer <token>
Accept: text/event-stream

Stream Events:
data: {"type": "intent", "intent": "explanation"}

data: {"type": "sources", "sources": [...]}

data: {"type": "token", "content": "Action potentials are..."}
data: {"type": "token", "content": "electrical signals..."}

data: {"type": "complete", "metadata": {"new_session_token": "..."}}
```

#### Get Chat History
```http
GET /chat/history
Authorization: Bearer <token>

Response:
{
  "session_id": "session_uuid",
  "interactions": [...],
  "topics_covered": ["synapse", "neuron"],
  "new_session_token": "..."
}
```

### Query (RAG)

#### Direct Query
```http
POST /query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What is the blood-brain barrier?",
  "n_results": 3,
  "include_sources": true,
  "include_attribution": true
}

Response:
{
  "answer": "The blood-brain barrier is a highly selective...",
  "sources": [...],
  "attribution": {
    "attributions": [...],
    "overall_confidence": 0.92,
    "paragraphs": [...]
  },
  "query_time_ms": 1250,
  "new_session_token": "..."
}
```

#### Search Documents
```http
GET /query/search?q=blood-brain+barrier&limit=5
Authorization: Bearer <token>

Response:
{
  "query": "blood-brain barrier",
  "results": [...],
  "total": 5,
  "new_session_token": "..."
}
```

### Quiz

#### Generate Quiz
```http
POST /quiz/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "topic": "neurophysiology",
  "difficulty": "intermediate",
  "question_count": 5,
  "question_types": ["multiple_choice"]
}

Response:
{
  "quiz_id": "quiz_uuid",
  "topic": "neurophysiology",
  "difficulty": "intermediate",
  "questions": [...],
  "estimated_time_minutes": 10,
  "new_session_token": "..."
}
```

#### Submit Quiz
```http
POST /quiz/submit
Authorization: Bearer <token>
Content-Type: application/json

{
  "quiz_id": "quiz_uuid",
  "answers": {
    "q_0": "Option A",
    "q_1": "Option C"
  },
  "time_spent_seconds": 300
}

Response:
{
  "quiz_id": "quiz_uuid",
  "score": 80.0,
  "correct_count": 4,
  "total_questions": 5,
  "answers_feedback": [...],
  "mastery_updates": {
    "neurophysiology": 0.65
  },
  "recommendations": [
    "Ready for advanced neurophysiology concepts"
  ],
  "new_session_token": "..."
}
```

### Progress

#### Get Overall Progress
```http
GET /progress
Authorization: Bearer <token>

Response:
{
  "user_id": "anon_a1b2c3d4",
  "overall_stats": {
    "accuracy": 0.75,
    "total_sessions": 12,
    "total_questions_answered": 45,
    "learning_streak": 3
  },
  "mastery": {
    "scores": {
      "neurophysiology": 0.65,
      "cardiovascular": 0.80
    },
    "knowledge_gaps": ["endocrine"],
    "strong_areas": ["cardiovascular"]
  },
  "current_session": {
    "topics": ["synapse", "neurotransmission"],
    "objectives": ["Practice neurophysiology concepts"],
    "interactions": 5
  },
  "recommendations": [...],
  "new_session_token": "..."
}
```

#### Get Topic Progress
```http
GET /progress/topics/neurophysiology
Authorization: Bearer <token>

Response:
{
  "topic": "neurophysiology",
  "mastery_score": 0.65,
  "difficulty_level": "intermediate",
  "needs_review": false,
  "new_session_token": "..."
}
```

### Documents

#### List Documents
```http
GET /documents
Authorization: Bearer <token>

Response:
{
  "documents": [
    {
      "id": "Neurophysiology_Chapter1",
      "name": "Neurophysiology_Chapter1",
      "chunks": 15,
      "images": 8,
      "processed_date": "2024-01-15T10:30:00"
    }
  ],
  "total": 1,
  "new_session_token": "..."
}
```

#### Upload Document
```http
POST /documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <PDF file>

Response:
{
  "job_id": "job_uuid",
  "status": "processing",
  "filename": "document.pdf",
  "message": "Document uploaded and processing in background...",
  "new_session_token": "..."
}
```

#### Check Upload Status
```http
GET /documents/upload/status/{job_id}

Response:
{
  "job_id": "job_uuid",
  "status": "completed",
  "progress": 100,
  "document_id": "document_name"
}
```

## Session Management

The API uses **stateless sessions** with JWT tokens:

1. **Initial Request**: Call `/auth/login` to get a token
2. **Subsequent Requests**: Include token in `Authorization: Bearer <token>` header
3. **Token Rotation**: Each response includes a `new_session_token` with updated state
4. **Token Expiry**: Tokens expire after 24 hours; use `/auth/refresh` to renew

### Important Notes

- **Always use the `new_session_token`** from the latest response
- Tokens contain session state (topics, mastery scores, preferences)
- Stateless design allows easy horizontal scaling
- No server-side session storage required

## Error Handling

All errors follow the standard HTTP status codes:

- **400** - Bad Request (invalid parameters)
- **401** - Unauthorized (missing or invalid token)
- **403** - Forbidden (access denied)
- **404** - Not Found (resource doesn't exist)
- **500** - Internal Server Error

Error Response Format:
```json
{
  "detail": "Error description"
}
```

## Rate Limiting

Add rate limiting middleware for production:

```python
from fastapi_limiter import FastAPILimiter
import redis

@app.on_event("startup")
async def startup():
    redis_connection = redis.from_url("redis://localhost", encoding="utf-8")
    await FastAPILimiter.init(redis_connection)
```

## Testing

### Using curl

```bash
# Create session
curl -X POST http://localhost:8000/auth/login

# Send chat message
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain synaptic transmission"}'
```

### Using Python

```python
import requests

# Create session
response = requests.post("http://localhost:8000/auth/login")
token = response.json()["access_token"]

# Send message
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"message": "Explain action potentials"}
)
print(response.json())
```

## Development

### Adding New Endpoints

1. Create router file in `physiology_rag/api/routers/`
2. Define Pydantic models in `physiology_rag/api/models/schemas.py`
3. Register router in `physiology_rag/api/main.py`

### Running Tests

```bash
pytest tests/api/
```

## Production Deployment

### Environment Variables

```bash
GEMINI_API_KEY=your-api-key
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
```

### Docker

```dockerfile
FROM python:3.12-slim

# Install uv
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY physiology_rag/ ./physiology_rag/

# Run with uv
CMD ["uv", "run", "gunicorn", "physiology_rag.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Scaling

The stateless design allows easy horizontal scaling:

1. Deploy multiple API instances behind a load balancer
2. Use Redis for shared caching (quiz cache, job cache)
3. Use PostgreSQL/MongoDB for persistent storage

## Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Architecture Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│  API Server   │────▶│  RAG System     │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │                       │
                           ▼                       ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │    JWT       │     │  ChromaDB       │
                    │   Tokens     │     │  (Vector DB)    │
                    └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │MedicalContext│
                    │  (Session)   │
                    └──────────────┘
```
