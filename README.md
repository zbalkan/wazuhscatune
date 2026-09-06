# wazuhscatune

`wazuhscatune` is a local application for tailoring a trusted Wazuh Security
Configuration Assessment (SCA) baseline. It opens a browser-based review UI where
each check is accepted, recorded as an exception, or marked not applicable.

Review states:

- **Unreviewed** — not yet explicitly reviewed.
- **Accepted** — retained in the tailored policy.
- **Exception** — justified and removed because the control applies but its risk is accepted.
- **Not Applicable** — justified and removed because the control does not apply to the platform or role.

![Review Wazuh SCA checks](assets/review.png "Review Wazuh SCA checks")

## Requirements

Python 3.11 or newer. Python 3.11, 3.12, and 3.13 are tested on Windows, macOS,
and Linux.

`wazuhscatune` is a local single-user application. Server deployment, multi-user
operation, and use of the internal `sca` package as a Python library are not
supported.

## Install

Install with `pipx`:

```bash
pipx install wazuhscatune
```

From a local checkout:

```bash
pipx install .
```

## Run

```bash
wazuhscatune
```

The application listens on `http://127.0.0.1:5000` and opens the local browser.
If the browser does not open automatically, open that address manually.

![Upload Wazuh SCA file](assets/upload.png "Upload Wazuh SCA file")

## Workflow

1. Upload a Wazuh SCA `.yml`, `.yaml`, or a ZIP previously exported by
   `wazuhscatune`.
2. Name and describe the tailored policy.
3. Review every check as accepted, a justified exception, or justified as not applicable.
4. Review the final decisions.
5. Export a ZIP containing:
   - `<policy>.yml` — tailored SCA policy;
   - `<policy>_exceptions.yml` — machine-readable exception record;
   - `<policy>_exceptions.md` — human-readable exception record.

Export is blocked until every check has been reviewed. The uploaded baseline is
never modified.

![Review decisions before export](assets/approval.png "Review decisions before export")

## Local data

Review state is saved locally after each decision. Drafts can be recovered while
their uploaded baseline remains available. Application-created temporary files
expire after 48 hours by default; configure this with
`WAZUHSCATUNE_FILE_TTL_HOURS`.

The browser session lifetime is 24 hours. Uploads, drafts, session files, exports,
and logs remain on the local machine.

## Validation

Input validation covers YAML syntax and expected Wazuh SCA structure, including
policy metadata, requirements, checks, rule lists, compliance mappings, and unique
integer check IDs. ZIP imports are bounded by upload, member-count, and extracted
policy-size limits. The application does not execute SCA checks or emulate the
Wazuh SCA engine.

## Development

For development and testing:

```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m pycodestyle sca
python -m mypy sca
python -m compileall -q sca
python -m build
python -m twine check --strict dist/*
```

Python 3.11 is the compatibility floor. `pyproject.toml` is the authoritative
package and dependency declaration.

Release history is kept in [`CHANGELOG.md`](CHANGELOG.md).

## License

GNU General Public License v3 or later. See `LICENSE`.
