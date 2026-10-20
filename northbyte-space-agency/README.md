# NorthByte Space Agency (NSA) — Website v1.0

**A division of NorthByte Norway Tec Ltd.**  
**Supported by the House of Yegin** (supporter only; not an owner/parent organisation).

A working English-language, responsive website with orbital tracker, satellite imagery map, curated natural-event overlays, editable journal, contact inbox and staff CMS. No domain, third-party account or public hosting is assumed.

## Features

| Module | Implementation | Data / status |
|---|---|---|
| Institutional website | Responsive home, about, missions, research, contact | Operational |
| Satellite tracker | Python orbital propagation, search and interactive global map | Real CelesTrak GP/OMM when upstream reachable |
| Earth observation lab | Leaflet map and date-selectable imagery | NASA GIBS, internet required |
| Natural events overlay | NASA EONET API, map markers and clickable event list | NASA EONET, internet required |
| Observatory section | Phased roadmap, no invented claims | Planned concept, not a physical facility |
| Journal / blog | SQLite CRUD with Markdown and sanitized HTML | Operational |
| Staff dashboard | Password login, session auth and CSRF form protection | Operational when credentials configured |
| Contact form | SQLite inbox, validation, honeypot, simple rate limit | Operational, **does not send email** |
| Docker/VPS | Dockerfile, Compose, persistent named volume | Ready for deployment on a user-controlled server |

## Quick start (Python)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit your .env values and configure them as shell environment variables.
# A simple option: set -a; source .env; set +a (Linux Bash)
uvicorn app:app --host 127.0.0.1 --port 8080
```

Visit **http://127.0.0.1:8080**; staff CMS: **http://127.0.0.1:8080/admin**.

If you do not set `NSA_ADMIN_PASSWORD`, the public site still runs but the staff dashboard is disabled. Admin credentials are never embedded in the source archive.

## Docker / VPS setup

```bash
cp .env.example .env
# Set a unique strong NSA_ADMIN_PASSWORD and a random NSA_SESSION_SECRET.
# e.g. python -c 'import secrets; print(secrets.token_urlsafe(48))'
docker compose up --build -d
curl http://127.0.0.1:8080/health
```

The Docker service binds to localhost only. **It is not publicly exposed**. Add a reverse proxy on the server to provide your domain and HTTPS (Caddy/Nginx). Once TLS is configured, set `NSA_HTTPS_ONLY=true`, enable HTTPS headers and redeploy. DNS/domain/SSL deployment cannot be done without server credentials and your permission. Back up the SQLite database in the Docker volume `nsa-data`.

### Caddy reverse proxy example

```caddy
space.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8080
}
```

Replace `space.example.com` with a domain you actually own, create the relevant DNS record, and make sure port 443 can receive connections. The example is **not** a live URL.

### Server sizing

A VPS with **2 vCPU, 4–8 GB RAM, 30–60 GB SSD** is a reasonable pilot. Heavy imagery is loaded directly from NASA GIBS (no large image files stored by default). For high-traffic deployments, move to PostgreSQL, durable external cache, managed tile hosting, monitoring and persistent session keys.

## Data and scientific caveats

- **CelesTrak:** The server fetches selected OMM-compatible JSON groups no more than approximately once every 2 hours per group. No fake satellites are inserted. Exact SGP4 propagation is used if `sgp4` is available (installed by `requirements.txt`). In a minimal local runtime lacking that package, a labelled two-body approximation is used; this is not suitable for precision operations.
- The `STATIONS`, `WEATHER`, `RESOURCE` groups are explicit supported datasets. Source unavailability is shown rather than replaced by demonstration points.
- **NASA GIBS:** Public tiled browse imagery, not a live video feed. A date selector is exposed; allow time for products to become available.
- **NASA EONET:** Curated geospatial events, not emergency alert information and not an exhaustive hazard catalogue.
- Satellite ground positions and displayed altitudes are estimates. They are not direct telemetry, nor validated safety-critical guidance.
- The equirectangular land map is a Natural Earth-derived illustration, not a precision cartographic layer.
- NASA, CelesTrak and OSM are independent external services. The site is not affiliated with their organisations.

### Official developer documentation

- https://celestrak.org/NORAD/documentation/gp-data-formats.php
- https://celestrak.org/usage-policy.php
- https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- https://eonet.gsfc.nasa.gov/docs/v3
- https://operations.osmfoundation.org/policies/tiles/

## Site routes

`/`, `/about`, `/missions`, `/satellite-tracker`, `/earth-observation`, `/observatory`, `/research`, `/journal`, `/journal/{slug}`, `/contact`, `/privacy`, `/admin`, `/api/satellites?group=STATIONS`, `/api/events`, `/health`.

## Blog and contact inbox

After configuring administrator credentials, open `/admin`. Articles can be created, edited, unpublished and deleted. Only published entries are visible publicly. Markdown is escaped and sanitised to prevent injected HTML/script content. Contact submissions are stored in the SQLite `inquiries` table and visible/deletable in `/admin`; this site **does not send an email** on its own. Email notifications can be integrated later via a transactional SMTP/API provider.

## Security and production checklist

- [ ] Configure a strong unique admin password; use TLS-only sessions and a persistent random secret.
- [ ] Attach domain/DNS and a TLS reverse proxy. Restrict origin server port to localhost.
- [ ] Set up firewall, database backups and off-server encrypted backups.
- [ ] Add stronger IP-based request rate limiting at the reverse proxy for a public deployment.
- [ ] Prepare privacy policy, cookie statement and terms if required by deployment jurisdiction. Collect only essential form data.
- [ ] Replace or verify source usage policies, attribution and licenses when expanding usage.
- [ ] Confirm editorial content, organisational contact information and brand assets before publishing.
- [ ] For production commercial traffic, consider an imagery/map provider with capacity guarantees.

## Legal identity

This project treats NSA as **an internal division of NorthByte Norway Tec Ltd.** No separate incorporation, government status, actual satellite operation or operational physical observatory is asserted. House of Yegin is named only as a **supporter**.

## Repo structure

```
app.py              FastAPI routes, SQLite CMS, orbital propagation and data APIs
requirements.txt    Python requirements (sgp4 included)
templates/          HTML pages
static/css/         Responsive visual design
static/js/          Navigation, orbital tracker, NASA Earth map, editorial UI
static/img/         NSA logo and vector Earth illustrations
Dockerfile           Docker image
docker-compose.yml  Local-only published container + persistent database volume
.env.example        Environment variable example
sources.json        Scientific data reference endpoints
tests/              Local smoke tests
```
