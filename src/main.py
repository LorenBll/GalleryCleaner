"""GalleryCleaner local web service."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import json
import logging
import os
import socket
import threading
import time
import uuid
import urllib.request
from pathlib import Path

import torch
from flask import Flask, Response, jsonify, render_template_string, request, send_from_directory

from models import GetRequest, GetResponse, PostRequestSpec, PostResponse
logger = logging.getLogger(__name__)

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = None

SERVICEHANDLER_HASH = None

_AI_ENABLED = True

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

_DISKIDENTIFIER_PORT: int | None = None

_CONFIG_CACHE: dict | None = None
_LOCAL_ADDRESSES_CACHE: set[str] | None = None
_UI_PAGE_CACHE: dict[str, str] = {}

# Runtime path storage
_checked_path: str | None = None
_checked_recursive: bool = True

# Search index (runtime)
_SEARCH_INDEX: dict[str, list[dict[str, float]]] = {}
_SEARCH_INDEX_REVERSE: dict[str, dict[float, str]] = {}
_SEARCH_INDEX_LOCK = threading.Lock()
_INDEXED_IMAGES: dict[str, str] = {}  # ultimate_path -> raw_path

# Search progress (for SSE streaming)
_SEARCH_PROGRESS: dict[str, dict] = {}
_SEARCH_PROGRESS_LOCK = threading.Lock()
_SEARCH_IN_PROGRESS = False
_SEARCH_CANCELLED: set[str] = set()

# CLIP model (lazy loaded via openai/clip)
_clip_model = None
_clip_preprocess = None
_clip_device = "cpu"


# ============================================================================
# HTTP REQUEST HELPERS
# ============================================================================


def _send_post_request(spec: PostRequestSpec) -> PostResponse:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        spec.url.strip(),
        data=spec.body,
        headers=dict(spec.headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=spec.timeout) as resp:
            body = resp.read().decode("utf-8")
            json_body = json.loads(body) if body else None
            return PostResponse(
                status_code=resp.status,
                reason=resp.reason,
                body=body,
                body_size=len(body),
                headers=dict(resp.headers),
                json_body=json_body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        json_body = json.loads(body) if body else None
        return PostResponse(
            status_code=exc.code,
            reason=exc.reason,
            body=body,
            body_size=len(body),
            headers=dict(exc.headers),
            json_body=json_body,
        )


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def _check_diskidentifier_health(port: int | None = None) -> bool:
    if port is None:
        config = _load_configuration()
        port = config.get("diskidentifierPort", 49157)
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _path_has_images(path: str, recursive: bool) -> bool:
    if recursive:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[1].lower() in _IMAGE_EXTENSIONS:
                    return True
    else:
        try:
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                if os.path.isfile(full):
                    if os.path.splitext(entry)[1].lower() in _IMAGE_EXTENSIONS:
                        return True
        except PermissionError:
            return False
    return False


def _open_image_files(path: str, recursive: bool) -> None:
    global _INDEXED_IMAGES
    _INDEXED_IMAGES.clear()
    raw_paths: list[str] = []
    if recursive:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[1].lower() not in _IMAGE_EXTENSIONS:
                    continue
                full = os.path.join(root, f)
                try:
                    with open(full, "rb") as fh:
                        fh.read(1)
                    raw_paths.append(os.path.realpath(full))
                except Exception:
                    pass
    else:
        for entry in os.listdir(path):
            full = os.path.join(path, entry)
            if not os.path.isfile(full):
                continue
            if os.path.splitext(entry)[1].lower() not in _IMAGE_EXTENSIONS:
                continue
            try:
                with open(full, "rb") as fh:
                    fh.read(1)
                raw_paths.append(os.path.realpath(full))
            except Exception:
                pass

    for rp in raw_paths:
        ultimate = _to_ultimate_path(rp)
        if ultimate:
            _INDEXED_IMAGES[ultimate] = rp
        else:
            _INDEXED_IMAGES[rp] = rp


# ============================================================================
# SEARCH INDEX (JSON) HELPERS
# ============================================================================


def _forward_index_path() -> str:
    return os.path.realpath(os.path.join(Path(__file__).resolve().parent.parent, "resources", "search_index.json"))


def _reverse_index_path() -> str:
    return os.path.realpath(os.path.join(Path(__file__).resolve().parent.parent, "resources", "search_index_reverse.json"))


def _load_search_index() -> tuple[dict[str, list[dict[str, float]]], dict[str, dict[float, str]]]:
    global _SEARCH_INDEX, _SEARCH_INDEX_REVERSE
    fwd_file = _forward_index_path()
    rev_file = _reverse_index_path()

    logger.info(f"Loading forward index from {fwd_file}")
    raw_forward = {}
    if os.path.exists(fwd_file):
        try:
            raw_forward = json.loads(Path(fwd_file).read_text(encoding="utf-8").strip() or "{}")
        except Exception as exc:
            logger.warning(f"Failed to read forward index: {exc}")

    logger.info(f"Loading reverse index from {rev_file}")
    raw_reverse = {}
    if os.path.exists(rev_file):
        try:
            raw_reverse = json.loads(Path(rev_file).read_text(encoding="utf-8").strip() or "{}")
        except Exception as exc:
            logger.warning(f"Failed to read reverse index: {exc}")

    logger.debug("Parsing forward index entries")
    with _SEARCH_INDEX_LOCK:
        _SEARCH_INDEX = {}
        _SEARCH_INDEX_REVERSE = {}
        for path_key, entries in raw_forward.items():
            if isinstance(entries, list):
                cleaned = []
                for e in entries:
                    if isinstance(e, dict):
                        cleaned.append(e)
                _SEARCH_INDEX[path_key] = cleaned
        for query_key, score_map in raw_reverse.items():
            if isinstance(score_map, dict):
                parsed = {}
                for score_str, path_val in score_map.items():
                    try:
                        parsed[float(score_str)] = str(path_val)
                    except (ValueError, TypeError):
                        continue
                _SEARCH_INDEX_REVERSE[query_key] = parsed

    logger.info(
        f"Loaded {len(_SEARCH_INDEX)} forward paths, {len(_SEARCH_INDEX_REVERSE)} reverse queries"
    )
    return _SEARCH_INDEX, _SEARCH_INDEX_REVERSE


def _save_search_index() -> None:
    fwd_file = _forward_index_path()
    rev_file = _reverse_index_path()
    logger.info(f"Saving forward index to {fwd_file}, reverse to {rev_file}")

    # Merge forward index with persisted
    persisted_forward: dict = {}
    if os.path.exists(fwd_file):
        try:
            persisted_forward = json.loads(Path(fwd_file).read_text(encoding="utf-8").strip() or "{}")
        except Exception:
            persisted_forward = {}
    if not isinstance(persisted_forward, dict):
        persisted_forward = {}

    with _SEARCH_INDEX_LOCK:
        merged_forward = dict(persisted_forward)
        for path_key, runtime_entries in _SEARCH_INDEX.items():
            if path_key not in merged_forward:
                merged_forward[path_key] = []
            for entry in runtime_entries:
                if isinstance(entry, dict):
                    for q in entry:
                        exists = any(q in e for e in merged_forward[path_key])
                        if not exists:
                            merged_forward[path_key].append(entry)
        fwd_count = len(merged_forward)

        # Rebuild reverse from merged forward
        merged_reverse = {}
        for path_key, entries in merged_forward.items():
            for entry in entries:
                if isinstance(entry, dict):
                    for q, s in entry.items():
                        merged_reverse.setdefault(q, {})[str(s)] = path_key
        rev_count = len(merged_reverse)

    # Write forward
    fwd_text = json.dumps(merged_forward, indent=2, ensure_ascii=False)
    try:
        if os.path.exists(fwd_file):
            if Path(fwd_file).read_text(encoding="utf-8") == fwd_text:
                logger.info("Forward index unchanged, skipping write")
            else:
                Path(fwd_file).write_text(fwd_text, encoding="utf-8")
                logger.info(f"Forward index written ({fwd_count} paths)")
        else:
            Path(fwd_file).write_text(fwd_text, encoding="utf-8")
            logger.info(f"Forward index written ({fwd_count} paths)")
    except Exception as exc:
        logger.error(f"Failed to write forward index: {exc}")

    # Write reverse
    rev_text = json.dumps(merged_reverse, indent=2, ensure_ascii=False)
    try:
        if os.path.exists(rev_file):
            if Path(rev_file).read_text(encoding="utf-8") == rev_text:
                logger.info("Reverse index unchanged, skipping write")
            else:
                Path(rev_file).write_text(rev_text, encoding="utf-8")
                logger.info(f"Reverse index written ({rev_count} queries)")
        else:
            Path(rev_file).write_text(rev_text, encoding="utf-8")
            logger.info(f"Reverse index written ({rev_count} queries)")
    except Exception as exc:
        logger.error(f"Failed to write reverse index: {exc}")


def _load_and_filter_index(confirmed_path: str) -> dict[str, list[dict[str, float]]]:
    """Load search_index.json and return only entries whose absolute path
    starts with *confirmed_path* (the directory the user accepted).
    Rebuilds the reverse index from the loaded forward index."""
    logger.info(f"Loading and filtering index for path: {confirmed_path}")
    _load_search_index()
    resolved = os.path.realpath(confirmed_path)
    filtered = {}
    with _SEARCH_INDEX_LOCK:
        for path_key, entries in list(_SEARCH_INDEX.items()):
            raw = _from_ultimate_path(path_key)
            if raw and os.path.exists(raw) and os.path.realpath(raw).startswith(resolved):
                filtered[path_key] = entries
            else:
                _SEARCH_INDEX.pop(path_key, None)
        _SEARCH_INDEX_REVERSE.clear()
        for path_key, entries in _SEARCH_INDEX.items():
            for entry in entries:
                if isinstance(entry, dict):
                    for q, s in entry.items():
                        _SEARCH_INDEX_REVERSE.setdefault(q, {})[s] = path_key
    logger.info(f"Filtered index: {len(filtered)} kept, reverse index has {len(_SEARCH_INDEX_REVERSE)} queries")
    return filtered


def _lazy_load_clip():
    global _clip_model, _clip_preprocess, _clip_device
    if _clip_model is not None:
        return
    import clip
    _clip_device = "cuda" if torch.cuda.is_available() else "cpu"
    _clip_model, _clip_preprocess = clip.load("ViT-B/32", device=_clip_device)


# ============================================================================
# ULTIMATE PATH (DISKIDENTIFIER) HELPERS
# ============================================================================


def _extract_disk_root(raw_path: str) -> str:
    r"""Extract the disk root (e.g. C:\) from an absolute path."""
    path = Path(raw_path)
    drive = path.drive  # e.g. "C:"
    if drive:
        return drive + "\\"
    return "/"


def _to_ultimate_path(raw_path: str) -> str | None:
    """Resolve a raw absolute path to its ultimate form via DiskIdentifier.
    Returns '<disk_identifier>::<relative_posix_path>' or None on failure."""
    raw_real = os.path.realpath(raw_path)
    disk_root = _extract_disk_root(raw_real)
    port = _DISKIDENTIFIER_PORT
    if port is None:
        logger.error("DiskIdentifier not available, cannot resolve ultimate path")
        return None
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/whoisit/disk",
            data=json.dumps({"path": disk_root}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        disk_id = data.get("disk_identifier")
        if not isinstance(disk_id, str) or not disk_id.strip():
            return None
        rel = Path(raw_real).relative_to(disk_root).as_posix()
        return f"{disk_id}::{rel}"
    except Exception as exc:
        logger.warning(f"Failed to resolve ultimate path: {exc}")
        return None


def _from_ultimate_path(ultimate_path: str) -> str | None:
    """Resolve an ultimate path '<disk_id>::<relative_path>' back to a
    raw absolute filesystem path via DiskIdentifier."""
    port = _DISKIDENTIFIER_PORT
    if port is None:
        logger.error("DiskIdentifier not available, cannot resolve ultimate path")
        return None
    try:
        disk_id, rel = ultimate_path.split("::", 1)
    except ValueError:
        return None
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/locate/disk",
            data=json.dumps({"disk_identifier": disk_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        disk_root = data.get("path")
        if not isinstance(disk_root, str):
            return None
        return os.path.realpath(os.path.join(disk_root, rel))
    except Exception as exc:
        logger.warning(f"Failed to resolve ultimate path: {exc}")
        return None


# ============================================================================
# CONFIGURATION LOADING
# ============================================================================


def _load_configuration() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "resources" / "configuration.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            "Ensure resources/configuration.json exists."
        )

    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Configuration file at {config_path} contains invalid JSON: {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read configuration file at {config_path}: {exc}"
        ) from exc

    _CONFIG_CACHE = config
    return config


def _initialize_service_config() -> None:
    global SERVICE_PORT, _AI_ENABLED
    config = _load_configuration()

    configured_port = config.get("port", 49160)

    if isinstance(configured_port, str) and configured_port.isdigit():
        configured_port = int(configured_port)
    if not isinstance(configured_port, int):
        configured_port = 49160

    SERVICE_PORT = configured_port

    _AI_ENABLED = config.get("aiEnabled", True)


# ============================================================================
# LOCAL DEVICE ACCESS CONTROL
# ============================================================================


def _get_local_device_addresses() -> set[str]:
    global _LOCAL_ADDRESSES_CACHE
    if _LOCAL_ADDRESSES_CACHE is not None:
        return _LOCAL_ADDRESSES_CACHE

    local_addresses: set[str] = set()

    for candidate_name in {socket.gethostname(), socket.getfqdn()}:
        if not candidate_name:
            continue

        try:
            local_addresses.update(
                address_info[4][0]
                for address_info in socket.getaddrinfo(candidate_name, None)
            )
        except OSError:
            pass

        try:
            local_addresses.update(socket.gethostbyname_ex(candidate_name)[2])
        except OSError:
            pass

    normalized_addresses: set[str] = set()
    for address_value in local_addresses:
        try:
            normalized_addresses.add(ipaddress.ip_address(address_value).compressed)
        except ValueError:
            continue

    normalized_addresses.update({"127.0.0.1", "::1"})
    _LOCAL_ADDRESSES_CACHE = normalized_addresses
    return normalized_addresses


def _is_local_request() -> bool:
    remote_address = request.remote_addr
    if not isinstance(remote_address, str) or not remote_address.strip():
        return False

    try:
        client_ip = ipaddress.ip_address(remote_address.strip())
    except ValueError:
        return False

    if client_ip.is_loopback:
        return True

    return client_ip.compressed in _get_local_device_addresses()


# ============================================================================
# FLASK APP
# ============================================================================


app = Flask(__name__)


@app.before_request
def restrict_to_local_device() -> tuple | None:
    if request.path.startswith("/api/") and not _is_local_request():
        return jsonify({"error": "Local device access only."}), 403
    return None


@app.after_request
def set_connection_header(response):
    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("text/html"):
        response.headers["Connection"] = "keep-alive"
    else:
        response.headers["Connection"] = "close"
    return response


def _options_response(allowed_methods: list[str]) -> tuple:
    response = jsonify({})
    response.headers["Allow"] = ", ".join(allowed_methods)
    response.headers["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response, 200


def _head_response() -> tuple:
    response = jsonify({})
    return response, 200


# ============================================================================
# UI ROUTES
# ============================================================================


def _load_ui_page(filename: str) -> str:
    search_base = Path(__file__).resolve()
    for level in range(1, 6):
        try:
            root = search_base.parents[level]
        except Exception:
            continue
        candidate = root / "ui" / "pages" / filename
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except Exception:
                continue

    fallback = f"<html><body><h1>UI file '{filename}' not found.</h1></body></html>"
    return fallback


def index() -> str:
    if request.method == "OPTIONS":
        return _options_response(["GET", "HEAD", "OPTIONS"])
    if request.method == "HEAD":
        return _head_response()
    content = _load_ui_page("index.html")
    extra = ""
    if not _AI_ENABLED:
        extra += 'window._AI_ENABLED = false;\n'
    if _DISKIDENTIFIER_PORT is None:
        extra += 'window._DISKIDENTIFIER_ERROR = "DiskIdentifier could not be found.";\n'
    if extra:
        content = content.replace(
            "<script>",
            f"<script>{extra}",
            1,
        )
    return render_template_string(content)


def ui_css(filename: str):
    if request.method == "OPTIONS":
        return _options_response(["GET", "HEAD", "OPTIONS"])
    if request.method == "HEAD":
        return _head_response()
    css_dir = Path(__file__).resolve().parent.parent / "ui" / "css"
    return send_from_directory(css_dir, filename)


# ============================================================================
# RESPONSE HELPERS
# ============================================================================


def _json_response(data: dict, status_code: int = 200, reason: str = "OK") -> tuple:
    body = json.dumps(data)
    resp = PostResponse(
        status_code=status_code,
        reason=reason,
        body=body,
        body_size=len(body),
        headers={"Content-Type": "application/json"},
        json_body=data,
    )
    return jsonify(resp.json_body), resp.status_code


def _error_response(message: str, status_code: int = 400) -> tuple:
    return _json_response({"error": message}, status_code=status_code, reason="error")


def _success_response(data: dict, status_code: int = 200) -> tuple:
    return _json_response(data, status_code=status_code, reason="OK")


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.route("/api/health", methods=["GET", "HEAD", "OPTIONS"])
def health() -> tuple:
    if request.method == "OPTIONS":
        return _options_response(["GET", "HEAD", "OPTIONS"])
    if request.method == "HEAD":
        return _head_response()

    return _success_response(
        {
            "status": "ok",
            "service": "GalleryCleaner",
            "bind_address": SERVICE_HOST,
            "port": SERVICE_PORT,
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
        }
    )


@app.route("/api/check/path", methods=["POST", "OPTIONS"])
def check_path() -> tuple:
    global _checked_path, _checked_recursive

    if request.method == "OPTIONS":
        return _options_response(["POST", "OPTIONS"])

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("Invalid JSON body.", 400)

    path = data.get("path", "")
    if not isinstance(path, str) or not path.strip():
        return _error_response("Path is required.", 400)

    path = path.strip()
    recursive = bool(data.get("recursive", True))

    if not os.path.exists(path):
        return _error_response("The specified path does not exist or is not accessible.", 404)

    if not os.path.isdir(path):
        return _error_response("The specified path does not exist or is not accessible.", 400)

    if not _path_has_images(path, recursive):
        return _error_response("The selected directory does not contain any image files.", 400)

    if _AI_ENABLED:
        if _DISKIDENTIFIER_PORT is None:
            return _error_response("DiskIdentifier is required but not available.", 503)

        _open_image_files(path, recursive)

        _load_and_filter_index(path)
    else:
        _INDEXED_IMAGES.clear()

    _checked_path = path
    _checked_recursive = recursive

    return _success_response(
        {
            "path": _checked_path,
            "recursive": _checked_recursive,
            "indexed": len(_INDEXED_IMAGES) if _AI_ENABLED else 0,
            "status": "confirmed",
            "ai_enabled": _AI_ENABLED,
        }
    )


@app.route("/api/search", methods=["POST", "OPTIONS"])
def search() -> tuple:
    if request.method == "OPTIONS":
        return _options_response(["POST", "OPTIONS"])

    if not _AI_ENABLED:
        return _error_response("AI operations are disabled.", 503)

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error_response("Invalid JSON body.", 400)

    query = data.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return _error_response("Query text is required.", 400)

    query = query.strip()

    if not query.isalnum():
        return _error_response("Query must contain only letters and numbers.", 400)

    if not _INDEXED_IMAGES:
        return _error_response("No indexed images. Select a path first.", 400)

    global _SEARCH_IN_PROGRESS
    if _SEARCH_IN_PROGRESS:
        return _error_response("A search is already running.", 429)

    search_id = str(uuid.uuid4())

    with _SEARCH_PROGRESS_LOCK:
        _SEARCH_PROGRESS[search_id] = {
            "status": "queued",
            "query": query,
            "phase": "",
            "filtered_out": 0,
            "total_images": len(_INDEXED_IMAGES),
            "to_process": 0,
            "processed": 0,
            "failed": 0,
            "workers": 0,
            "total_workers": 0,
            "platoons": 0,
            "current_platoon": 0,
            "total_platoons": 0,
            "results": None,
            "error": None,
        }

    _SEARCH_IN_PROGRESS = True
    thread = threading.Thread(
        target=_run_search,
        args=(search_id, query),
        name=f"search-{search_id[:8]}",
        daemon=True,
    )
    thread.start()

    return _success_response({"search_id": search_id})


def _update_progress(search_id: str, **kwargs) -> None:
    with _SEARCH_PROGRESS_LOCK:
        if search_id in _SEARCH_PROGRESS:
            _SEARCH_PROGRESS[search_id].update(kwargs)


def _run_search(search_id: str, query: str) -> None:
    """Run the full search pipeline in a background thread, updating progress."""
    global _SEARCH_IN_PROGRESS
    from PIL import Image

    try:
        # ---------------------------------------------------------------
        # 1. Filtering out
        # ---------------------------------------------------------------
        _update_progress(search_id, status="running", phase="filtering")
        images_to_process: list[str] = []
        cached_results: list[dict] = []

        with _SEARCH_INDEX_LOCK:
            for ultimate_path, raw_path in _INDEXED_IMAGES.items():
                entries = _SEARCH_INDEX.get(ultimate_path, [])
                found = False
                for entry in entries:
                    if isinstance(entry, dict) and query in entry:
                        cached_results.append({"path": ultimate_path, "score": entry[query], "_raw": raw_path})
                        found = True
                        break
                if not found:
                    images_to_process.append(raw_path)

        filtered_out = len(cached_results)
        _update_progress(
            search_id,
            phase="filtered",
            filtered_out=filtered_out,
            to_process=len(images_to_process),
        )

        logger.info(
            f"Search '{query}': {filtered_out} cached, "
            f"{len(images_to_process)} to process out of {len(_INDEXED_IMAGES)} total"
        )

        if not images_to_process:
            cached_results.sort(key=lambda r: r["score"], reverse=True)
            with _SEARCH_PROGRESS_LOCK:
                if search_id in _SEARCH_PROGRESS:
                    _SEARCH_PROGRESS[search_id].update(
                        status="complete",
                        phase="done",
                        results={
                            "query": query,
                            "results": cached_results[:50],
                            "total": len(cached_results),
                            "filtered_out": filtered_out,
                            "workers": 0,
                            "platoons": 0,
                        },
                    )
            _SEARCH_IN_PROGRESS = False
            return

        # ---------------------------------------------------------------
        # 2. Lazy-load CLIP model and compute shared text features
        # ---------------------------------------------------------------
        _update_progress(search_id, phase="loading_model")
        try:
            _lazy_load_clip()
        except Exception as exc:
            logger.error(f"Failed to load CLIP model: {exc}")
            with _SEARCH_PROGRESS_LOCK:
                if search_id in _SEARCH_PROGRESS:
                    _SEARCH_PROGRESS[search_id].update(
                        status="error", error=str(exc)
                    )
            _SEARCH_IN_PROGRESS = False
            return

        logger.info("CLIP model loaded, computing text features...")
        import clip
        text_tokens = clip.tokenize([query]).to(_clip_device)
        with torch.no_grad():
            text_features = _clip_model.encode_text(text_tokens)

        _update_progress(search_id, phase="assigning_workers")

        # ---------------------------------------------------------------
        # 3. Assign images to workers (max N MB per worker)
        # ---------------------------------------------------------------
        cfg = _load_configuration()
        MAX_WORKER_MB = cfg.get("maxWorkerMB", 50)
        MAX_WORKER_BYTES = MAX_WORKER_MB * 1024 * 1024
        workers: list[list[str]] = []
        current_worker: list[str] = []
        current_size = 0

        for img_path in images_to_process:
            try:
                fsize = os.path.getsize(img_path)
            except OSError:
                logger.warning(f"Cannot get size of {img_path}, skipping")
                continue

            if fsize > MAX_WORKER_BYTES:
                if current_worker:
                    workers.append(current_worker)
                    current_worker = []
                    current_size = 0
                workers.append([img_path])
                continue

            if current_size + fsize > MAX_WORKER_BYTES:
                workers.append(current_worker)
                current_worker = []
                current_size = 0

            current_worker.append(img_path)
            current_size += fsize

        if current_worker:
            workers.append(current_worker)

        total_workers = len(workers)
        _update_progress(
            search_id,
            phase="workers_assigned",
            workers=0,
            total_workers=total_workers,
            processed=0,
        )

        logger.info(f"Assigned {len(images_to_process)} images to {total_workers} workers")

        if not workers:
            cached_results.sort(key=lambda r: r["score"], reverse=True)
            with _SEARCH_PROGRESS_LOCK:
                if search_id in _SEARCH_PROGRESS:
                    _SEARCH_PROGRESS[search_id].update(
                        status="complete",
                        phase="done",
                        results={
                            "query": query,
                            "results": cached_results[:50],
                            "total": len(cached_results),
                            "filtered_out": filtered_out,
                            "workers": 0,
                            "platoons": 0,
                        },
                    )
            _SEARCH_IN_PROGRESS = False
            return

        # ---------------------------------------------------------------
        # 4. Worker function
        # ---------------------------------------------------------------
        def _worker_process(
            worker_id: int, image_paths: list[str], t_features
        ) -> list[dict]:
            local_results: list[dict] = []
            for img_path in image_paths:
                try:
                    image_tensor = (
                        _clip_preprocess(Image.open(img_path).convert("RGB"))
                        .unsqueeze(0)
                        .to(_clip_device)
                    )
                    with torch.no_grad():
                        image_features = _clip_model.encode_image(image_tensor)
                    t_feat = t_features / t_features.norm(dim=-1, keepdim=True)
                    i_feat = image_features / image_features.norm(dim=-1, keepdim=True)
                    cos = (t_feat @ i_feat.T).item()
                    score = round(float(cos), 4)
                    local_results.append({"path": img_path, "score": score})
                except Exception as exc:
                    logger.warning(f"Worker {worker_id}: failed on {img_path}: {exc}")
                    continue
            logger.info(f"Worker {worker_id}: processed {len(local_results)}/{len(image_paths)} images")
            return local_results

        # ---------------------------------------------------------------
        # 5. Split workers into platoons and execute sequentially
        # ---------------------------------------------------------------
        MAX_WORKERS_PER_PLATOON = cfg.get("maxWorkersPerPlatoon", 15)
        platoons = [
            workers[i : i + MAX_WORKERS_PER_PLATOON]
            for i in range(0, len(workers), MAX_WORKERS_PER_PLATOON)
        ]
        total_platoons = len(platoons)
        _update_progress(
            search_id,
            phase="processing",
            platoons=total_platoons,
            total_platoons=total_platoons,
            current_platoon=0,
        )

        logger.info(f"Split {total_workers} workers into {total_platoons} platoons")

        new_results: list[dict] = []
        for platoon_idx, platoon in enumerate(platoons, start=1):
            if search_id in _SEARCH_CANCELLED:
                logger.info(f"Search '{query}' cancelled before platoon {platoon_idx}")
                break
            _update_progress(
                search_id,
                current_platoon=platoon_idx,
                phase=f"platoon_{platoon_idx}_of_{total_platoons}",
                workers=0,
            )
            logger.info(f"Starting platoon {platoon_idx}/{total_platoons} with {len(platoon)} workers")
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(platoon)
            ) as executor:
                fut_to_wid = {}
                for wid, batch in enumerate(platoon, start=1):
                    fut = executor.submit(
                        _worker_process, wid, batch, text_features
                    )
                    fut_to_wid[fut] = wid

                for fut in concurrent.futures.as_completed(fut_to_wid):
                    try:
                        batch_results = fut.result()
                        new_results.extend(batch_results)
                        done = len(new_results)
                        _update_progress(
                            search_id,
                            processed=done,
                            workers=done,
                        )
                    except Exception as exc:
                        logger.warning(f"Worker in platoon {platoon_idx} failed: {exc}")
                        _update_progress(search_id, failed=_SEARCH_PROGRESS.get(search_id, {}).get("failed", 0) + 1)
                        continue
            logger.info(f"Platoon {platoon_idx} finished, {len(new_results)} total new results so far")

        # ---------------------------------------------------------------
        # 6. Persist new results
        # ---------------------------------------------------------------
        if search_id not in _SEARCH_CANCELLED:
            _update_progress(search_id, phase="persisting")
            raw_to_ultimate = {raw: ult for ult, raw in _INDEXED_IMAGES.items()}
            logger.info(f"Persisting {len(new_results)} new results for query '{query}'")
            with _SEARCH_INDEX_LOCK:
                for r in new_results:
                    raw_path = r["path"]
                    ultimate_path = raw_to_ultimate.get(raw_path, raw_path)
                    if ultimate_path not in _SEARCH_INDEX:
                        _SEARCH_INDEX[ultimate_path] = []
                    _SEARCH_INDEX[ultimate_path].append({query: r["score"]})
                    _SEARCH_INDEX_REVERSE.setdefault(query, {})[r["score"]] = ultimate_path
                fwd_count = len(_SEARCH_INDEX)
                rev_count = len(_SEARCH_INDEX_REVERSE)

            logger.info(f"Indices updated: forward={fwd_count} paths, reverse={rev_count} queries")
            _save_search_index()

        # ---------------------------------------------------------------
        # 7. Combine and return
        # ---------------------------------------------------------------
        all_results = cached_results + new_results
        all_results.sort(key=lambda r: r["score"], reverse=True)

        final_results = {
            "query": query,
            "results": all_results[:50],
            "total": len(all_results),
            "filtered_out": filtered_out,
            "workers": total_workers,
            "platoons": total_platoons,
        }

        if search_id in _SEARCH_CANCELLED:
            with _SEARCH_PROGRESS_LOCK:
                if search_id in _SEARCH_PROGRESS:
                    _SEARCH_PROGRESS[search_id].update(
                        status="cancelled",
                        phase="done",
                        results=final_results,
                    )
            logger.info(f"Search '{query}' cancelled with {len(all_results)} interim results")
        else:
            with _SEARCH_PROGRESS_LOCK:
                if search_id in _SEARCH_PROGRESS:
                    _SEARCH_PROGRESS[search_id].update(
                        status="complete",
                        phase="done",
                        results=final_results,
                    )
            logger.info(f"Search '{query}' complete: {len(all_results)} results")
    except Exception as exc:
        logger.error(f"Search '{query}' failed: {exc}")
        with _SEARCH_PROGRESS_LOCK:
            if search_id in _SEARCH_PROGRESS:
                _SEARCH_PROGRESS[search_id].update(
                    status="error", error=str(exc)
                )
    finally:
        _SEARCH_CANCELLED.discard(search_id)
        _SEARCH_IN_PROGRESS = False


@app.route("/api/search/progress/<search_id>", methods=["GET"])
def search_progress(search_id: str) -> Response:
    if not _AI_ENABLED:
        return _error_response("AI operations are disabled.", 503)

    def generate():
        while True:
            with _SEARCH_PROGRESS_LOCK:
                progress = _SEARCH_PROGRESS.get(search_id, {})
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            status = progress.get("status")
            if status in ("complete", "error", "cancelled") or not progress:
                break
            time.sleep(0.5)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/search/cancel/<search_id>", methods=["POST", "OPTIONS"])
def search_cancel(search_id: str) -> tuple:
    if request.method == "OPTIONS":
        return _options_response(["POST", "OPTIONS"])
    if not _AI_ENABLED:
        return _error_response("AI operations are disabled.", 503)
    with _SEARCH_PROGRESS_LOCK:
        if search_id not in _SEARCH_PROGRESS:
            return _error_response("Search not found.", 404)
        _SEARCH_CANCELLED.add(search_id)
    logger.info(f"Search '{search_id[:8]}...' cancellation requested")
    return _success_response({"status": "cancelling"})


# ============================================================================
# STARTUP VALIDATION
# ============================================================================


def _resolve_diskidentifier_port() -> int | None:
    global _DISKIDENTIFIER_PORT

    config = _load_configuration()
    candidate = config.get("diskidentifierPort")
    logger.debug(f"Checking DiskIdentifier port candidate: {candidate}")
    if isinstance(candidate, (int, str)):
        try:
            port = int(candidate)
            if _check_diskidentifier_health(port):
                _DISKIDENTIFIER_PORT = port
                logger.info(f"DiskIdentifier found on port {port} (via config)")
                return port
        except (ValueError, TypeError):
            pass

    sh_port = config.get("servicehandlerPort", 49155)
    try:
        spec = PostRequestSpec(
            url=f"http://127.0.0.1:{sh_port}/api/question/service",
            body=json.dumps({"name": "DiskIdentifier"}).encode("utf-8"),
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        resp = _send_post_request(spec)
        if resp.status_code == 200 and resp.json_body:
            port = resp.json_body.get("port")
            if isinstance(port, int) and _check_diskidentifier_health(port):
                _DISKIDENTIFIER_PORT = port
                logger.info(f"DiskIdentifier found on port {port} (via ServiceHandler)")
                return port
    except Exception as exc:
        logger.warning(f"Failed to query ServiceHandler for DiskIdentifier port: {exc}")

    logger.error("DiskIdentifier is not available.")
    return None


def _diskidentifier_keepalive_forever() -> None:
    """Keep trying to find DiskIdentifier every 15 seconds."""
    global _DISKIDENTIFIER_PORT
    config = _load_configuration()
    while True:
        time.sleep(15)
        if _check_diskidentifier_health(_DISKIDENTIFIER_PORT):
            continue
        _DISKIDENTIFIER_PORT = _resolve_diskidentifier_port()


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================


def _register_endpoints_with_servicehandler() -> None:
    global SERVICEHANDLER_HASH
    if not SERVICEHANDLER_HASH:
        return

    config = _load_configuration()
    sh_port = config.get("servicehandlerPort", 49155)

    endpoints = [
        {
            "verb": "GET",
            "path": "/api/health",
            "path_variables": [],
            "body_schema": {},
            "description": "Service health check.",
        },
        {
            "verb": "POST",
            "path": "/api/check/path",
            "path_variables": [],
            "body_schema": {"path": "string", "recursive": "boolean"},
            "description": "Check an image directory path for validity.",
        },
        {
            "verb": "POST",
            "path": "/api/search",
            "path_variables": [],
            "body_schema": {"query": "string"},
            "description": "Search indexed images using CLIP text query.",
        },
        {
            "verb": "GET",
            "path": "/api/search/progress/<search_id>",
            "path_variables": ["search_id"],
            "body_schema": {},
            "description": "SSE stream of search progress.",
        },
    ]

    for ep in endpoints:
        try:
            spec = PostRequestSpec(
                url=f"http://127.0.0.1:{sh_port}/api/register/endpoint",
                body=json.dumps({"hash": SERVICEHANDLER_HASH, **ep}).encode("utf-8"),
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            resp = _send_post_request(spec)
            if resp.status_code == 201:
                logger.info(f"Registered endpoint: {ep['verb']} {ep['path']}")
            elif resp.status_code == 409:
                logger.debug(f"Endpoint already registered: {ep['verb']} {ep['path']}")
            else:
                logger.warning(
                    f"Failed to register endpoint {ep['verb']} {ep['path']} "
                    f"(HTTP {resp.status_code})"
                )
        except Exception as exc:
            logger.warning(
                f"Failed to register endpoint {ep['verb']} {ep['path']}: {exc}"
            )


def _servicehandler_keepalive_forever() -> None:
    global SERVICEHANDLER_HASH
    config = _load_configuration()
    sh_port = config.get("servicehandlerPort", 49155)
    service_name = "GalleryCleaner"

    while True:
        time.sleep(15)
        try:
            spec = PostRequestSpec(
                url=f"http://127.0.0.1:{sh_port}/api/question/service",
                body=json.dumps({"name": service_name}).encode("utf-8"),
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            resp = _send_post_request(spec)
            if resp.status_code == 200:
                if not SERVICEHANDLER_HASH:
                    data = json.loads(resp.body)
                    SERVICEHANDLER_HASH = data.get("hash")
                continue
            if resp.status_code != 404:
                logger.warning(
                    f"ServiceHandler question failed (HTTP {resp.status_code})"
                )
                continue
        except Exception as exc:
            logger.warning(f"ServiceHandler question failed: {exc}")
            continue

        try:
            spec = PostRequestSpec(
                url=f"http://127.0.0.1:{sh_port}/api/register/service",
                body=json.dumps(
                    {
                        "name": service_name,
                        "port": SERVICE_PORT,
                        "starting_script": str(
                            Path(__file__).resolve().parent.parent
                            / "scripts"
                            / ("run.bat" if os.name == "nt" else "run.sh")
                        ),
                        "bind_address": SERVICE_HOST,
                        "hostname": socket.gethostname(),
                    }
                ).encode("utf-8"),
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            resp = _send_post_request(spec)
            if resp.status_code == 201:
                data = json.loads(resp.body)
                SERVICEHANDLER_HASH = data.get("hash")
                logger.info(
                    f"Registered with ServiceHandler, hash={SERVICEHANDLER_HASH[:16]}..."
                )
                if SERVICEHANDLER_HASH:
                    _register_endpoints_with_servicehandler()
        except Exception as exc:
            logger.warning(f"ServiceHandler registration attempt failed: {exc}")


def _register_ui_routes(app_instance: Flask) -> None:
    app_instance.add_url_rule(
        "/", methods=["GET", "HEAD", "OPTIONS"], view_func=index
    )
    app_instance.add_url_rule(
        "/ui/css/<path:filename>",
        methods=["GET", "HEAD", "OPTIONS"],
        view_func=ui_css,
    )


if __name__ == "__main__":
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        _initialize_service_config()
        _register_ui_routes(app)

        if _AI_ENABLED:
            _resolve_diskidentifier_port()
    except Exception as exc:
        logger.error(f"Failed to load configuration: {exc}")
        exit(1)

    config = _load_configuration()
    if config.get("servicehandlerEnabled", True):
        servicehandler_thread = threading.Thread(
            target=_servicehandler_keepalive_forever,
            name="servicehandler-keepalive",
            daemon=True,
        )
        servicehandler_thread.start()

    if _AI_ENABLED:
        diskidentifier_thread = threading.Thread(
            target=_diskidentifier_keepalive_forever,
            name="diskidentifier-keepalive",
            daemon=True,
        )
        diskidentifier_thread.start()

    try:
        logger.info("=" * 50)
        mode_str = "AI" if _AI_ENABLED else "Non-AI"
        logger.info(f"  GalleryCleaner ({mode_str} mode)")
        logger.info("=" * 50)
        logger.info(f"Binding to: http://{SERVICE_HOST}:{SERVICE_PORT}")
        logger.info(f"Mode: private (local only)")
        if not _AI_ENABLED:
            logger.info("AI operations disabled via configuration")
        logger.info("Server starting...")

        app.run(host=SERVICE_HOST, port=SERVICE_PORT, debug=False, threaded=True)

    except OSError as exc:
        if "Address already in use" in str(exc):
            logger.error(
                f"Port {SERVICE_PORT} is already in use. "
                f"Change the port in configuration.json"
            )
        elif "Permission denied" in str(exc):
            logger.error(
                f"Permission denied to bind to port {SERVICE_PORT}. "
                f"Use a port >= 1024 or run with elevated privileges."
            )
        else:
            logger.error(f"Network binding failed: {exc}")

    except Exception as exc:
        logger.error(f"Server startup failed: {exc}")
