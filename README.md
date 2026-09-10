# Agent Ultra

`agent-ultra 0.1.0-1` composes local knowledge and communication infrastructure
for an AGPC (Agent Computer). Its required dependencies are Agent Sphere
`0.2.0-1`, Redixs `4.1.0-1`, Comm `1.0.0-1`, Obsidian `1.13.7`, Mote Vault Sync
`1.1.0-3` and Mote Vault Syncd `1.1.0-3`. There are no Recommends or Suggests.

The package owns documentation and `agentsphere-local.target`. This target
wants `redixs.service` and `comm.service`, is ordered after `agentsphere.target`
and is enabled for `multi-user.target`. Standard Debian systemd helpers
(`init-system-helpers >= 1.54`) preserve owner disable and mask decisions.
It does not require UltraOne or network-online to start. Owner configuration
and current component health determine readiness; an active target alone does
not establish storage, Telegram connectivity or provider availability.

Redixs owns its bounded local persisted KV/table/cache/FIFO profile. Comm owns
local communication and its owner-configured Telegram adapter. Their native
packages own the executable, service, configuration and state; this composition
adds no wrapper daemon, alternate transport identity or package manager.

Obsidian uses its exact official amd64 DEB, obtained and verified by the
canonical `agpc.sh` installer in the same four-entry APT
transaction. MoteBus does not rehost it. The contract records its upstream
version and SHA-256. Vault Sync remains the separate native client and SSH
subsystem pair; installation does not select or copy an existing vault.

Removing this package removes its target and documentation. It does not
remove dependency packages, owner configuration or data. No implicit purge or
autoremove is performed. Complete product removal needs the separately
reviewed component lifecycle and data-preservation plan.

Exact main artifacts, signed aggregate resolution and native lifecycle checks
are required before distribution. No metadata-only fixture or version floor
establishes operational readiness. Source validation:

```sh
python3 scripts/package.py build
python3 scripts/package.py compatibility
python3 -m unittest discover -s tests -v
```
