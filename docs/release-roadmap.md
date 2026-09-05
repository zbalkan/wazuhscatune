# PyPI alpha 0.1.0 release roadmap

This roadmap tracks release readiness for `wazuhscatune` 0.1.0. The benchmark is the release approach used by `zbalkan/wazuhregex`: conventional Python packaging, a supported-version test matrix, installed-wheel smoke testing, and a manually triggered trusted-publishing workflow.

`wazuhscatune` is a single-user local helper whose Flask server exists only to provide a browser interface on the same machine. Production, shared, remote, and multi-user deployment are unsupported.

## P0 — Required before 0.1.0

### Identity and compatibility

- [x] Use `wazuhscatune` as the distribution name and `0.1.0` as the first public alpha.
- [x] Keep `sca` as an internal implementation package for 0.1.x rather than performing a release-only refactor.
- [x] Support Python 3.10–3.13 on current Windows, macOS, and Linux desktop environments.
- [x] Define the application as a local, single-user helper with no production-server compatibility contract.
- [x] Use installed distribution metadata as the runtime version source and `pyproject.toml` as the package/dependency source of truth.

### Distribution and CI

- [x] Add GPL-3.0-or-later license metadata and ship `LICENSE`.
- [x] Add package metadata, project URLs, classifiers, and keywords.
- [x] Remove duplicate legacy requirements files.
- [x] Base CI on the `wazuhregex` workflow: tests on Windows, macOS, and Linux across every supported Python version, followed by a package job.
- [x] Ignore documentation/image-only changes consistently with `wazuhregex`.
- [x] Build wheel/sdist, validate them with `twine check`, install the wheel, and run an application smoke test.
- [ ] Resolve any failures exposed by the CI matrix.

### Local helper behavior

- [x] Bind execution to loopback.
- [x] Disable Flask debug mode, reloader, banner, and Werkzeug request-log clutter for normal execution.
- [x] Open the local browser automatically and write diagnostics to a per-user log.
- [x] Document that server deployment and multi-user use are unsupported.

Uploaded YAML and filenames are still treated as untrusted input, as documented in the README. Path containment, validation of malformed policy structures, temporary-file expiry, draft recovery, corrupt-state handling, and exact export/archive invariants are application behaviors covered by the normal pytest suite. They remain security-relevant application invariants, but they are not duplicated here as separate release-process gates. P0 follows the same release model as `wazuhregex`: the supported test matrix must pass, and failures in these invariants fail that matrix like any other regression.

This distinction does not remove those behaviors from scope; it avoids maintaining a second checklist that restates individual tests. Production web-server hardening, TLS termination, reverse proxies, persistent application secrets, authentication, authorization, and multi-user isolation remain outside the supported local-helper model.

### Release workflow

- [x] Base publishing on the `wazuhregex` workflow.
- [x] Publish only from a manually triggered workflow on `main`.
- [x] Read the version from `pyproject.toml` and create/reuse the corresponding `vX.Y.Z` tag.
- [x] Build once, smoke-test the built wheel, upload the distribution artifact, and publish that artifact with PyPI Trusted Publishing/OIDC.
- [ ] Configure the PyPI Trusted Publisher before the first release.

A broken PyPI release is fixed forward with a new version; published files are never replaced and a version is never reused.

## P1 — Optional maintenance

These are not 0.1.0 release gates. Add them only when they become useful to the project.

- [ ] Add a concise `CHANGELOG.md` if release history becomes difficult to follow from tags and GitHub history.
- [ ] Add `CONTRIBUTING.md` if outside contributions need a documented workflow.
- [ ] Add `SECURITY.md` if a dedicated private reporting process is established.
- [ ] Add troubleshooting or screenshots when recurring user problems justify them.
- [ ] Improve test organization and coverage as the codebase grows.
- [ ] Add static analysis, dependency auditing, or source scanning when each tool has an understood policy and actionable failure criteria.
- [ ] Revisit supported Python versions as dependencies and user needs change.
- [ ] Revisit the internal `sca` package name only if it causes a concrete collision or the project develops a supported Python API.

Production-server support is not an objective. If the project ever changes from a local helper into a remotely accessible service, that is a separate architectural decision requiring a new threat model.

## 0.1.0 definition of done

The alpha is ready when the documented OS/Python CI matrix is green, the built package passes `twine check`, the installed wheel passes the local application smoke test, and PyPI Trusted Publishing is configured for the manual release workflow. Application security invariants documented in the README are enforced through that pytest matrix rather than tracked as separate release-roadmap checkboxes.
