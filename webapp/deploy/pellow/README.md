# pellow supervision

Installed by `install.sh` (idempotent; `sudo bash install.sh` from a checkout).

| layer | what |
|---|---|
| backend | `Restart=always`, 3 s delay, no start-limit (never gives up); `Wants/After` redis + postgres; clean stop (`systemctl stop/restart`) is silent |
| redis | `Restart=always`, 2 s; AOF `everysec`, `maxmemory 2gb`, `volatile-lru` (cache + counters survive a crash) |
| hang watchdog | `cc-healthcheck.timer` (every 60 s): `redis-cli ping` and `GET /health`; 3 consecutive failures -> `systemctl restart` + alert |
| crash alert | `ExecStopPost=+cc-crash-notify`: Telegram (mevgo ops bot) when `SERVICE_RESULT != success`, at most 1 per unit per 5 min |
| logs | journald (`journalctl -u crystal-clear-backend`, `-t cc-healthcheck`, `-t cc-notify`); capped 20 G / 1 week files; startup banner logs signer/pool/rate-limit/redis status; fail-open of the limiter logs at ERROR |

Fault injection results (2026-10-15): SIGKILL backend -> serving again in 4.6 s;
SIGKILL redis -> back in 2.5 s with data intact, backend kept serving;
SIGSTOP backend (hang) -> watchdog restart after 168 s (3 failed checks).

Not covered: `/health` is shallow (process answers HTTP; it does not touch
Postgres), `request_logs/*.jsonl` (416 MB) is not rotated, and a down host or
nginx outage is invisible from the host itself (the `ledger-probe` cron checks
the public HTTPS path end to end).
