"use strict";
const $ = id => document.getElementById(id);
const labels = {museum:"Bảo tàng",historic:"Di tích",attraction:"Tham quan",viewpoint:"Ngắm cảnh",park:"Công viên",beach:"Bãi biển",temple:"Đền/chùa",gallery:"Triển lãm",zoo:"Vườn thú",theme_park:"Khu vui chơi",old_quarter:"Phố cổ",craft_village:"Làng nghề",market:"Chợ",nature_area:"Khu thiên nhiên",performance_venue:"Biểu diễn",restaurant:"Nhà hàng",cafe:"Cà phê",food_street:"Khu ẩm thực"};
const foodCategories = new Set(["restaurant","cafe","food_street"]);
const basemapConfig = {"Hà Nội":{slug:"hanoi",center:[21.0285,105.8542]},"Đà Nẵng":{slug:"danang",center:[16.0544,108.2022]}};
const presets = {morning:["08:00","12:00"],afternoon:["13:00","18:00"],day:["08:00","18:00"]};
const state = {pois:[],selected:new Map(),required:new Set(),saved:new Set(),durationOverrides:{},manualOrder:null,
  city:"Đà Nẵng",listVersion:0,planVersion:0,basemapVersion:0,recoVersion:0,detailVersion:0,offset:0,
  result:null,chosen:null,preview:null,stale:false,busy:false,controller:null,pickingStart:false,selectedId:null};
try{state.saved=new Set(JSON.parse(localStorage.getItem("where2go-saved-v2")||"[]"));}catch{}
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function button(text,handler,className){const el=node("button",text,className);el.type="button";el.onclick=handler;return el;}
function tell(text){$("systemStatus").textContent=text;}
function safeLink(url,text){try{const u=new URL(url);if(!["http:","https:"].includes(u.protocol)||u.username||u.password)return node("span",text);const el=node("a",text);el.href=u.href;el.target="_blank";el.rel="noopener noreferrer";return el;}catch{return node("span",text);}}
function imageElement(url,name="địa điểm"){
  const fallback=node("div","Chưa có ảnh","photo");
  try{const u=new URL(url);if(u.protocol!=="https:"||u.username||u.password||/\/ogw\/|\/a-\//.test(u.pathname))return fallback;
    const img=node("img");img.src=u.href;img.alt=`Ảnh ${name}`;img.loading="lazy";img.className="photo";img.onerror=()=>img.replaceWith(fallback);return img;
  }catch{return fallback;}
}
async function api(path,options){const response=await fetch(path,options);const data=await response.json();if(!response.ok){const detail=Array.isArray(data.detail)?data.detail.map(i=>i.msg).join("; "):data.detail;throw new Error(detail||"Chưa đọc được dữ liệu. Hãy thử lại.");}return data;}
function post(path,data,signal){return api(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data),signal});}
function today(){return new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());}
const formKeys=["tripDate","startTime","endTime","timePreset","latitude","longitude","interests","tripTheme"];
const checkKeys=["includeMeals","includeCoffee","autoAdd"];
function saveDraft(city=state.city){
  const fields=Object.fromEntries(formKeys.map(k=>[k,$(k).value]));for(const k of checkKeys)fields[k]=$(k).checked;
  const draft={version:1,fields,startLabel:$("startDescription").textContent,selected:[...state.selected.values()],required:[...state.required],
    durations:state.durationOverrides,manualOrder:state.manualOrder,result:state.result,chosen:state.chosen,stale:state.stale};
  try{localStorage.setItem(`where2go-trip-v1:${city}`,JSON.stringify(draft));localStorage.setItem("where2go-trip-city-v1",city);}
  catch{tell("Bộ nhớ trình duyệt đã đầy hoặc bị chặn; chuyến đi hiện tại chưa được lưu nháp.");}
}
function restoreCity(city){
  state.city=city;$("planLocation").value=city;state.selected=new Map();state.required=new Set();state.durationOverrides={};state.manualOrder=null;state.result=null;state.chosen=null;state.preview=null;state.stale=false;
  $("tripDate").value=today();$("startTime").value="08:00";$("endTime").value="18:00";$("timePreset").value="day";$("interests").value="";$("tripTheme").value="";$("includeMeals").checked=true;$("includeCoffee").checked=false;$("autoAdd").checked=false;
  const center=basemapConfig[city].center;$("latitude").value=center[0];$("longitude").value=center[1];$("startDescription").textContent=`Tâm ${city} — điểm mẫu, hãy chọn vị trí của bạn.`;
  try{const d=JSON.parse(localStorage.getItem(`where2go-trip-v1:${city}`)||"null");if(d?.version===1){
    for(const k of formKeys)if(d.fields?.[k]!==undefined)$(k).value=d.fields[k];for(const k of checkKeys)if(d.fields?.[k]!==undefined)$(k).checked=d.fields[k];
    state.selected=new Map((d.selected||[]).slice(0,12).map(p=>[p.poi_id,p]));state.required=new Set((d.required||[]).filter(i=>state.selected.has(i)));
    state.durationOverrides=d.durations||{};state.manualOrder=d.manualOrder||null;state.result=d.result||null;state.chosen=d.chosen||null;state.preview=state.chosen;state.stale=!!d.stale;
    if(d.startLabel)$("startDescription").textContent=d.startLabel;
  }}catch{tell("Chưa đọc được nháp cũ; bạn có thể chọn địa điểm để bắt đầu lại.");}
  $("autoAdd").disabled=!!state.manualOrder;updateStart();renderSelections();renderResult();renderTimeline(state.chosen);drawRoute(state.chosen);$("recommendationLocation").textContent=city;
  const version=++state.detailVersion;
  Promise.allSettled([...state.selected.keys()].map(async ident=>{const data=await api(`/api/v2/pois/${encodeURIComponent(ident)}?view=explore`);return data.poi;})).then(rows=>{
    if(version!==state.detailVersion||city!==state.city)return;let changed=false;for(const row of rows)if(row.status==="fulfilled"&&state.selected.has(row.value.poi_id)){state.selected.set(row.value.poi_id,row.value);if(!row.value.manual_trip_quality?.eligible)changed=true;}
    if(changed)invalidatePlan();renderSelections();saveDraft();
  });
}
function setView(view){
  $("workspace").dataset.view=view;
  for(const [name,id] of [["explore","exploreView"],["selected","selectedView"],["itinerary","itineraryView"]])$(id).hidden=view!==name;
  for(const el of document.querySelectorAll(".view-tabs [data-view]")){const active=el.dataset.view===view;el.classList.toggle("active",active);el.setAttribute("aria-pressed",String(active));}
  if(view==="map"&&!matchMedia("(max-width:800px)").matches)$("exploreView").hidden=false;
  setTimeout(()=>map?.invalidateSize(),0);
}
function invalidatePlan(){
  state.planVersion++;state.controller?.abort();state.busy=false;state.stale=!!(state.result||state.chosen);
  $("planButton").disabled=false;$("planStatus").textContent=state.stale?"Lựa chọn đã thay đổi. Lịch cũ được giữ để tham khảo; hãy tính lại trước khi chọn.":"";
  if($("confirmDialog").open)$("confirmDialog").close();
  document.querySelectorAll(".choose-option").forEach(el=>el.disabled=state.stale);saveDraft();
}
function updateStart(){
  const coords=[Number($("latitude").value),Number($("longitude").value)];if(!map||!coords.every(Number.isFinite))return;
  if(startMarker)startMarker.setLatLng(coords);else startMarker=L.marker(coords).addTo(map).bindPopup("Điểm xuất phát và quay về");
}
function setStart(lat,lon,label){$("latitude").value=Number(lat).toFixed(6);$("longitude").value=Number(lon).toFixed(6);$("startDescription").textContent=label;state.pickingStart=false;$("mapInstruction").hidden=true;$("pickStart").textContent="Ghim bản đồ";updateStart();invalidatePlan();scheduleRecommendations();}
function onMapStart(lat,lon){if(state.pickingStart){setStart(lat,lon,"Vị trí bạn ghim trên bản đồ");tell("Đã đặt điểm xuất phát và quay về.");}}
function canSelect(p){return p.location===state.city&&p.manual_trip_quality?.eligible!==false&&!['permanently_closed','temporarily_closed'].includes(p.business_status);}
function togglePlace(p){
  if(state.selected.has(p.poi_id)){state.selected.delete(p.poi_id);state.required.delete(p.poi_id);delete state.durationOverrides[p.poi_id];if(state.manualOrder)state.manualOrder=state.manualOrder.filter(i=>i!==p.poi_id);}
  else{if(!canSelect(p)){tell("Địa điểm chưa chọn được cho chuyến đi tại "+state.city+".");return;}if(state.selected.size>=12){tell("Mỗi chuyến hỗ trợ tối đa 12 địa điểm. Hãy bớt một điểm trước khi thêm.");return;}state.selected.set(p.poi_id,p);if(state.manualOrder)state.manualOrder.push(p.poi_id);}
  invalidatePlan();renderSelections();scheduleRecommendations();if(state.detailPoi?.poi_id===p.poi_id)showDetail(state.detailPoi);
}
function mustControl(p){const label=node("label",undefined,"check-label"),input=node("input");input.type="checkbox";input.className="must-visit";input.dataset.poiId=p.poi_id;input.checked=state.required.has(p.poi_id);input.disabled=!state.selected.has(p.poi_id);input.setAttribute("aria-label",`Nhất định phải ghé ${p.name}`);input.onchange=()=>{const inSelection=!!input.closest("#selectedList");if(input.checked)state.required.add(p.poi_id);else state.required.delete(p.poi_id);invalidatePlan();renderSelections();if(inSelection)[...$("selectedList").querySelectorAll(".must-visit")].find(el=>el.dataset.poiId===p.poi_id)?.focus();};label.append(input,node("span","Nhất định phải ghé"));return label;}
function placeCard(p){
  const el=node("article",undefined,"poi-card");el.dataset.poiId=p.poi_id;el.classList.toggle("is-selected",state.selected.has(p.poi_id));el.append(imageElement(p.image,p.name));
  const copy=node("div",undefined,"card-copy"),title=button(p.name,()=>loadPoiDetail(p.poi_id),"poi-title");title.dataset.poiId=p.poi_id;
  copy.append(title,node("p",`${labels[p.category]||p.category} · ${p.location}`),node("p",`Tham khảo: ${p.duration_profile?.typical_minutes||"chưa rõ"} phút`));
  for(const text of p.reasons||[])copy.append(node("span",text,"reason"));
  if(p.hours_weekly===null||(p.warnings||[]).some(w=>w.includes("giờ")))copy.append(node("span","Chưa có giờ mở cửa","quality-note"));
  if(p.manual_trip_quality?.reasons?.includes("business_closed"))copy.append(node("span","Nguồn báo đã đóng cửa; hãy chọn điểm khác.","quality-note"));
  const add=button(state.selected.has(p.poi_id)?"Bỏ khỏi chuyến đi":"Thêm vào chuyến đi",()=>togglePlace(p),"add-place");add.disabled=!canSelect(p)&&!state.selected.has(p.poi_id);if(!canSelect(p))add.title=p.location!==state.city?`Chuyến đi hiện tại ở ${state.city}`:"Danh tính, vị trí hoặc tình trạng hoạt động chưa phù hợp";
  copy.append(add,mustControl(p));el.append(copy);return el;
}
function syncCards(){for(const card of document.querySelectorAll(".poi-card")){const ident=card.dataset.poiId,selected=state.selected.has(ident);card.classList.toggle("is-selected",selected);card.querySelector(".add-place").textContent=selected?"Bỏ khỏi chuyến đi":"Thêm vào chuyến đi";const must=card.querySelector(".must-visit");must.checked=state.required.has(ident);must.disabled=!selected;}}
function editDuration(ident,value){const n=Number(value);if(!Number.isInteger(n)||n<5||n>720){tell("Thời lượng phải là số nguyên từ 5 đến 720 phút.");return false;}state.durationOverrides[ident]=n;invalidatePlan();return true;}
function reorder(ident,delta,fromTimeline=false){
  let order=state.manualOrder?[...state.manualOrder]:fromTimeline&&state.chosen?[...state.chosen.scheduled_poi_ids.filter(i=>state.selected.has(i)),...[...state.selected.keys()].filter(i=>!state.chosen.scheduled_poi_ids.includes(i))]:[...state.selected.keys()];
  const index=order.indexOf(ident),other=index+delta;if(other<0||other>=order.length)return;[order[index],order[other]]=[order[other],order[index]];state.manualOrder=order;$("autoAdd").checked=false;$("autoAdd").disabled=true;invalidatePlan();renderSelections();if(fromTimeline)submitPlan();
}
function renderSelections(){
  const n=state.selected.size;$("selectedCount").textContent=n;$("tripSummary").textContent=n?`${n}/12 địa điểm · ${state.required.size} nơi nhất định phải ghé · ${state.city}`:"Chưa chọn địa điểm. Bắt đầu từ những nơi bạn yêu thích.";
  const strip=$("selectionStrip");strip.replaceChildren();for(const p of state.selected.values())strip.append(button((state.required.has(p.poi_id)?"★ ":"")+p.name,()=>setView("selected")));
  const list=$("selectedList");list.replaceChildren();const order=state.manualOrder||[...state.selected.keys()];
  $("orderStatus").textContent=state.manualOrder?"Thứ tự do bạn chọn. Ứng dụng sẽ giữ thứ tự này khi tính lại.":"Ứng dụng sẽ thử các thứ tự ghé để tìm lịch phù hợp.";
  if(!n)list.append(node("p","Bạn chưa chọn địa điểm. Sang Khám phá để thêm những nơi muốn ghé.","empty-state"));
  order.forEach((ident,index)=>{const p=state.selected.get(ident);if(!p)return;const el=node("article",undefined,"selected-card");el.append(node("h3",`${index+1}. ${p.name}`),mustControl(p));
    if(!canSelect(p))el.append(node("p","Địa điểm cần được kiểm tra lại hoặc thay thế.","warning"));
    const edit=node("div",undefined,"duration-editor"),label=node("label","Thời lượng (phút)"),input=node("input");input.type="number";input.min=5;input.max=720;input.step=1;input.value=state.durationOverrides[ident]||p.duration_profile?.typical_minutes||60;input.setAttribute("aria-label",`Thời lượng ${p.name}`);input.onchange=()=>editDuration(ident,input.value);label.append(input);edit.append(label);el.append(edit);
    const actions=node("div",undefined,"actions"),up=button("↑ Lên",()=>reorder(ident,-1)),down=button("↓ Xuống",()=>reorder(ident,1));up.disabled=index===0;down.disabled=index===order.length-1;up.setAttribute("aria-label",`Đưa ${p.name} lên`);down.setAttribute("aria-label",`Đưa ${p.name} xuống`);
    actions.append(up,down,button("Bỏ điểm",()=>togglePlace(p)),button("Xem địa điểm",()=>loadPoiDetail(ident)));if(ident in state.durationOverrides)actions.append(button("Dùng thời lượng tham khảo",()=>{delete state.durationOverrides[ident];invalidatePlan();renderSelections();}));el.append(actions);list.append(el);
  });syncCards();saveDraft();
}
async function loadPois(append=false){
  if(!append)state.offset=0;const version=++state.listVersion;
  const params=new URLSearchParams({view:"explore",location:$("locationFilter").value,category:$("typeFilter").value,query:$("searchInput").value,limit:"250",offset:String(state.offset)});
  try{const data=await api("/api/v2/pois?"+params);if(version!==state.listVersion)return;state.pois=append?[...state.pois,...data.pois]:data.pois;$("listTitle").textContent=`Địa điểm (${data.total.toLocaleString("vi-VN")})`;
    const list=$("poiList");if(!append)list.replaceChildren();$("loadMorePois")?.remove();for(const p of data.pois)list.append(placeCard(p));
    if(!data.pois.length)list.append(node("p","Chưa tìm thấy. Thử tên khác hoặc mở rộng bộ lọc.","empty-state"));
    if(data.has_more){const more=button("Xem thêm địa điểm",()=>{state.offset+=250;loadPois(true);});more.id="loadMorePois";list.append(more);}if(!append)loadMapPois();
  }catch(e){tell(e.message);}
}
let recoTimer;
function scheduleRecommendations(){state.recoVersion++;clearTimeout(recoTimer);recoTimer=setTimeout(loadRecommendations,350);}
function contextPayload(){return {start:{latitude:Number($("latitude").value),longitude:Number($("longitude").value)},date:$("tripDate").value,location:state.city,selected_poi_ids:[...state.selected.keys()],interests:$("interests").value.split(",").map(s=>s.trim()).filter(Boolean),preferred_categories:$("tripTheme").value?[$("tripTheme").value]:[]};}
async function loadRecommendations(){const version=++state.recoVersion;$("recommendationStatus").textContent="Đang tìm địa điểm phù hợp…";try{const data=await post("/api/v2/trip-recommendations",contextPayload());if(version!==state.recoVersion)return;
  for(const [id,key] of [["featuredList","featured"],["contextualList","contextual"]]){const panel=$(id);panel.replaceChildren();for(const p of data[key])panel.append(placeCard(p));if(!data[key].length)panel.append(node("p","Bạn có thể tìm thêm địa điểm bên dưới.","muted"));}
  $("recommendationStatus").textContent=data.routing_status==="ready"?"Các địa điểm gợi ý chỉ được thêm khi bạn chọn.":"Gợi ý theo vị trí; chưa xác nhận thời gian lái xe. Các điểm chỉ được thêm khi bạn chọn.";
}catch(e){if(version===state.recoVersion)$("recommendationStatus").textContent=e.message;}}
async function loadPoiDetail(ident){const version=++state.detailVersion;try{const data=await api(`/api/v2/pois/${encodeURIComponent(ident)}?view=explore`);if(version!==state.detailVersion)return;showDetail(data.poi);if(matchMedia("(max-width:800px)").matches)setView("map");if(map)map.setView([data.poi.latitude,data.poi.longitude],15,{animate:false});}catch(e){tell(e.message);}}
function showDetail(p){
  state.detailPoi=p;state.selectedId=p.poi_id;highlightPoi(p);const panel=$("detailPanel"),close=button("×",()=>{panel.replaceChildren();state.detailPoi=null;},"detail-close");close.setAttribute("aria-label","Đóng chi tiết");
  const photo=imageElement(p.image,p.name);photo.classList.add("detail-image");panel.replaceChildren(close,photo,node("h2",p.name),node("p",`${labels[p.category]||p.category} · ${p.location}`),node("p",p.description||"Chưa có mô tả."),node("p",p.hours_raw?`Giờ theo nguồn: ${p.hours_raw}`:"Chưa có giờ mở cửa; kiểm tra trước khi đi."),node("p",`Thời lượng tham khảo: ${p.duration_profile?.typical_minutes||"chưa rõ"} phút. Giờ ghé sẽ được tính sau khi bạn chọn lịch.`));
  const rating=(p.ratings||[]).filter(r=>r.same_observation).sort((a,b)=>(b.observed_at||"").localeCompare(a.observed_at||""))[0];panel.append(node("p",rating?`${rating.rating}/5 · ${rating.review_count} đánh giá · ${rating.provider}`:"Chưa có cặp điểm đánh giá và số lượt đánh giá đủ bằng chứng."));
  const actions=node("div",undefined,"actions"),add=button(state.selected.has(p.poi_id)?"Bỏ khỏi chuyến đi":"Thêm vào chuyến đi",()=>togglePlace(p),"primary");add.id="addDetailPoi";add.disabled=!canSelect(p)&&!state.selected.has(p.poi_id);actions.append(add,button("Xuất phát từ đây",()=>{setStart(p.latitude,p.longitude,p.name);panel.replaceChildren();}));
  const save=button(state.saved.has(p.poi_id)?"Đã lưu":"Lưu địa điểm",()=>{if(state.saved.has(p.poi_id))state.saved.delete(p.poi_id);else state.saved.add(p.poi_id);try{localStorage.setItem("where2go-saved-v2",JSON.stringify([...state.saved]));}catch{tell("Chưa lưu được địa điểm trên trình duyệt.");}showDetail(p);});save.id="savePoi";actions.append(save);panel.append(actions,mustControl(p));
  if(p.location!==state.city&&basemapConfig[p.location])panel.append(button(`Mở chuyến đi tại ${p.location}`,()=>{$("planLocation").value=p.location;$("planLocation").dispatchEvent(new Event("change"));showDetail(p);}));
  if(!p.manual_trip_quality?.eligible)panel.append(node("p",p.manual_trip_quality?.reasons?.includes("business_closed")?"Nguồn báo địa điểm đã đóng cửa. Hãy chọn một địa điểm thay thế.":"Chưa đủ điều kiện chọn cho chuyến ô tô trong ngày tại Hà Nội/Đà Nẵng.","quality-note"));
  if(p.source_url)panel.append(safeLink(p.source_url,"Xem nguồn địa điểm"));if(p.image_metadata?.source_url)panel.append(node("p"),safeLink(p.image_metadata.source_url,"Nguồn ảnh · "+p.image_metadata.provider));
}
function requestPayload(otherWindows=false){return {...contextPayload(),start_time:$("startTime").value,end_time:$("endTime").value,must_visit_poi_ids:[...state.required],duration_overrides:state.durationOverrides,manual_order:state.manualOrder,include_meals:$("includeMeals").checked,include_coffee_break:$("includeCoffee").checked,auto_add:$("autoAdd").checked,try_other_windows:otherWindows};}
function drawRoute(option){if(routeLayer&&map)map.removeLayer(routeLayer);routeLayer=null;if(option?.geometry&&map){
  routeLayer=L.featureGroup([L.geoJSON(option.geometry,{style:{color:"#cf632c",weight:5,opacity:.9}})]).addTo(map);
  (option.stops||[]).forEach((p,i)=>{const badge=node("span",String(i+1),"route-stop-badge");L.marker([p.latitude,p.longitude],{icon:L.divIcon({html:badge,className:"route-stop-icon",iconSize:[30,30]})}).addTo(routeLayer).bindTooltip(node("span",p.name)).on("click",()=>loadPoiDetail(p.poi_id));});
  map.fitBounds(routeLayer.getBounds(),{padding:[45,45],animate:false});}}
function focusTimeline(){const title=$("timeline").querySelector("h2");if(title){title.tabIndex=-1;title.focus({preventScroll:true});title.scrollIntoView({block:"start"});}}
function previewOption(option){state.preview=option;renderTimeline(option);drawRoute(option);focusTimeline();}
async function chooseOption(option){
  if(state.stale||state.busy)return;const version=state.planVersion;
  if(option.requires_confirmation){$("confirmationChanges").replaceChildren(...option.changes.map(c=>node("p",c.message,"warning")));$("confirmDialog").showModal();
    $("confirmOption").onclick=()=>{$("confirmDialog").close();if(version===state.planVersion&&!state.stale)commitOption(option);};return;}
  await commitOption(option);
}
async function commitOption(option){
  const version=state.planVersion;
  // Auto-added places become editable selections only after this option is chosen.
  const missing=option.scheduled_poi_ids.filter(i=>!state.selected.has(i));
  if(missing.length){const rows=await Promise.allSettled(missing.map(i=>api(`/api/v2/pois/${encodeURIComponent(i)}?view=explore`)));if(version!==state.planVersion)return;for(const r of rows)if(r.status==="fulfilled")state.selected.set(r.value.poi.poi_id,r.value.poi);}
  state.chosen=option;state.preview=option;$("startTime").value=option.window.start_time;$("endTime").value=option.window.end_time;$("timePreset").value="custom";renderSelections();renderResult();renderTimeline(option);drawRoute(option);saveDraft();focusTimeline();tell("Đã chọn lịch. Bạn có thể đổi thứ tự, thời lượng hoặc giờ đi rồi tính lại.");
}
function renderResult(){
  const panel=$("itinerary");panel.replaceChildren();const data=state.result;
  if(!data){panel.append(node("p","Chọn nơi muốn ghé, sau đó bấm Xem lịch gợi ý. Các lịch được tính từ vị trí xuất phát và giờ mở cửa hiện có.","empty-state"));return;}
  panel.append(node("p",data.message));
  for(const issue of data.issues||[])panel.append(node("p",`${issue.name}: ${issue.message}`,"warning"));
  for(const option of data.options){const el=node("article",undefined,"option-card");el.dataset.optionId=option.option_id;const chosen=state.chosen?.option_id===option.option_id;el.classList.toggle("chosen",chosen);
    el.append(node("h3",option.label+(chosen?" · Đã chọn":"")),node("p",`${option.coverage.selected}/${option.coverage.selected_total} điểm · ${option.coverage.must}/${option.coverage.must_total} điểm bắt buộc`,"coverage"),node("p",`${option.start_time} → ${option.return_time} · Lái xe ${Math.ceil(option.drive_seconds/60)} phút · Còn dư ${Math.floor(option.reserve_minutes)} phút đến mốc giờ về`));
    const durations=visitsOf(option).map(t=>`${t.name}: ${t.duration_minutes} phút`).join(" · ");el.append(node("p",durations));if(option.auto_added?.length)el.append(node("p","Tự bổ sung theo tùy chọn của bạn: "+option.auto_added.map(p=>p.name).join(", ")));
    for(const change of option.changes)el.append(node("p",change.message,"warning"));
    if(option.unscheduled.length){const details=node("details"),list=node("ul",undefined,"adjustments");details.append(node("summary",`${option.unscheduled.length} điểm chưa xếp được`));for(const p of option.unscheduled)list.append(node("li",`${p.name}: ${p.message}`));details.append(list);el.append(details);}
    const warnings=[...option.warnings,...new Set(visitsOf(option).flatMap(t=>(t.warnings||[]).filter(w=>w.includes("giờ")).map(w=>`${t.name}: ${w}`)))];
    const details=node("details");details.append(node("summary","Thông tin cần kiểm tra trước khi đi"));for(const w of warnings)details.append(node("p",w));el.append(details);
    const actions=node("div",undefined,"actions"),select=button(option.requires_confirmation?"Chọn và xem điều chỉnh":"Chọn lịch này",()=>chooseOption(option),"primary choose-option");select.disabled=state.stale||state.busy;actions.append(button("Xem chi tiết",()=>previewOption(option)),select);el.append(actions);panel.append(el);
  }
  const actions=node("div",undefined,"actions");for(const a of data.actions||[])actions.append(button(a.label,()=>performAction(a)));panel.append(actions);
}
function visitsOf(option){return (option?.timeline||[]).filter(t=>t.role==="visit");}
function performAction(action){
  if(action.code==="try_other_windows")return submitPlan(true);
  if(action.code==="retry_routing")return submitPlan();
  if(action.code==="change_start"){$("pickStart").click();return;}
  if(action.code==="change_date"){$("tripDate").focus();$("tripDate").scrollIntoView({block:"center"});tell("Chọn ngày khác rồi bấm Xem lịch gợi ý.");return;}
  if(action.code==="choose_places"||action.code==="replace_places"){setView("explore");return;}
  if(action.code==="split_trip")tell("Các điểm chưa xếp vẫn ở trong danh sách. Bạn có thể bỏ các điểm đã đi, chọn ngày mới rồi tạo chuyến tiếp theo.");
  setView("selected");
}
function renderTimeline(option){
  const panel=$("timeline");panel.replaceChildren();if(!option)return;const chosen=state.chosen?.option_id===option.option_id;
  const header=node("div",undefined,"timeline-heading");header.append(node("h2",chosen?"Lịch bạn đã chọn":"Xem trước lịch"),node("p",`${option.label} · ${option.date} · ${option.start_time}–${option.return_time}`));panel.append(header);
  if(!chosen)panel.append(node("p","Chọn lịch này để chỉnh thứ tự và thời lượng.","muted"));
  else{const label=node("label","Đổi giờ xuất phát"),input=node("input");input.type="time";input.value=$("startTime").value;input.id="timelineDeparture";input.onchange=()=>{$("startTime").value=input.value;$("timePreset").value="custom";invalidatePlan();submitPlan();};label.append(input);panel.append(label);}
  const visits=visitsOf(option);
  for(const block of option.timeline){const isVisit=block.role==="visit",el=node("article",undefined,isVisit?"timeline-stop":"timeline-transit");el.dataset.role=block.role;el.append(node("span",`${block.start_time}–${block.end_time}`),node(isVisit?"h3":"span",isVisit?block.name:` · ${block.name} · ${Math.ceil(block.duration_minutes)} phút`));
    if(isVisit){el.dataset.poiId=block.poi_id;for(const warning of block.warnings||[])el.append(node("p",warning,"muted"));
      if(chosen){const edit=node("div",undefined,"duration-editor"),label=node("label","Thời lượng (phút)"),input=node("input");input.type="number";input.min=5;input.max=720;input.step=1;input.value=state.durationOverrides[block.poi_id]||block.duration_minutes;input.setAttribute("aria-label",`Thời lượng ${block.name}`);label.append(input);edit.append(label,button("Tính lại",()=>{if(editDuration(block.poi_id,input.value))submitPlan();}));el.append(edit);
        const actions=node("div",undefined,"actions"),idx=visits.indexOf(block),up=button("↑ Lên",()=>reorder(block.poi_id,-1,true)),down=button("↓ Xuống",()=>reorder(block.poi_id,1,true));up.disabled=idx===0;down.disabled=idx===visits.length-1;up.setAttribute("aria-label",`Đưa ${block.name} lên`);down.setAttribute("aria-label",`Đưa ${block.name} xuống`);actions.append(up,down,button("Bỏ điểm",()=>{const p=state.selected.get(block.poi_id);if(p){togglePlace(p);submitPlan();}}));el.append(actions);
      }el.append(button("Xem địa điểm",()=>loadPoiDetail(block.poi_id)));
    }panel.append(el);
  }
  if(chosen)panel.append(button("Thêm địa điểm",()=>setView("explore")));
  if(option.unscheduled.length)panel.append(node("p","Vẫn trong danh sách muốn ghé: "+option.unscheduled.map(p=>p.name).join(", "),"warning"));
}
async function submitPlan(otherWindows=false){
  if(!$("planForm").reportValidity())return;
  state.controller?.abort();state.controller=new AbortController();const version=++state.planVersion;state.busy=true;
  $("planButton").disabled=true;$("planStatus").textContent="Đang thử thứ tự ghé và kiểm tra đường đi… Lịch trước vẫn được giữ để tham khảo.";setView("itinerary");document.querySelectorAll(".choose-option").forEach(el=>el.disabled=true);
  try{const data=await post("/api/v2/trip-suggestions",requestPayload(otherWindows),state.controller.signal);if(version!==state.planVersion)return;
    state.result=data;state.stale=false;state.busy=false;renderResult();$("planStatus").textContent=data.options.length?`${data.options.length} phương án. Xem chi tiết, rồi chọn lịch phù hợp.`:"Bạn có thể điều chỉnh theo các gợi ý bên dưới.";
    // Recalculation is a new proposal: a changed-time/partial-must option is never auto-accepted.
    if(state.chosen)$("planStatus").textContent+=" Lịch đã chọn được giữ bên dưới; chọn một phương án mới để cập nhật.";
    if(!state.chosen&&data.options.length){state.preview=data.options[0];renderTimeline(data.options[0]);drawRoute(data.options[0]);}else renderTimeline(state.chosen);$("itineraryView").scrollIntoView({block:"start"});saveDraft();
  }catch(e){if(version===state.planVersion&&e.name!=="AbortError"){$("planStatus").textContent=e.message;state.stale=true;}}
  finally{if(version===state.planVersion){state.busy=false;$("planButton").disabled=false;}}
}
$("planForm").onsubmit=e=>{e.preventDefault();submitPlan();};$("selectedPlan").onclick=()=>submitPlan();$("tryWindows").onclick=()=>submitPlan(true);
$("cancelOption").onclick=()=>$("confirmDialog").close();
$("timePreset").onchange=()=>{const times=presets[$("timePreset").value];if(times){$("startTime").value=times[0];$("endTime").value=times[1];}};
$("planForm").addEventListener("change",e=>{if(e.target.id==="planLocation")return;if(["startTime","endTime"].includes(e.target.id))$("timePreset").value="custom";if(["latitude","longitude"].includes(e.target.id)){$("startDescription").textContent="Tọa độ bạn nhập";updateStart();}invalidatePlan();scheduleRecommendations();});
$("planLocation").onchange=()=>{const next=$("planLocation").value;saveDraft(state.city);state.controller?.abort();state.planVersion++;state.recoVersion++;state.busy=false;$("planButton").disabled=false;restoreCity(next);$("planStatus").textContent="Đã khôi phục chuyến đi tại "+next;loadRecommendations();loadPois();};
$("pickStart").onclick=()=>{state.pickingStart=!state.pickingStart;$("mapInstruction").hidden=!state.pickingStart;$("pickStart").textContent=state.pickingStart?"Hủy ghim":"Ghim bản đồ";if(state.pickingStart){setView("map");map?.setView(basemapConfig[state.city].center,12,{animate:false});$("mapPanel").scrollIntoView({block:"center"});}};
$("locateStart").onclick=()=>{if(!navigator.geolocation){tell("Trình duyệt chưa hỗ trợ vị trí. Bạn có thể ghim trên bản đồ.");return;}const city=state.city;tell("Đang lấy vị trí của bạn…");navigator.geolocation.getCurrentPosition(p=>{if(city!==state.city)return;setStart(p.coords.latitude,p.coords.longitude,"Vị trí hiện tại của bạn");tell("Đã lấy vị trí hiện tại.");},()=>tell("Chưa lấy được vị trí. Hãy ghim trên bản đồ hoặc chọn một địa điểm."),{timeout:10000});};
$("catalogStart").onclick=()=>{setView("explore");tell("Mở chi tiết một địa điểm rồi chọn Xuất phát từ đây.");$("searchInput").focus();};
$("optimizeOrder").onclick=()=>{state.manualOrder=null;$("autoAdd").disabled=false;invalidatePlan();renderSelections();};
for(const el of document.querySelectorAll(".view-tabs [data-view]"))el.onclick=()=>setView(el.dataset.view);
let searchTimer;$("searchInput").oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadPois(),250);};$("typeFilter").onchange=()=>loadPois();
$("locationFilter").onchange=()=>{const loc=$("locationFilter").value,config=basemapConfig[loc];if(config)map?.setView(config.center,12,{animate:false});else if(!loc&&map&&nationalBounds)map.fitBounds(nationalBounds,{padding:[24,24]});loadBasemap(loc);loadPois();};
for(const [value,label] of Object.entries(labels)){const opt=node("option",label);opt.value=value;$("typeFilter").append(opt.cloneNode(true));$("tripTheme").append(opt);}
(async()=>{let city="Đà Nẵng";try{const saved=localStorage.getItem("where2go-trip-city-v1");if(basemapConfig[saved])city=saved;}catch{}
  restoreCity(city);try{await initializeMap();const data=await api("/api/v2/pois?view=explore&limit=1");for(const loc of data.locations){const opt=node("option",loc);opt.value=loc;$("locationFilter").append(opt);}await Promise.all([loadPois(),loadRecommendations()]);updateStart();if(state.chosen)drawRoute(state.chosen);}catch(e){tell(e.message);}
})();
