"""Shared fixtures for provision tests."""

from __future__ import annotations

SAMPLE_MANIFEST: dict = {
    "provisions": {
        "jq": {
            "provision_type": "package",
            "provider": "dnf",
            "destination": "/usr/bin",
            "links": ["/usr/local/bin/jq"],
            "get_latest": True,
            "schedule": "0 1 * * *",
        },
        "requests": {
            "provision_type": "package",
            "provider": "pip",
            "version": "2.31.0",
        },
        "my-app": {
            "provision_type": "source",
            "repo": "git@github.com:myorg/my-app.git",
            "destination": "/opt/my-app",
            "branch": "main",
            "compile_cmd": "make install",
            "schedule": "0 */12 * * *",
            "get_latest": True,
        },
        "trading-hosts": {
            "provision_type": "file",
            "destination": "/etc/proviso/hosts/trading.hocon",
            "tags": ["trading", "production"],
        },
        "deploy-key": {
            "provision_type": "file",
            "destination": "~/.ssh/deploy_ed25519",
            "tags": ["ssh", "credentials"],
        },
    }
}
