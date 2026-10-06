# Co-Build AI — AI Service

> This repository contains the AI component of the [Co-Build AI](https://github.com/esmacakar/co-build-ai) platform.

## About Co-Build AI

Co-Build AI is a marketplace platform that connects non-technical founders with developers. Founders describe their project ideas in their own words; the platform converts these ideas into professional technical specifications, closing the communication and trust gap between founders and developers. The platform consists of a Next.js web application and this standalone AI service.

## Role of This Service

This service processes raw project ideas submitted through the platform and produces:

- A structured Product Requirements Document (PRD), including a preliminary patent/originality check
- A limited set of project-specific technical skill tags
- A differentiation and market-positioning analysis backed by real startup data
- A ranked list of recommended developers for the project, via a semantic + keyword matchmaking engine

All LLM inference runs on a GPU we rent ourselves (see Architecture), with no dependency on third-party AI APIs (OpenAI, Anthropic, etc.). This architectural choice ensures that user data is never transmitted abroad, supporting compliance with Turkey's data protection law (KVKK) at the technical level.

## Architecture

```
Next.js Client
      │  POST /prd-uret-baslat
      ▼
FastAPI (main.py)
      │
      ├──►  ChromaDB "startup_ornekleri"   (RAG: similar startup search)
      ├──►  ChromaDB "patent_ornekleri"    (RAG: patent originality check)
      │
      ▼
LangGraph agent (prd_agent.py): generate → self-critique → revise (max 1x) → match
      │
      │  via LangChain's OpenAI-compatible client (ChatOpenAI)
      ▼
vLLM · Qwen/Qwen2.5-32B-Instruct-AWQ · running on a rented RunPod GPU (RTX 4090)
      │
      ▼
matchmaking_engine.py: hybrid (semantic + BM25) developer ranking, via Supabase/pgvector
      │
      ▼
In-memory job store
      ▲
      │  GET /prd-durum/{id}
Next.js Client  (periodic polling)
```

The model previously ran locally on CPU via Ollama (`llama3.1:8b`); this was replaced with a rented GPU running vLLM because CPU inference was too slow (1-5 minutes per request) and Turkish output quality was weak. `ChatOpenAI` (LangChain's OpenAI-compatible client) is used because vLLM exposes an OpenAI-compatible API — no data is sent to OpenAI itself; `base_url` points at our own RunPod server.

A full generation cycle (PRD + self-critique + matchmaking) currently completes in roughly 35 seconds on a RunPod RTX 4090. Requests are still handled asynchronously (job started in the background, client polls for the result) to keep the API responsive under concurrent load.

## Capabilities

**PRD Generation (self-reflecting agent)**
Converts a raw idea into a structured document (product summary, target audience, core features, technical requirements, differentiation analysis, patent/originality check, estimated infrastructure cost). A LangGraph state machine generates a draft, critiques it against a checklist (all sections present, no foreign-alphabet contamination), and regenerates once if needed before finalizing.

**Skill Tag Extraction**
Parses the model's output into a clean list of at most five technical skills genuinely relevant to the project.

**RAG-Backed Differentiation Analysis**
Performs a semantic search against a vector database of real startup descriptions and supplies the closest matches to the model as context, so its differentiation suggestions are grounded in real reference points rather than generated from memory alone.

**Patent/Originality Pre-Check**
Searches a second vector database built from the Harvard USPTO Patent Dataset (HUPD, classes G06F/G06N) for conceptually similar patents and surfaces them in the PRD. This is a rough, automated pre-check only — it does not produce a legal conclusion, and recommends legal counsel when similarity is high.

**Developer Matchmaking**
Combines semantic search (embedding similarity via `sentence-transformers`, stored in Supabase/pgvector) with BM25 keyword search over developer skills/bio, merged via Reciprocal Rank Fusion, to recommend the top developers for a generated PRD. Developers with a verified patent (`profiles.has_verified_patent`) receive a ranking bonus.

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Model runtime | vLLM (`Qwen/Qwen2.5-32B-Instruct-AWQ`), on a rented RunPod GPU |
| Orchestration | LangChain + LangGraph |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector store | ChromaDB (startup + patent RAG), Supabase/pgvector (developer matchmaking) |
| Keyword search | `rank_bm25` |

## Environment Variables

Secrets are never committed. Copy the template and fill in your own values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | yes | Supabase project URL — used for seeding demo data and by the matchmaking engine |
| `SUPABASE_SERVICE_KEY` | yes | Supabase secret key. Bypasses Row Level Security — server-side only, never exposed to a client |
| `VLLM_BASE_URL` | for PRD generation | OpenAI-compatible base URL of the vLLM server (default `http://localhost:8000/v1`; set to your RunPod proxy URL, e.g. `https://<pod-id>-8000.proxy.runpod.net/v1`) |
| `VLLM_API_KEY` | no | vLLM API key, if one was set when starting the server (default `EMPTY`) |
| `VLLM_MODEL_ADI` | no | Model name, must match the `--model` vLLM was started with (default `Qwen/Qwen2.5-32B-Instruct-AWQ`) |
| `DEMO_USER_PASSWORD` | no | Password for generated demo accounts (default: `DemoSifre123!`) |
| `DEMO_SEED_ONAY` | no | Set to `true` to skip the interactive confirmation prompt when seeding |

The AI service itself (`main.py`) requires `VLLM_BASE_URL` (or the localhost default) to reach the vLLM server, plus `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` for the matchmaking engine. The Supabase credentials are also used by the optional `demo_kullanici_uret.py` seeding script.

### Secret Protection

- `.gitignore` blocks `.env` and every `.env.*` variant, allowing only `.env.example` through
- A `pre-commit` hook in `.githooks/` refuses any commit containing an env file or a secret-shaped string. Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

- `demo_kullanici_uret.py` fails fast on missing variables, redacts secrets from all error output, and requires explicit confirmation before writing to a database with admin privileges

## Setup

**Prerequisites:** Python 3.11+, a running vLLM server (locally with a GPU, or via a rented RunPod GPU — see this repo's `runpod_kurulum.sh` and the root project's `CLAUDE.md` for the RunPod setup used in this project).

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Build the startup-example vector database (run once, on first setup):

```bash
python veri_yukle.py
```

Optionally build the patent RAG vector database (CPU-only, no GPU/vLLM required):

```bash
python patent_veri_yukle.py --yil 2016
```

Start the server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service runs at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service health check |
| `POST` | `/prd-uret-baslat` | Starts PRD generation (+ matchmaking) in the background, returns immediately |
| `GET` | `/prd-durum/{project_id}` | Returns the current status of a job and its result once complete |
| `POST` | `/gelistirici/vektorle` | Embeds and upserts a developer profile into the matchmaking index |
| `POST` | `/eslestir/semantik-top5` | Pure semantic search for the top developers matching a PRD |
| `POST` | `/eslestir/hibrit` | Hybrid (semantic + BM25) developer search, merged via Reciprocal Rank Fusion |

```json
POST /prd-uret-baslat
{
  "project_id": "abc-123",
  "title": "Neighborhood Tool-Sharing App",
  "raw_idea": "An app for neighbors to share rarely-used tools with each other."
}
```

## Known Limitations

- Skill-tag extraction relies on the model consistently labeling its own output section; formatting drift (numbered lists, paraphrased headings) is handled defensively but not fully eliminated
- The patent pre-check is a static-dataset RAG prototype, not a real-time or official patent office integration — it must not be treated as legal advice
- Concurrent requests are processed by a single background worker (queued), so heavy concurrent load increases wait time

## Data Sources & License

This project is maintained in a private repository.

- The startup-example RAG dataset is sourced from [HackerNoon/where-startups-trend](https://huggingface.co/datasets/HackerNoon/where-startups-trend), licensed under MIT.
- The patent RAG dataset is sourced from the [Harvard USPTO Patent Dataset (HUPD)](https://huggingface.co/datasets/HUPD/hupd), filtered to classes G06F/G06N.
