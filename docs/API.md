# API Reference

All endpoints accept JSON (`Content-Type: application/json`) and require a Bearer JWT in the `Authorization` header (except `/auth/login`, `/health`, `/ready`).

Base URL (prod): `https://api.ticketml.example.com`

---

## Authentication

### `POST /auth/login`

Obtain a JWT.

**Request** (`application/x-www-form-urlencoded`):
```
username=admin&password=<password>
```

**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**
- `401 invalid_credentials` — bad username or password.

---

## Health

### `GET /health`
Always returns 200 when the process is up. Used as the Kubernetes **liveness** probe.

### `GET /ready`
Returns 200 only when the model is loaded and downstream dependencies are responsive. Used as the **readiness** probe.

```json
{
  "status": "ready",
  "model_loaded": true,
  "db": "ok",
  "redis": "ok"
}
```

---

## Prediction

### `POST /predict`

Classify a single ticket.

**Request**
```json
{
  "subject": "Refund not received",
  "body": "Hi team, I cancelled my subscription on June 3rd but the refund still hasn't hit my account. Order #A-2231."
}
```

**Response 200**
```json
{
  "ticket_id": "5f3c1d4a-2b8e-4f7c-9a1b-7e6d8c2f1a3b",
  "predicted_category": "Billing",
  "confidence": 0.9742,
  "top_3": [
    {"category": "Billing",  "score": 0.9742},
    {"category": "Finance",  "score": 0.0181},
    {"category": "Account",  "score": 0.0054}
  ],
  "routed_to_queue": "billing-l2",
  "needs_review": false,
  "model_version": "v2.3.0",
  "latency_ms": 18,
  "timestamp": "2026-05-24T10:42:13Z"
}
```

**Notes**
- `routed_to_queue` is populated only when `confidence ≥ HIGH_CONFIDENCE_THRESHOLD` (default 0.85). Otherwise it is `null` and `needs_review = true`.

**Errors**
- `400 invalid_input` — subject or body missing / too long.
- `401 invalid_token` — JWT missing, expired, or malformed.
- `503 model_not_loaded` — predictor singleton not initialized yet.

---

### `POST /predict/batch`

Classify up to 500 tickets in one call.

**Request**
```json
{
  "tickets": [
    {"subject": "Unable to login", "body": "Getting 500 error since this morning."},
    {"subject": "Salary slip missing", "body": "Cannot find my May salary slip on the HR portal."},
    {"subject": "Payment failed", "body": "Card was charged twice but the order says failed."}
  ]
}
```

**Response 200**
```json
{
  "results": [
    {"predicted_category": "Technical", "confidence": 0.9612, "needs_review": false},
    {"predicted_category": "HR",        "confidence": 0.9885, "needs_review": false},
    {"predicted_category": "Billing",   "confidence": 0.9437, "needs_review": false}
  ],
  "count": 3,
  "model_version": "v2.3.0",
  "latency_ms": 42
}
```

---

## Training (admin only)

### `POST /train`

Kick off an asynchronous retraining job.

**Request**
```json
{
  "data_source": "mysql",
  "min_samples_per_class": 100,
  "promote_if_better": true
}
```

**Response 202**
```json
{
  "job_id": "train-20260524-1041-a4f7c2",
  "status": "started",
  "estimated_seconds": 240
}
```

**Errors**
- `403 forbidden` — user is not `admin`.

---

## Rate limits

| Endpoint                | Limit                  |
|-------------------------|------------------------|
| `/auth/login`           | 10 / minute / IP       |
| `/predict`              | 600 / minute / token   |
| `/predict/batch`        | 60 / minute / token    |
| `/train`                | 4 / hour / admin       |

Enforced at the ingress (Nginx) and re-checked at API Management. Exceeding the limit returns `429 too_many_requests` with a `Retry-After` header.

---

## Errors

All error responses follow:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable explanation."
  }
}
```

| HTTP | Code                  | When                                          |
|------|------------------------|-----------------------------------------------|
| 400  | `invalid_input`        | Validation failed                             |
| 401  | `invalid_token`        | JWT missing / expired / malformed             |
| 403  | `forbidden`            | Role not allowed                              |
| 404  | `not_found`            | Resource doesn't exist                        |
| 429  | `rate_limited`         | Rate limit exceeded                           |
| 500  | `internal_error`       | Unexpected server-side failure                |
| 503  | `model_not_loaded`     | Predictor not yet initialized                 |
| 503  | `dependency_unavailable` | MySQL / Redis unreachable                    |
