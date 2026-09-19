"use strict";
function exploreFilters() {
  const location = $("locationFilter").value, category = $("typeFilter").value;
  return {scope: location === "danang_hoian" ? location : "", location: location === "danang_hoian" ? "" : location,
    category: category === "tourism" ? "" : category, tourism_only: category === "tourism"};
}
const state = {
  city: tripStore.city(),
  basemapVersion: 0,
  listVersion: 0,
  detailVersion: 0,
  offset: 0,
  pois: [],
  pickingStart: new URLSearchParams(location.search).get("pick") === "start",
};
function renderList() {
  const ids = new Set(tripStore.read(state.city).selected.map((p) => p.poi_id));
  $("poiList").replaceChildren(
    ...state.pois.map((p) =>
      poiCard(p, {
        selected: ids.has(p.poi_id),
        onDetail: (p) => loadPoiDetail(p.poi_id),
        onToggle: (p) => {
          if (tripStore.toggle(p, state.city)) renderList();
        },
      }),
    ),
  );
}
async function loadPois(append = false) {
  const v = ++state.listVersion;
  if (!append) state.offset = 0;
  $("loadMore").disabled = true;
  const params = new URLSearchParams({
    view: "explore",
    ...exploreFilters(),
    query: $("searchInput").value,
    limit: 40,
    offset: state.offset,
  });
  try {
    const data = await api("/api/v2/pois?" + params);
    if (v !== state.listVersion) return;
    state.pois = append ? [...state.pois, ...data.pois] : data.pois;
    renderList();
    $("listTitle").textContent =
      `Địa điểm (${data.total.toLocaleString("vi-VN")})`;
    $("loadMore").hidden = !data.has_more;
    if (!state.pois.length)
      $("poiList").append(
        node(
          "p",
          "Chưa có kết quả. Hãy thử tên khác hoặc mở rộng bộ lọc.",
          "empty-state",
        ),
      );
    if (!append) loadMapPois();
  } catch (e) {
    if (v === state.listVersion) tell(e.message);
  } finally {
    if (v === state.listVersion) $("loadMore").disabled = false;
  }
}
function saveOrigin(lat, lon, label) {
  const d = tripStore.read(state.city);
  d.fields.latitude = lat;
  d.fields.longitude = lon;
  d.startLabel = label;
  d.stale = !!(d.result || d.chosen);
  tripStore.save(state.city, d);
  state.pickingStart = false;
  $("mapInstruction").hidden = true;
  if (startMarker) map.removeLayer(startMarker);
  startMarker = L.marker([lat, lon]).addTo(map).bindPopup(label);
  tell(
    "Đã lưu điểm xuất phát cho " +
      state.city +
      ". Quay lại Gợi ý POI để tìm địa điểm phù hợp.",
  );
}
function onMapStart(lat, lon) {
  if (state.pickingStart) saveOrigin(lat, lon, "Vị trí bạn ghim trên bản đồ");
}
async function loadPoiDetail(ident) {
  const v = ++state.detailVersion;
  try {
    const { poi: p } = await api(
      `/api/v2/pois/${encodeURIComponent(ident)}?view=explore`,
    );
    if (v !== state.detailVersion) return;
    highlightPoi(p);
    map?.setView([p.latitude, p.longitude], 15, { animate: false });
    const panel = $("detailPanel"),
      close = button(
        "Đóng",
        () => {
          state.detailVersion++;
          panel.replaceChildren();
        },
        "dialog-close",
      );
    panel.replaceChildren(
      close,
      node("h2", p.name),
      imageElement(p.image, p.name),
      node("p", `${labels[p.category]} · ${p.location}`),
      node("p", p.description || "Chưa có mô tả."),
      node(
        "p",
        p.hours_raw || "Chưa có giờ mở cửa; cần kiểm tra trước khi đi.",
      ),
    );
    if (p.requires_boat) panel.append(node("p", "Cần chặng tàu ra Cù Lao Chàm; chưa hỗ trợ trong lịch trình ô tô.", "quality-note"));
    appendPlaceMetadata(panel, p);
    if (basemapConfig[p.location] && p.manual_trip_quality?.eligible) {
      if (p.location !== state.city)
        panel.append(
          button("Chọn chuyến đi tại " + p.location, () => {
            $("tripCity").value = p.location;
            $("tripCity").dispatchEvent(new Event("change"));
            loadPoiDetail(ident);
          }),
        );
      else {
        const has = tripStore
          .read(state.city)
          .selected.some((x) => x.poi_id === ident);
        panel.append(
          button(
            has ? "Bỏ khỏi chuyến đi" : "Thêm vào chuyến đi",
            () => {
              tripStore.toggle(p, state.city);
              renderList();
              loadPoiDetail(ident);
            },
            "primary",
          ),
        );
      }
      panel.append(
        button("Xuất phát từ đây", () => {
          if (state.city !== p.location) {
            state.city = p.location;
            $("tripCity").value = p.location;
          }
          saveOrigin(p.latitude, p.longitude, p.name);
        }),
      );
    } else
      panel.append(
        node(
          "p",
          "Địa điểm này hiện chỉ hỗ trợ khám phá, chưa đủ điều kiện lập lịch tại địa bàn đang hỗ trợ.",
          "quality-note",
        ),
      );
    if (p.source_url) panel.append(safeLink(p.source_url, "Xem nguồn"));
    if (matchMedia("(max-width:800px)").matches)
      $("mapPanel").scrollIntoView({ block: "start" });
  } catch (e) {
    if (v === state.detailVersion) tell(e.message);
  }
}
$("tripCity").value = state.city;
$("tripCity").onchange = () => {
  state.city = $("tripCity").value;
  tripStore.save(state.city, tripStore.read(state.city));
  renderList();
  tell("Chuyến đi đang chọn: " + state.city);
};
for (const [value, text] of Object.entries(labels)) {
  const option = node("option", text);
  option.value = value;
  $("typeFilter").append(option);
}
$("typeFilter").onchange = () => loadPois();
let timer;
$("searchInput").oninput = () => {
  state.listVersion++;
  clearTimeout(timer);
  timer = setTimeout(() => loadPois(), 250);
};
$("locationFilter").onchange = () => {
  const c = basemapConfig[$("locationFilter").value === "danang_hoian" ? "Đà Nẵng" : $("locationFilter").value];
  if (c) map?.setView(c.center, 12, { animate: false });
  loadBasemap($("locationFilter").value === "danang_hoian" ? "Đà Nẵng" : $("locationFilter").value);
  loadPois();
};
$("loadMore").onclick = () => {
  state.offset += 40;
  loadPois(true);
};
$("pickStart").onclick = () => {
  state.pickingStart = !state.pickingStart;
  $("mapInstruction").hidden = !state.pickingStart;
};
(async () => {
  try {
    const data = await api("/api/v2/pois?view=explore&limit=1");
    for (const text of data.locations) {
      const o = node("option", text);
      o.value = text;
      $("locationFilter").append(o);
    }
    await initializeMap();
    if ($("locationFilter").value === "danang_hoian") map?.setView([16.02, 108.25], 11);
    if (state.pickingStart) {
      $("mapInstruction").hidden = false;
      map?.setView(basemapConfig[state.city].center, 12, { animate: false });
    }
    await loadPois();
    const poi = new URLSearchParams(location.search).get("poi");
    if (poi) loadPoiDetail(poi);
  } catch (e) {
    tell(e.message);
  }
})();
window.addEventListener("storage", () => {
  state.city = tripStore.city();
  $("tripCity").value = state.city;
  tripStore.nav();
  renderList();
});
