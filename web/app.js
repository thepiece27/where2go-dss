"use strict";
const $ = (id) => document.getElementById(id);
const state = {pois: [], selectedId: null, saved: new Set(), listVersion: 0, planVersion: 0};
try { state.saved = new Set(JSON.parse(localStorage.getItem("where2go-saved-v2") || "[]")); } catch {}
const labels = {museum:"Bảo tàng", historic:"Di tích", attraction:"Tham quan", viewpoint:"Ngắm cảnh", park:"Công viên", beach:"Bãi biển", temple:"Đền/chùa", gallery:"Triển lãm", zoo:"Vườn thú", theme_park:"Khu vui chơi"};
const map = window.L ? L.map("map").setView([21.0285,105.8542],12) : null;
let markerLayer, startMarker, routeLayer;
if (map) {
  const tiles=L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'});
  let tileFailures=0;
  tiles.on("loading",()=>{tileFailures=0;});
  tiles.on("tileerror",()=>{tileFailures++;$("mapStatus").hidden=false;$("mapStatus").textContent="Không tải được một phần hoặc toàn bộ nền bản đồ. Hãy kiểm tra kết nối mạng; lịch trình và đường từ OSRM vẫn hiển thị.";});
  tiles.on("load",()=>{if(!tileFailures) $("mapStatus").hidden=true;});
  tiles.addTo(map);
  markerLayer = L.layerGroup().addTo(map);
  map.on("click", (event) => { $("latitude").value=event.latlng.lat.toFixed(6); $("longitude").value=event.latlng.lng.toFixed(6); updateStart(); invalidatePlan(); });
}
else {$("mapStatus").hidden=false;$("mapStatus").textContent="Chưa tải được thư viện bản đồ. Bạn vẫn có thể nhập tọa độ và đọc lịch trình.";}
function node(tag, text, className) {
  const item=document.createElement(tag);
  if(text !== undefined) item.textContent=text;
  if(className) item.className=className;
  return item;
}
function safeLink(url, text) {
  try {
    const parsed=new URL(url);
    if(!["https:","http:"].includes(parsed.protocol) || parsed.username || parsed.password) return node("span",text);
    const a=node("a",text); a.href=parsed.href; a.target="_blank"; a.rel="noopener noreferrer"; return a;
  } catch { return node("span",text); }
}
function imageElement(url) {
  const fallback=node("div","Ảnh chưa có nguồn được kiểm chứng");
  try {
    const parsed=new URL(url);
    if(parsed.protocol!=="https:" || parsed.hostname!=="upload.wikimedia.org") return fallback;
    const img=document.createElement("img"); img.src=parsed.href; img.alt="Ảnh địa điểm"; img.loading="lazy";
    img.addEventListener("error",()=>img.replaceWith(fallback)); return img;
  } catch { return fallback; }
}
async function api(path, options) {
  const response=await fetch(path, options);
  const data=await response.json();
  if(!response.ok) {
    const errors=Array.isArray(data.detail) ? data.detail.map(e=>e.msg).join("; ") : data.detail;
    throw new Error(errors || "Không đọc được phản hồi");
  }
  return data;
}
function updateStart() {
  const coords=[Number($("latitude").value),Number($("longitude").value)];
  if(!map || !coords.every(Number.isFinite)) return;
  if(startMarker) startMarker.setLatLng(coords); else startMarker=L.marker(coords).addTo(map).bindPopup("Điểm xuất phát và quay về");
}
function showDetail(poi) {
  state.selectedId=poi.poi_id;
  const panel=$("detailPanel");
  const save=node("button",state.saved.has(poi.poi_id) ? "Đã lưu" : "Lưu địa điểm","action-button");
  save.id="savePoi";
  save.onclick=()=>{
    if(state.saved.has(poi.poi_id)) state.saved.delete(poi.poi_id); else state.saved.add(poi.poi_id);
    try { localStorage.setItem("where2go-saved-v2",JSON.stringify([...state.saved])); } catch {}
    showDetail(poi);
  };
  panel.replaceChildren(node("h2",poi.name),node("p",(labels[poi.category]||poi.category)+" · "+poi.location),
    node("p",poi.description || "Chưa có mô tả trải nghiệm được kiểm chứng."),
    node("p","Giờ nguồn: "+(poi.hours_raw || "Chưa biết")),
    node("p","Tham quan dự kiến: "+poi.visit_duration_minutes+" phút (ước lượng)"),
    safeLink(poi.source_url,"Xem nguồn địa điểm"),save);
  if(poi.image) panel.append(imageElement(poi.image));
}
function invalidatePlan() {
  state.planVersion++;
  $("itinerary").replaceChildren();
  if(routeLayer && map) {map.removeLayer(routeLayer);routeLayer=null;}
}
async function loadPois() {
  const version=++state.listVersion;
  const params=new URLSearchParams({location:$("locationFilter").value,category:$("typeFilter").value,query:$("searchInput").value,limit:"1000"});
  try {
    const data=await api("/api/pois?"+params);
    if(version!==state.listVersion) return;
    state.pois=data.pois; $("listTitle").textContent="Địa điểm ("+data.total+")";
    const list=$("poiList");list.replaceChildren(); if(markerLayer) markerLayer.clearLayers();
    for(const poi of data.pois) {
      const button=node("button",poi.name+" · "+(labels[poi.category]||poi.category),"poi-button");
      button.onclick=()=>{showDetail(poi);if(map) map.setView([poi.latitude,poi.longitude],15);};
      list.append(button);
      if(markerLayer) L.circleMarker([poi.latitude,poi.longitude],{radius:5,color:"#0f766e"}).addTo(markerLayer).on("click",()=>showDetail(poi)).bindTooltip(node("span",poi.name));
    }
    if(data.total>data.pois.length) list.append(node("p","Đang hiển thị "+data.pois.length+" điểm. Hãy lọc để xem cụ thể hơn."));
    if(data.pois.length) showDetail(data.pois.find(p=>p.poi_id===state.selectedId)||data.pois[0]);
    else {state.selectedId=null;$("detailPanel").replaceChildren(node("p","Không có địa điểm phù hợp."));}
  } catch(error) {$("systemStatus").textContent=error.message;}
}
function renderPlan(data) {
  const panel=$("itinerary");panel.replaceChildren();
  const status={ready:"Lịch trình theo dữ liệu hiện có",provisional:"Lịch trình tạm tính",insufficient_data:"Chưa tạo được lịch trình",routing_unavailable:"Chưa có dịch vụ tuyến đường"};
  panel.append(node("h2",status[data.status]||data.status),node("p",data.reason));
  for(const warning of data.warnings||[]) panel.append(node("p",warning,"warning"));
  for(const [index,stop] of (data.stops||[]).entries()) {
    const card=node("article",undefined,"stop");
    const title=node("button",(index+1)+". "+stop.name,"poi-button");title.onclick=()=>showDetail(stop);
    card.append(title,node("p",stop.arrival_time+" đến · "+stop.visit_start_time+" tham quan · "+stop.departure_time+" rời"),
      node("p","Lái xe tới điểm: "+Math.ceil(data.legs[index].duration_seconds/60)+" phút · Chờ: "+Math.ceil(stop.wait_minutes)+" phút"),
      node("p",stop.hours_status==="known" ? "Lịch mở cửa có dữ liệu cho ngày chọn" : "Cần kiểm tra giờ mở cửa"));
    panel.append(card);
  }
  if(data.return_time) panel.append(node("p","Quay về: "+data.return_time+" · Tổng lái xe: "+Math.ceil(data.drive_seconds/60)+" phút"));
  if(data.ranking) {
    const details=node("details");details.append(node("summary","Vì sao có kết quả này?"));
    details.append(node("p","Fuzzy AHP + TOPSIS · CR="+data.ranking.cr.toFixed(3)+" · Điểm tương đối trong tập ứng viên"));
    details.append(node("p","Trọng số: "+Object.entries(data.ranking.weights).map(([k,v])=>k+" "+v.toFixed(3)).join(" · ")));
    panel.append(details);
  }
  if(data.geometry && map) {routeLayer=L.geoJSON(data.geometry,{style:{color:"#b45309",weight:5}}).addTo(map);map.fitBounds(routeLayer.getBounds(),{padding:[30,30],animate:false});}
  if(data.stops?.length) showDetail(data.stops[0]);
}
$("planForm").onsubmit=async event=>{
  event.preventDefault();invalidatePlan();const version=state.planVersion;
  $("planButton").disabled=true;$("itinerary").replaceChildren(node("p","Đang kiểm tra tuyến đường và giờ mở cửa…"));
  const payload={start:{latitude:Number($("latitude").value),longitude:Number($("longitude").value)},date:$("tripDate").value,
    start_time:$("startTime").value,end_time:$("endTime").value,radius_km:Number($("radius").value),
    location:$("locationFilter").value,query:$("searchInput").value,
    categories:$("typeFilter").value?[$("typeFilter").value]:[],interests:$("interests").value.split(",").map(x=>x.trim()).filter(Boolean),
    pairwise_preferences:{preference_over_drive_time:Number($("prefDrive").value),preference_over_data_confidence:Number($("prefData").value),drive_time_over_data_confidence:Number($("driveData").value)}};
  try {const data=await api("/api/itineraries",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});if(version===state.planVersion) renderPlan(data);}
  catch(error) {if(version===state.planVersion) $("itinerary").replaceChildren(node("p",error.message,"warning"));}
  finally {$("planButton").disabled=false;}
};
for(const id of ["prefDrive","prefData","driveData"]) {
  for(const value of [1/9,1/5,1/3,1,3,5,9]) {const opt=node("option",value<1?"1/"+Math.round(1/value):String(value));opt.value=value;$(id).append(opt);}
  $(id).value="1";
}
$("tripDate").value=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
$("planForm").addEventListener("change",()=>{updateStart();invalidatePlan();});
let searchTimer;
$("searchInput").oninput=()=>{invalidatePlan();clearTimeout(searchTimer);searchTimer=setTimeout(loadPois,250);};
$("typeFilter").onchange=()=>{invalidatePlan();loadPois();};
$("locationFilter").onchange=()=>{
  const centers={"Hà Nội":[21.0285,105.8542],"Đà Nẵng":[16.0544,108.2022]};
  const center=centers[$("locationFilter").value];
  if(center){$("latitude").value=center[0];$("longitude").value=center[1];if(map)map.setView(center,12);}
  updateStart();invalidatePlan();loadPois();
};
(async()=>{
  try {
    const data=await api("/api/pois?limit=1");
    for(const location of data.locations) {const opt=node("option",location);opt.value=location;$("locationFilter").append(opt);}
    for(const category of data.categories) {const opt=node("option",labels[category]||category);opt.value=category;$("typeFilter").append(opt);}
    $("locationFilter").value="Hà Nội";
    const cov=await api("/api/coverage");
    for(const row of cov.locations.filter(r=>["Hà Nội","Đà Nẵng"].includes(r.location))) {
      $("coverage").append(node("p",row.location+": "+row.usable+" điểm đủ điều kiện dữ liệu; "+row.hours_parsed+" có giờ phân tích được; "+row.source_checked+" có biên bản đối soát nguồn."));
    }
    $("systemStatus").textContent="Dữ liệu có nguồn · Chọn điểm xuất phát và thời gian để bắt đầu.";
    $("coverage").append(node("p","Phiên bản dữ liệu: "+cov.dataset_version));
    for(const row of cov.road_audit||[]) $("coverage").append(node("p",row.location+": "+row.routable+"/"+row.tested+" điểm qua kiểm tra đường đi và khoảng cách tới đường ô tô. Chưa xác minh lối vào thực địa."));
    updateStart();await loadPois();
  }catch(error){$("systemStatus").textContent=error.message;}
})();
