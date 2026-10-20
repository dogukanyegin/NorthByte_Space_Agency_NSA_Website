(() => {
  const el = document.getElementById('earth-map'); if (!el) return;
  const date = document.getElementById('earth-date'), layer = document.getElementById('earth-layer');
  const toggle = document.getElementById('show-events');
  const display = document.getElementById('earth-date-display');
  const eventList = document.getElementById('event-list');
  display.textContent = date.value;
  let map, imagery, markers, eventData = [];
  if (typeof L !== 'undefined') {
    el.replaceChildren();
    map = L.map('earth-map', {center:[18,12],zoom:2,minZoom:2,maxZoom:8,worldCopyJump:true});
    // Imagery is date-controlled via GIBS public WMTS; NASA attribution always visible.
    markers = L.layerGroup().addTo(map);
    function setImagery() {
      if (imagery) map.removeLayer(imagery);
      const src = `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer.value}/default/${date.value}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;
      imagery = L.tileLayer(src, {minZoom:2, maxNativeZoom:8, maxZoom:8, tileSize:256,
        attribution:'Imagery: NASA GIBS / MODIS', crossOrigin:true, noWrap:false});
      imagery.addTo(map); imagery.bringToBack(); display.textContent = date.value;
    }
    date.addEventListener('change', setImagery); layer.addEventListener('change', setImagery);
    setImagery();
  } else {
    const p = document.createElement('p'); p.className = 'offline-warning';
    p.textContent = 'The interactive map library is unavailable. Check your network connection; NASA data layers require internet access.';
    el.append(p);
  }
  function drawEvents() {
    if (markers) markers.clearLayers();
    eventList.replaceChildren();
    const visible = toggle.checked ? eventData : [];
    if (!visible.length) {const p=document.createElement('p');p.className='small-muted';p.textContent=toggle.checked ? 'No events available from the NASA source right now.' : 'Natural events layer is hidden.';eventList.append(p);return;}
    visible.slice(0, 12).forEach(ev => {
      const item = document.createElement('button'); item.className='event-row';item.type='button';
      const title=document.createElement('strong');title.textContent=ev.title;
      const cat=document.createElement('span');cat.textContent=(ev.category || 'Event')+' · '+(ev.date||'').slice(0,10);
      item.append(title,cat);eventList.append(item);
      if (map) {
        const marker=L.circleMarker([ev.lat,ev.lon],{radius:6,color:'#92eadb',weight:2,fillColor:'#0f3d42',fillOpacity:0.95});
        const popup=document.createElement('span');popup.textContent=ev.title;
        marker.bindPopup(popup); marker.addTo(markers);
        item.addEventListener('click',()=> {map.setView([ev.lat, ev.lon],5);marker.openPopup();});
      }
    });
  }
  toggle.addEventListener('change',drawEvents);
  fetch('/api/events').then(r=>{if(!r.ok)throw Error('Source unavailable');return r.json()})
    .then(data=>{eventData=data.events||[];drawEvents();})
    .catch(()=>{eventList.innerHTML='<p class="small-muted">NASA EONET is unavailable. Live event records cannot be shown right now.</p>';});
})();
