#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/nvme/javier/crystal-clear/webapp/backend/tools/ethereum-neo4j-indexer"
VENV_BIN="$ROOT/.venv/bin"
STATE_FILE="/mnt/nvme/javier/neo4j/repartitioned-pair-shards/repartition-state.json"
PARTITION_DIR="/mnt/nvme/javier/neo4j/repartitioned-pair-shards"
LOAD_STATE_DIR="$PARTITION_DIR/load-states"
LOG_FILE="/mnt/nvme/javier/neo4j/repartition-watch.log"
LOAD_BATCH_SIZE="${LOAD_BATCH_SIZE:-5000}"
LOAD_CONCURRENCY="${LOAD_CONCURRENCY:-4}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-3600}"
LOAD_CHECK_INTERVAL_SECONDS="${LOAD_CHECK_INTERVAL_SECONDS:-300}"
STATUS_LOG_INTERVAL_SECONDS="${STATUS_LOG_INTERVAL_SECONDS:-3600}"
SQLITE_INDEXER_SERVICE="${SQLITE_INDEXER_SERVICE:-eth-graph-sqlite-indexer.service}"
LIVE_INDEXER_SERVICE="${LIVE_INDEXER_SERVICE:-eth-graph-indexer.service}"

mkdir -p "$LOAD_STATE_DIR"
touch "$LOG_FILE"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$LOG_FILE"
}

start_parallel_loads() {
  local sqlite
  local stem
  local state
  local unit
  local active_count
  local available_slots

  active_count=0
  for sqlite in "$PARTITION_DIR"/part-*.sqlite3; do
    stem="$(basename "$sqlite" .sqlite3)"
    unit="eth-graph-partition-load-$stem"

    if systemctl --user show "$unit.service" --property=ActiveState --value 2>/dev/null | rg -qx 'active|activating'; then
      log "load unit already active: $unit"
      active_count=$((active_count + 1))
    fi
  done

  available_slots=$((LOAD_CONCURRENCY - active_count))
  if (( available_slots <= 0 )); then
    return
  fi

  for sqlite in "$PARTITION_DIR"/part-*.sqlite3; do
    if (( available_slots <= 0 )); then
      break
    fi

    stem="$(basename "$sqlite" .sqlite3)"
    state="$LOAD_STATE_DIR/$stem.json"
    unit="eth-graph-partition-load-$stem"

    if systemctl --user show "$unit.service" --property=ActiveState --value 2>/dev/null | rg -qx 'active|activating'; then
      continue
    fi

    if [[ "$(load_state_finished "$state")" == "true" ]]; then
      continue
    fi

    restart_partition_load "$sqlite" "$stem" "$state" "$unit"
    available_slots=$((available_slots - 1))
  done
}

load_state_finished() {
  local state_file="$1"
  if [[ ! -f "$state_file" ]]; then
    printf 'false\n'
    return
  fi
  "$VENV_BIN/python" - <<PY
import json
from pathlib import Path
path = Path("$state_file")
data = json.loads(path.read_text())
print("true" if data.get("finished") else "false")
PY
}

restart_partition_load() {
  local sqlite="$1"
  local stem="$2"
  local state="$3"
  local unit="$4"
  log "restarting load unit: $unit sqlite=$sqlite state=$state batch=$LOAD_BATCH_SIZE"
  systemctl --user stop "$unit.service" >/dev/null 2>&1 || true
  systemctl --user reset-failed "$unit.service" >/dev/null 2>&1 || true
  systemd-run --user \
    --unit "$unit" \
    --same-dir \
    --property=WorkingDirectory="$ROOT" \
    "$VENV_BIN/eth-graph-indexer-external-pair-aggregation" \
    --json-logs \
    load \
    --sqlite-path "$sqlite" \
    --state-file "$state" \
    --neo4j-batch-size "$LOAD_BATCH_SIZE" >/dev/null
}

monitor_parallel_loads() {
  local last_status_epoch
  local now
  local sqlite
  local stem
  local state
  local unit
  local active_state
  local finished_state
  local active_count
  local finished_count
  local failed_count
  local available_slots

  last_status_epoch=0
  while true; do
    active_count=0
    finished_count=0
    failed_count=0

    for sqlite in "$PARTITION_DIR"/part-*.sqlite3; do
      stem="$(basename "$sqlite" .sqlite3)"
      state="$LOAD_STATE_DIR/$stem.json"
      unit="eth-graph-partition-load-$stem.service"
      active_state="$(systemctl --user show "$unit" --property=ActiveState --value 2>/dev/null || true)"
      finished_state="$(load_state_finished "$state")"

      case "$active_state" in
        active|activating)
          active_count=$((active_count + 1))
          ;;
        failed|inactive|deactivating|"")
          if [[ "$finished_state" == "true" ]]; then
            finished_count=$((finished_count + 1))
          fi
          ;;
        *)
          log "unexpected unit state: unit=$unit active_state=$active_state"
          ;;
      esac
    done

    available_slots=$((LOAD_CONCURRENCY - active_count))
    if (( available_slots < 0 )); then
      available_slots=0
    fi

    if (( available_slots > 0 )); then
      for sqlite in "$PARTITION_DIR"/part-*.sqlite3; do
        if (( available_slots <= 0 )); then
          break
        fi

        stem="$(basename "$sqlite" .sqlite3)"
        state="$LOAD_STATE_DIR/$stem.json"
        unit="eth-graph-partition-load-$stem.service"
        active_state="$(systemctl --user show "$unit" --property=ActiveState --value 2>/dev/null || true)"
        finished_state="$(load_state_finished "$state")"

        case "$active_state" in
          active|activating)
            continue
            ;;
          failed|inactive|deactivating|"")
            if [[ "$finished_state" == "true" ]]; then
              continue
            fi
            failed_count=$((failed_count + 1))
            restart_partition_load "$sqlite" "$stem" "$state" "${unit%.service}"
            active_count=$((active_count + 1))
            available_slots=$((available_slots - 1))
            ;;
          *)
            log "unexpected unit state during refill: unit=$unit active_state=$active_state"
            ;;
        esac
      done
    fi

    now="$(date +%s)"
    if (( last_status_epoch == 0 || now - last_status_epoch >= STATUS_LOG_INTERVAL_SECONDS )); then
      log "parallel load status active=$active_count finished=$finished_count restarted=$failed_count concurrency=$LOAD_CONCURRENCY batch=$LOAD_BATCH_SIZE"
      last_status_epoch="$now"
    fi

    if (( finished_count == 16 )); then
      log "all partition load units finished"
      log "stopping SQLite-only indexer: $SQLITE_INDEXER_SERVICE"
      systemctl --user disable --now "$SQLITE_INDEXER_SERVICE"
      if systemctl --user enable --now "$LIVE_INDEXER_SERVICE"; then
        log "started dual-write live indexer: $LIVE_INDEXER_SERVICE"
        exit 0
      fi
      log "failed to start dual-write live indexer; will retry"
      systemctl --user enable --now "$SQLITE_INDEXER_SERVICE"
    fi

    sleep "$LOAD_CHECK_INTERVAL_SECONDS"
  done
}

log "watcher started state_file=$STATE_FILE interval=${CHECK_INTERVAL_SECONDS}s load_interval=${LOAD_CHECK_INTERVAL_SECONDS}s batch=$LOAD_BATCH_SIZE"

while true; do
  if [[ ! -f "$STATE_FILE" ]]; then
    log "state file missing: $STATE_FILE"
    sleep "$CHECK_INTERVAL_SECONDS"
    continue
  fi

  finished="$("$VENV_BIN/python" - <<'PY'
import json
from pathlib import Path
path = Path("/mnt/nvme/javier/neo4j/repartitioned-pair-shards/repartition-state.json")
data = json.loads(path.read_text())
print("true" if data.get("finished") else "false")
print(data.get("source_index", 0))
print(data.get("rows_repartitioned", 0))
PY
)"

  done_flag="$(printf '%s\n' "$finished" | sed -n '1p')"
  source_index="$(printf '%s\n' "$finished" | sed -n '2p')"
  rows_repartitioned="$(printf '%s\n' "$finished" | sed -n '3p')"

  log "repartition status finished=$done_flag source_index=$source_index rows_repartitioned=$rows_repartitioned"

  if [[ "$done_flag" == "true" ]]; then
    start_parallel_loads
    log "all partition load units launched; entering load monitor"
    monitor_parallel_loads
  fi

  sleep "$CHECK_INTERVAL_SECONDS"
done
