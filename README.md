# wazuhscatune

`wazuhscatune` is a local web application for tailoring a trusted Wazuh Security
Configuration Assessment (SCA) baseline. Every baseline check is retained unless
a reviewer records an explicit exception with a justification.

The review model distinguishes:

- **Unreviewed** — retained by default, but not yet explicitly reviewed.
- **Accepted** — reviewed and retained.
- **Exception** — reviewed, justified, and removed from the tailored policy.

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

Start the local application with the installed command:

```bash
wazuhscatune
```

Alternatively, run the package module:

```bash
python -m sca.app
```

The server listens on `http://127.0.0.1:5000`. Set `FLASK_ENV=development`
only for local development; that enables debug mode and external binding.

Set a stable `SECRET_KEY` in production. Without one, a random development key
is generated at startup and existing browser sessions become invalid.

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

## Drafts and cleanup

Review state is saved locally after each decision and through **Save Draft**. A
known draft can be restored at `/recover/<session-id>` while its uploaded baseline
is still available. Drafts and other application-created temporary files expire
after 48 hours by default. Configure the interval with
`WAZUHSCATUNE_FILE_TTL_HOURS`.

The browser session lifetime is 24 hours. File operations are restricted to the
configured upload, draft, and export directories.

## Validation scope

Validation covers YAML syntax, the minimum policy and requirements structure,
unique integer check IDs, supported scalar and list types, compliance mappings,
and obvious local consistency errors. `wazuhscatune` does not execute checks or
attempt to reproduce the Wazuh SCA engine.

## Development

Run the tests with:

```bash
pytest
```

The application intentionally does not perform SCA checks, recommend exceptions,
rewrite rules, integrate with a Wazuh manager, or provide a multi-user workflow.

## License

This project is licensed under the GNU General Public License v3 or later.
