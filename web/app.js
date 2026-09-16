const state = {
  pois: [],
  filtered: [],
  selectedId: null,
  markers: new Map(),
  interactions: [],
};

const ACTION_WEIGHTS = { view: 1, click: 2, save: 3, like: 4, visit: 5 };
const INTERACTION_STORAGE_KEY = "vietnam-poi-interactions-v1";

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
  userMode: document.querySelector("#userMode"),
  recommendationMode: document.querySelector("#recommendationMode"),
  recommendationQuery: document.querySelector("#recommendationQuery"),
  recommendButton: document.querySelector("#recommendButton"),
  recommendationList: document.querySelector("#recommendationList"),
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

function loadInteractions() {
  try {
    const saved = JSON.parse(localStorage.getItem(INTERACTION_STORAGE_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch (error) {
    return [];
  }
}

function saveInteractions() {
  localStorage.setItem(INTERACTION_STORAGE_KEY, JSON.stringify(state.interactions));
}

function ensureDemoInteractions() {
  if (state.interactions.some((event) => event.userId === "user_demo")) return;
  state.pois.slice(0, 4).forEach((poi, index) => {
    state.interactions.push({
      userId: "user_demo",
      poiId: poi.id,
      action: index === 0 ? "save" : "click",
      timestamp: Date.now() - (4 - index) * 86400000,
    });
  });
  saveInteractions();
}

function userHistory(userId) {
  if (userId === "new") return [];
  return state.interactions
    .filter((event) => event.userId === userId)
    .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
}

function tokenSet(value) {
  return new Set(normalize(value).split(/\s+/).filter(Boolean));
}

function overlapScore(left, right) {
  const a = tokenSet(left);
  const b = tokenSet(right);
  if (!a.size || !b.size) return 0;
  let shared = 0;
  a.forEach((token) => { if (b.has(token)) shared += 1; });
  return shared / Math.max(a.size, b.size);
}

function minMaxValues(values) {
  const numeric = values.map((value) => Number(value) || 0);
  const low = Math.min(...numeric);
  const high = Math.max(...numeric);
  if (high === low) return numeric.map(() => 0);
  return numeric.map((value) => (value - low) / (high - low));
}

function behaviorScoreMap(userId) {
  const history = userHistory(userId);
  const globalCounts = new Map();
  state.interactions.forEach((event) => {
    globalCounts.set(event.poiId, (globalCounts.get(event.poiId) || 0) + (ACTION_WEIGHTS[event.action] || 1));
  });
  const personalCounts = new Map();
  history.forEach((event) => {
    personalCounts.set(event.poiId, (personalCounts.get(event.poiId) || 0) + (ACTION_WEIGHTS[event.action] || 1));
  });
  const lastPoi = state.pois.find((poi) => poi.id === history[0]?.poiId);
  const raw = state.pois.map((poi) => {
    const personal = personalCounts.get(poi.id) || 0;
    const global = globalCounts.get(poi.id) || 0;
    const transition = lastPoi ? Math.max(overlapScore(poi.type, lastPoi.type), overlapScore(poi.keywords.join(" "), lastPoi.keywords.join(" "))) : 0;
    return 0.60 * personal + 0.15 * global + 0.25 * transition;
  });
  const normalized = minMaxValues(raw);
  return new Map(state.pois.map((poi, index) => [poi.id, normalized[index]]));
}

function recommendationRows() {
  const userId = els.userMode.value;
  const query = els.recommendationQuery.value;
  const history = userHistory(userId);
  const historyIds = new Set(history.map((event) => event.poiId));
  const behavior = behaviorScoreMap(userId);
  const knownUser = userId !== "new" && history.length > 0;
  const rawRows = state.pois
    .filter((poi) => !historyIds.has(poi.id))
    .map((poi) => {
      const content = query ? overlapScore(query, poiSearchText(poi)) : poi.quality || 0;
      const behaviorScore = knownUser ? behavior.get(poi.id) || 0 : 0;
      const candidateScore = knownUser ? 0.65 * behaviorScore + 0.35 * content : content;
      const typeContext = query ? overlapScore(query, `${poi.type} ${poi.location}`) : 0.5;
      const distanceScore = 1;
      const qualityScore = poi.quality || 0;
      const contextualScore = 0.35 * behaviorScore + 0.20 * distanceScore + 0.20 * qualityScore + 0.25 * typeContext;
      return { poi, candidateScore, behaviorScore, contentScore: content, distanceScore, qualityScore, typeContext, contextualScore };
    })
    .sort((a, b) => b.candidateScore - a.candidateScore)
    .slice(0, 80);

  if (!rawRows.length) return [];
  const criteria = rawRows.map((row) => [row.behaviorScore, row.contentScore, row.distanceScore, row.qualityScore, row.typeContext]);
  const columnNorms = [0, 1, 2, 3, 4].map((column) => Math.sqrt(criteria.reduce((sum, row) => sum + row[column] ** 2, 0)) || 1);
  const weights = [0.30, 0.20, 0.15, 0.20, 0.15];
  const weighted = criteria.map((row) => row.map((value, column) => value / columnNorms[column] * weights[column]));
  const best = [0, 1, 2, 3, 4].map((column) => Math.max(...weighted.map((row) => row[column])));
  const worst = [0, 1, 2, 3, 4].map((column) => Math.min(...weighted.map((row) => row[column])));
  return rawRows.map((row, index) => {
    const toBest = Math.sqrt(weighted[index].reduce((sum, value, column) => sum + (value - best[column]) ** 2, 0));
    const toWorst = Math.sqrt(weighted[index].reduce((sum, value, column) => sum + (value - worst[column]) ** 2, 0));
    return { ...row, topsisScore: toWorst / (toBest + toWorst || 1) };
  }).sort((a, b) => b.topsisScore - a.topsisScore).slice(0, 8);
}

function renderRecommendations() {
  if (!els.recommendationList) return;
  const knownUser = els.userMode.value !== "new";
  els.recommendationMode.textContent = knownUser ? "Behavior + context" : "Cold-start";
  const rows = recommendationRows();
  els.recommendationList.innerHTML = rows.length ? rows.map((row, index) => `
    <button class="recommendation-item" data-id="${row.poi.id}" type="button">
      <span class="recommendation-rank">${index + 1}</span>
      <span><strong>${escapeHtml(row.poi.name)}</strong><small>${escapeHtml(row.poi.location)} · ${escapeHtml(row.poi.type || "Unknown")}</small></span>
      <span class="recommendation-score">${(row.topsisScore * 100).toFixed(0)}%</span>
    </button>
  `).join("") : `<div class="empty-state">Chưa có gợi ý.</div>`;
}

function recordInteraction(poiId, action) {
  const userId = els.userMode?.value;
  if (!userId || userId === "new") return;
  state.interactions.push({ userId, poiId, action, timestamp: Date.now() });
  saveInteractions();
  renderRecommendations();
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
      <button class="action-button" data-action="save" type="button">Lưu</button>
      <button class="action-button" data-action="visit" type="button">Đã ghé</button>
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

  els.recommendButton.addEventListener("click", renderRecommendations);
  els.userMode.addEventListener("change", renderRecommendations);
  els.recommendationQuery.addEventListener("input", renderRecommendations);
  els.recommendationList.addEventListener("click", (event) => {
    const item = event.target.closest(".recommendation-item");
    if (!item) return;
    selectPoi(Number(item.dataset.id), true);
    recordInteraction(Number(item.dataset.id), "click");
  });
  els.detailPanel.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) return;
    const poi = state.pois.find((item) => item.id === state.selectedId);
    if (poi) recordInteraction(poi.id, actionButton.dataset.action);
  });
}

async function init() {
  // Always load the latest generated coordinates during local development.
  const response = await fetch("./data/pois.json", { cache: "no-store" });
  const data = await response.json();
  state.pois = data.pois.map((poi) => ({ ...poi, _search: poiSearchText(poi) }));
  state.interactions = loadInteractions();
  ensureDemoInteractions();
  populateFilters(data.meta);
  bindEvents();
  filterPois();
  renderRecommendations();
}

init().catch((error) => {
  els.poiList.innerHTML = `<div class="empty-state">Không tải được dữ liệu: ${escapeHtml(error.message)}</div>`;
});
