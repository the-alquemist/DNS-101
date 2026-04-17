# DNS Resolver — CC4303

TCP/UDP networking project implementing a UDP-based iterative DNS resolver with selective popularity-based caching.

---

## Overview

`resolver_v2.py`:

- Receives DNS queries over UDP (`127.0.0.1:8000`)
- Performs iterative resolution starting from a fixed root DNS server
- Uses delegation (`NS`) and glue records (`A` in Additional)
- Applies selective caching for the most frequent recent domains

---

## How It Works

### General Flow

1. Start UDP server socket and bind to `127.0.0.1:8000`.
2. Receive incoming DNS packets from clients.
3. Parse the packet into a DNS object:
   - Invalid packets are ignored.
   - Valid packets extract queried domain (`qname`).
4. Append `qname` to query history.
5. Compute popularity ranking:
   - Last 20 queries
   - Top 3 most frequent domains
6. Apply cache policy:
   - If domain is top-ranked and cached and not expired (`< 60s`), answer from cache.
  - If cached but expired, resolve again and refresh cache.
  - If not cached (or not in top-ranked set), resolve normally.
  - Only store new entries when domain belongs to current top 3.
7. Before replying to client:
   - Restore original transaction ID.
   - Send DNS response back through UDP.
8. If resolution fails (no valid delegation/answer), no response is sent for that query.

---

### Resolution Strategy

1. Send query to current DNS target (initially root DNS `192.33.4.12`).
2. If Answer section contains an `A` record, resolution completes.
3. If no `A` record:
   - Check Authority section for `NS` records.
   - If no `NS` exists, resolution fails.
4. If `NS` records exist:
   - Prefer glue `A` records from Additional and continue with that IP.
   - If no glue is available, resolve NS hostname first, then retry original query using resolved NS IP.
5. Upstream communication details:
  - One-shot UDP queries with timeout (`3s`).
  - DNS port `53` for upstream servers.
  - Buffer size `4096` bytes.

---

## Usage

### Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install dnslib
```

### Run Resolver

```bash
python resolver_v2.py
```

### Test Query (from another terminal)

```bash
dig @127.0.0.1 -p 8000 www.example.com
```

---

## Notes

- Resolver listens on `127.0.0.1:8000`
- Upstream DNS queries use port `53`
- Root DNS bootstrap server is `192.33.4.12`
- Upstream timeout is `3` seconds
- UDP receive buffer is `4096` bytes
- Cache TTL is fixed at `60` seconds
- Caching applies only to domains in the top 3 of the last 20 queries
- Query history used for ranking is stored continuously, but ranking uses a sliding window of the latest 20
- Server runs continuously until interrupted (`Ctrl+C`)

---

## Key Design Choices

- **Fixed root DNS bootstrap**
  - Starts iterative resolution from a known root (`192.33.4.12`).

- **Iterative delegation handling**
  - Follows `NS` referrals directly instead of relying on system resolver recursion.

- **Glue-first optimization**
  - Uses Additional `A` records when available to avoid extra lookups.

- **Fallback NS hostname resolution**
  - Resolves name server hostnames when glue records are missing.

- **Selective popularity-based caching**
  - Caches only the most frequent domains to reduce memory usage.

- **Full-response caching with ID fixup**
  - Stores full DNS response bytes and rewrites transaction ID per client query.