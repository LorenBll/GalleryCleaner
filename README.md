# GalleryCleaner

GalleryCleaner is a local web service that uses OpenAI's CLIP model for natural language-based image search on local directories.

## About

GalleryCleaner binds to `127.0.0.1` on port `49160` and rejects API calls that do not come from the local device. It indexes images from user-specified directories and searches them using text queries via CLIP (Contrastive Language-Image Pre-training). Search results are cached in a JSON index to accelerate subsequent queries. Progress streaming is available via Server-Sent Events (SSE).

**Features:**

- **Path validation** — check whether a directory contains image files and register it for searching.
- **CLIP-based semantic search** — search indexed images using natural language text queries.
- **Caching** — search results are persisted to `resources/search_index.json` so repeated queries skip recomputation.
- **Parallel processing** — images are split into worker batches and processed in platoons for efficient GPU/CPU utilization.
- **SSE progress streaming** — get real-time updates as a search runs, including filtering, model loading, and worker progress.
- **DiskIdentifier integration** — resolves drive identities for portable path references across reboots.
- **ServiceHandler registration** — auto-registers all API endpoints with ServiceHandler for service discovery.

> **Safety notice**: GalleryCleaner is intended only for environments where safety is not a major risk — the chances of malevolent actors are low, and the consequences of an eventual mishap are low.

## Setup

1. Install Python dependencies: `pip install -r requirements.txt`.
2. Review `resources/configuration.json` to adjust the port, worker settings, and ServiceHandler integration.
3. Leave the project structure intact so the service can find `resources/` and `src/`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GC_API_KEYS` | JSON object mapping service names to plain API keys. Loaded at session initialization. API keys are stored as plain text in `.env`. (Not yet implemented) |
| `GC_PORT` | Override the port set in `configuration.json`. |

## Run

1. Windows: run `scripts\run.bat`.
2. Unix-like systems: run `bash scripts/run.sh`.
3. Manual: run `python src/main.py` from the project root.

## Access Control

All `/api/*` endpoints are local-device only. Requests from non-local addresses are rejected with:
- `403` -> `{ "error": "Local device access only." }`
- All endpoints also support `HEAD` and `OPTIONS`.
- API responses use `Connection: close`.

No API key authentication is currently implemented for GalleryCleaner endpoints. Only localhost access control is enforced.

## API Endpoints

### `GET /api/health` (also `HEAD`, `OPTIONS`)
Service health check.
- Auth: local-device only
- Body: none
- Returns:
  - `200` ->
    ```json
    {
      "status": "ok",
      "service": "GalleryCleaner",
      "bind_address": "127.0.0.1",
      "port": 49160,
      "hostname": "workstation-name",
      "pid": 12345
    }
    ```

### `POST /api/check/path` (also `HEAD`, `OPTIONS`)
Validate a directory path for image content, index its files, and load/search the persisted search index for entries under that path.
- Auth: local-device only
- Body (JSON object):
  - `path` (string, required): absolute path to a directory to validate.
  - `recursive` (boolean, optional, default `true`): whether to scan subdirectories.
- Returns:
  - `200` ->
    ```json
    {
      "path": "C:\\Users\\Me\\Pictures",
      "recursive": true,
      "indexed": 1500,
      "status": "confirmed"
    }
    ```
  - `400` -> `{ "error": "Path is required." }`
  - `400` -> `{ "error": "The specified path does not exist or is not accessible." }`
  - `400` -> `{ "error": "The selected directory does not contain any image files." }`
  - `404` -> `{ "error": "The specified path does not exist or is not accessible." }`
  - `503` -> `{ "error": "DiskIdentifier is required but not available." }`

### `POST /api/search` (also `HEAD`, `OPTIONS`)
Start a CLIP-based semantic image search. Returns a `search_id` that can be polled via the progress endpoint.
- Auth: local-device only
- Body (JSON object):
  - `query` (string, required): alphanumeric text query for the CLIP model.
- Returns:
  - `200` -> `{ "search_id": "<uuid>" }`
  - `400` -> `{ "error": "Invalid JSON body." }`
  - `400` -> `{ "error": "Query text is required." }`
  - `400` -> `{ "error": "Query must contain only letters and numbers." }`
  - `400` -> `{ "error": "No indexed images. Select a path first." }`
  - `429` -> `{ "error": "A search is already running." }`

### `GET /api/search/progress/<search_id>` (also `HEAD`, `OPTIONS`)
Stream search progress via Server-Sent Events (SSE). Yields JSON progress objects every 500ms until the search is complete or fails.
- Auth: local-device only
- Path parameters:
  - `search_id` (string, required): UUID returned from `/api/search`.
- Body: none
- Returns:
  - `200` -> `text/event-stream` with `data: { ... }` lines
- Progress fields:
  - `status`: `"queued"` | `"running"` | `"complete"` | `"error"`
  - `query`: the search query
  - `phase`: current processing phase (`"filtering"`, `"filtered"`, `"loading_model"`, `"assigning_workers"`, `"workers_assigned"`, `"processing"`, `"platoon_X_of_Y"`, `"persisting"`, `"done"`)
  - `total_images`: total images in the index
  - `filtered_out`: images with cached results for this query
  - `to_process`: images requiring CLIP inference
  - `processed`: images processed so far
  - `workers` / `total_workers`: current and total worker count
  - `platoons` / `current_platoon` / `total_platoons`: platoon progress
  - `results`: final result object when `status` is `"complete"`

---

## Support
- Open an issue on [GitHub](https://github.com/LorenBll/GalleryCleaner/issues) for bug reports, feature requests, or help.

## License
- [LICENSE](LICENSE)

## Author
- [LorenBll](https://github.com/LorenBll)
