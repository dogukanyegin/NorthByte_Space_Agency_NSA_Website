"""NorthByte Space Agency public website and editorial CMS.

NorthByte Space Agency is a division of NorthByte Norway Tec Ltd.
House of Yegin is credited solely as a supporter.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

import bleach
import httpx
import mistune
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('NSA_DB_PATH', str(BASE / 'data' / 'nsa.db'))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = BASE / DB_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DB_PATH.parent
ADMIN_PASSWORD = os.getenv('NSA_ADMIN_PASSWORD', '')
if ADMIN_PASSWORD.startswith('REPLACE_'):
    ADMIN_PASSWORD = ''  # Default examples must never enable an admin login.
SECRET = os.getenv('NSA_SESSION_SECRET', '')
if SECRET.startswith('REPLACE_') or len(SECRET) < 32:
    SECRET = secrets.token_urlsafe(48)  # Ephemeral sessions until configured.
HTTPS_ONLY = os.getenv('NSA_HTTPS_ONLY', 'false').lower() in ('true', '1', 'yes')
PUBLIC_EMAIL = os.getenv('NSA_PUBLIC_EMAIL', '').strip()
MAP_TILES = os.getenv('NSA_MAP_TILES', 'https://tile.openstreetmap.org/{z}/{x}/{y}.png')
SITE_NAME = 'NorthByte Space Agency'
logger = logging.getLogger('nsa')
logger.setLevel(logging.INFO)

app = FastAPI(title=SITE_NAME, docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, https_only=HTTPS_ONLY,
                   same_site='lax', session_cookie='nsa_session', max_age=12 * 3600)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
templates = Jinja2Templates(directory=str(BASE / 'templates'))

DB_LOCK = Lock()
HTTP_CACHE_LOCK = Lock()
RATE_BUCKET = {}
SAFE_GROUPS = ('STATIONS', 'WEATHER', 'RESOURCE')
ORBIT_TTL = 2 * 3600 + 120  # CelesTrak updates no more frequently than ~2h
EONET_TTL = 20 * 60


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def db():
    connection = sqlite3.connect(str(DB_PATH), timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL;')
    connection.execute('PRAGMA busy_timeout=20000;')
    return connection


def initialize_database():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            excerpt TEXT NOT NULL,
            body TEXT NOT NULL,
            published INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_posts_pub ON posts(published, created_at DESC);
        ''')
        count = c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
        if count == 0:
            now = utcnow()
            seed = [
              ('a-new-chapter-for-northbyte', 'Introducing NorthByte Space Agency', 'Announcement',
               'An introduction to NSA as an internal space research and technology division.',
               'NorthByte Space Agency (NSA) is being developed as an internal space research and technology division of **NorthByte Norway Tec Ltd.**\n\nOur initial focus is on accessible tools for Earth observation, orbital data exploration, scientific software, and educational research. The **House of Yegin** is acknowledged as a supporter, not as a parent organisation or owner.\n\nThis website is the first stage of that work. Projects described as *planned* or *in development* are not completed space missions.'),
              ('open-earth-data-programme', 'An Open Earth Data Programme', 'Research Note',
               'How publicly available Earth observation data can support independent research.',
               'Public space datasets create opportunities for smaller research teams. NSA is developing a browser-based workspace using **NASA GIBS** imagery and **NASA EONET** natural-event records.\n\nWe aim to keep the distinction between source measurements, analytical interpretation, and future concepts explicit. All external imagery and event data remain credited to their original providers.'),
              ('observatory-concept-note', 'Astronomical Observatory: Concept Note', 'Concept',
               'A staged approach to a future NSA astronomical observatory.',
               'The **NSA Astronomical Observatory** is currently a proposed project.\n\nIts initial phase would concentrate on observations, astronomy education, observation logs, and telescope integration. Site selection, remote-control capabilities, equipment, and any physical installation will depend on technical feasibility and resources.\n\nNo physical observatory is claimed to be operational at this stage.')
            ]
            c.executemany('INSERT INTO posts (slug,title,category,excerpt,body,published,created_at,updated_at) VALUES (?,?,?,?,?,1,?,?)',
                          [(*row, now, now) for row in seed])

initialize_database()


def base_context(request: Request, **kwargs):
    route = request.url.path
    return {
        'request': request, 'active': route, 'site_name': SITE_NAME,
        'contact_email': PUBLIC_EMAIL, 'map_tiles': MAP_TILES,
        'year': datetime.now(timezone.utc).year,
        'is_admin': bool(request.session.get('admin')),
        **kwargs,
    }


def render(request: Request, template: str, **kwargs):
    return templates.TemplateResponse(request, template, base_context(request, **kwargs))


def row_to_dict(row):
    return dict(row) if row is not None else None


def published_posts(limit=None):
    with db() as c:
        q = 'SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC, id DESC'
        if limit:
            return [dict(x) for x in c.execute(q + ' LIMIT ?', (limit,)).fetchall()]
        return [dict(x) for x in c.execute(q).fetchall()]


def get_post(slug, include_drafts=False):
    with db() as c:
        stmt = 'SELECT * FROM posts WHERE slug = ?' if include_drafts else 'SELECT * FROM posts WHERE slug = ? AND published = 1'
        return row_to_dict(c.execute(stmt, (slug,)).fetchone())


MARKDOWN = mistune.create_markdown(escape=True, plugins=['table'])

def markdown_safe(text):
    html = MARKDOWN(text)
    return bleach.clean(html, tags=['p', 'br', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'em', 'a', 'blockquote', 'code', 'pre', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
                        attributes={'a': ['href', 'title']}, protocols=['https', 'http', 'mailto'])

templates.env.filters['render_markdown'] = markdown_safe


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return render(request, 'index.html', posts=published_posts(3))


@app.get('/about', response_class=HTMLResponse)
def about(request: Request):
    return render(request, 'about.html')


@app.get('/missions', response_class=HTMLResponse)
def missions(request: Request):
    return render(request, 'missions.html')


@app.get('/satellite-tracker', response_class=HTMLResponse)
def satellite_tracker(request: Request):
    return render(request, 'tracker.html')


@app.get('/earth-observation', response_class=HTMLResponse)
def earth_observation(request: Request):
    today = (datetime.now(timezone.utc) - timedelta(days=2)).strftime('%Y-%m-%d')
    return render(request, 'earth.html', suggested_date=today)


@app.get('/observatory', response_class=HTMLResponse)
def observatory(request: Request):
    return render(request, 'observatory.html')


@app.get('/research', response_class=HTMLResponse)
def research(request: Request):
    return render(request, 'research.html')


@app.get('/journal', response_class=HTMLResponse)
def journal(request: Request):
    return render(request, 'journal.html', posts=published_posts())


@app.get('/journal/{slug}', response_class=HTMLResponse)
def article(request: Request, slug: str):
    post = get_post(slug)
    if not post:
        raise HTTPException(404, 'Article not found')
    return render(request, 'article.html', post=post)


@app.get('/privacy', response_class=HTMLResponse)
def privacy(request: Request):
    return render(request, 'privacy.html')


@app.get('/contact', response_class=HTMLResponse)
def contact(request: Request):
    return render(request, 'contact.html', csrf=csrf_token(request), submitted=False)


def csrf_token(request):
    token = request.session.get('csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        request.session['csrf'] = token
    return token


def valid_csrf(request, token):
    expected = request.session.get('csrf', '')
    return bool(expected and token and hmac.compare_digest(expected, token))


def limited(client_id, capacity=5, window=3600):
    now = time.monotonic()
    with DB_LOCK:
        for key, events in list(RATE_BUCKET.items()):
            RATE_BUCKET[key] = [t for t in events if now - t < window]
            if not RATE_BUCKET[key]:
                del RATE_BUCKET[key]
        events = RATE_BUCKET.setdefault(client_id, [])
        if len(events) >= capacity:
            return True
        events.append(now)
        return False


@app.post('/contact', response_class=HTMLResponse)
def post_contact(request: Request, name: str = Form(''), email: str = Form(''),
                 subject: str = Form(''), message: str = Form(''),
                 csrf: str = Form(''), website: str = Form('')):
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Form expired. Reload the page and try again.')
    if website.strip():
        return render(request, 'contact.html', csrf=csrf_token(request), submitted=True)
    client_id = request.client.host if request.client else 'unknown'
    if limited('contact:' + client_id):
        raise HTTPException(429, 'Too many messages. Please try again later.')
    fields = [name.strip(), email.strip(), subject.strip(), message.strip()]
    if not (2 <= len(fields[0]) <= 120 and 5 <= len(fields[1]) <= 254
            and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', fields[1])
            and 3 <= len(fields[2]) <= 160 and 10 <= len(fields[3]) <= 5000):
        return render(request, 'contact.html', csrf=csrf_token(request), submitted=False,
                      error='Please fill in all fields with valid information.')
    with db() as c:
        c.execute('INSERT INTO inquiries (name,email,subject,message,created_at) VALUES (?,?,?,?,?)', (*fields, utcnow()))
    return render(request, 'contact.html', csrf=csrf_token(request), submitted=True)


def require_admin(request: Request):
    if not request.session.get('admin'):
        raise HTTPException(403, 'Administrator access required')


@app.get('/admin', response_class=HTMLResponse)
def admin(request: Request):
    if not ADMIN_PASSWORD:
        return render(request, 'admin.html', admin_disabled=True, csrf=csrf_token(request))
    if not request.session.get('admin'):
        return render(request, 'admin.html', login=True, csrf=csrf_token(request))
    with db() as c:
        posts = [dict(x) for x in c.execute('SELECT * FROM posts ORDER BY id DESC')]
        inbox = [dict(x) for x in c.execute('SELECT * FROM inquiries ORDER BY id DESC LIMIT 60')]
    return render(request, 'admin.html', posts=posts, inbox=inbox, csrf=csrf_token(request))


@app.post('/admin/login')
def login(request: Request, password: str = Form(''), csrf: str = Form('')):
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Invalid CSRF token')
    ip = request.client.host if request.client else 'unknown'
    if limited('login:' + ip, capacity=12, window=3600):
        raise HTTPException(429, 'Too many login attempts')
    if not ADMIN_PASSWORD or not hmac.compare_digest(password, ADMIN_PASSWORD):
        return render(request, 'admin.html', login=True, csrf=csrf_token(request), error='Invalid password.')
    request.session.clear()
    request.session['admin'] = True
    return RedirectResponse('/admin', status_code=303)


@app.post('/admin/logout')
def logout(request: Request, csrf: str = Form('')):
    require_admin(request)
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Invalid CSRF token')
    request.session.clear()
    return RedirectResponse('/', status_code=303)


@app.post('/admin/inquiries/delete')
def delete_inquiry(request: Request, id: int = Form(...), csrf: str = Form('')):
    require_admin(request)
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Invalid CSRF token')
    with db() as c:
        c.execute('DELETE FROM inquiries WHERE id=?', (id,))
    return RedirectResponse('/admin', status_code=303)


@app.post('/admin/posts/save')
def save_post(request: Request, id: int = Form(0), title: str = Form(''), slug: str = Form(''),
              category: str = Form('Research'), excerpt: str = Form(''), body: str = Form(''),
              published: int = Form(0), csrf: str = Form('')):
    require_admin(request)
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Invalid CSRF token')
    title, slug, category, excerpt, body = [t.strip() for t in (title, slug, category, excerpt, body)]
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or not (4 <= len(title) <= 150) or not (3 <= len(category) <= 60) or not (10 <= len(excerpt) <= 300) or not (30 <= len(body) <= 60000):
        raise HTTPException(422, 'Invalid post fields')
    with db() as c:
        try:
            if id:
                existing = c.execute('SELECT id FROM posts WHERE id=?', (id,)).fetchone()
                if not existing:
                    raise HTTPException(404, 'Post not found')
                c.execute('UPDATE posts SET slug=?, title=?, category=?, excerpt=?, body=?, published=?, updated_at=? WHERE id=?', (slug,title,category,excerpt,body,1 if published else 0,utcnow(),id))
            else:
                c.execute('INSERT INTO posts (slug,title,category,excerpt,body,published,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', (slug,title,category,excerpt,body,1 if published else 0,utcnow(),utcnow()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'The slug is already in use')
    return RedirectResponse('/admin', status_code=303)


@app.post('/admin/posts/delete')
def delete_post(request: Request, id: int = Form(...), csrf: str = Form('')):
    require_admin(request)
    if not valid_csrf(request, csrf):
        raise HTTPException(403, 'Invalid CSRF token')
    with db() as c:
        c.execute('DELETE FROM posts WHERE id=?', (id,))
    return RedirectResponse('/admin', status_code=303)


# Never fetch arbitrary user-provided URLs: the fixed upstream map is an allowlist.
UPSTREAM = {
    'STATIONS': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=STATIONS&FORMAT=JSON',
    'WEATHER': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=JSON',
    'RESOURCE': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=RESOURCE&FORMAT=JSON',
    'EONET': 'https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=60',
}


def fetch_cached(key: str, ttl: int):
    """Disk cache is shared across requests and persists across restarts.

    Serve stale data on upstream failure but label the age clearly in responses.
    Never fabricate source records.
    """
    dest = CACHE_DIR / ('cache_' + key.lower() + '.json')
    with HTTP_CACHE_LOCK:
        saved = None
        if dest.exists():
            try:
                saved = json.loads(dest.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                saved = None
        if saved and time.time() - saved['fetched_epoch'] < ttl:
            return saved['data'], saved['fetched_utc'], False
        try:
            with httpx.Client(timeout=9, follow_redirects=False,
                              headers={'User-Agent': 'NorthByteSpaceAgency/1.0 (public research web service)'}) as client:
                response = client.get(UPSTREAM[key])
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list if key != 'EONET' else dict):
                    raise ValueError('Unexpected source format')
                payload = {'fetched_epoch': time.time(), 'fetched_utc': utcnow(), 'data': data}
                tmp = dest.with_suffix('.tmp')
                tmp.write_text(json.dumps(payload), encoding='utf-8')
                os.replace(tmp, dest)
                return data, payload['fetched_utc'], False
        except (httpx.HTTPError, ValueError, OSError) as exc:
            logger.warning('External service %s unavailable: %s', key, str(exc)[:130])
            if saved:
                return saved['data'], saved['fetched_utc'], True
            raise HTTPException(503, f'{key} source is temporarily unavailable')


def gmst_rad(jd):
    t = (jd - 2451545.0) / 36525.0
    degrees = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t*t - t*t*t / 38710000.0
    return math.radians(degrees % 360)


def julian(dt):
    # UNIX epoch is JD 2440587.5
    return dt.timestamp() / 86400.0 + 2440587.5


def eci_to_coords(x, y, z, jd):
    """TEME -> approximate terrestrial geodetic coordinates.

    Uses GMST rotation and WGS84 ellipsoid. Not suitable for precision navigation.
    """
    theta = gmst_rad(jd)
    xe = math.cos(theta)*x + math.sin(theta)*y
    ye = -math.sin(theta)*x + math.cos(theta)*y
    a = 6378.137
    e2 = 0.00669437999014
    p = math.hypot(xe, ye)
    lat = math.atan2(z, p*(1-e2))
    height = 0
    for _ in range(7):
        n = a / math.sqrt(1 - e2*math.sin(lat)**2)
        height = p / max(0.000001, math.cos(lat)) - n
        lat = math.atan2(z, p * (1 - e2*n/(n+height)))
    lon = math.atan2(ye, xe)
    return round(math.degrees(lat), 3), round((math.degrees(lon)+180)%360-180, 3), round(height, 1)


def position_from_omm(omm, instant):
    """True SGP4 if installed; transparently labeled Keplerian fallback otherwise."""
    jd = julian(instant)
    try:
        from sgp4 import omm as sgp_omm
        from sgp4.api import Satrec, jday
        sat = Satrec()
        sgp_omm.initialize(sat, omm)
        epoch_jd, epoch_fr = jday(instant.year, instant.month, instant.day, instant.hour, instant.minute, instant.second + instant.microsecond / 1e6)
        error, r, v = sat.sgp4(epoch_jd, epoch_fr)
        if error:
            raise ValueError('SGP4 computation error ' + str(error))
        lat, lon, alt = eci_to_coords(*r, jd)
        return lat, lon, alt, 'SGP4'
    except (ImportError, AttributeError):
        pass
    # Fallback displays true source orbital elements but approximates gravity as two-body.
    mu = 398600.4418
    n = float(omm['MEAN_MOTION']) * 2 * math.pi / 86400.0
    semimajor = (mu / n**2)**(1/3)
    ecc = float(omm['ECCENTRICITY'])
    inc, raan, arg, m0 = [math.radians(float(omm[x])) for x in ('INCLINATION', 'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY')]
    epoch = datetime.fromisoformat(omm['EPOCH'].replace('Z','+00:00'))
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    M = (m0 + n * (instant - epoch).total_seconds()) % (math.pi*2)
    E = M
    for _ in range(12):
        E -= (E - ecc*math.sin(E) - M) / (1 - ecc*math.cos(E))
    true_anomaly = math.atan2(math.sqrt(1-ecc**2)*math.sin(E), math.cos(E)-ecc)
    radius = semimajor*(1-ecc*math.cos(E))
    u = arg + true_anomaly
    x = radius*(math.cos(raan)*math.cos(u) - math.sin(raan)*math.sin(u)*math.cos(inc))
    y = radius*(math.sin(raan)*math.cos(u) + math.cos(raan)*math.sin(u)*math.cos(inc))
    z = radius*math.sin(u)*math.sin(inc)
    lat, lon, alt = eci_to_coords(x,y,z,jd)
    return lat, lon, alt, 'Keplerian approximation'


@app.get('/api/satellites')
def satellites(group: str = 'STATIONS'):
    group = group.upper()
    if group not in SAFE_GROUPS:
        raise HTTPException(400, 'Unsupported group')
    records, fetched, stale = fetch_cached(group, ORBIT_TTL)
    instant = datetime.now(timezone.utc)
    results = []
    for item in records[:90]:
        try:
            lat, lon, alt, model = position_from_omm(item, instant)
            if not (math.isfinite(lat) and math.isfinite(lon) and math.isfinite(alt)):
                continue
            results.append({
                'name': str(item.get('OBJECT_NAME', 'Unnamed')), 'norad': item.get('NORAD_CAT_ID'),
                'latitude': lat, 'longitude': lon, 'altitude_km': alt,
                'inclination_deg': item.get('INCLINATION'), 'epoch': item.get('EPOCH'),
                'model': model
            })
        except (ValueError, TypeError, KeyError, ZeroDivisionError, OverflowError):
            continue
    return {'source':'CelesTrak', 'fetched_at': fetched, 'calculated_at': instant.isoformat(),
            'stale': stale, 'count': len(results), 'satellites': results,
            'caveat': 'Positions are propagated predictions, not live satellite telemetry.'}


@app.get('/api/events')
def events():
    data, fetched, stale = fetch_cached('EONET', EONET_TTL)
    events_list = []
    for ev in data.get('events', [])[:60]:
        geos = ev.get('geometry') or []
        point = next((g for g in reversed(geos) if g.get('type') == 'Point' and isinstance(g.get('coordinates'), list)), None)
        if point is None:
            continue
        coords = point['coordinates']
        if len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except (ValueError, TypeError):
            continue
        events_list.append({'id': ev.get('id'), 'title': ev.get('title'),
                            'category': ', '.join(c.get('title', '') for c in ev.get('categories', [])),
                            'lat': lat, 'lon': lon, 'date': point.get('date'),
                            'url': ev.get('link', '')})
    return {'source':'NASA EONET', 'fetched_at': fetched, 'stale': stale,
            'count':len(events_list), 'events': events_list,
            'caveat':'EONET is a curated event catalogue, not an emergency warning service.'}


@app.get('/health')
def health():
    with db() as c:
        c.execute('SELECT 1').fetchone()
    return {'status': 'ok', 'service': 'NorthByte Space Agency'}


@app.get('/robots.txt')
def robots():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse('User-agent: *\nDisallow: /admin\nDisallow: /api/\n')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if HTTPS_ONLY:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
