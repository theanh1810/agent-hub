# Count the retries

## Proposal

Count the retries of each request.

## Design

One counter in the request loop.

## W1 - Counter

### 1. W1-T1 · Count the retries per request - `done`

- [x] 1.1 `src/app.py` - change the counter constant - so the retries are counted
