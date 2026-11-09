# Model-Based Testing of Synapse room membership

Testing Techniques, Assignment: Model-Based Testing with the Axini Modelling Platform (AMP).
The SUT is the [Synapse](https://github.com/element-hq/synapse) Matrix homeserver (v1.160.0),
tested through the Matrix Client-Server API. The tested functionality is room membership:
invite, join, leave, kick, ban and unban.

## Contents

| Path | What |
|---|---|
| `docker-compose.yml` | Runs Synapse locally on port 8008 |
| `probe_membership.py` | Investigation script: tries every membership action from every state |
| `model/membership.aml` | The AML model used in AMP |

## Requirements

- Docker
- [uv](https://docs.astral.sh/uv/) (Python 3.13)

## 1. Start Synapse

Generate the configuration (first time only):

```bash
docker compose run --rm -e SYNAPSE_SERVER_NAME=localhost -e SYNAPSE_REPORT_STATS=no synapse generate
```

Add the following to the end of `synapse-data/homeserver.yaml`:

```yaml
enable_registration: true
enable_registration_without_verification: true

rc_message:      {per_second: 1000, burst_count: 1000}
rc_registration: {per_second: 1000, burst_count: 1000}
rc_joins:
  local:  {per_second: 1000, burst_count: 1000}
rc_invites:
  per_room:   {per_second: 1000, burst_count: 1000}
  per_user:   {per_second: 1000, burst_count: 1000}
rc_login:
  address: {per_second: 1000, burst_count: 1000}
  account: {per_second: 1000, burst_count: 1000}
```

The raised rate limits are needed because MBT sends many requests in a short time.

Start Synapse and check that it responds:

```bash
docker compose up -d
curl http://localhost:8008/_matrix/client/versions
```

## 2. Run the probe

```bash
uv sync
uv run python probe_membership.py
```

Prints a table with, for every starting state of `bob` and every action, the HTTP status,
the Matrix error code and `bob`'s membership afterwards.

## 3. The model

`model/membership.aml` is loaded into AMP (course02.axini.com). It has one state per
membership of `bob` (`never`, `invite`, `join`, `leave`, `ban`) and one stimulus per
action and actor (`admin_*`, `bob_*`, `eve_*`), with responses `ok` (200) and `forbidden` (403).

## 4. Run the adapter

With Synapse running:

```bash
cd adapter
uv run python plugin_adapter.py -u wss://course02.axini.com:443/adapters -t <AMP API key>
```

In AMP: map the channel `matrix` to this adapter on the Adapters page, keep
`synapse_url = http://localhost:8008`, and start a test run.
