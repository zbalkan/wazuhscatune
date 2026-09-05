# PyPI alpha 0.1.0 release roadmap

This roadmap tracks release readiness for `wazuhscatune` 0.1.0. The benchmark is the release approach used by `zbalkan/wazuhregex`: conventional Python packaging, a supported-version test matrix, wheel smoke testing, and a manually triggered trusted-publishing workflow.

`wazuhscatune` is deliberately narrower in runtime scope. It is a single-user local helper whose Flask server exists only to provide a browser interface on the same machine. Production, shared, remote, and multi-user deployment are unsupported. The roadmap therefore does not treat production web-server hardening as release work.

## P0 — Required before 0.1.0

### Identity and compatibility

- [x] Use `wazuhscatune` as the distribution name and `0.1.0` as the first public alpha.
- [x] Keep `sca` as an internal implementation package for 0.1.x rather than performing a release-only refactor.
- [x] Support Python 3.10–3.13 on current Windows, macOS, and Linux desktop environments.
- [x] Define the application as a local, single-user helper with no production-server compatibility contract.
- [x] Use installed distribution metadata as the runtime version source and `pyproject.toml` as the package/dependency source of truth.

### Distribution

- [x] Add GPL-3.0-or-later license metadata and ship `LICENSE`.
- [x] Add package metadata, project URLs, classifiers, and keywords.
- [x] Remove duplicate legacy requirements files.
- [ ] Confirm the wheel and sdist contain templates, static assets, README, and license while excluding runtime temporary/session data.
- [ ] Install the wheel in a clean environment and complete a basic upload/review/export smoke test.

### CI and packaging

- [x] Base CI on the `wazuhregex` workflow: tests on Windows, macOS, and Linux across every supported Python version, followed by a package job.
- [x] Ignore documentation/image-only changes consistently with `wazuhregex`.
- [x] Build and validate wheel/sdist and install the wheel before the application smoke test.
- [ ] Resolve any failures exposed by the first complete matrix run.
- [ ] Add focused regression tests where failures identify real packaging, path-handling, parsing, or export risks.

Style, typing, coverage, dependency auditing, and source scanners are useful maintenance tools, but they are not all mandatory release gates merely because the application uses Flask. Add them when they provide actionable signal rather than expanding P0 mechanically.

### Local-helper security boundary

- [x] Bind normal execution to loopback.
- [x] Document that server deployment and multi-user use are unsupported.
- [ ] Verify uploaded YAML is parsed safely and bounded by the existing upload/resource limits.
- [ ] Verify filenames and generated paths cannot escape application-controlled directories.
- [ ] Verify draft, upload, session, and export cleanup behavior.
- [ ] Verify exports contain only the expected policy and exception artifacts.

The following are explicitly **not release requirements**: production `SECRET_KEY` management, WSGI/ASGI deployment, reverse-proxy configuration, TLS termination, Internet-facing hardening, distributed/shared sessions, authentication, authorization, or multi-user isolation. Adding these would imply a deployment model the project does not support.

### Release workflow

- [x] Base publishing on the `wazuhregex` workflow.
- [x] Publish only from a manually triggered workflow on `main`.
- [x] Read the version from `pyproject.toml` and create/reuse the corresponding `vX.Y.Z` tag.
- [x] Build once, smoke-test the built wheel, upload the distribution artifact, and publish that artifact with PyPI Trusted Publishing/OIDC.
- [ ] Configure/verify the PyPI Trusted Publisher before the first release.
- [ ] Rehearse the release without publishing and verify the built artifacts.
- [ ] After publication, verify PyPI metadata, installation, console entry point, local browser startup, and a basic upload-to-export workflow.

A broken PyPI release is fixed forward with a new version; published files are never replaced or a version reused.

## P1 — Alpha usability and maintenance

- [ ] Add a concise `CHANGELOG.md` beginning with 0.1.0 and record known alpha limitations.
- [ ] Add `CONTRIBUTING.md` only when outside contributions need a documented development workflow.
- [ ] Add `SECURITY.md` with a private reporting route and the supported-version policy.
- [ ] Add concise troubleshooting for port conflicts, browser auto-open failure, permissions, expired drafts, and invalid policies.
- [ ] Document the local data directories clearly enough that a user can inspect and remove generated state.
- [ ] Add screenshots only after the UI is stable enough that they will not immediately become stale.

## P2 — Later improvements

- [ ] Revisit the internal `sca` package name only if it causes a concrete collision or the project develops a supported Python API.
- [ ] Improve test organization and coverage as the codebase grows.
- [ ] Add static analysis, dependency auditing, or source scanning where each tool has an understood policy and actionable failure criteria.
- [ ] Revisit supported Python versions as dependencies and user needs change.

Production-server support is not a P2 objective. If the project ever changes from a local helper into a remotely accessible service, that is a separate architectural decision requiring a new threat model rather than an incremental hardening task.

## 0.1.0 definition of done

The alpha is ready when CI is green on the documented OS/Python matrix, wheel and sdist contents are correct, the installed wheel completes the local smoke workflow, the local input/filesystem/data-lifecycle checks pass, PyPI Trusted Publishing is configured, and the manual release workflow has been rehearsed. Production Flask deployment controls are intentionally excluded because production deployment itself is unsupported.
