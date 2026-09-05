# Release decision: 0.1.0 alpha

Date: 2026-09-05

The first public PyPI release is `wazuhscatune` 0.1.0.

The distribution name remains `wazuhscatune`. The existing `sca` import package is retained for the 0.1.x alpha series to avoid an unnecessary internal refactor during release preparation. It is explicitly not a supported public Python API and may be renamed during alpha.

The supported runtime matrix is Python 3.10 through 3.13 on current Windows, macOS, and Linux desktop environments. `wazuhscatune` is a single-user local helper. Its Flask server exists only to provide the browser UI on the local machine; production, shared, remote, and multi-user deployment are unsupported.

Consequently, production web-application concerns are outside the compatibility and security contract. The project does not need production WSGI deployment, reverse-proxy or TLS configuration, persistent application-secret management, or multi-user session isolation. Security work remains focused on the local trust boundary: untrusted YAML and filenames, safe filesystem access, bounded uploads/parsing, temporary-data lifecycle, and predictable export contents.

Draft persistence and internal Python APIs have no compatibility guarantee during alpha. The installed distribution metadata is the authoritative source for the runtime version. `pyproject.toml` is the authoritative source for project dependencies and package metadata.
