#!/bin/bash
# Idempotent. Run on pellow as a sudoer:  bash install.sh   (from this directory)
set -euo pipefail
cd "$(dirname "$0")"
sudo install -m 755 cc-notify cc-crash-notify cc-healthcheck cc-request-logs-rotate /usr/local/sbin/
sudo install -m 644 cc-healthcheck.service cc-healthcheck.timer cc-request-logs-rotate.service cc-request-logs-rotate.timer /etc/systemd/system/
sudo install -D -m 644 backend-supervision.conf /etc/systemd/system/crystal-clear-backend.service.d/supervision.conf
sudo install -D -m 644 redis-supervision.conf /etc/systemd/system/redis-server.service.d/supervision.conf
sudo install -D -m 644 journald-cc.conf /etc/systemd/journald.conf.d/crystal-clear.conf
sudo install -m 644 -o redis -g redis redis-cc.conf /etc/redis/cc.conf
grep -q '^include /etc/redis/cc.conf' /etc/redis/redis.conf || echo 'include /etc/redis/cc.conf' | sudo tee -a /etc/redis/redis.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl restart systemd-journald
# apply redis settings live (no restart; takes effect on next restart too)
redis-cli config set appendonly yes >/dev/null
redis-cli config set appendfsync everysec >/dev/null
redis-cli config set maxmemory 2gb >/dev/null
redis-cli config set maxmemory-policy volatile-lru >/dev/null
sudo systemctl enable --now cc-healthcheck.timer cc-request-logs-rotate.timer
echo "installed; units: $(systemctl show crystal-clear-backend -p Restart,RestartUSec,StartLimitIntervalUSec | tr '\n' ' ')"
