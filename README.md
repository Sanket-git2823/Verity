# Verity — Research Intelligence & Retrieval Engine

**Verity** is a production-grade Retrieval-Augmented Generation (RAG) platform designed for research-intensive workflows. It ingests documents, chunks and indexes them using hybrid retrieval (BM25 + vector similarity), re-ranks results with a cross-encoder, and generates grounded, citation-backed answers using a large language model.

---

## Architecture Overview

```
┌─────────────┐         ┌─────────────────────────────────────────────────┐
│   Frontend   │ ◄─────► │                  Backend API                    │
│  (Next.js)   │  REST   │                  (FastAPI)                      │
└─────────────┘         │                                                 │
                        │  ┌──────────┐  ┌────────────┐  ┌────────────┐  │
                        │  │ Ingestion│  │  Retrieval  │  │ Generation │  │
                        │  │ Pipeline │  │  Pipeline   │  │  Pipeline  │  │
                        │  └────┬─────┘  └──────┬─────┘  └─────┬──────┘  │
                        │       │               │              │          │
                        │  ┌────▼───────────────▼──────────────▼──────┐  │
                        │  │          PostgreSQL + pgvector            │  │
                        │  │               Redis Cache                │  │
                        │  └──────────────────────────────────────────┘  │
                        └─────────────────────────────────────────────────┘
```

## Tech Stack

| Layer        | Technology                                      |
| ------------ | ----------------------------------------------- |
| Frontend     | Next.js 14, TypeScript, Tailwind CSS             |
| Backend      | Python 3.12, FastAPI, SQLAlchemy 2.0, asyncpg    |
| Database     | PostgreSQL 16 with pgvector extension             |
| Cache        | Redis 7                                           |
| Embeddings   | OpenAI text-embedding-3-small (configurable)      |
| Reranker     | cross-encoder/ms-marco-MiniLM-L-6-v2              |
| LLM          | GPT-4o via OpenAI API (configurable)               |
| Deployment   | Docker & Docker Compose                            |

## Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** ≥ 2.20
- An **OpenAI API key** (or compatible provider endpoint)
- 4 GB RAM minimum (8 GB recommended)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/verity.git
cd verity

# 2. Create your environment file
cp .env.example .env
# Edit .env and add your LLM_API_KEY and EMBEDDING_API_KEY

# 3. Build and start all services
docker-compose up --build

# 4. Access the application
#    Frontend:  http://localhost:3000
#    API:       http://localhost:8000
#    API Docs:  http://localhost:8000/docs
```

## Configuration Reference

| Variable                | Default                                | Description                                               |
| ----------------------- | -------------------------------------- | --------------------------------------------------------- |
| `DATABASE_URL`          | `postgresql+asyncpg://verity:verity@localhost:5432/verity` | Async PostgreSQL connection string       |
| `REDIS_URL`             | `redis://localhost:6379/0`             | Redis connection string                                    |
| `LLM_API_BASE`          | `https://api.openai.com/v1`           | LLM API base URL                                           |
| `LLM_API_KEY`           | —                                      | API key for the LLM provider                               |
| `LLM_MODEL`             | `gpt-4o`                              | Model identifier for generation                            |
| `LLM_TEMPERATURE`       | `0.1`                                 | Sampling temperature                                       |
| `LLM_MAX_TOKENS`        | `2048`                                | Max tokens in LLM response                                 |
| `EMBEDDING_API_BASE`    | `https://api.openai.com/v1`           | Embedding API base URL                                     |
| `EMBEDDING_API_KEY`     | —                                      | API key for embedding provider                              |
| `EMBEDDING_MODEL`       | `text-embedding-3-small`              | Embedding model identifier                                 |
| `EMBEDDING_DIMENSIONS`  | `1536`                                | Embedding vector dimensionality                             |
| `RERANKER_MODEL`        | `cross-encoder/ms-marco-MiniLM-L-6-v2`| Cross-encoder reranker model                               |
| `RERANKER_TOP_K`        | `5`                                   | Candidates to keep after reranking                          |
| `CHUNK_SIZE`            | `1024`                                | Max characters per chunk                                    |
| `CHUNK_OVERLAP`         | `128`                                 | Character overlap between chunks                            |
| `BM25_WEIGHT`           | `0.4`                                 | BM25 score weight in hybrid fusion                          |
| `VECTOR_WEIGHT`         | `0.6`                                 | Vector score weight in hybrid fusion                        |
| `BM25_TOP_K`            | `20`                                  | Results from BM25 retriever                                 |
| `VECTOR_TOP_K`          | `20`                                  | Results from vector retriever                               |
| `HYBRID_TOP_K`          | `15`                                  | Results after RRF fusion                                    |
| `RRF_K`                 | `60`                                  | RRF fusion constant                                         |
| `MAX_CONTEXT_TOKENS`    | `4096`                                | Max context tokens for LLM prompt                           |
| `CORS_ORIGINS`          | `http://localhost:3000`               | Allowed CORS origins (comma-separated)                      |
| `LOG_LEVEL`             | `INFO`                                | Logging level                                               |
| `BATCH_INGESTION_WORKERS`| `4`                                  | Concurrent ingestion workers                                |
| `MAX_FILE_SIZE_MB`      | `50`                                  | Upload file size limit (MB)                                 |

## API Documentation

Once the backend is running, interactive API documentation is available at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```
verity/
├── docker-compose.yml          # Multi-service orchestration
├── init.sql                    # PostgreSQL extension setup
├── .env.example                # Environment variable template
├── .gitignore
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── config.py           # Pydantic settings
│   │   ├── database.py         # Async SQLAlchemy engine & session
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── documents.py    # Document CRUD & upload
│   │   │   ├── query.py        # Query & generation endpoint
│   │   │   └── evaluation.py   # Eval dataset management
│   │   └── services/
│   │       ├── ingestion.py    # Chunking & embedding pipeline
│   │       ├── retrieval.py    # BM25 + vector + hybrid search
│   │       ├── reranker.py     # Cross-encoder reranking
│   │       ├── generation.py   # LLM prompt construction & call
│   │       └── evaluation.py   # Retrieval quality metrics
│   └── sample_data/
│       ├── sample_eval_dataset.json
│       └── documents/
│           ├── sample_research_001.md
│           ├── sample_research_002.md
│           ├── sample_research_003.md
│           ├── sample_research_004.txt
│           └── sample_research_005.txt
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.ts
    ├── next.config.js
    └── app/
        ├── layout.tsx
        ├── page.tsx
        └── components/
            ├── QueryInterface.tsx
            ├── DocumentList.tsx
            └── CitationPanel.tsx
```

## Development Setup (Without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Ensure PostgreSQL and Redis are running locally
# Apply database migrations
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:3000
```

## Retrieval Pipeline

Verity uses a multi-stage retrieval pipeline to maximize both recall and precision:

```
   Query
     │
     ▼
┌──────────┐     ┌──────────────┐
│  BM25     │     │   Vector      │
│  Search   │     │   Search      │
│ (top 20)  │     │  (top 20)     │
└─────┬────┘     └──────┬───────┘
      │                 │
      └────────┬────────┘
               ▼
     ┌───────────────────┐
     │  Reciprocal Rank  │
     │  Fusion (RRF)     │
     │   → top 15        │
     └────────┬──────────┘
              ▼
     ┌───────────────────┐
     │  Cross-Encoder    │
     │  Reranking        │
     │   → top 5         │
     └────────┬──────────┘
              ▼
     ┌───────────────────┐
     │  LLM Generation   │
     │  with Citations   │
     └───────────────────┘
```

1. **BM25 Search** — Lexical keyword matching using the Okapi BM25 scoring function. Finds documents with exact term overlap.
2. **Vector Search** — Semantic similarity search using dense embeddings stored in pgvector. Captures meaning beyond exact keywords.
3. **Reciprocal Rank Fusion** — Merges ranked lists from BM25 and vector search using rank-based scoring, eliminating the need for score normalization.
4. **Cross-Encoder Reranking** — A transformer cross-encoder model jointly encodes each (query, passage) pair to produce a fine-grained relevance score, reordering the fused candidates.
5. **LLM Generation** — The top-ranked passages are assembled into a context window and passed to the LLM along with the user query. The model generates a grounded answer with inline citations.

## Evaluation Framework

Verity includes a built-in evaluation framework for measuring retrieval quality:

```bash
# Upload an evaluation dataset
curl -X POST http://localhost:8000/api/evaluation/datasets \
  -H "Content-Type: application/json" \
  -d @backend/sample_data/sample_eval_dataset.json

# Run evaluation
curl -X POST http://localhost:8000/api/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "<dataset-id>", "config_overrides": {}}'
```

Metrics computed include:
- **Precision@K** — Fraction of retrieved documents that are relevant
- **Recall@K** — Fraction of relevant documents that are retrieved
- **MRR** (Mean Reciprocal Rank) — Average of 1/rank of the first relevant result
- **NDCG@K** — Normalized Discounted Cumulative Gain

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
