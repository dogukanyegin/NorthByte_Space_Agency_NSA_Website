(() => {
  const group = document.getElementById('sat-group');
  if (!group) return;
  const list = document.getElementById('sat-list');
  const markers = document.getElementById('orbit-markers');
  const search = document.getElementById('sat-search');
  const status = document.getElementById('sat-map-status');
  const utc = document.getElementById('tracker-time');
  let satellites = [], selectedId = null, requestInProgress = false;
  const text = (id, value) => { document.getElementById(id).textContent = value; };
  const number = v => v === null || v === undefined ? '—' : String(v);
  const format = (n, suffix = '') => Number.isFinite(Number(n)) ? `${Number(n).toFixed(2)}${suffix}` : '—';
  const updateUtc = () => { utc.textContent = new Date().toISOString().slice(0, 19).replace('T', ' ') + ' UTC'; };
  updateUtc(); setInterval(updateUtc, 30000);
  function select(s) {
    selectedId = String(s.norad);
    text('detail-name', s.name); text('detail-lat', format(s.latitude, '°'));
    text('detail-lon', format(s.longitude, '°')); text('detail-alt', format(s.altitude_km, ' km'));
    text('detail-id', number(s.norad));
    document.querySelectorAll('[data-satellite-id]').forEach(el => el.classList.toggle('selected', el.dataset.satelliteId === selectedId));
  }
  function draw() {
    markers.replaceChildren(); list.replaceChildren();
    const q = search.value.trim().toLowerCase();
    const filtered = satellites.filter(s => s.name.toLowerCase().includes(q) || String(s.norad).includes(q));
    filtered.forEach(s => {
      const id = String(s.norad);
      const item = document.createElement('button'); item.type = 'button';
      item.className = 'satellite-item'; item.dataset.satelliteId = id;
      const label = document.createElement('span'); label.textContent = s.name;
      const meta = document.createElement('small'); meta.textContent = `NORAD ${id}  ·  ${Math.round(s.altitude_km)} km`;
      item.append(label, meta); item.addEventListener('click', () => select(s)); list.append(item);
      const mark = document.createElement('button'); mark.type = 'button'; mark.className = 'sat-marker';
      mark.dataset.satelliteId = id;
      mark.style.left = ((Number(s.longitude) + 180) / 360 * 100) + '%';
      mark.style.top = ((90 - Number(s.latitude)) / 180 * 100) + '%';
      mark.setAttribute('aria-label', s.name + ', ' + format(s.latitude, '°') + ' latitude');
      mark.title = s.name; mark.addEventListener('click', () => select(s)); markers.append(mark);
    });
    if (!filtered.length) list.innerHTML = '<p class="empty-state">No matching satellites in this dataset.</p>';
    const current = filtered.find(s => String(s.norad) === selectedId) || filtered[0];
    if (current) select(current);
    else { ['detail-name','detail-lat','detail-lon','detail-alt','detail-id'].forEach(id => text(id, '—')); }
  }
  async function load() {
    if (requestInProgress) return;
    requestInProgress = true; text('sat-map-status', 'Loading validated orbital elements…');
    list.innerHTML = '<p class="empty-state">Connecting to CelesTrak…</p>';
    try {
      const resp = await fetch(`/api/satellites?group=${encodeURIComponent(group.value)}`, {cache:'no-store'});
      if (!resp.ok) throw new Error(`Data source currently unavailable (${resp.status})`);
      const data = await resp.json(); satellites = data.satellites || [];
      const model = satellites[0]?.model || 'Not available';
      status.textContent = `${satellites.length} calculated positions · ${model} · ${data.stale ? 'Cached / potentially stale' : 'Source available'} · Data retrieved: ${data.fetched_at.slice(0,16).replace('T',' ')} UTC`;
      draw();
    } catch (error) {
      satellites = []; list.innerHTML = '<p class="empty-state">' + error.message + '. Please try again later.</p>';
      markers.replaceChildren(); text('sat-map-status', 'No validated orbital dataset is currently available.');
    } finally { requestInProgress = false; }
  }
  document.getElementById('tracker-refresh').addEventListener('click', load);
  group.addEventListener('change', () => {selectedId = null; load();});
  search.addEventListener('input', draw);
  load();
  setInterval(() => { if (!document.hidden) load(); }, 5 * 60 * 1000);
})();
