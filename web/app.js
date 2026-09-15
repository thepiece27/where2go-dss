const state = {
  pois: [],
  filtered: [],
  selectedId: null,
  markers: new Map(),
};

const els = {
  totalCount: document.querySelector("#totalCount"),
  visibleCount: document.querySelector("#visibleCount"),
  avgRating: document.querySelector("#avgRating"),
  searchInput: document.querySelector("#searchInput"),
  locationFilter: document.querySelector("#locationFilter"),
  typeFilter: document.querySelector("#typeFilter"),
  ratingFilter: document.querySelector("#ratingFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  hasReviews: document.querySelector("#hasReviews"),
  hasHours: document.querySelector("#hasHours"),
  resetFilters: document.querySelector("#resetFilters"),
  poiList: document.querySelector("#poiList"),
  detailPanel: document.querySelector("#detailPanel"),
};

const map = L.map("map", { zoomControl: false }).setView([15.9, 106.8], 6);
L.control.zoom({ position: "bottomleft" }).addTo(map);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);

function formatNumber(value) {
  return new Intl.NumberFormat("vi-VN").format(value || 0);
}

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

function option(label, value = label) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = label;
  return item;
}

function populateFilters(meta) {
  els.locationFilter.replaceChildren(option("Tất cả", ""));
  meta.locations.forEach((location) => els.locationFilter.appendChild(option(location)));

  els.typeFilter.replaceChildren(option("Tất cả", ""));
  meta.types.forEach((type) => els.typeFilter.appendChild(option(type)));
}

function imageMarkup(poi, className) {
  if (!poi.image) {
    return `<div class="${className}" role="img" aria-label="No image"></div>`;
  }
  return `<img class="${className}" src="${poi.image}" alt="${escapeHtml(poi.name)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('div'), {className: '${className}'}))" />`;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function poiSearchText(poi) {
  return normalize([
    poi.name,
    poi.resultName,
    poi.location,
    poi.type,
    poi.description,
    ...(poi.keywords || []),
  ].join(" "));
}

function filterPois() {
  const query = normalize(els.searchInput.value);
  const location = els.locationFilter.value;
  const type = els.typeFilter.value;
  const minRating = Number(els.ratingFilter.value || 0);
  const requireReviews = els.hasReviews.checked;
  const requireHours = els.hasHours.checked;

  state.filtered = state.pois.filter((poi) => {
    if (query && !poi._search.includes(query)) return false;
    if (location && poi.location !== location) return false;
    if (type && poi.type !== type) return false;
    if ((poi.rating || 0) < minRating) return false;
    if (requireReviews && !poi.reviewCount) return false;
    if (requireHours && !poi.hours) return false;
    return true;
  });

  const sort = els.sortSelect.value;
  state.filtered.sort((a, b) => {
    if (sort === "reviews") return (b.reviewCount || 0) - (a.reviewCount || 0);
    if (sort === "rating") return (b.rating || 0) - (a.rating || 0);
    if (sort === "name") return a.name.localeCompare(b.name, "vi");
    return (b.quality || 0) - (a.quality || 0);
  });

  render();
}

function renderStats() {
  els.totalCount.textContent = formatNumber(state.pois.length);
  els.visibleCount.textContent = formatNumber(state.filtered.length);
  const ratings = state.filtered.map((poi) => poi.rating).filter(Boolean);
  const average = ratings.length ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length : 0;
  els.avgRating.textContent = average.toFixed(1);
}

function renderList() {
  const visible = state.filtered.slice(0, 120);
  if (!visible.length) {
    els.poiList.innerHTML = `<div class="empty-state">Không có địa điểm phù hợp.</div>`;
    return;
  }

  els.poiList.innerHTML = visible.map((poi) => `
    <button class="poi-card ${poi.id === state.selectedId ? "active" : ""}" data-id="${poi.id}">
      ${imageMarkup(poi, "thumb")}
      <span>
        <h2>${escapeHtml(poi.name)}</h2>
        <p class="meta-line">
          <span>${escapeHtml(poi.location)}</span>
          <span>${escapeHtml(poi.type || "Unknown")}</span>
        </p>
        <p class="meta-line">
          <span>${poi.rating ? `${poi.rating.toFixed(1)} sao` : "Chưa có rating"}</span>
          <span>${formatNumber(poi.reviewCount)} reviews</span>
        </p>
        <span class="tag-row">
          ${(poi.keywords || []).slice(0, 3).map((keyword) => `<span class="tag">${escapeHtml(keyword)}</span>`).join("")}
        </span>
      </span>
    </button>
  `).join("");
}

function markerIcon(poi) {
  const isHot = (poi.reviewCount || 0) > 1000 || (poi.rating || 0) >= 4.7;
  return L.divIcon({
    className: "",
    html: `<div class="marker-dot ${isHot ? "hot" : ""}"></div>`,
    iconSize: [13, 13],
    iconAnchor: [6, 6],
  });
}

function renderMap() {
  markerLayer.clearLayers();
  state.markers.clear();

  const visible = state.filtered.slice(0, 650);
  const bounds = [];
  visible.forEach((poi) => {
    const marker = L.marker([poi.lat, poi.lng], { icon: markerIcon(poi), title: poi.name });
    marker.on("click", () => selectPoi(poi.id, true));
    marker.addTo(markerLayer);
    state.markers.set(poi.id, marker);
    bounds.push([poi.lat, poi.lng]);
  });

  if (bounds.length && !state.selectedId) {
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 8 });
  }
}

function renderDetail(poi) {
  if (!poi) {
    els.detailPanel.innerHTML = "";
    return;
  }

  els.detailPanel.innerHTML = `
    ${imageMarkup(poi, "detail-image")}
    <h2>${escapeHtml(poi.name)}</h2>
    <p class="meta-line">
      <span>${escapeHtml(poi.location)}</span>
      <span>${escapeHtml(poi.type || "Unknown")}</span>
      <span>${poi.rating ? `${poi.rating.toFixed(1)} sao` : "Chưa có rating"}</span>
      <span>${formatNumber(poi.reviewCount)} reviews</span>
    </p>
    ${poi.description ? `<p>${escapeHtml(poi.description)}</p>` : ""}
    ${poi.hours ? `<p><strong>Giờ mở cửa:</strong> ${escapeHtml(poi.hours)}</p>` : ""}
    <div class="tag-row">
      ${(poi.keywords || []).map((keyword) => `<span class="tag">${escapeHtml(keyword)}</span>`).join("")}
    </div>
    <div class="detail-actions">
      ${poi.url ? `<a href="${escapeHtml(poi.url)}" target="_blank" rel="noreferrer">Mở Google Maps</a>` : ""}
    </div>
  `;
}

function selectPoi(id, pan = false) {
  state.selectedId = id;
  const poi = state.pois.find((item) => item.id === id);
  renderDetail(poi);
  renderList();

  const marker = state.markers.get(id);
  if (marker) {
    marker.openPopup();
  }
  if (pan && poi) {
    map.setView([poi.lat, poi.lng], Math.max(map.getZoom(), 12), { animate: true });
  }
}

function render() {
  renderStats();
  renderList();
  renderMap();
  const selected = state.filtered.find((poi) => poi.id === state.selectedId);
  renderDetail(selected || state.filtered[0]);
}

function bindEvents() {
  [
    els.searchInput,
    els.locationFilter,
    els.typeFilter,
    els.ratingFilter,
    els.sortSelect,
    els.hasReviews,
    els.hasHours,
  ].forEach((input) => input.addEventListener("input", () => {
    state.selectedId = null;
    filterPois();
  }));

  els.resetFilters.addEventListener("click", () => {
    els.searchInput.value = "";
    els.locationFilter.value = "";
    els.typeFilter.value = "";
    els.ratingFilter.value = "0";
    els.sortSelect.value = "quality";
    els.hasReviews.checked = false;
    els.hasHours.checked = false;
    state.selectedId = null;
    filterPois();
  });

  els.poiList.addEventListener("click", (event) => {
    const card = event.target.closest(".poi-card");
    if (!card) return;
    selectPoi(Number(card.dataset.id), true);
  });
}

async function init() {
  const response = await fetch("./data/pois.json");
  const data = await response.json();
  state.pois = data.pois.map((poi) => ({ ...poi, _search: poiSearchText(poi) }));
  populateFilters(data.meta);
  bindEvents();
  filterPois();
}

init().catch((error) => {
  els.poiList.innerHTML = `<div class="empty-state">Không tải được dữ liệu: ${escapeHtml(error.message)}</div>`;
});
