"use strict";
const $ = (id) => document.getElementById(id);
const labels = {
  water_park: "Công viên nước",
  playground: "Sân chơi",
  walking_street: "Phố đi bộ và đường dạo",
  bridge: "Cầu tham quan",
  cave: "Hang động",
  waterfall: "Thác nước",
  campground: "Khu cắm trại",
  trailhead: "Điểm bắt đầu đường mòn",
  museum: "Bảo tàng",
  historic: "Di tích",
  attraction: "Tham quan",
  viewpoint: "Ngắm cảnh",
  park: "Công viên",
  beach: "Bãi biển",
  temple: "Đền/chùa",
  gallery: "Triển lãm",
  zoo: "Vườn thú",
  theme_park: "Khu vui chơi",
  old_quarter: "Phố cổ",
  craft_village: "Làng nghề",
  market: "Chợ",
  nature_area: "Khu thiên nhiên",
  performance_venue: "Biểu diễn",
  restaurant: "Nhà hàng",
  cafe: "Cà phê",
  food_street: "Khu ẩm thực",
};
const foodCategories = new Set(["restaurant", "cafe", "food_street"]);
const basemapConfig = {
  "Hà Nội": { slug: "hanoi", center: [21.0285, 105.8542] },
  "Đà Nẵng": { slug: "danang", center: [16.0544, 108.2022] },
};
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function appendPlaceMetadata(panel, poi) {
  const clean = value => String(value).replace(/[\ue000-\uf8ff]/g, "").replace(/\s+/g, " ").trim();
  if (poi.address_raw) panel.append(node("p", clean(poi.address_raw)));
  if (poi.phone) panel.append(node("p", "Điện thoại: " + clean(poi.phone)));
  if (poi.website) panel.append(safeLink(poi.website, "Website địa điểm"));
  if (poi.admission_raw?.length) panel.append(node("p", "Vé/phí theo nguồn: " + poi.admission_raw.join(" · ")));
  for (const image of (poi.images || []).filter(i => i.url !== poi.image).slice(0, 3)) panel.append(imageElement(image.url, poi.name));
}
function button(text, handler, className) {
  const el = node("button", text, className);
  el.type = "button";
  el.onclick = handler;
  return el;
}
function tell(text) {
  const status = $("systemStatus");
  if (status) status.textContent = text;
}
function safeLink(url, text) {
  try {
    const u = new URL(url);
    if (!["http:", "https:"].includes(u.protocol) || u.username || u.password)
      return node("span", text);
    const el = node("a", text);
    el.href = u.href;
    el.target = "_blank";
    el.rel = "noopener noreferrer";
    return el;
  } catch {
    return node("span", text);
  }
}
function imageElement(url, name = "địa điểm") {
  const fallback = node("div", "Chưa có ảnh", "photo");
  try {
    const u = new URL(url);
    if (
      u.protocol !== "https:" ||
      u.username ||
      u.password ||
      /\/ogw\/|\/a-\//.test(u.pathname)
    )
      return fallback;
    const img = node("img");
    img.src = u.href;
    img.alt = `Ảnh ${name}`;
    img.loading = "lazy";
    img.className = "photo";
    img.onerror = () => img.replaceWith(fallback);
    return img;
  } catch {
    return fallback;
  }
}
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((i) => i.msg).join("; ")
      : data.detail;
    throw new Error(detail || "Chưa đọc được dữ liệu. Hãy thử lại.");
  }
  return data;
}
function post(path, data, signal) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    signal,
  });
}
function today() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
const tripStore = {
  city() {
    try {
      const c = localStorage.getItem("where2go-trip-city-v1");
      return basemapConfig[c] ? c : "Đà Nẵng";
    } catch {
      return "Đà Nẵng";
    }
  },
  read(city = this.city()) {
    let d = {};
    try {
      d = JSON.parse(localStorage.getItem(`where2go-trip-v1:${city}`) || "{}");
    } catch {
      tell("Nháp cũ chưa đọc được. Hãy chọn lại địa điểm.");
    }
    if (!d || d.version !== 1) d = {};
    const center = basemapConfig[city].center;
    return {
      ...d,
      version: 1,
      fields: {
        tripDate: today(),
        startTime: "08:00",
        endTime: "18:00",
        timePreset: "day",
        latitude: center[0],
        longitude: center[1],
        interests: "",
        tripTheme: "",
        includeMeals: true,
        ...d.fields,
      },
      selected: Array.isArray(d.selected)
        ? d.selected
            .filter((p) => p && p.poi_id && p.location === city)
            .slice(0, 12)
        : [],
      required: Array.isArray(d.required) ? d.required : [],
      durations: d.durations || {},
    };
  },
  save(city, d) {
    try {
      localStorage.setItem(`where2go-trip-v1:${city}`, JSON.stringify(d));
      localStorage.setItem("where2go-trip-city-v1", city);
      this.nav(city, d.selected.length);
      return true;
    } catch {
      tell("Bộ nhớ trình duyệt bị chặn hoặc đầy; chưa lưu được lựa chọn.");
      return false;
    }
  },
  nav(city = this.city(), count = this.read(city).selected.length) {
    document
      .querySelectorAll("[data-trip-count]")
      .forEach((el) => (el.textContent = count));
  },
  toggle(p, city = this.city()) {
    const d = this.read(city),
      exists = d.selected.some((x) => x.poi_id === p.poi_id);
    if (!exists) {
      if (p.location !== city || p.manual_trip_quality?.eligible === false) {
        tell("Chọn địa phương chuyến đi phù hợp trước khi thêm địa điểm.");
        return false;
      }
      if (d.selected.length >= 12) {
        tell("Mỗi chuyến hỗ trợ tối đa 12 địa điểm.");
        return false;
      }
      d.selected.push(p);
      if (d.manualOrder) d.manualOrder.push(p.poi_id);
    } else {
      d.selected = d.selected.filter((x) => x.poi_id !== p.poi_id);
      d.required = d.required.filter((i) => i !== p.poi_id);
      delete d.durations[p.poi_id];
      if (d.manualOrder)
        d.manualOrder = d.manualOrder.filter((i) => i !== p.poi_id);
    }
    d.stale = !!(d.result || d.chosen);
    return this.save(city, d);
  },
};
function poiCard(p, { selected = false, onToggle, onDetail, metric } = {}) {
  const article = node("article", undefined, "poi-card");
  article.dataset.poiId = p.poi_id;
  article.classList.toggle("is-selected", selected);
  article.append(imageElement(p.image, p.name));
  const copy = node("div", undefined, "card-copy");
  if (p.rank) copy.append(node("span", `Gợi ý ${p.rank}`, "eyebrow"));
  copy.append(
    button(p.name, () => onDetail?.(p), "poi-title"),
    node("p", `${labels[p.category] || p.category} · ${p.location}`),
  );
  for (const reason of p.reasons || [])
    copy.append(node("p", reason, "reason"));
  if (p.criteria) {
    const details = node("details", undefined, "score-detail");
    details.append(node("summary", "Vì sao được gợi ý?"));
    details.append(
      node(
        "p",
        `Điểm xếp hạng tương đối: ${p.score.toFixed(3)}. Chỉ so trong lượt gợi ý này.`,
      ),
    );
    const names = {
      preference_match: "Khớp sở thích",
      place_quality: "Chất lượng tham khảo",
      travel_cost:
        metric === "road_time" ? "Lái xe (phút)" : "Đường chim bay (km)",
      data_confidence: "Bằng chứng dữ liệu",
    };
    const dl = node("dl");
    for (const [key, value] of Object.entries(p.criteria)) {
      dl.append(
        node("dt", names[key]),
        node(
          "dd",
          (key === "travel_cost" && metric === "road_time"
            ? value / 60
            : value
          ).toFixed(2),
        ),
      );
    }
    details.append(dl);
    const r = p.explanation?.rating?.observation;
    details.append(
      node(
        "p",
        r
          ? `${r.provider}: ${r.rating}/5, ${r.review_count} lượt; quan sát ${r.observed_at || "chưa rõ ngày"}.`
          : "Chưa có rating đủ bằng chứng. Giá trị trung tính không phải điểm đánh giá thực.",
      ),
    );
    for (const warning of p.warnings || [])
      details.append(node("p", warning, "quality-note"));
    const sources = [
      ...new Set(
        Object.values(p.provenance || {})
          .filter((x) => x.source_key)
          .map((x) =>
            x.source_key.startsWith("osm:")
              ? "OpenStreetMap"
              : "Workbook / quan sát bổ sung",
          ),
      ),
    ];
    if (sources.length)
      details.append(node("p", "Nguồn dữ liệu: " + sources.join(", ")));
    if (p.source_url)
      details.append(safeLink(p.source_url, "Xem nguồn địa điểm"));
    copy.append(details);
  }
  const add = button(
    selected ? "Bỏ khỏi chuyến đi" : "Thêm vào chuyến đi",
    () => onToggle?.(p),
    "add-place",
  );
  add.disabled =
    !selected &&
    (p.manual_trip_quality?.eligible === false ||
      p.location !== tripStore.city());
  copy.append(add);
  article.append(copy);
  return article;
}
async function openPoiDialog(p) {
  const dialog = $("poiDialog");
  if (!dialog) return;
  dialog.showModal();
  dialog.replaceChildren(
    button("Đóng", () => dialog.close(), "dialog-close"),
    node("p", "Đang tải địa điểm…"),
  );
  const ident = p.poi_id;
  dialog.dataset.poiId = ident;
  try {
    const { poi } = await api(
      `/api/v2/pois/${encodeURIComponent(ident)}?view=explore`,
    );
    if (!dialog.open || dialog.dataset.poiId !== ident) return;
    dialog.replaceChildren(
      button("Đóng", () => dialog.close(), "dialog-close"),
      node("h2", poi.name),
      imageElement(poi.image, poi.name),
      node("p", poi.description || "Chưa có mô tả."),
      node("p", poi.hours_raw || "Chưa có giờ mở cửa; kiểm tra trước khi đi."),
    );
    appendPlaceMetadata(dialog, poi);
    const a = node("a", "Xem trên bản đồ", "button-link");
    a.href = "/explore?poi=" + encodeURIComponent(ident);
    dialog.append(a);
    if (poi.source_url) dialog.append(safeLink(poi.source_url, "Xem nguồn"));
  } catch (e) {
    if (dialog.open && dialog.dataset.poiId === ident)
      dialog.append(node("p", e.message));
  }
}
document.addEventListener("DOMContentLoaded", () => tripStore.nav());
window.addEventListener("pageshow", (e) => {
  if (e.persisted) location.reload();
});
