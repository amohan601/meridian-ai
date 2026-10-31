# Meridian AI

## Project phases

Phases 1 and 2 run in the local Meridian AI backend. Phase 1 provides local PDF question answering, and Phase 2 adds the procurement audit agents. Phase 2 still requires configured model access and uses the Frankfurter API for exchange-rate validation when available. Phase 3 focuses on unit tests for the agent, RAG, and API endpoint code. Phase 4 adds centralized structured logging and monitoring support. Phase 5 adds custom exceptions for expected configuration and document-ingestion failures.

This README documents seven phases of Meridian AI:

- [Phase 1 — Local PDF question answering](#phase-1--local-pdf-question-answering)
- [Phase 2 — Local agentic procurement audit](#phase-2--agentic-procurement-audit)
- [Phase 3 — Unit testing](#phase-3--unit-testing)
- [Phase 4 — Logging and monitoring](#phase-4--logging-and-monitoring)
- [Phase 5 — Custom exceptions](#phase-5--custom-exceptions)
- [Phase 6 — API docs, status, ingestion and lifespan](#phase-6--api-docs-status-ingestion-and-lifespan)
- [Phase 7 — React frontend](#phase-7--react-frontend)

# Phase 1 — Local PDF question answering

Phase 1 provides a local, non-cloud backend for checking service health and asking questions about uploaded PDF documents. It includes a health-check endpoint, a PDF upload endpoint, an upload-history endpoint, and a document-question endpoint.

PDFs are saved locally, their text is split into chunks, and the chunks are embedded with Google's Gemini embedding model and indexed in a local Chroma database. Answers are generated from retrieved document text using a Gemini chat model. No Google Cloud project or cloud credentials are needed. No separate logger or custom exception configuration is needed to run this phase.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Set up and run locally

Clone the repository and move into the project directory:

```bash
git clone <this-repo>
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
| `POST` | `/api/rag/upload` | Upload one or more PDF files, save the originals, and ingest their text into the vector store. |
| `GET` | `/api/rag/uploads` | Return upload history for the current backend process. |
| `POST` | `/api/rag/ask` | Ask a question about indexed documents. |

### Health check

```bash
curl http://localhost:8080/api/health
```

The response includes `status: "ok"` and the active mode (`local`).

### Upload PDFs

In `/docs`, select **POST /api/rag/upload**, click **Try it out**, add one or more PDF files under `files`, and execute the request. The endpoint accepts `files: list[UploadFile]`. Non-PDF files are skipped. The response reports each file's status, page count, and indexed chunk count where applicable.

You can also upload a sample PDF with curl:

```bash
curl -X POST http://localhost:8080/api/rag/upload \
  -F "files=@sample_docs/aldermoor_annual_report_fy2024.pdf"
```

Each uploaded original is saved to local document storage, then ingested by extracting and splitting its text and saving chunks to Chroma. The supplied notes use two names for the local PDF folder: `meridian_docs/uploads/` in the learning notes and `.meridian/uploads/` in the existing setup. The existing setup places the local data under `.meridian/` by default, with `.meridian/chroma/` for the Chroma index. Both storage folders are created as needed and ignored by Git. Set `LOCAL_DATA_DIR` in `.env` to choose a different local data root. Uploaded PDFs and the vector index remain after restarting the backend. Scanned image-only PDFs may not contain extractable text to index.

### View upload history

Use the upload-history **GET** route shown in `/docs` to retrieve upload history. Its exact path was not included in the supplied README notes. Each upload is recorded in an in-memory `upload_history` dictionary. The history resets when the backend process restarts; it is not the persistent store for the original PDFs or Chroma index.

### Ask questions about uploaded documents

Use **POST /api/rag/ask** in `/docs` with a JSON body:

```json
{
  "query": "What was Aldermoor Industries' total revenue in FY2024?"
}
```

The response contains an `answer` field. The question endpoint accepts the custom Pydantic `QueryRequest` schema and returns `QueryResponse`.

```bash
curl -X POST http://localhost:8080/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What was Aldermoor Industries total revenue in FY2024?"}'
```

The default retrieval method is `similarity`. An optional `retriever_type` can select `similarity`, `multiquery`, `contextual`, `mmr`, or `hyde`.

## Architecture and file-by-file learning notes

### `data_ingestion`

The ingestion flow prepares uploaded PDFs for semantic search:

1. `PyPDFLoader` loads a PDF into a list of LangChain `Document` objects (`langchain_core.documents.Document`), with page content and metadata.
2. `RecursiveCharacterTextSplitter` (`langchain_text_splitters.RecursiveCharacterTextSplitter`) divides the loaded documents into smaller text chunks.
3. A unique ID is generated for each chunk so individual chunks can be stored and identified in the vector store.
4. The chunk documents and IDs are saved to Chroma.

The Chroma integration is `langchain_chroma.Chroma`, a subclass of LangChain's `langchain_core.vectorstores.VectorStore`. The local vector store uses the `meridian_docs` collection name and the `.meridian/chroma/` directory. Creating it requires an embedding function, collection name, and persistence location.

### `vector_store.py`

This module creates and configures the local Chroma vector store used by ingestion and retrieval. It wires together the `Chroma` implementation, the embedding function returned by `embeddings.py`, the `meridian_docs` collection, and the `.meridian/chroma/` persistence directory. Ingestion adds the chunk documents and their unique IDs to this store; retrieval queries the same store to find relevant document chunks.

### `document_store`

This stores the original uploaded PDF files. The supplied notes identify `meridian_docs/uploads/` as the local upload folder, while the original setup describes `.meridian/uploads/`; verify the configured data path in the implementation if you need the precise on-disk location. These original files are distinct from the chunk documents and embeddings in Chroma. Uploading first saves each file to document storage and then runs ingestion to split and index its text.

### `embeddings.py`

This module creates and returns a `GoogleGenerativeAIEmbeddings` instance from `langchain_google_genai`. Its configuration includes:

- Model: `gemini-embedding-001`
- Google API key, supplied through `GOOGLE_API_KEY`
- Output dimensionality: `768`

The embedding function converts document chunks and search queries into vectors for Chroma storage and retrieval. The API key is required for document embeddings and question answering.

### `llm.py`

This module supplies the chat model used when answering questions from ingested documents. It creates a `ChatGoogleGenerativeAI` instance from `langchain_google_genai`, configured with the model name `gemini-3.8-flash`, the Google API key, and a temperature setting. The model receives a prompt containing retrieved document context and the user's question.

The module also provides `extract_text(content) -> str`. It accepts content that may be plain text or a list of content blocks. For a list, it joins the text from blocks whose type is `text` into one string.

### `retrieval.py`

This is the most involved part of the question-answering flow. It builds the RAG chain in `build_rag_chain` and invokes the chain with the user's question to get an answer.

`build_rag_chain` receives a retriever type. The supported implementations are `similarity`, `multiquery`, `contextual`, `mmr`, and `hyde`. The selected retriever is wrapped with `RunnableLambda` (`langchain_core.runnables.RunnableLambda`), which calls the corresponding retriever implementation with the original question. The retriever returns a list of `Document` objects.

The chain formats the retrieved documents as context: `format_docs` joins each document's metadata source and `page_content`. The original question is passed through as `input`, so the prompt receives two keys:

- `context`: formatted retrieved-document information
- `input`: the original question

A `ChatPromptTemplate` from `langchain_core.prompts` is configured with a system message and a human message. The system prompt tells the model to answer using the provided context; the human message contains `{input}`. The chain then calls the `ChatGoogleGenerativeAI` model from `get_llm()` and uses `StrOutputParser` (`langchain_core.output_parsers.StrOutputParser`) to return the model response as a string.

Conceptually, the LCEL flow is:

```text
{
  "context": build_retriever(retriever_type) | format_docs,
  "input": RunnablePassthrough()
}
| ANSWER_PROMPT
| get_llm()
| StrOutputParser()
```

The endpoint invokes this question-answering flow through `retrieval.py`. Answers are based on retrieved document text, so the uploaded PDF needs extractable text and relevant indexed chunks for a useful response.

### API schemas and endpoints

The upload endpoint receives `files: list[UploadFile]` from FastAPI. It saves each original file to document storage, runs ingestion to split and index its contents, and records each upload in the in-memory `upload_history` dictionary. A separate history endpoint returns those records. The ask endpoint accepts `QueryRequest`, invokes the retrieval chain with the question, and returns a `QueryResponse` containing the answer.

## Local data and configuration

- `GOOGLE_API_KEY` is needed for embeddings and question answering.
- `APP_MODE=local` uses Chroma on disk; Google Cloud services are not used.
- Local uploaded PDFs and the Chroma index persist under the configured local data directory, `.meridian/` by default.
- `LOCAL_DATA_DIR` changes the local data root.
- Upload history is held in memory and resets when the backend process restarts.
- `.venv/` is local and should not be committed.

## Troubleshooting

- **Missing API key:** Add `GOOGLE_API_KEY` to `.env`, then restart the backend.
- **Import error for `api`:** Run the command from the project root and include `--app-dir backend`.
- **No text indexed:** Try a text-based PDF rather than a scanned image PDF.
- **Port 8080 is already in use:** Stop the other process or use a different port, such as `--port 8081`.
- **No useful answer:** Confirm the upload response reports indexed chunks, then ask a question the document text can answer.

# Phase 2 — Agentic procurement audit

Phase 2 runs locally as part of the Meridian AI backend and adds a procurement audit workflow at `POST /api/agent/audit`. It accepts procurement information and runs specialist agents to assess risk, tax and treasury, and financial controls, then synthesizes their findings into a CFO audit memo. The local service uses the configured Gemini model and calls the Frankfurter API for FX-rate validation when available. The endpoint uses the custom Pydantic schemas `AuditRequest` and `AuditResponse`: the request contains `request_text`; the response contains `risk_result`, `tax_result`, `control_result`, and `cfo_memo`.

The Phase 2 notes describe the following outcomes: the Risk Agent returns sanctions and credit findings, payment-term recommendations, supply-chain flags, and a vendor verdict; the Tax Agent reports tax and landed-cost findings, FX validation, and a treasury verdict; the Control Agent returns expense classification, accounting/control findings, flags, and a control verdict. The synthesis step combines all three specialist reports into an executive memo with a final decision and next steps.

## Phase 2 architecture and file-by-file notes

### `POST /api/agent/audit` endpoint and schemas

The endpoint initializes a `ProcurementSupervisor`, passing procurement text to its `run_audit` method. `AuditRequest.request_text` is the input. The response is represented by `AuditResponse` with four fields: `risk_result`, `tax_result`, `control_result`, and `cfo_memo`.

Example request using the local server:

```bash
curl -X POST http://127.0.0.1:8080/api/agent/audit \
  -H "Content-Type: application/json" \
  -d '{"request_text":"Purchase Request — Aldermoor Industries Global Procurement:\n- Vendor: Takumi Controls Europe B.V. (Netherlands)\n- Item: Industrial PLC Controllers + HMI Panels (Qty: 200 units) for the Aldermoor filling line production\n- Total Cost: 80,000 EUR\n- Origin: JP (Japan — manufactured)\n- Destination: DE (Aldermoor Industries, Hamburg, Germany)\n- FX Rate quoted: 1 EUR = 163.5 JPY\n- Cost Centre: Production Hamburg (Plant 1)\n- Requested by: Global Procurement — Electronics & Automation Category"}'
```

### `agents.py`

`ProcurementSupervisor` manages the Phase 2 agent workflow. It uses the shared Google chat model (obtained through an LRU-cached model instance) and three specialist agents:

- **Risk Agent:** created with LangChain's `create_agent`, `RISK_AGENT_PROMPT`, and the `check_sanctions_list` and `get_vendor_credit_score` tools.
- **Tax Agent:** created with `create_agent`, `TAX_AGENT_PROMPT`, and the `calculate_cross_border_tax` and `validate_fx_hedge` tools.
- **Control Agent:** created with `create_agent`, `CONTROL_AGENT_PROMPT`, and the `categorize_expense` tool.

`run_audit` runs the three agents one after another using the procurement text. It then runs a synthesis action: the shared model receives the three agent results through `SYNTHESIS_PROMPT_TEMPLATE` and generates `cfo_memo`. The synthesis agent does not call tools directly.

### `middleware.py`

The specialist agents use LangChain agent middleware for input handling, call limits, retries, and tool-call timing:

- `PIIMiddleware("email", strategy="redact", apply_to_input=True)` redacts email addresses in agent input.
- `PIIMiddleware("credit_card", strategy="mask", apply_to_input=True)` masks credit card numbers in agent input.
- `ModelCallLimitMiddleware` uses `settings.agent_max_model_calls` and ends the phase when its limit is reached.
- `ToolCallLimitMiddleware` uses `settings.agent_max_tool_calls` and continues when its limit is reached.
- `ModelRetryMiddleware` and `ToolRetryMiddleware` retry transient failures, using `settings.agent_max_retries` and exponential backoff. The model retry starts at 1.0 seconds; tool retry starts at 0.5 seconds.
- The custom `log_tool_calls` middleware, implemented with `@wrap_tool_call`, records the time taken to run tools.

The model-call and tool-call limits can be overridden through the settings configured from `.env`.

### `tools.py`

The agents call focused tools. Each tool has its own prompt or calculation logic; these tool prompts are separate from the specialist agent prompts in `backend/agent/prompt.py`.

**Risk Agent tools**

- `check_sanctions_list(vendor_name: str) -> str` uses a model call with instructions to assess whether the vendor appears on a sanctions list. It returns `RED ALERT` or `CLEARED`; model-call errors are caught and returned as `LLM_ERROR`.
- `get_vendor_credit_score(vendor_name: str) -> str` uses a model call to assess vendor creditworthiness. Its instructions request a score, risk level, and reasoning.

**Tax Agent tools**

- `calculate_cross_border_tax(amount: float, origin: str, destination: str) -> Dict` estimates tax information using the model's available knowledge. Its result includes tax, VAT/GST, import-duty rates and amounts, total cost, trade-agreement notes, and the origin/destination route.
- `validate_fx_hedge(currency_pair: str, rate_used: float) -> str` obtains a market rate from `api.frankfurter.dev`, with a fallback to model knowledge if the API call fails. It computes `abs(rate_used - market_rate) / market_rate`. A variance above 5% triggers an audit-required FX alert. The supplied notes show the same alert text in both the above-5% and at-or-below-5% return branches, so confirm the implementation if the below-threshold message matters.

**Control Agent tool**

- `categorize_expense(amount: float, item_description: str) -> str` classifies a purchase as CapEx when it provides future economic benefit and has a useful life over one year; otherwise it classifies it as OpEx. It is instructed to flag CapEx above `$500,000` for CFO sign-off, OpEx above `$100,000` for possible misclassification, and suggest a depreciation period for CapEx. Its result includes classification, reasoning, depreciation, and flags.
- If the model call fails, the described fallback labels the expense CapEx (three-year depreciation) when the amount is over `$50,000` or the description contains `server`, `machine`, `vehicle`, `building`, `equipment`, or `hardware`. Otherwise it returns OpEx with an immediate-deduction fallback label. Both fallback messages identify that the LLM was unavailable and a heuristic was used.

### `backend/agent/prompt.py`

This module defines prompts for the three specialist agents and the synthesis step:

- `RISK_AGENT_PROMPT` directs the Risk Agent to use sanctions screening and credit assessment, recommend payment terms, identify supply-chain risks, and decide whether to approve, conditionally approve, or reject the vendor. The expected report includes sanctions status, credit score, payment terms, risk flags, and verdict.
- `TAX_AGENT_PROMPT` directs the Tax Agent to calculate taxes, VAT, and customs duties for international purchases and check exchange rates against company policy. The expected report includes tax liability, effective tax rate, landed cost, FX status, and a treasury decision: approved, hold for treasury audit, or escalate to Group Treasury.
- `CONTROL_AGENT_PROMPT` directs the Control Agent to classify expenses as CapEx or OpEx under IFRS, suggest a GL account range and depreciation schedule, and flag approval thresholds or potentially misclassified maintenance. The expected report includes classification, IFRS reference, GL range, depreciation, approval threshold, anomaly flags, and control verdict.
- `SYNTHESIS_PROMPT_TEMPLATE` combines the three reports into a CFO audit memo. Expected content includes an executive summary, key findings, a final decision (`Approved to Pay`, `Conditional Hold`, or `Rejected`), reasons, and actionable next steps with responsible teams and deadlines.

## Phase 2 response and decision flow

```text
AuditRequest.request_text
        |
        v
ProcurementSupervisor.run_audit
        |
        +--> Risk Agent   --> risk_result
        +--> Tax Agent    --> tax_result
        +--> Control Agent --> control_result
                              |
                              v
                    synthesis prompt + shared LLM
                              |
                              v
                           cfo_memo
```

The three specialist agents run sequentially, as described in the supplied Phase 2 notes. Their results feed the synthesis step; the synthesis step does not use tools directly.

# Phase 3 — Unit testing

Phase 3 adds unit-test coverage for the main backend components:

- `backend/agent/` — agent setup, orchestration, middleware, prompts, and tools.
- `backend/rag/` — PDF ingestion, document and vector storage, embeddings, language-model helpers, and retrieval.
- `backend/api/endpoints.py` — HTTP endpoint behavior, including the Phase 1 document routes and Phase 2 procurement audit route.

These tests are intended to check each component's behavior independently.

# Phase 4 — Logging and monitoring

Phase 4 introduces centralized logging for the Meridian AI backend using Python's `logging` module and `structlog`. It makes application behavior, processing events, and errors easier to trace during development and troubleshooting.

## Features

- **Shared logger:** `GLOBAL_LOGGER` provides a reusable logger that backend modules can import. It is initialized when the `logger` package is first imported in a Python process; later imports reuse the cached module.
- **Structured JSON:** `structlog` adds a UTC timestamp, log level, uppercase `severity`, event name, contextual fields, and formatted exception details before rendering each record as JSON.
- **Console and file output:** Python logging handlers write JSON log entries to the console and to a timestamped `.log` file under a `logs/` directory.
- **Exception details:** Exception tracebacks are included when exception information is supplied, such as through `log.exception(...)`.
- **Severity filtering:** The configuration accepts `INFO`, `WARNING`, `ERROR`, and `CRITICAL` records. `DEBUG` records are filtered out.

## Logging architecture

1. `CustomLogger` initializes the logging environment, creates the log file path, and configures handlers.
2. `GLOBAL_LOGGER`, exposed from `backend/logger/__init__.py` as the `logger` package, provides the shared logger to backend modules.
3. `structlog` processors add a UTC timestamp, level, uppercase severity, and formatted exception details to each event, then render it as JSON.
4. Python logging handlers send the rendered message to both console and the timestamped log file.

## Usage

Backend modules can import and use the shared logger:

```python
from logger import GLOBAL_LOGGER as log

log.info("document_upload_started", filename="policy.pdf")
log.warning("no_relevant_chunks_found", query="tax policy")
log.error("document_processing_failed", filename="policy.pdf")
```

For exception handling, the logger can capture exception details and traceback:

```python
try:
    # Document processing logic
    pass
except Exception:
    log.exception("document_processing_failed")
    raise
```

Structured fields such as `filename` and `query` provide context for searching and investigating log entries.

## Log output

Each entry is rendered as a JSON object. This example is illustrative:

```json
{
  "timestamp": "2026-10-25T02:00:00Z",
  "level": "info",
  "severity": "INFO",
  "event": "document_upload_started",
  "filename": "policy.pdf"
}
```

## Important notes

- Log files are created in `logs/` relative to the application's current working directory.
- Do not write API keys, credentials, or sensitive document contents to logs.

## Phase 4 outcome

Phase 4 provides a reusable structured logging layer for consistent backend event and error output, helping developers trace and investigate application behavior.

# Phase 5 — Custom exceptions

Phase 5 adds custom exceptions so expected failures return clear HTTP responses instead of generic 500 errors. All exception classes live in `backend/exceptions/__init__.py`.

## Exception classes

- **`MeridianError`** — Base class for errors the application raises intentionally.
- **`ConfigurationError`** — Indicates a required setting is missing, such as `GOOGLE_API_KEY`. The API returns **503 Service Unavailable** with a message identifying what needs to be set.
- **`IngestionError`** — Indicates a document could not be read, chunked, or indexed. The API returns **422 Unprocessable Entity** with the reason.

## Where exceptions are raised and handled

- `backend/rag/llm.py` and `backend/rag/embeddings.py` raise `ConfigurationError` when the API key is empty.
- `backend/rag/data_ingestion.py` raises `IngestionError` when a PDF cannot be read.
- `backend/api/main.py` registers a handler for each exception class. Each handler logs the failure and returns the corresponding status code and message.
- `backend/api/endpoints.py` re-raises `MeridianError` so the registered handlers can process it. Other exceptions continue to produce a 500 response.

## Phase 5 outcome

A missing API key or unreadable PDF produces a specific, readable response, and the failure is recorded in the log.

# Phase 6 — API docs, status, ingestion and lifespan

## API docs

With the server running, FastAPI serves these pages automatically:

- **Swagger UI:** http://localhost:8080/docs, an interactive page where you can try each endpoint.
- **ReDoc:** http://localhost:8080/redoc, a read-only view of the same API.
- **OpenAPI schema:** http://localhost:8080/openapi.json, the raw schema the other two pages are built from.

## Status endpoint

`GET /api/status` returns the running configuration: the mode, backend status and uptime, the Python version and platform, and the storage, vector search and model settings. It makes no calls to Google.

## Ingest stored documents

`POST /api/rag/ingest` indexes every PDF already in the document store. It does not take a file; it reads what was saved earlier by the upload route.

- **Local mode:** the PDFs are read from `.meridian/uploads/`.
- **Cloud mode:** the PDFs are read from the Cloud Storage bucket. This is not implemented yet.

Each PDF is chunked and embedded, and the chunks are written to the vector store. Chunk IDs are stable, so running the endpoint again overwrites the same chunks instead of duplicating them.

Example request and response:

```bash
curl -X POST http://localhost:8080/api/rag/ingest
```

```json
{
  "status": "Ingestion complete (local mode)",
  "files": 1,
  "pages": 1,
  "chunks": 1
}
```

If the store has no PDFs, the response is zeros for `files`, `pages` and `chunks`. If indexing fails, the endpoint returns HTTP 500 with the error message in `detail`.

The "Index Stored Documents" button on the Index Documents tab calls this endpoint. `POST /api/rag/ingest-gcs` is an older alias that does the same thing.

## Lifespan

On startup, the app logs the mode and the LLM model name. The shutdown step is a placeholder for flushing logs to Cloud Storage in cloud mode, which is not implemented yet.

# Phase 7 — React frontend

Phase 7 adds a single-page web interface in `frontend/` for the backend. It has four tabs: Index Documents, RAG Q&A, Procurement Audit and System Status.

## Tech stack

- **React 18 and TypeScript**, built and served by **Vite**. The dev server runs on port 3000.
- **Tailwind CSS** for styling, with **shadcn/ui** components built on Radix UI primitives in `src/components/ui/`.
- **lucide-react** for icons, **React Router** for routing, **TanStack Query** for data fetching, **Recharts** for charts, and **Sonner** for toast notifications.
- **Vitest** (with jsdom) for unit tests and **Playwright** for browser tests. Both are configured, but only a placeholder test exists so far.

## Key files

| File | Purpose |
|---|---|
| `frontend/package.json` | Dependencies and scripts: `dev`, `build`, `test`, `lint`. |
| `frontend/vite.config.ts` | Dev server settings and the `@/` alias for `src/`. |
| `frontend/src/main.tsx` | Mounts the app and loads the global CSS. |
| `frontend/src/App.tsx` | Providers and routes: `/` and a catch-all Not Found page. |
| `frontend/src/pages/Index.tsx` | Main page with the sidebar of four tabs. |
| `frontend/src/components/DocumentUploadTab.tsx` | Index Documents tab (default): uploads PDFs and indexes stored documents. |
| `frontend/src/components/RagQATab.tsx` | RAG Q&A tab: asks questions about indexed documents. |
| `frontend/src/components/AuditTab.tsx` | Procurement Audit tab: submits a purchase request to the agent audit. |
| `frontend/src/components/SystemStatusTab.tsx` | System Status tab: shows the `/api/status` output. |
| `frontend/src/lib/api.ts` | All backend calls. The base URL is `http://localhost:8080` in dev, or `VITE_API_URL` if it is set. |
| `frontend/src/index.css` | Colour and font tokens for the theme. |

## Running the frontend

With the backend running on port 8080, run the following from the `frontend/` folder:

```bash
npm install
```

```bash
npm run dev
```

Then open http://localhost:3000.

## Notes

- The "Index Stored Documents" button calls `POST /api/rag/ingest` through `triggerStoreIngestion` in `src/lib/api.ts`. The backend must be restarted after the ingestion fixes before this button works.

## Project layout

```text
.
├── backend/
│   ├── agent/
│   │   ├── agents.py          ProcurementSupervisor and agent orchestration
│   │   ├── middleware.py      Agent middleware
│   │   ├── prompt.py          Agent and synthesis prompts
│   │   └── tools.py           Risk, tax/FX, and control tools
│   ├── api/
│   │   ├── endpoints.py       HTTP endpoints
│   │   ├── main.py            FastAPI application
│   │   └── schemas.py         API request/response schemas
│   ├── config/
│   │   └── settings.py        Environment-based settings
│   ├── exceptions/            Exception definitions
│   ├── logger/                Logging setup
│   ├── rag/
│   │   ├── data_ingestion.py  PDF loading, splitting, and indexing
│   │   ├── document_store.py  Original PDF storage
│   │   ├── embeddings.py      Gemini embedding configuration
│   │   ├── llm.py             Gemini chat model and text utility
│   │   ├── retrieval.py       RAG retrieval and answer chain
│   │   └── vector_store.py    Local Chroma configuration
│   └── tests/
│       ├── conftest.py        Shared test setup
│       ├── agent/             Agent tests
│       ├── api/               API endpoint tests
│       └── rag/               RAG component tests
├── frontend/                  React web interface (Phase 7)
│   ├── src/
│   │   ├── components/        The four tabs and shadcn/ui components (ui/)
│   │   ├── lib/api.ts         Backend API client
│   │   ├── pages/             Main page and Not Found page
│   │   └── index.css          Theme colours and fonts
│   ├── package.json           Dependencies and scripts
│   └── vite.config.ts         Vite dev server settings
├── sample_docs/               Example PDFs for local use
├── .meridian/
│   ├── chroma/                 Local Chroma database (generated)
│   └── uploads/                Uploaded original PDFs (generated)
├── logs/                       Timestamped application logs (generated)
├── lib_check.py                Local library check utility
├── main.py                     Root-level entry point
├── pyproject.toml              Project metadata and dependencies
├── requirements.txt            Runtime dependencies
├── requirements-dev.txt        Development dependencies
├── uv.lock                     Locked dependency versions
├── .env.example                Local environment-variable template
└── README.md
```

`.meridian/` contains local generated data and should remain out of version control. The `.env` file contains local configuration and secrets; do not commit it. The company and example data in the sample documents are fictional.
