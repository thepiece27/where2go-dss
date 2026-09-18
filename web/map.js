"use strict";
// Map layers are independent of list pagination and of the routing snapshot.
const map = window.L ? L.map("map", {preferCanvas:true, minZoom:4}).setView([16,108],5) : null;
let markerLayer, startMarker, routeLayer, basemapLayer, basemapLocalLayer, basemapRenderer;
let nationalLayer, nationalBounds, onlineTiles, selectedMarker;
let mapFeatures=[], mapVersion=0, offline=false, tilesLoaded=0;
const localCache=new Map();

function basemapStyle(feature) {
  const kind=feature.properties?.kind, detail=feature.properties?.class;
  if(kind==="focus_boundary")return {color:"#aab6bb",weight:1,fillColor:"#f1f4ec",fillOpacity:1};
  if(kind==="green")return {stroke:false,fillColor:"#c9dfbc",fillOpacity:.8};
  if(kind==="water")return {stroke:false,fillColor:"#a5d3e3",fillOpacity:1};
  if(kind==="waterway"||kind==="coastline")return {color:"#73b3cd",weight:1.5};
  if(kind==="admin")return {color:"#a1a5b1",weight:1,dashArray:"4 5",fill:false};
  if(kind==="road")return {color:detail==="major"?"#e6b25f":detail==="secondary"?"#ead1a5":"#fff",weight:detail==="major"?3:1.5};
  return {color:"#abb6b8",weight:1,fillOpacity:.2};
}
function clearBasemap() {
  for(const layer of [basemapLayer,basemapLocalLayer])if(layer&&map)map.removeLayer(layer);
  basemapLayer=basemapLocalLayer=null;
}
function updateLocalBasemapVisibility() {
  if(!map||!basemapLocalLayer)return;
  if(offline&&map.getZoom()>=13)basemapLocalLayer.addTo(map);
  else map.removeLayer(basemapLocalLayer);
}
function setOffline(value) {
  offline=value;
  if(!map)return;
  map.getContainer().dataset.basemap=value?"offline":"online";
  $("mapStatus").hidden=!value;
  $("mapStatus").textContent=value?"Đang dùng bản đồ dự phòng. Chi tiết offline có tại Hà Nội và Đà Nẵng.":"";
  if(value)loadBasemap($("locationFilter").value);
  else clearBasemap();
}
async function loadBasemap(location) {
  if(!map)return;
  const version=++state.basemapVersion, config=basemapConfig[location];
  clearBasemap();
  if(!offline||!config)return;
  try {
    let data=localCache.get(config.slug);
    if(!data){data=await api(`/api/v2/basemaps/${config.slug}`);localCache.set(config.slug,data);}
    if(version!==state.basemapVersion||!offline)return;
    const options={renderer:basemapRenderer,pane:"basemapPane",interactive:false,style:basemapStyle};
    basemapLayer=L.geoJSON(data,{...options,filter:f=>!(f.properties?.kind==="road"&&f.properties?.class==="local")}).addTo(map);
    basemapLocalLayer=L.geoJSON(data,{...options,filter:f=>f.properties?.kind==="road"&&f.properties?.class==="local"});
    updateLocalBasemapVisibility();
    map.getContainer().dataset.basemap=config.slug;
    map.getContainer().dataset.basemapFeatures=String(data.features.length);
  } catch(error) {
    if(version===state.basemapVersion)$("mapStatus").textContent="Bản đồ dự phòng toàn quốc; chi tiết địa phương chưa sẵn sàng.";
  }
}
function markerColor(category) {
  if(["beach","nature_area","park","viewpoint"].includes(category))return "#137c8b";
  if(foodCategories.has(category))return "#b56522";
  if(["temple","historic","museum","old_quarter"].includes(category))return "#7552a0";
  return "#2368aa";
}
function highlightPoi(poi) {
  if(!map)return;
  if(selectedMarker)map.removeLayer(selectedMarker);
  selectedMarker=L.circleMarker([poi.latitude,poi.longitude],{radius:11,color:"#d64c28",weight:3,fillOpacity:.12}).addTo(map);
}
function renderMapMarkers() {
  if(!map||!markerLayer)return;
  markerLayer.clearLayers();
  const buckets=new Map(), zoom=map.getZoom();
  for(const feature of mapFeatures) {
    const [lon,lat]=feature.geometry.coordinates, point=map.project([lat,lon],zoom);
    const key=`${Math.floor(point.x/52)}:${Math.floor(point.y/52)}`;
    if(!buckets.has(key))buckets.set(key,[]);
    buckets.get(key).push(feature);
  }
  for(const group of buckets.values()) {
    if(group.length===1) {
      const feature=group[0],p=feature.properties,[lon,lat]=feature.geometry.coordinates;
      L.circleMarker([lat,lon],{radius:6,color:"#fff",weight:1.5,fillColor:markerColor(p.category),fillOpacity:.92})
        .addTo(markerLayer).bindTooltip(node("span",p.name)).on("click",()=>loadPoiDetail(p.poi_id));
    } else {
      const coords=group.map(f=>[f.geometry.coordinates[1],f.geometry.coordinates[0]]), bounds=L.latLngBounds(coords);
      const badge=node("span",String(group.length),"poi-cluster");
      L.marker(bounds.getCenter(),{icon:L.divIcon({html:badge,className:"cluster-icon",iconSize:[38,38]})}).addTo(markerLayer)
        .on("click",()=>{
          if(zoom<17){map.fitBounds(bounds,{padding:[55,55],maxZoom:zoom+3});return;}
          const list=node("div",undefined,"cluster-list");
          for(const feature of group){const button=node("button",feature.properties.name);button.onclick=()=>{map.closePopup();loadPoiDetail(feature.properties.poi_id);};list.append(button);}
          L.popup().setLatLng(bounds.getCenter()).setContent(list).openOn(map);
        });
    }
  }
  map.getContainer().dataset.mapPoiCount=String(mapFeatures.length);
}
async function loadMapPois() {
  if(!map)return;
  const version=++mapVersion,b=map.getBounds();
  const params=new URLSearchParams({bbox:[Math.max(-180,b.getWest()),Math.max(-90,b.getSouth()),Math.min(180,b.getEast()),Math.min(90,b.getNorth())].join(","),
    location:$("locationFilter").value,category:$("typeFilter").value,query:$("searchInput").value});
  try {const data=await api("/api/v2/map-pois?"+params);if(version!==mapVersion)return;mapFeatures=data.features;renderMapMarkers();}
  catch(error){if(version===mapVersion){mapFeatures=[];renderMapMarkers();$("systemStatus").textContent=error.message;}}
}
async function initializeMap() {
  if(!map)return;
  map.createPane("nationalPane");map.getPane("nationalPane").style.zIndex="180";
  map.createPane("basemapPane");map.getPane("basemapPane").style.zIndex="190";
  map.getPane("basemapPane").style.pointerEvents="none";
  basemapRenderer=L.canvas({pane:"basemapPane",padding:.5});
  markerLayer=L.layerGroup().addTo(map);
  onlineTiles=L.tileLayer("https://tile.openstreetmap.de/{z}/{x}/{y}.png",{
    maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Tiles: <a href="https://www.openstreetmap.de/">FOSSGIS</a>'});
  onlineTiles.on("tileload",()=>{tilesLoaded++;if(offline)setOffline(false);});
  onlineTiles.on("loading",()=>{tilesLoaded=0;});
  onlineTiles.on("load",()=>setOffline(!tilesLoaded));
  onlineTiles.on("tileerror",()=>{if(!tilesLoaded&&!offline)setOffline(true);});
  onlineTiles.addTo(map);
  setTimeout(()=>{if(!tilesLoaded)setOffline(true);},6000);
  let timer;map.on("moveend",()=>{clearTimeout(timer);timer=setTimeout(loadMapPois,180);});
  map.on("zoomend",updateLocalBasemapVisibility);
  map.on("click",e=>onMapStart(e.latlng.lat,e.latlng.lng));
  try {
    const data=await api("/data/vietnam-boundaries.json");
    nationalLayer=L.geoJSON(data,{pane:"nationalPane",style:{color:"#98b1b2",weight:.8,fillColor:"#edf0df",fillOpacity:1},
      onEachFeature:(feature,layer)=>layer.bindTooltip(node("span",feature.properties.name))}).addTo(map);
    nationalBounds=nationalLayer.getBounds();map.fitBounds(nationalBounds,{padding:[24,24],animate:false});
  } catch {nationalBounds=L.latLngBounds([[7.1,102],[23.5,117.9]]);map.fitBounds(nationalBounds);}
  $("viewVietnam").onclick=()=>{$("locationFilter").value="";map.fitBounds(nationalBounds,{padding:[24,24]});loadPois();loadBasemap("");};
  for(const button of document.querySelectorAll("[data-map-location]"))button.onclick=()=>{$("locationFilter").value=button.dataset.mapLocation;$("locationFilter").dispatchEvent(new Event("change"));};
}
