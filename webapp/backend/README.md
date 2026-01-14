# Crystal-Clear Backend API

## API Key Authentication

### Development

When `API_KEY_AUTH_ENABLED` is true, two types of keys exist:

- **Root API key** – full admin access; required to manage other keys and bypasses database lookups in `require_admin_api_key`.
- **Client API key** – scoped to regular requests; validated against the `api_key` table via `require_api_key`.

Follow the steps below to bootstrap both keys in a new environment.

### 0. Prepare your environment file

```bash
cp api/.env.example api/.env  # adjust values here
```

### 1. Enable API key enforcement and configure headers

Edit `api/.env` (or the env file your process loads) and ensure the following variables exist:

```
API_KEY_AUTH_ENABLED=true
API_KEY_HEADER=X-API-Key        # optional override
ROOT_API_KEY=<plaintext root key>    # OPTIONAL when storing hash only
ROOT_API_KEY_HASH=<sha256 hash>     # preferred storage method
```

Restart the FastAPI process after editing so the new env vars load.

### 2. Generate the root admin key

The root key is a long, random secret. Generate it once and store it in a secure secret manager.

```bash
ROOT_API_KEY=$(python - <<'PY'
import secrets; print(secrets.token_urlsafe(48))
PY)
```

Persist one of the following:

1. **Plaintext** (least secure – avoid when possible)
   ```bash
   echo "ROOT_API_KEY=${ROOT_API_KEY}" >> api/.env
   ```
2. **SHA-256 hash** (recommended)
   ```bash
   python - <<'PY' >> api/.env
import hashlib, os
key = os.environ["ROOT_API_KEY"]
print(f"ROOT_API_KEY_HASH={hashlib.sha256(key.encode()).hexdigest()}")
PY
   ```

Only the hashed value is stored on disk, while the plaintext key lives in your secret manager. `require_admin_api_key` accepts either the plaintext (`ROOT_API_KEY`) or a SHA-256 hex digest (`ROOT_API_KEY_HASH`).

### 3. Run the API with the root key available

Export the root secret in the shell (or inject it via your process manager) before starting the backend:

```bash
export ROOT_API_KEY="<plaintext key from your secret store>"
uvicorn api.api.main:app --host 0.0.0.0 --port 8000
```

### 4. Create client API keys via the `/keys` endpoints

```bash
curl -X POST http://localhost:8000/keys \
     -H "Content-Type: application/json" \
     -H "X-API-Key: ${ROOT_API_KEY}" \
     -d '{"name": "frontend"}'
```

Sample response (the `key` field is only returned once):

```json
{
  "id": 1,
  "name": "frontend",
  "prefix": "0c14d3d5",
  "created_at": "2024-05-20T12:34:56.000000",
  "revoked_at": null,
  "last_used_at": null,
  "key": "0c14d3d5m3c...<snip>..."
}
```

Share the returned `key` securely with the client.

### 5. Manage the lifecycle of keys

All management endpoints require the root key:

```bash
# List keys (set include_revoked=true to inspect historical entries)
curl -H "X-API-Key: ${ROOT_API_KEY}" \
     'http://localhost:8000/keys?include_revoked=false'

# Revoke a key by its numeric ID
curl -X DELETE http://localhost:8000/keys/1 \
     -H "X-API-Key: ${ROOT_API_KEY}"
```

Revoking sets `revoked_at` and any subsequent request made with that key will result in `HTTP 403 Invalid or revoked API key`.

### 6. Client usage checklist

- Include the configured header (default `X-API-Key`) or `api_key` query parameter on every call to `/analysis`, `/audit`, `/contract`, `/info`, and `/repository`.
- Root keys satisfy both `require_api_key` and `require_admin_api_key`. Client keys only satisfy `require_api_key`.
- Monitor activity by checking the `last_used_at` timestamp returned by `/keys`.
- Missing header → `HTTP 401 API key required`; invalid/revoked key → `HTTP 403 Invalid or revoked API key`.

With these steps your API has a hardened bootstrap process for both root and client keys, and operators have a repeatable workflow for rotation and revocation.

### Azure production deployment

Crystal-Clear's production stack runs in Azure and relies on Key Vault at this moment.

### 1. Store only the root key hash in Key Vault

`ROOT_API_KEY` and `ROOT_API_KEY_HASH` are generated the same way as development

### 2. Inject the hash into the Azure runtime

Set `API_KEY_AUTH_ENABLED=true`, reference the Key Vault secret from Web App configuration so the FastAPI process reads it as `ROOT_API_KEY_HASH`.

The SHA-256 digest is all the backend needs to validate incoming admin calls thanks to `_is_root_key_value` in `src/api/core/security.py`.

### 3. Generate customer keys through the API

Call the `/keys` endpoint to generate or list customer keys. The customer api keys can be revoked via `DELETE /keys/{id}` when access must be removed.

**List**
```
curl -H "X-API-Key: ${ROOT_API_KEY}" \
         "https://api.mab.xyz/keys/?include_revoked=false"
```

**Generate**
```
curl -X POST https://api.mab.xyz/keys/ \
     -H "Content-Type: application/json" \
     -H "X-API-Key: ${ROOT_API_KEY}" \
     -d '{"name": "customer-name"}'
```

**Delete**
```
curl -X DELETE https://https://api.mab.xyz/keys/4 \
         -H "X-API-Key: ${ROOT_API_KEY}"
```

