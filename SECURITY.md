# Security Policy

## Supported Versions

Only the latest released version receives security updates.

| Version | Supported |
| ------- | --------- |
| Latest  | Yes       |

## Reporting a Vulnerability

If you believe you have found a security issue in GalleryCleaner, please report it privately to the maintainers rather than opening a public issue.

GalleryCleaner is a local desktop image review application that involves:
- **File system access** — reading user-provided directory paths and recursively scanning for image files
- **Image processing** — opening, decoding, and transforming images via Pillow from untrusted file content
- **Trash operations** — moving files to the system trash via send2trash, a privileged filesystem operation
- **Localhost API communication** — communicating with a DiskIdentifier API on localhost for ultimate path resolution
- **Persistent file writes** — overwriting image files on disk during rotation operations

Include as much detail as possible, such as:
- A clear description of the issue and the affected component
- Steps to reproduce the problem (directory paths, image files, application state)
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

- **Local file access** — GalleryCleaner only accesses directories and files that the user explicitly provides. The application validates directory existence and read/write/execute permissions before scanning. Recursive scanning is opt-in, and `desktop.ini` files are filtered out during directory listing.
- **Image file handling** — Supported image formats are restricted to common types. Unreadable or unsupported images fail gracefully without crashing the application. Keep Pillow updated to the latest version, as its format parsers have historically contained vulnerabilities.
- **Send2Trash safety** — Deletion uses send2trash, which moves files to the operating system's trash rather than permanently deleting them. This provides a recovery safety net. The application does not bypass OS-level trash confirmations.
- **Localhost API communication** — GalleryCleaner communicates with DiskIdentifier over the loopback interface only. No data is exposed to the network. Verify that no external process binds to the same port.
- **Configuration file** — Settings are stored in `configuration.json` on the local filesystem and are not transmitted externally.
- **Dependency review** — Keep dependencies (customtkinter, pillow, send2trash) updated to their latest stable versions. Review changelogs and CVEs before upgrading.

## Disclosure Notes

Do not publicly disclose an unpatched vulnerability until maintainers have had reasonable time to investigate and respond. If a coordinated disclosure timeline is needed, it can be discussed during the report process.
