# Ethereum Neo4j Indexer

A resumable Python 3.12 batch indexer that reads Ethereum blocks and traces
from a local Erigon JSON-RPC endpoint and writes an address interaction graph
to a local Neo4j database.

The indexer reads only from Ethereum RPC and writes only to Neo4j. It does not
use public RPC providers or external APIs.

## Setup

Prerequisites:

- A local, archive-capable Erigon node with `eth`, `trace`, and/or `debug`
  JSON-RPC APIs enabled.
- A local Neo4j 5.x or 6.x installation. Docker is not required.
- Python 3.12 or newer.

From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Start Neo4j using the normal service or Neo4j Desktop mechanism for your
installation. Configure the password through an environment variable to avoid
putting it in shell history:

```bash
export NEO4J_PASSWORD='replace-with-your-password'
export ERIGON_RPC_URL='http://localhost:8545'
```

To distribute JSON-RPC requests across multiple equivalent nodes, provide a
comma-separated list through `ERIGON_RPC_URLS` or `--rpc-url`:

```bash
export ERIGON_RPC_URLS='http://node-a:8545,http://node-b:8545'
```

Verify that Erigon and Neo4j are reachable before running a large range.

## Usage

```bash
eth-graph-indexer ingest \
  --rpc-url http://localhost:8545,http://localhost:8546 \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --end-block 18001000 \
  --batch-size 100 \
  --concurrent-blocks 4 \
  --trace-mode trace_block \
  --resume true
```

By default, ingestion starts at Ethereum block `15537394`, the first
proof-of-stake block after The Merge. The indexer writes interactions for all
addresses in every processed block.

Use `--start-block` only when you intentionally want to repair or backfill from
a different block:

```bash
eth-graph-indexer ingest \
  --start-block 18000000 \
  --end-block 18001000
```

When `--end-block` is omitted, the run stops at the chain head observed when
the job starts. Run it again with `--resume true` to process a newer head.

To run continuously and index new blocks as they arrive, enable follow mode:

```bash
eth-graph-indexer ingest \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --trace-mode trace_block \
  --concurrent-blocks 4 \
  --resume true \
  --follow true \
  --poll-interval 12
```

Follow mode cannot be combined with `--end-block`. It processes up to the
current chain head, sleeps for `--poll-interval` seconds, then resumes from the
Neo4j checkpoint.

`--concurrent-blocks` controls how many blocks are fetched and parsed in
parallel. The default is `4`. Neo4j writes and checkpoint commits still happen
in block-number order.

### Trace modes

- `trace_block` uses Erigon's Parity-style `trace_block` response.
- `debug_traceBlockByNumber` uses `callTracer` and recursively parses internal
  call frames.
- `none` indexes external transactions and contract creations only.

By default a trace failure stops the run. Use
`--continue-on-trace-error true` to retain external interactions and checkpoint
the block despite missing traces.

`--continue-on-error true` skips and checkpoints a failed block with the hash
`ERROR_SKIPPED`. This permits forward progress but creates an intentional data
gap that must be repaired separately. The safe default is `false`.

## Graph schema

Address node:

```cypher
(:Address {
  address: byte array
})
```

Interaction relationship:

```cypher
(:Address)-[:INTERACTION {
  blockNumber: integer
}]->(:Address)
```

The indexer keeps Ethereum addresses as normalized `0x` strings while parsing,
then converts them to 20-byte values before writing to Neo4j.

An address uniqueness constraint is created at startup. Relationships are
merged by ordered source address, target address, and `blockNumber`, so repeated
interactions between the same ordered address pair in one block collapse into
one relationship.

## Checkpointing and idempotency

After each successfully written block, the same Neo4j transaction updates:

```cypher
(:IndexerCheckpoint {
  id: "default",
  lastProcessedBlock: integer,
  lastProcessedBlockHash: string,
  updatedAt: datetime
})
```

With `--resume true`, a checkpoint at or after the configured start block
causes the next run to start at `lastProcessedBlock + 1`. With
`--resume false`, processing starts exactly at `--start-block`.

Address and relationship writes use `MERGE`. Each block's graph changes and
checkpoint update are committed atomically, so normal `--resume true` runs do
not reprocess checkpointed blocks.

Reorganization handling is deliberately deferred. `lastProcessedBlockHash` is
stored so a future implementation can compare canonical ancestry.

## Example Cypher queries

Find all counterparties of an address:

```cypher
MATCH (a:Address {address: $addressBytes})-[r:INTERACTION]-(other:Address)
RETURN other.address, count(r) AS interactions
ORDER BY interactions DESC
```

Find top addresses by degree:

```cypher
MATCH (a:Address)-[r:INTERACTION]-()
RETURN a.address, count(r) AS degree
ORDER BY degree DESC
LIMIT 25
```

Find paths between two addresses:

```cypher
MATCH path = shortestPath(
  (source:Address {address: $sourceBytes})-[:INTERACTION*..8]-
  (target:Address {address: $targetBytes})
)
RETURN path
```

## Tests and linting

```bash
pytest
ruff check .
```

The test suite uses fake RPC and Neo4j store objects. It does not require live
Erigon or Neo4j services.

## Operational notes

- Historical tracing requires a local archive-capable Erigon node.
- Long-running service mode is enabled with `--follow true`; use systemd,
  supervisord, or another service manager to restart the process if it exits.
- Remote archive/trace RPC backfills benefit from `--concurrent-blocks`; tune
  it against provider rate limits and observed throughput.
- Multiple RPC URLs are used round-robin per JSON-RPC request. If one endpoint
  fails after its configured retries, the request is attempted against the next
  endpoint before the indexer gives up.
- Tracing every block is expensive. Start with a small block range and measure
  throughput before indexing a large range.
- `eth_getBlockReceipts` is preferred. If Erigon reports that method as
  unavailable, the indexer falls back to batched
  `eth_getTransactionReceipt` calls.
- Receipt, graph-write, and HTTP request batch sizes are independently
  configurable.
- RPC requests use timeouts and exponential-backoff retries.
- Passwords are never logged. Prefer `NEO4J_PASSWORD` over the command-line
  password flag.
- Contract creations in processed blocks are derived from transaction
  receipts. Otterscan creator lookup is not needed for block-by-block
  ingestion.

## Deliberately deferred

- TODO: Detect chain reorganizations by validating the checkpoint block hash
  against the current canonical chain and rolling back affected graph data.

## systemd example

Create an environment file such as `/etc/eth-graph-indexer.env`:

```bash
NEO4J_PASSWORD=replace-with-your-password
ERIGON_RPC_URLS=http://localhost:8545,http://localhost:8546
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
```

Then adapt `deploy/eth-graph-indexer.service.example` for your local checkout
and virtualenv paths.

## Terminal monitor

The package installs `eth-graph-indexer-monitor`, a minimal terminal dashboard
that reads `/etc/eth-graph-indexer-monitor.env` when present, otherwise
`/etc/eth-graph-indexer.env`. It checks the systemd service, reads the Neo4j
checkpoint, and compares it with the current Erigon head.
It also reports Neo4j data directory usage, database store size, transaction
log size, free space on the underlying filesystem, and the recent checkpoint
processing rate in blocks per second.
Exact graph counts can be slow on large databases, so they are disabled by
default. Add `--counts` when you explicitly want address and relationship
counts.

```bash
sudo eth-graph-indexer-monitor
```

Use `--once` for a single snapshot:

```bash
sudo eth-graph-indexer-monitor --once
```
