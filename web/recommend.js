"use strict";
let city = tripStore.city(),
  version = 0,
  controller = null,
  lastResult = null;
const topics = [
  "văn hóa",
  "lịch sử",
  "thiên nhiên",
  "gia đình",
  "ẩm thực",
  "thư giãn",
  "nghệ thuật",
  "chụp ảnh",
  "tâm linh",
  "biển",
];
let activeTopics = new Set();
function restore() {
  const d = tripStore.read(city),
    r = d.recommendation || {};
  $("location").value = city;
  $("date").value = d.fields.tripDate;
  $("latitude").value = d.fields.latitude;
  $("longitude").value = d.fields.longitude;
  $("interests").value = r.text ?? d.fields.interests;
  $("radius").value = r.radius || 30;
  $("preset").value = r.preset || "balanced";
  $("tourismScope").value = r.scope ?? (city === "Đà Nẵng" ? "danang_hoian" : "");
  $("tourismOnly").value = String(r.tourismOnly ?? true);
  $("categoryMode").value = r.categoryMode || "preferred";
  $("requireKnownHours").checked = !!r.requireKnownHours;
  $("allowNonMatching").checked = !!r.allowNonMatching;
  activeTopics = new Set(r.topics || []);
  for (const option of $("categories").options)
    option.selected = (r.categories || [d.fields.tripTheme]).includes(
      option.value,
    );
  for (const option of $("excludedCategories").options)
    option.selected = (r.excludedCategories || []).includes(option.value);
  renderTopics();
  tripStore.nav(city, d.selected.length);
}
function renderTopics() {
  const container = $("topics");
  container.replaceChildren();
  for (const text of topics) {
    const b = button(
      text,
      () => {
        if (activeTopics.has(text)) activeTopics.delete(text);
        else activeTopics.add(text);
        renderTopics();
        invalidate();
      },
      "topic",
    );
    b.setAttribute("aria-pressed", String(activeTopics.has(text)));
    container.append(b);
  }
}
function save() {
  const d = tripStore.read(city),
    previous = JSON.stringify(d.fields),
    moved =
      Number(d.fields.latitude) !== Number($("latitude").value) ||
      Number(d.fields.longitude) !== Number($("longitude").value);
  d.fields = {
    ...d.fields,
    tripDate: $("date").value,
    latitude: $("latitude").value,
    longitude: $("longitude").value,
    interests: [...activeTopics, $("interests").value]
      .filter(Boolean)
      .join(", "),
    tripTheme: $("categories").selectedOptions[0]?.value || "",
  };
  d.recommendation = {
    text: $("interests").value,
    topics: [...activeTopics],
    categories: [...$("categories").selectedOptions].map((o) => o.value),
    radius: Number($("radius").value),
    preset: $("preset").value,
    scope: $("tourismScope").value,
    tourismOnly: $("tourismOnly").value === "true",
    categoryMode: $("categoryMode").value,
    excludedCategories: [...$("excludedCategories").selectedOptions].map(
      (o) => o.value,
    ),
    requireKnownHours: $("requireKnownHours").checked,
    allowNonMatching: $("allowNonMatching").checked,
  };
  if (moved) d.startLabel = "Vị trí đã chọn trong yêu cầu gợi ý";
  if (previous !== JSON.stringify(d.fields)) d.stale = !!(d.result || d.chosen);
  tripStore.save(city, d);
  return d;
}
function invalidate() {
  version++;
  controller?.abort();
  $("recommendButton").disabled = false;
  lastResult = null;
  $("results").replaceChildren();
  $("resultSummary").textContent =
    "Nhu cầu đã thay đổi. Bấm Nhận gợi ý để cập nhật.";
  save();
}
function render() {
  if (!lastResult) return;
  const selected = new Set(tripStore.read(city).selected.map((p) => p.poi_id));
  $("results").replaceChildren(
    ...lastResult.items.map((p) =>
      poiCard(p, {
        selected: selected.has(p.poi_id),
        metric: lastResult.travel_metric,
        onDetail: openPoiDialog,
        onToggle: (poi) => {
          if (tripStore.toggle(poi, city)) {
            render();
            tell(
              "Đã cập nhật chuyến đi. Bạn có thể tiếp tục chọn hoặc sang Lịch trình.",
            );
          }
        },
      }),
    ),
  );
}
async function recommend() {
  if (!$("recommendForm").reportValidity()) return;
  const d = save(),
    r = d.recommendation;
  controller?.abort();
  controller = new AbortController();
  const current = ++version;
  $("recommendButton").disabled = true;
  $("resultSummary").textContent =
    "Đang đối chiếu sở thích, vị trí và dữ liệu địa điểm…";
  try {
    const interests = r.text
        .split(/[,;\n]/)
        .map((x) => x.trim())
        .filter(Boolean);
    const data = await post(
      "/api/v2/recommendations",
      {
        location: city,
        scope: r.scope,
        tourism_only: r.tourismOnly,
        date: d.fields.tripDate,
        start: {
          latitude: Number(d.fields.latitude),
          longitude: Number(d.fields.longitude),
        },
        interests,
        experience_topics: [...activeTopics],
        preferred_categories: r.categories,
        excluded_categories: r.excludedCategories,
        category_mode: r.categoryMode,
        require_known_hours: r.requireKnownHours,
        allow_non_matching: r.allowNonMatching,
        preset: r.preset,
        radius_km: r.radius,
        top_k: 10,
        selected_poi_ids: d.selected.map((p) => p.poi_id),
      },
      controller.signal,
    );
    if (current !== version) return;
    lastResult = data;
    render();
    $("resultSummary").textContent = data.items.length
      ? `${data.items.length} gợi ý · xếp hạng từ ${data.candidate_count} ứng viên có bằng chứng phù hợp (${data.matching_count}/${data.eligible_count} POI qua điều kiện cứng).`
      : data.message;
    const understood = data.interpreted_request,
      understoodParts = [
        understood.positive_concepts.length
          ? `chủ đề ${understood.positive_concepts.join(", ")}`
          : "",
        understood.preferred_categories.length
          ? `${understood.category_mode === "only" ? "chỉ " : "ưu tiên "}${understood.preferred_categories.map((x) => labels[x] || x).join(", ")}`
          : "",
        understood.excluded_categories.length
          ? `loại ${understood.excluded_categories.map((x) => labels[x] || x).join(", ")}`
          : "",
      ].filter(Boolean);
    tell(
      (understoodParts.length
        ? `Hệ thống hiểu: ${understoodParts.join("; ")}. `
        : data.personalized
          ? "Gợi ý theo nhu cầu bạn khai báo. "
        : "Chưa khai báo sở thích: gợi ý theo vị trí và mẫu ưu tiên. ") +
        (data.filter_message ? `${data.filter_message} ` : "") +
        data.routing_message,
    );
  } catch (e) {
    if (current === version && e.name !== "AbortError") {
      $("resultSummary").textContent = e.message;
      lastResult = null;
      $("results").replaceChildren();
    }
  } finally {
    if (current === version) $("recommendButton").disabled = false;
  }
}
for (const [value, text] of Object.entries(labels)) {
  const option = node("option", text);
  option.value = value;
  $("categories").append(option);
  const excluded = node("option", text);
  excluded.value = value;
  $("excludedCategories").append(excluded);
}
restore();
$("recommendForm").onsubmit = (e) => {
  e.preventDefault();
  recommend();
};
$("recommendForm").addEventListener("change", (e) => {
  if (e.target.id !== "location") invalidate();
});
$("interests").addEventListener("input", invalidate);
$("location").onchange = () => {
  save();
  city = $("location").value;
  tripStore.save(city, tripStore.read(city));
  restore();
  invalidate();
};
$("locate").onclick = () => {
  if (!navigator.geolocation) {
    tell("Hãy nhập tọa độ hoặc chọn điểm xuất phát tại trang Khám phá.");
    return;
  }
  const requestCity = city;
  navigator.geolocation.getCurrentPosition(
    (p) => {
      if (city !== requestCity) return;
      $("latitude").value = p.coords.latitude.toFixed(6);
      $("longitude").value = p.coords.longitude.toFixed(6);
      invalidate();
      tell("Đã lấy vị trí của bạn.");
    },
    () =>
      tell(
        "Chưa lấy được vị trí. Bạn có thể nhập tọa độ hoặc chọn trên trang Khám phá.",
      ),
    { timeout: 10000 },
  );
};
window.addEventListener("storage", () => {
  version++;
  controller?.abort();
  city = tripStore.city();
  restore();
  lastResult = null;
  $("results").replaceChildren();
  $("recommendButton").disabled = false;
  $("resultSummary").textContent =
    "Lựa chọn đã thay đổi ở tab khác. Bấm Nhận gợi ý để cập nhật.";
});
