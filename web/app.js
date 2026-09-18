"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  pois: [], selectedId: null, saved: new Set(), required: new Set(), durationOverrides: {},
  listVersion: 0, planVersion: 0, lastPlan: null,
};
try { state.saved = new Set(JSON.parse(localStorage.getItem("where2go-saved-v2") || "[]")); } catch {}
const labels = {
  museum:"Bảo tàng", historic:"Di tích", attraction:"Tham quan", viewpoint:"Ngắm cảnh",
  park:"Công viên", beach:"Bãi biển", temple:"Đền/chùa", gallery:"Triển lãm",
  zoo:"Vườn thú", theme_park:"Khu vui chơi", old_quarter:"Phố cổ", craft_village:"Làng nghề",
  market:"Chợ", nature_area:"Khu thiên nhiên", performance_venue:"Biểu diễn",
  restaurant:"Nhà hàng", cafe:"Cà phê", food_street:"Khu ẩm thực",
};
const foodCategories = new Set(["restaurant", "cafe", "food_street"]);
const durationLabels = {
  category_default:"Ước lượng theo loại hình",
  curated_planning_estimate:"Ước lượng biên tập cho POI",
  manual_estimate:"Ước lượng đã nhập thủ công",
  source_reported:"Thời lượng từ nguồn",
  user_override:"Người dùng điều chỉnh",
};
const criterionLabels = {
  preference_match:"Sở thích", place_quality:"Chất lượng điểm đến",
  drive_time:"Thời gian lái xe", data_confidence:"Độ tin cậy dữ liệu",
};
const map = window.L ? L.map("map").setView([21.0285,105.8542],12) : null;
let markerLayer, startMarker, routeLayer;

if (map) {
  const tiles=L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'});
  let tileFailures=0;
  tiles.on("loading",()=>{tileFailures=0;});
  tiles.on("tileerror",()=>{tileFailures++;$("mapStatus").hidden=false;$("mapStatus").textContent="Không tải được một phần hoặc toàn bộ nền bản đồ. Lịch trình và đường OSRM vẫn có thể hoạt động.";});
  tiles.on("load",()=>{if(!tileFailures) $("mapStatus").hidden=true;});
  tiles.addTo(map);
  markerLayer=L.layerGroup().addTo(map);
  map.on("click",(event)=>{$("latitude").value=event.latlng.lat.toFixed(6);$("longitude").value=event.latlng.lng.toFixed(6);updateStart();invalidatePlan();});
} else {
  $("mapStatus").hidden=false;
  $("mapStatus").textContent="Chưa tải được thư viện bản đồ. Bạn vẫn có thể nhập tọa độ và đọc lịch trình.";
}

function node(tag,text,className) {
  const item=document.createElement(tag);
  if(text!==undefined) item.textContent=text;
  if(className) item.className=className;
  return item;
}
function safeLink(url,text) {
  try {
    const parsed=new URL(url);
    if(!["https:","http:"].includes(parsed.protocol)||parsed.username||parsed.password) return node("span",text);
    const link=node("a",text);link.href=parsed.href;link.target="_blank";link.rel="noopener noreferrer";return link;
  } catch {return node("span",text);}
}
function downloadLink(href,text) {
  const link=node("a",text,"dataset-link");link.href=href;link.download="";return link;
}
function percent(value) {
  return `${Number(value||0).toLocaleString("vi-VN",{maximumFractionDigits:2})}%`;
}
function renderCoverage(data) {
  const panel=$("coverage");panel.replaceChildren();
  panel.append(node("p",`Catalog ${data.poi_count.toLocaleString("vi-VN")} POI \u00b7 phi\u00ean b\u1ea3n ${data.dataset_version}.`));
  for(const row of data.locations) {
    const card=node("article",undefined,"coverage-card");
    const priority=row.priority_set||{};const target=priority.target_status||{};
    card.append(node("h3",row.location));
    card.append(node("p",`${row.usable.toLocaleString("vi-VN")} POI hợp lệ; ${row.serviceable.toLocaleString("vi-VN")} đủ điều kiện phục vụ hiện tại.`));
    card.append(node("p",`To\u00e0n catalog: gi\u1edd c\u1ea5u tr\u00fac ${row.with_structured_hours.toLocaleString("vi-VN")} (${percent(row.coverage_percent?.structured_hours)}); h\u1ed3 s\u01a1 th\u1eddi l\u01b0\u1ee3ng ri\u00eang ${row.with_specific_duration.toLocaleString("vi-VN")} (${percent(row.coverage_percent?.specific_duration)}), \u0111\u00e3 x\u00e1c minh ${row.with_verified_duration.toLocaleString("vi-VN")} (${percent(row.coverage_percent?.verified_duration)}); \u0111i\u1ec3m ti\u1ebfp c\u1eadn x\u00e1c minh ${row.with_verified_access.toLocaleString("vi-VN")} (${percent(row.coverage_percent?.verified_access)}).`));
    card.append(node("p",`T\u1eadp \u01b0u ti\u00ean ${priority.selected||0}/70: ${priority.attractions||0}/50 tham quan, ${priority.food_rest||0}/20 \u0103n/ngh\u1ec9; gi\u1edd ${percent(priority.hours_percent)}; h\u1ed3 s\u01a1 th\u1eddi l\u01b0\u1ee3ng ri\u00eang ${percent(priority.specific_duration_percent)}, \u0111\u00e3 x\u00e1c minh ${percent(priority.verified_duration_percent)}.`));
    const flags=node("p",undefined,"coverage-flags");
    for(const [label,ok] of [["S\u1ed1 POI",target.attractions&&target.food_rest],["Gi\u1edd \u226580%",target.hours],["Th\u1eddi l\u01b0\u1ee3ng \u0111\u00e3 x\u00e1c minh \u226580%",target.verified_duration??target.specific_duration]]) {
      flags.append(node("span",`${ok?"PASS":"CH\u01afA \u0110\u1ea0T"}: ${label}`,ok?"status-ok":"status-gap"));
    }
    card.append(flags);panel.append(card);
  }
  const downloads=$("datasetDownloads");downloads.replaceChildren(node("h3","File dataset d\u1ec5 \u0111\u1ecdc"));
  const files=[
    ["pois.csv","POI h\u1ee3p nh\u1ea5t"],["opening_hours.csv","Gi\u1edd m\u1edf c\u1eeda"],
    ["ratings.csv","Rating v\u00e0 s\u1ed1 review"],["duration_profiles.csv","H\u1ed3 s\u01a1 th\u1eddi l\u01b0\u1ee3ng"],
    ["access_points.csv","\u0110i\u1ec3m ti\u1ebfp c\u1eadn"],["sources.csv","Ngu\u1ed3n v\u00e0 quy\u1ec1n s\u1eed d\u1ee5ng"],
    ["summary.json","B\u00e1o c\u00e1o coverage"],["audit.json","Ki\u1ec3m tra t\u00ednh nh\u1ea5t qu\u00e1n"],
  ];
  for(const [file,label] of files) downloads.append(downloadLink(`/api/v2/dataset/${file}`,`${label} (${file})`));
  downloads.append(node("p","Catalog chu\u1ea9n: data/catalog_v2.sqlite. C\u00e1c CSV n\u1eb1m t\u1ea1i data/reports/v2/dataset/. D\u1eef li\u1ec7u Google Maps \u0111\u01b0\u1ee3c \u0111\u00e1nh d\u1ea5u restricted_internal."));
}
function imageElement(url) {
  const fallback=node("div","Ảnh chưa có nguồn được kiểm chứng");
  try {
    const parsed=new URL(url);
    if(parsed.protocol!=="https:"||parsed.hostname!=="upload.wikimedia.org") return fallback;
    const img=document.createElement("img");img.src=parsed.href;img.alt="Ảnh địa điểm";img.loading="lazy";img.className="detail-image";
    img.addEventListener("error",()=>img.replaceWith(fallback));return img;
  } catch {return fallback;}
}
async function api(path,options) {
  const response=await fetch(path,options);const data=await response.json();
  if(!response.ok) {
    const detail=Array.isArray(data.detail)?data.detail.map(item=>item.msg).join("; "):data.detail;
    throw new Error(detail||"Không đọc được phản hồi từ máy chủ");
  }
  return data;
}
function updateStart() {
  const coords=[Number($("latitude").value),Number($("longitude").value)];
  if(!map||!coords.every(Number.isFinite)) return;
  if(startMarker) startMarker.setLatLng(coords); else startMarker=L.marker(coords).addTo(map).bindPopup("Điểm xuất phát và quay về");
}
function latestRating(poi) {
  return [...(poi.ratings||[])].filter(row=>row.same_observation).sort((a,b)=>(b.observed_at||"").localeCompare(a.observed_at||""))[0];
}
function showDetail(poi) {
  state.selectedId=poi.poi_id;
  const panel=$("detailPanel");
  const rating=latestRating(poi);
  const close=node("button","×","detail-close");close.type="button";close.title="Đóng chi tiết";close.setAttribute("aria-label","Đóng chi tiết");
  close.onclick=()=>{state.selectedId=null;panel.replaceChildren();document.querySelectorAll('.poi-button[data-poi-id]').forEach(item=>item.classList.remove('active'));};
  const save=node("button",state.saved.has(poi.poi_id)?"Đã lưu":"Lưu địa điểm","action-button");save.id="savePoi";
  save.onclick=()=>{if(state.saved.has(poi.poi_id))state.saved.delete(poi.poi_id);else state.saved.add(poi.poi_id);try{localStorage.setItem("where2go-saved-v2",JSON.stringify([...state.saved]));}catch{}showDetail(poi);};
  const required=node("button",state.required.has(poi.poi_id)?"Bỏ bắt buộc":"Bắt buộc trong lịch","action-button");required.id="requirePoi";
  required.onclick=()=>{if(state.required.has(poi.poi_id))state.required.delete(poi.poi_id);else state.required.add(poi.poi_id);invalidatePlan();showDetail(poi);};
  const actions=node("div",undefined,"detail-actions");actions.append(save);
  if(!foodCategories.has(poi.category)) actions.append(required);
  if(poi.source_url) actions.append(safeLink(poi.source_url,"Xem nguồn POI"));
  const profile=poi.duration_profile||{};
  panel.replaceChildren(
    close,
    node("h2",poi.name),node("p",(labels[poi.category]||poi.category)+" · "+poi.location),
    node("p",poi.description||"Chưa có mô tả trải nghiệm được kiểm chứng."),
    node("p",rating?`${rating.rating}/5 · ${rating.review_count} đánh giá · ${rating.provider}`:"Chưa có cặp rating/số review hợp lệ"),
    node("p","Giờ nguồn: "+(poi.hours_raw||"Chưa biết")),
    node("p",profile.typical_minutes?`Thời lượng: ${profile.short_minutes}/${profile.typical_minutes}/${profile.long_minutes} phút · ${durationLabels[profile.method]||profile.method}${profile.verified_at?" · đã xác minh":" · chưa xác minh"}`:"Chưa có hồ sơ thời lượng"),
    actions,
  );
  if(poi.image) panel.prepend(imageElement(poi.image));
  document.querySelectorAll('.poi-button[data-poi-id]').forEach(item=>item.classList.toggle('active',item.dataset.poiId===poi.poi_id));
}
async function showPoiById(poiId) {
  const local=state.pois.find(item=>item.poi_id===poiId);
  if(local){showDetail(local);return;}
  try{const data=await api(`/api/v2/pois/${encodeURIComponent(poiId)}`);showDetail(data.poi);}
  catch(error){$("systemStatus").textContent=error.message;}
}
function invalidatePlan() {
  state.planVersion++;state.lastPlan=null;$("itinerary").replaceChildren();
  if(routeLayer&&map){map.removeLayer(routeLayer);routeLayer=null;}
}
async function loadPois() {
  const version=++state.listVersion;
  const params=new URLSearchParams({location:$("locationFilter").value,category:$("typeFilter").value,query:$("searchInput").value,limit:"250"});
  try {
    const data=await api("/api/v2/pois?"+params);
    if(version!==state.listVersion)return;
    state.pois=data.pois;$("listTitle").textContent=`Địa điểm (${data.total})`;
    const list=$("poiList");list.replaceChildren();if(markerLayer)markerLayer.clearLayers();
    for(const poi of data.pois) {
      const button=node("button",`${poi.name} · ${labels[poi.category]||poi.category}`,"poi-button");
      button.type="button";button.dataset.poiId=poi.poi_id;
      button.onclick=()=>{showDetail(poi);if(map)map.setView([poi.latitude,poi.longitude],15);};list.append(button);
      if(markerLayer&&Number.isFinite(poi.latitude)&&Number.isFinite(poi.longitude)) L.circleMarker([poi.latitude,poi.longitude],{radius:4,color:"#0f766e",weight:2,fillOpacity:.28}).addTo(markerLayer).on("click",()=>showDetail(poi)).bindTooltip(node("span",poi.name));
    }
    if(data.total>data.pois.length)list.append(node("p",`Đang hiển thị ${data.pois.length} điểm. Hãy lọc để xem cụ thể hơn.`));
    const selected=data.pois.find(poi=>poi.poi_id===state.selectedId);
    if(selected)showDetail(selected);
    else{$("detailPanel").replaceChildren();state.selectedId=null;}
  } catch(error){$("systemStatus").textContent=error.message;}
}
function selectedTripCategories() {return [...$("tripCategories").querySelectorAll("input:checked")].map(input=>input.value);}
function excludedCategories() {return [...$("excludedCategories").selectedOptions].map(option=>option.value);}
function requestPayload() {
  return {
    start:{latitude:Number($("latitude").value),longitude:Number($("longitude").value)},date:$("tripDate").value,
    start_time:$("startTime").value,end_time:$("endTime").value,radius_km:Number($("radius").value),
    location:$("locationFilter").value,interests:$("interests").value.split(",").map(text=>text.trim()).filter(Boolean),
    preferred_categories:selectedTripCategories(),excluded_categories:excludedCategories(),
    category_mode:$("onlyCategories").checked?"only":"preferred",
    pace:document.querySelector('input[name="pace"]:checked').value,
    include_meals:$("includeMeals").checked,include_coffee_break:$("includeCoffee").checked,
    required_poi_ids:[...state.required],duration_overrides:state.durationOverrides,
    ahp:{criteria_order:["preference_match","place_quality","drive_time","data_confidence"],
      comparisons:["prefQuality","prefDrive","prefData","qualityDrive","qualityData","driveData"].map(id=>Number($(id).value)),uncertainty:[1.2,1.2,1.2,1.2,1.2,1.2]},
  };
}
function blockTitle(block,index) {
  if(block.role==="attraction")return `${index+1}. ${block.name}`;
  if(block.role==="meal")return `Bữa ăn · ${block.name}`;
  return `Nghỉ · ${block.name}`;
}
function renderPlan(data) {
  state.lastPlan=data;const panel=$("itinerary");panel.replaceChildren();
  const status={ready:"Lịch trình theo dữ liệu hiện có",provisional:"Lịch trình tạm tính",insufficient_data:"Chưa tạo được lịch trình",routing_unavailable:"Chưa có dịch vụ tuyến đường"};
  panel.append(node("h2",status[data.status]||data.status),node("p",data.reason));
  for(const warning of data.warnings||[])panel.append(node("p",warning,"warning"));
  let attractionIndex=0;
  for(const block of data.blocks||[]) {
    const card=node("article",undefined,"stop");const current=attractionIndex;
    const title=node("button",blockTitle(block,current),"poi-button");
    if(block.role==="attraction"){
      attractionIndex++;title.type="button";title.dataset.poiId=block.poi_id;title.onclick=()=>showPoiById(block.poi_id);
    } else title.disabled=true;
    card.append(title,node("p",`${block.start_time}–${block.end_time} · ${block.duration_minutes} phút`));
    if(block.role==="attraction") {
      const access=block.access_status==="verified"?"đã xác minh":"ước lượng";
      card.append(node("p",`Giờ: ${block.hours_status==="known"?"đã có dữ liệu":"cần kiểm tra"} · Tiếp cận: ${access}`));
      const editor=node("div",undefined,"duration-editor");const label=node("label","Sửa thời lượng (phút)");
      const input=document.createElement("input");input.type="number";input.min="5";input.max="720";input.step="5";input.value=state.durationOverrides[block.poi_id]||block.duration_minutes;
      input.onchange=()=>{state.durationOverrides[block.poi_id]=Number(input.value);};label.append(input);
      const update=node("button","Tính lại","action-button");update.type="button";update.onclick=()=>submitPlan();editor.append(label,update);card.append(editor);
    }
    panel.append(card);
  }
  if(data.return_time)panel.append(node("p",`Quay về: ${data.return_time} · Tổng lái xe: ${Math.ceil(data.drive_seconds/60)} phút · Dự phòng: ${data.reserve_minutes} phút`));
  if(data.ranking){const details=node("details");details.append(node("summary","Vì sao có kết quả này?"));details.append(node("p",`${data.ranking.method==="fuzzy"?"Fuzzy AHP":"AHP"} + TOPSIS · CR=${data.ranking.cr.toFixed(3)}`));details.append(node("p","Trọng số: "+Object.entries(data.ranking.weights).map(([key,value])=>`${criterionLabels[key]||key} ${value.toFixed(3)}`).join(" · ")));panel.append(details);}
  if(data.geometry&&map){routeLayer=L.geoJSON(data.geometry,{style:{color:"#b45309",weight:5}}).addTo(map);map.fitBounds(routeLayer.getBounds(),{padding:[30,30],animate:false});}
}
async function submitPlan() {
  invalidatePlan();const version=state.planVersion;$("planButton").disabled=true;$("itinerary").replaceChildren(node("p","Đang kiểm tra tuyến đường, thời lượng và giờ mở cửa…"));
  try{const data=await api("/api/v2/itineraries",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(requestPayload())});if(version===state.planVersion)renderPlan(data);}
  catch(error){if(version===state.planVersion)$("itinerary").replaceChildren(node("p",error.message,"warning"));}
  finally{$("planButton").disabled=false;}
}
$("planForm").onsubmit=event=>{event.preventDefault();submitPlan();};
$("tripDate").value=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
$("planForm").addEventListener("change",event=>{if(!event.target.closest(".duration-editor")){updateStart();invalidatePlan();}});
let searchTimer;$("searchInput").oninput=()=>{invalidatePlan();clearTimeout(searchTimer);searchTimer=setTimeout(loadPois,250);};
$("typeFilter").onchange=()=>{invalidatePlan();loadPois();};
$("locationFilter").onchange=()=>{const centers={"Hà Nội":[21.0285,105.8542],"Đà Nẵng":[16.0544,108.2022]};const center=centers[$("locationFilter").value];state.required.clear();state.durationOverrides={};state.selectedId=null;$("detailPanel").replaceChildren();if(center){$("latitude").value=center[0];$("longitude").value=center[1];if(map)map.setView(center,12);}updateStart();invalidatePlan();loadPois();};

(async()=>{
  try{
    const data=await api("/api/v2/pois?limit=1");
    for(const location of data.locations){const option=node("option",location);option.value=location;$("locationFilter").append(option);}
    for(const category of data.categories){const option=node("option",labels[category]||category);option.value=category;$("typeFilter").append(option.cloneNode(true));$("excludedCategories").append(option);if(!foodCategories.has(category)){const label=node("label");const input=document.createElement("input");input.type="checkbox";input.value=category;label.append(input,node("span",labels[category]||category));$("tripCategories").append(label);}}
    $("locationFilter").value="Hà Nội";
    const coverage=await api("/api/v2/coverage");
    renderCoverage(coverage);
    $("systemStatus").textContent="Catalog v2 đa nguồn · Chọn điểm xuất phát, chủ đề và thời gian.";updateStart();await loadPois();
  }catch(error){$("systemStatus").textContent=error.message;}
})();
