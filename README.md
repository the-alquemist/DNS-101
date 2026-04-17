# DNS Resolver with Selective Cache

## Overview

This project implements a custom DNS resolver over UDP. It performs iterative resolution starting from a root DNS server and includes a selective caching mechanism based on query popularity.

---

## a) Code Execution Flow

1. The program creates a UDP socket and listens on `127.0.0.1:8000`.

2. For each incoming message:
   - Attempts to parse it as a DNS query.
   - If parsing fails, the message is discarded.
   - If successful, it extracts the queried domain (`qname`).

3. Stores `qname` in `historial_consultas`.

4. Computes a frequency-based ranking:
   - Takes the last 20 queries.
   - Determines the top 3 most frequent domains.

5. Cache decision logic:
   - If `qname` is in the top and exists in cache:
     - If not expired (less than 60 seconds), responds from cache.
     - If expired, resolves again and updates cache.
   - If cache does not apply, resolves normally.
   - Only stores results in cache if the domain belongs to the top.

6. DNS resolution (core logic):
   - Sends the query to the target server (initially root DNS `192.33.4.12`).
   - If an `A` record is found in the Answer section, returns the response.
   - If no `A` record is found:
     - Looks for `NS` records in the Authority section.
     - If none are found, resolution fails.
     - If found:
       - Attempts to use glue records (`A`) from the Additional section.
       - If glue records exist, recursively queries the NS using its IP.
       - If no glue records:
         - Resolves the NS hostname first.
         - Then queries the resolved NS.

7. Before responding to the client:
   - Adjusts the DNS message ID to match the original client query ID.
   - Sends the response via UDP.

---

## b) How to Run

1. Navigate to the project directory.

2. Create a fresh virtual environment:
   ```bash
   python3 -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install dnslib
   ```

5. Run the resolver:
   ```bash
   python resolver_v2.py
   ```

6. Test from another terminal:
   ```bash
   dig @127.0.0.1 -p 8000 www.example.com
   ```

### Notes

- The process runs in a loop until interrupted with `Ctrl+C`.
- The resolver listens on port `8000`.
- Cache prioritizes popular domains and expires after 60 seconds.

---

## c) Design Decisions

1. **Use of UDP**
   - Lower complexity and reduced overhead for typical DNS queries.

2. **Fixed Root DNS**
   - Always starts from a known root server to control iterative resolution.

3. **Iterative Resolution**
   - Follows real DNS delegation flow using Authority and Additional sections instead of relying on the system resolver.

4. **Preference for Glue Records**
   - Avoids extra queries when the Additional section provides IPs for name servers.

5. **Fallback Without Glue**
   - Resolves the NS hostname when no glue records are available.

6. **Selective Popularity-Based Cache**
   - Only caches the top 3 domains from the last 20 queries.
   - Reduces memory usage and prioritizes frequent domains.

7. **Fixed Cache TTL (60s)**
   - Simplifies expiration logic, though it does not use real DNS record TTL values.

8. **Full Response Caching**
   - Stores complete DNS response bytes.
   - Only adjusts the message ID when reusing cached responses.