# Agent Ultra

`agent-ultra 0.1.0-1` owns the local Ultra infrastructure composition in the
four-package Agent Sphere system: Redixs, local Comm with Telegram, Obsidian
and the vault sync client/subsystem pair.

This is an **unreleased composition candidate**. Redixs and Comm have approved
component names, but their Debian versions and actual service artifacts remain
explicit release gates. Existing OCI source is not a Debian runtime, and a
successful metadata-only build does not establish working local communication.
The manifest command refuses release until those leaf packages are real and
their versions are fixed.

Required dependencies are Redixs, Comm, Obsidian `1.13.7`, Mote Vault Sync
`1.1.0-3` and Mote Vault Syncd `1.1.0-3`. No `Recommends` or `Suggests` are used.
The top-level plural installer requests Core, Ultra, Sphere Manager and Apps
in one APT transaction. It obtains the unmodified official Obsidian amd64 DEB
and checks the SHA-256 recorded in `dependency-contract.json`. MoteBus does
not redistribute Obsidian.

This metapackage contains documentation only, with no daemon, hook, executable,
credentials, migration logic or configuration. It does not send a Telegram
message, create a bot, configure an external provider, select or import a
vault, or alter existing identities. Redixs and Comm own their native service
lifecycle and admission; owner provisioning and live acceptance are separate
from installation.

Core is headless and contains AGOS, Codex Mesh, model execution and Mote.
Sphere Manager provides the separate native TUI/CLI backed by MEdge. Apps owns
Jujue, iAgent and desktop applications. Removing this meta removes only its
documentation; deleting runtime components or data requires a separate
reviewed removal plan.

Local review:

```sh
python3 scripts/package.py build
python3 scripts/package.py compatibility
python3 -m unittest discover -s tests -v
```

The signed four-package aggregate and actual native host checks must pass
before activation. No partial installation or fake provider is an acceptable
substitute for the unresolved native services.
