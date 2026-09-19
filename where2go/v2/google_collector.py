"""Repository-owned collector adapter. Entity coordinates never use the viewport."""
import re
from difflib import SequenceMatcher
from urllib.parse import unquote, urlparse, parse_qs, quote

from where2go.catalog import haversine
from where2go.ranking import normalize
from .observations import entity_coordinate


def google_identity(url):
    text = unquote(str(url or ""))
    query = parse_qs(urlparse(text).query)
    for key in ("query_place_id", "place_id", "cid"):
        if query.get(key):
            return query[key][0]
    match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+|ChI[^!/?&]+)", text)
    return match.group(1) if match else None


def image_url_allowed(url):
    try:
        parsed = urlparse(str(url or ""))
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username
                    and not parsed.password and not re.search(
                        r"/ogw/|/a-/|/a/|favicon|logo|avatar|[?&]w=32(?:&|$)", parsed.path + "?" + parsed.query, re.I))
    except ValueError:
        return False


def name_similarity(a, b):
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def normalize_place(raw, url):
    place = dict(raw)
    from .google_hours import clean_google_text
    for field in ("name", "address", "phone", "category", "description"):
        if place.get(field):
            place[field] = clean_google_text(place[field])
    url = place.get("google_maps_url") or url or place.get("url") or ""
    place["google_maps_url"] = url
    place["place_id"] = google_identity(url) or place.get("place_id")
    viewport = re.search(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", url)
    place["viewport_coordinate"] = list(map(float, viewport.groups())) if viewport else None
    coordinate = entity_coordinate(url)
    place["latitude"], place["longitude"] = coordinate or (None, None)
    place["coordinate_method"] = "google_entity_url" if coordinate else "unknown"
    if not image_url_allowed(place.get("image_url")):
        place["image_url"] = None
    return place


def spotlit_entity(tree):
    """Decode the single highlighted map entity, excluding viewport coordinates."""
    matches = {}
    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            if (len(value) > 3 and isinstance(value[0], list) and len(value[0]) == 2
                    and all(isinstance(v, str) and v.isdigit() for v in value[0])
                    and isinstance(value[1], str) and value[1].startswith(("/g/", "/m/"))
                    and isinstance(value[3], list) and len(value[3]) == 2
                    and all(isinstance(v, int) for v in value[3])):
                lat, lon = (v / 10_000_000 for v in value[3])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    ident = ":".join(hex(int(v)) for v in value[0])
                    matches[ident] = {"place_id": ident, "latitude": lat, "longitude": lon}
            for child in value:
                if isinstance(child, (dict, list)):
                    walk(child)
    walk(tree)
    return next(iter(matches.values())) if len(matches) == 1 else None


def assess_identity(seed, place):
    names = [seed.get("seed_name", ""), *seed.get("aliases", [])]
    score = max((name_similarity(name, place.get("name", "")) for name in names), default=0)
    expected_id = seed.get("expected_place_id")
    same_id = bool(expected_id and expected_id == place.get("place_id"))
    lat, lon = place.get("latitude"), place.get("longitude")
    distance = None
    if None not in (lat, lon, seed.get("latitude"), seed.get("longitude")):
        distance = haversine((lat, lon), (float(seed["latitude"]), float(seed["longitude"])))
    address = normalize(place.get("address") or "")
    expected = normalize(seed.get("location_expected") or "")
    location_ok = bool(expected and (expected in address or
                       (expected == "da nang" and any(x in address for x in ("hoi an", "quang nam")))))
    spatial_ok = distance is not None and distance <= .3
    # An already cross-checked external ID can describe an area whose marker is not its entrance.
    confirmed = bool(place.get("place_id") and lat is not None and lon is not None
                     and (same_id or (score >= .72 and (spatial_ok or location_ok))))
    return {"status": "tool_confirmed" if confirmed else "needs_review", "name_score": round(score, 4),
            "same_external_id": same_id, "location_match": location_ok,
            "distance_km": distance, "method": "external_id" if same_id else "name_and_location"}


def choose_anchor(seed, anchors):
    candidates = {}
    for anchor in anchors:
        ident = google_identity(anchor["url"])
        score = max(name_similarity(n, anchor["name"]) for n in [seed["seed_name"], *seed.get("aliases", [])])
        if score < .65 or not ident:
            continue
        coordinate = entity_coordinate(anchor["url"])
        distance = None
        if coordinate and seed.get("latitude") is not None and seed.get("longitude") is not None:
            distance = haversine(coordinate, (float(seed["latitude"]), float(seed["longitude"])))
        candidates[ident] = {**anchor, "score": score, "distance": distance}
    near = [r for r in candidates.values() if r["distance"] is not None and r["distance"] <= .3]
    if len(near) == 1:
        return near[0]["url"]
    if near:
        return None
    ordered = sorted(candidates.values(), key=lambda row: row["score"], reverse=True)
    if ordered and (len(ordered) == 1 or ordered[0]["score"] > ordered[1]["score"] + .08):
        return ordered[0]["url"]
    return None


async def collect_page(page, seed):
    """Use a normal browser context; stop on challenges; retain raw parser output."""
    from gmaps_scraper.parser import parse_place_details
    from urllib.parse import quote_plus
    url = seed.get("maps_url") or "https://www.google.com/maps/search/?api=1&query=" + quote_plus(seed["query"])
    await page.goto(url + ("&" if "?" in url else "?") + "hl=en", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(1800)
    body = (await page.locator("body").inner_text())[:18000].lower()
    if any(token in body for token in ("unusual traffic", "our systems have detected", "verify you're human", "before you continue to google")):
        return {"status": "blocked", "success": False, "error": "access_challenge", "place": None}
    if "/maps/place/" not in page.url:
        anchors = await page.locator('a[href*="/maps/place/"]').evaluate_all(
            "els=>els.map(a=>({url:a.href,name:a.getAttribute('aria-label')||a.innerText}))")
        selected = choose_anchor(seed, anchors)
        if selected:
            await page.goto(selected, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1500)
    try:
        await page.locator('h1').filter(has_not_text=re.compile(r"^(Results|Kết quả)$")).first.wait_for(timeout=12000)
    except Exception:
        return {"status": "unresolved", "success": False, "error": "no_entity_panel", "place": None}
    raw = (await parse_place_details(page)).model_dump(mode="json")
    entity_url = page.url
    marker = None
    if not entity_coordinate(entity_url):
        highlighted = await page.evaluate("()=>window.APP_INITIALIZATION_STATE?.[2]||null")
        marker = spotlit_entity(highlighted)
        if marker and not weak_panel_name(raw.get("name")):
            entity_url = ("https://www.google.com/maps/place/" + quote(raw["name"]) +
                          "/data=!4m6!3m5!1s" + marker["place_id"] +
                          f"!8m2!3d{marker['latitude']}!4d{marker['longitude']}")
            raw["google_maps_url"] = entity_url
    images = await page.locator('button.aoRNLd img, button[jsaction*="heroHeaderImage"] img, button[jsaction*="photo"] img').evaluate_all(
        "els=>els.filter(e=>e.naturalWidth>=200).map(e=>e.currentSrc||e.src)")
    place = normalize_place(raw, entity_url)
    place["entity_marker_evidence"] = marker
    place["image_url"] = next((url for url in images if image_url_allowed(url)), place.get("image_url"))
    place["image_urls"] = list(dict.fromkeys(url for url in [place.get("image_url"), *images] if image_url_allowed(url)))[:4]
    extras = await page.evaluate("""() => {
        const text = s => [...document.querySelectorAll(s)].map(e => e.innerText.trim()).filter(Boolean);
        return {amenities_raw: text('[data-section-id="7"] [aria-label]'),
                admission_raw: text('a[data-item-id*="ticket"], button[data-item-id*="ticket"]')};
    }""")
    place.update(extras)
    assessment = assess_identity(seed, place)
    missing = [field for field in ("image_url", "hours", "rating", "review_count", "address") if place.get(field) in (None, "", [])]
    if weak_panel_name(place.get("name")) or not google_identity(entity_url):
        return {"status": "unresolved", "success": False, "error": "search_results_not_entity", "place": place, "raw_place": raw}
    return {"status": "complete" if assessment["status"] == "tool_confirmed" and not missing else
            "partial" if assessment["status"] == "tool_confirmed" else "needs_review",
            "success": True, "place": place, "raw_place": raw, "identity": assessment, "missing_fields": missing}


def weak_panel_name(name):
    return normalize(name) in ("", "results", "ket qua")
