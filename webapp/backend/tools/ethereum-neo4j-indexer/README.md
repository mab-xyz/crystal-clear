# Ethereum Interaction Pair Indexer

A resumable Python 3.12 indexer that reads Ethereum blocks and execution traces
from Erigon and updates directed interaction-pair ranges in PostgreSQL.

Live ingestion writes only to PostgreSQL. The package retains the previous
Neo4j migration and SQLite shard tools for completed migration maintenance, but
`eth-graph-indexer ingest` does not use either store.

## Requirements

- Python 3.12 or newer.
- An archive-capable Erigon node with the `eth`, `trace`, and/or `debug` APIs.
- PostgreSQL containing the migrated `pair_ranges` and
  `indexer_checkpoints` tables.
- A PostgreSQL role with `SELECT`, `INSERT`, and `UPDATE` privileges on both
  tables.

Install the live indexer:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## PostgreSQL schema

The indexer expects:

```sql
CREATE TABLE public.pair_ranges (
    source bytea NOT NULL,
    target bytea NOT NULL,
    first_block_number bigint NOT NULL,
    last_block_number bigint NOT NULL,
    PRIMARY KEY (source, target),
    CHECK (octet_length(source) = 20 AND octet_length(target) = 20),
    CHECK (
        first_block_number >= 0
        AND last_block_number >= first_block_number
    )
);

CREATE TABLE public.indexer_checkpoints (
    id text PRIMARY KEY,
    last_processed_block bigint NOT NULL,
    last_processed_block_hash text NOT NULL,
    updated_at timestamptz NOT NULL
);
```

`pair_ranges` may be partitioned as long as `(source, target)` remains a valid
conflict target. Ethereum addresses are stored as 20-byte `bytea` values.

Each ordered pair has one row. A repeated interaction updates the range using:

```text
first_block_number = min(existing, observed)
last_block_number  = max(existing, observed)
```

This supports the historical predicate:

```text
seen at or before block B = first_block_number <= B
```

## Running

Use a dedicated connection string so the indexer does not accidentally inherit
an application role with read-only permissions:

```bash
export INDEXER_DATABASE_URL='postgresql://indexer:password@localhost:5432/cc'
export ERIGON_RPC_URL='http://localhost:8545'

eth-graph-indexer ingest \
  --trace-mode trace_block \
  --concurrent-blocks 4 \
  --resume true
```

The DSN can also be passed with `--postgres-dsn`. The CLI checks
`INDEXER_DATABASE_URL` first and then `DATABASE_URL`.

By default, ingestion starts at Ethereum block `15537394`, the first
proof-of-stake block after The Merge. With `--resume true`, an existing
checkpoint at or after that block causes ingestion to continue at
`last_processed_block + 1`.

Without `--end-block`, a non-follow run stops at the chain head observed when
the run starts. Continuous operation uses:

```bash
eth-graph-indexer ingest \
  --follow true \
  --poll-interval 12 \
  --resume true
```

Follow mode cannot be combined with `--end-block`.

## Interaction extraction

For every block, the indexer records:

- Top-level transaction `from -> to` interactions.
- Successful contract-creation addresses obtained from receipts.
- Internal calls from `trace_block` or `debug_traceBlockByNumber`.
- Internal contract creations and self-destruct beneficiaries.

The trace modes are:

- `trace_block`: Erigon Parity-style block traces; this is the default.
- `debug_traceBlockByNumber`: recursive `callTracer` frames.
- `none`: top-level transactions and contract creations only.

Only direct execution edges are indexed. The indexer does not materialize a
transitive closure.

## Commit and checkpoint guarantees

Blocks can be fetched and traced concurrently, but commits remain ordered.
The default commit batch contains 10 contiguous blocks.

Pair-range updates and the PostgreSQL checkpoint update happen in one database
transaction. The store rejects:

- A non-contiguous commit batch.
- A checkpoint gap.
- A block marked `ERROR_SKIPPED`.
- A replayed checkpoint block with a different hash.

Upserts are idempotent, so replaying a range after an interrupted run is safe.
Canonical-chain reorganization detection beyond an overlapping checkpoint is
still not implemented.

## RPC behavior

Multiple comma-separated RPC URLs are supported through `ERIGON_RPC_URLS` or
`--rpc-url`. Requests use timeouts, exponential-backoff retries, and endpoint
failover. `--endpoint-concurrency` can assign explicit worker counts to each
endpoint.

Receipt lookup prefers `eth_getBlockReceipts` and falls back to batched
`eth_getTransactionReceipt` calls when necessary.

## Legacy migration utilities

The following commands are retained for the completed Neo4j-to-pair-range and
SQLite-shard migration workflow:

- `eth-graph-indexer-migrate-pair-schema`
- `eth-graph-indexer-external-pair-aggregation`
- `eth-graph-pair-server`

Install their Neo4j dependency only when running those tools:

```bash
python -m pip install -e '.[legacy]'
```

They are not part of live PostgreSQL ingestion.

## Monitoring

The terminal monitor uses the same PostgreSQL DSN and Erigon RPC settings as
the indexer:

```bash
export INDEXER_DATABASE_URL='postgresql://indexer:password@localhost:5432/cc'
export ERIGON_RPC_URL='http://localhost:8545'

eth-graph-indexer-monitor
```

It reports service state, checkpoint and chain-head lag, ingestion rate,
estimated directed-pair rows, PostgreSQL database and pair-partition sizes, and
filesystem capacity. Set `POSTGRES_DATA_PATH` when PostgreSQL is stored on a
different filesystem. Pass `--counts` only when an exact `pair_ranges` row
count is needed; on a large database that scan can be slow.

## Continuous deployment

Changes under this tool are deployed from `main` by
`.github/workflows/pellow-indexer-deploy.yml`. The self-hosted production
runner:

1. Fast-forwards `/home/crystal-clear-prod/crystal-clear`.
2. Installs the package into the tool's dedicated `.venv`.
3. Calls the root-owned `/usr/local/sbin/restart-eth-graph-indexer` helper.

The systemd service and PostgreSQL peer-auth role both run as
`crystal-clear-prod`. The runner has passwordless sudo access only to the
root-owned restart helper.

## Verification

```bash
pytest
ruff check .
```

The unit test suite does not require live Erigon, PostgreSQL, Neo4j, or SQLite
services.
