# Meridian AI — Phase 1

Phase 1 provides a local, non-cloud backend for checking service health and asking questions about uploaded PDF documents. It includes a health-check endpoint, a document-upload endpoint, and a document-question endpoint.

Documents are split into text chunks, embedded with the Gemini API, and indexed in a Chroma database on your computer. Answers are generated from retrieved document text. No Google Cloud project or cloud credentials are needed. No separate logger or custom exception configuration is needed to run this phase.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Set up and run locally

Clone the repository and move into the project directory:

```bash
git clone <this repo>
cd meridian-ai-learner
```

Initialize the project with uv and install its dependencies:

```bash
uv init --bare
uv python pin 3.12
uv add -r requirements.txt
uv sync
```

Create your local environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your Gemini API key:

```dotenv
APP_MODE=local
GOOGLE_API_KEY=your-gemini-api-key
```

Start the backend from the project root:

```bash
uv run uvicorn api.main:app --app-dir backend --reload --port 8080
```

Interactive API documentation is available at [http://localhost:8080/docs](http://localhost:8080/docs). The server reads `.env` from the project root even though the application code is in `backend/`.

## Phase 1 endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check that the backend is responding. |
| `POST` | `/api/rag/upload` | Upload one or more PDF files and index their text. |
| `POST` | `/api/rag/ask` | Ask a question about the indexed documents. |

### Health check

```bash
curl http://localhost:8080/api/health
```

The response includes `status: "ok"` and the active mode (`local`).

### Upload PDFs

In `/docs`, select **POST /api/rag/upload**, click **Try it out**, add one or more PDF files under `files`, and execute the request. Non-PDF files are skipped. The response reports each file’s status, page count, and indexed chunk count where applicable.

You can also upload a sample PDF with curl:

```bash
curl -X POST http://localhost:8080/api/rag/upload \
  -F "files=@sample_docs/aldermoor_annual_report_fy2024.pdf"
```

Original PDFs are stored in `.meridian/uploads/`. The local Chroma index is stored in `.meridian/chroma/`. Both folders are created as needed and are ignored by Git. Scanned image-only PDFs may not contain extractable text to index.

### Ask questions about uploaded documents

Use **POST /api/rag/ask** in `/docs` with a JSON body:

```json
{
  "query": "What was Aldermoor Industries' total revenue in FY2024?"
}
```

The response contains an `answer` field. You can also send a request with curl:

```bash
curl -X POST http://localhost:8080/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What was Aldermoor Industries total revenue in FY2024?"}'
```

The default retrieval method is `similarity`. An optional `retriever_type` field can be set to `similarity`, `multiquery`, or `contextual`.

## Local data and configuration

- `GOOGLE_API_KEY` is required for document embeddings and question answering.
- `APP_MODE=local` uses Chroma on disk; Google Cloud services are not used.
- By default, uploaded PDFs and the Chroma index are saved under `.meridian/` in the project root.
- To use a different location, set `LOCAL_DATA_DIR` in `.env`.
- Uploaded PDFs and the vector index remain after restarting the backend. Upload history is kept in memory and resets when the process restarts.
- The `.venv/` folder is local and should not be committed.

## Troubleshooting

- **Missing API key:** Add `GOOGLE_API_KEY` to `.env`, then restart the backend.
- **Import error for `api`:** Run the command from the project root and include `--app-dir backend`.
- **No text indexed:** Try a text-based PDF rather than a scanned image PDF.
- **Port 8080 is already in use:** Stop the other process or use a different port, such as `--port 8081`.
- **No useful answer:** Confirm the upload response reports indexed chunks, then ask a question the document text can answer.

## Project layout

```text
backend/
  api/                 FastAPI application and endpoint definitions
  config/              Environment-based settings
  rag/                 PDF ingestion, local vector storage, and question answering
  tests/               Backend tests
sample_docs/           Example PDFs for local testing
requirements.txt       Python dependencies
.env.example           Local environment-variable template
```

The company and example data in the sample documents are fictional.
