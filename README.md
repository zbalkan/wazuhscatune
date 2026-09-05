# wazuhscatune

`wazuhscatune` is a local helper for tailoring a trusted Wazuh Security
Configuration Assessment (SCA) baseline. It runs a small local web interface so a
single user can review a policy in a browser. Every baseline check is retained
unless the reviewer records an explicit exception with a justification.

The review model distinguishes:

- **Unreviewed** — retained by default, but not yet explicitly reviewed.
- **Accepted** — reviewed and retained.
- **Exception** — reviewed, justified, and removed from the tailored policy.

## Alpha compatibility contract

Version `0.1.0` is the first public alpha. **Python 3.10 is the minimum supported
Python version.** Python 3.10, 3.11, 3.12, and 3.13 are tested on current Windows,
macOS, and Linux desktop environments. The minimum version is enforced by package
metadata and exercised by CI and release packaging. Support is revisited only when
a dependency, Python lifecycle change, or concrete user need requires it; versions
are not added or removed merely to track every new Python release.

The application is intended for one user on the local machine. It is not a web
service, server application, or multi-user application, and production deployment
is explicitly unsupported.

During the alpha series, persisted draft files and internal Python APIs may change
without compatibility guarantees. The distribution name is `wazuhscatune`; the
internal `sca` import package is an implementation detail and should not be used
as a public API.

## Installation

Install from the repository with Python 3.10 or newer:

```bash
python -m pip install .
```

For development and testing:

```bash
python -m pip install -e '.[dev]'
```

## Run

Start the helper with the installed command:

```bash
wazuhscatune
```

Alternatively, run the package module:

```bash
python -m sca.app
```

The helper always listens on `http://127.0.0.1:5000`, opens the local browser,
runs with Flask debug mode disabled, and disables the reloader. Flask's server
banner and Werkzeug request log are suppressed to keep terminal output minimal;
application diagnostics are written to a per-user log file instead.

The Flask server is only the local UI transport. Remote binding, production web
servers, reverse proxies, TLS termination, and shared access are outside the
supported use case.

## Workflow

1. Upload a structurally valid Wazuh SCA YAML baseline.
2. Name and describe the tailored policy.
3. Review checks as accepted or as justified exceptions.
4. Verify review completion and exception counts on the approval page.
5. Export a ZIP containing:
   - `<policy>.yml` — the deployable tailored SCA policy;
   - `<policy>_exceptions.yml` — a machine-readable exception record;
   - `<policy>_exceptions.md` — a human-readable exception record.

Unreviewed checks remain in the tailored policy. Exception records identify the
source baseline, its SHA-256 digest, the tailored policy, and the tool version.
The uploaded baseline is never modified.

## Local data and cleanup

Review state is saved locally after each decision. A known draft can be restored
at `/recover/<session-id>` while its uploaded baseline is still available. Drafts
and other application-created temporary files expire after 48 hours by default.
Configure the interval with `WAZUHSCATUNE_FILE_TTL_HOURS`.

The browser session lifetime is 24 hours. File operations are restricted to the
configured upload, draft, and export directories. Uploaded policies, draft state,
session files, and exports are written to local disk until the cleanup interval
removes them. This local data is the relevant privacy boundary: remove it when it
is no longer needed.

Application logs are also local. Their platform-specific location follows normal
per-user conventions: `%LOCALAPPDATA%\wazuhscatune\Logs` on Windows,
`~/Library/Logs/wazuhscatune` on macOS, and `$XDG_STATE_HOME/wazuhscatune`
(or the documented local-share fallback) on Linux.

## Validation scope

Validation covers YAML syntax, the minimum policy and requirements structure,
unique integer check IDs, supported scalar and list types, compliance mappings,
and obvious local consistency errors. `wazuhscatune` does not execute checks or
attempt to reproduce the Wazuh SCA engine.

The helper treats uploaded YAML and filenames as untrusted input even though it
runs locally. Path handling, YAML parsing, upload limits, temporary-file cleanup,
and export contents therefore remain security-relevant. Production web-server
hardening, TLS termination, reverse proxies, persistent application secrets, and
multi-user isolation are outside the supported use case.

## Troubleshooting

If the browser does not open automatically, open `http://127.0.0.1:5000` manually.
If startup reports that port 5000 is already in use, stop the other local process
using that port and run `wazuhscatune` again. If the application reports a file or
policy validation error, check that the input is YAML and follows the expected
Wazuh SCA structure before retrying.

For runtime diagnostics, check the per-user log location documented above. If the
log directory itself cannot be created or written, the startup error is printed to
the terminal instead.

## Development

Python 3.10 is the compatibility floor. New code must remain valid on Python 3.10,
and CI tests the supported Python range before release artifacts are published.

Run the canonical checks with:

```bash
python -m pytest
python -m pycodestyle sca
python -m mypy sca
python -m compileall -q sca
python -m build
python -m twine check --strict dist/*
```

Tests are grouped by concern as the suite grows. Add regression tests for bugs
that have actually occurred rather than expanding coverage speculatively.

`pyproject.toml` is the authoritative dependency declaration. Legacy requirements
files are intentionally not used for installation.

The application intentionally does not perform SCA checks, recommend exceptions,
rewrite rules, integrate with a Wazuh manager, provide a multi-user workflow, or
support server deployment.

Release history is kept in [`CHANGELOG.md`](CHANGELOG.md).

## License

This project is licensed under the GNU General Public License v3 or later. See
`LICENSE`.
