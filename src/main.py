"""GalleryCleaner local web service."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import socket
import threading
import time
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, send_from_directory

from models import GetRequest, GetResponse, PostRequestSpec, PostResponse
logger = logging.getLogger(__name__)

SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = None

SERVICEHANDLER_HASH = None

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

_DISKIDENTIFIER_PORT: int | None = None

_CONFIG_CACHE: dict | None = None
_LOCAL_ADDRESSES_CACHE: set[str] | None = None
_UI_PAGE_CACHE: dict[str, str] = {}

# Runtime path storage
_checked_path: str | None = None
_checked_recursive: bool = True


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
    if recursive:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[1].lower() not in _IMAGE_EXTENSIONS:
                    continue
                try:
                    with open(os.path.join(root, f), "rb") as fh:
                        fh.read(1)
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
            except Exception:
                pass


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
    global SERVICE_PORT
    config = _load_configuration()

    configured_port = config.get("port", 49160)

    if isinstance(configured_port, str) and configured_port.isdigit():
        configured_port = int(configured_port)
    if not isinstance(configured_port, int):
        configured_port = 49160

    SERVICE_PORT = configured_port


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
    if _DISKIDENTIFIER_PORT is None:
        content = content.replace(
            "<script>",
            '<script>window._DISKIDENTIFIER_ERROR = "DiskIdentifier could not be found.";\n',
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

    _open_image_files(path, recursive)

    _checked_path = path
    _checked_recursive = recursive

    return _success_response(
        {
            "path": _checked_path,
            "recursive": _checked_recursive,
            "status": "confirmed",
        }
    )


# ============================================================================
# STARTUP VALIDATION
# ============================================================================


def _resolve_diskidentifier_port() -> int | None:
    global _DISKIDENTIFIER_PORT

    config = _load_configuration()
    candidate = config.get("diskidentifierPort")
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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        _initialize_service_config()
        _register_ui_routes(app)

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

    try:
        logger.info("=" * 50)
        logger.info("  Local API Server")
        logger.info("=" * 50)
        logger.info(f"Binding to: http://{SERVICE_HOST}:{SERVICE_PORT}")
        logger.info(f"Mode: private (local only)")
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
