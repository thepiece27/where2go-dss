"use strict";
(async()=>{
  const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
  try{const response=await fetch("/api/v2/dataset");if(!response.ok)throw new Error("Chưa đọc được báo cáo dữ liệu.");const data=await response.json();document.getElementById("datasetStatus").textContent=`${data.poi_count.toLocaleString("vi-VN")} địa điểm · ${data.dataset_version}`;
    for(const row of data.locations){const card=node("article","");card.append(node("h2",row.location),node("p",`${row.usable.toLocaleString("vi-VN")} địa điểm hợp lệ; ${row.serviceable.toLocaleString("vi-VN")} qua điều kiện planner nghiên cứu.`),node("p",`${row.with_structured_hours.toLocaleString("vi-VN")} có giờ cấu trúc; ${row.with_specific_duration.toLocaleString("vi-VN")} có hồ sơ thời lượng riêng; ${row.with_verified_access.toLocaleString("vi-VN")} có điểm tiếp cận đã xác minh.`));document.getElementById("coverage").append(card);}
    for(const [file,label] of [["merged_dataset.xlsx","Workbook tổng hợp"],["pois.csv","Địa điểm"],["field_provenance.csv","Nguồn từng trường"],["opening_hours.csv","Giờ mở cửa"],["duration_profiles.csv","Thời lượng"],["access_points.csv","Điểm tiếp cận"],["ratings.csv","Đánh giá"],["images.csv","Ảnh"],["sources.csv","Nguồn và quyền sử dụng"],["summary.json","Báo cáo độ phủ"],["audit.json","Báo cáo kiểm tra"]]){const a=node("a",label);a.href="/api/v2/dataset/"+file;a.download="";document.getElementById("datasetDownloads").append(a);}
  }catch(e){document.getElementById("datasetStatus").textContent=e.message;}
})();
