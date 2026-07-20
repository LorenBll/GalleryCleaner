# Security Policy

## Supported Versions

Only the latest released version receives security updates.

| Version | Supported |
| ------- | --------- |
| Latest  | Yes       |

## Reporting a Vulnerability

If you believe you have found a security issue in GalleryCleaner, please report it privately to the maintainers rather than opening a public issue.

GalleryCleaner is a local image search service that involves:
- **File system access** — reading user-provided directory paths and recursively scanning for image files
- **Image processing** — opening, decoding, and transforming images via Pillow from untrusted file content
- **CLIP model inference** — running PyTorch and OpenAI's CLIP model for semantic image search
- **Localhost API communication** — communicating with DiskIdentifier and ServiceHandler services on localhost
- **JSON index persistence** — reading and writing search indices to `resources/search_index.json`

Include as much detail as possible, such as:
- A clear description of the issue and the affected endpoint or component
- Steps to reproduce the problem (directory paths, image files, application state)
- Any relevant logs or error messages
- Your environment details (operating system, Python version, dependency versions)
- The potential impact and how severe you believe it is

If the report involves file paths, image data, or configuration values, redact sensitive information before sharing.

## What To Expect

After a report is received:

1. The issue will be reviewed and triaged.
2. You may be contacted for clarification or additional details.
3. A fix may be developed and validated before public disclosure.
4. The reporter may be credited unless they prefer to remain anonymous.

## Security Guidelines

This project is intended to follow basic security hygiene:

- **GalleryCleaner binds to `127.0.0.1`** by default (port 49160). The before-request hook rejects non-local traffic. Do not change the bind address to `0.0.0.0` without additional network-layer protections.
- **Local file access** — GalleryCleaner only accesses directories and files that the user explicitly provides. The application validates directory existence before scanning. Recursive scanning is opt-in.
- **Image file handling** — Supported image formats are restricted to common types. Unreadable or unsupported images fail gracefully without crashing the application. Keep Pillow updated to the latest version, as its format parsers have historically contained vulnerabilities.
- **CLIP model execution** — The CLIP model (ViT-B/32) is loaded from the official OpenAI repository and executed locally on either CPU or GPU. No image data or query text is transmitted to external servers.
- **Localhost API communication** — GalleryCleaner communicates with DiskIdentifier and ServiceHandler over the loopback interface only. No data is exposed to the network.
- **Configuration file** — Settings are stored in `resources/configuration.json` on the local filesystem and are not transmitted externally.
- **Dependency review** — Keep dependencies (Flask, torch, torchvision, Pillow, clip) updated to their latest stable versions. Review changelogs and CVEs before upgrading.

## Disclosure Notes

Do not publicly disclose an unpatched vulnerability until maintainers have had reasonable time to investigate and respond. If a coordinated disclosure timeline is needed, it can be discussed during the report process.
