"""Check linked image candidates, redirects, dimensions and content without caching photos."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import io
import ipaddress
import json
from pathlib import Path
import socket
import sys
from urllib.parse import urlparse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import CATALOG_V2
from where2go.v2.google_collector import image_url_allowed
from where2go.v2.storage import connect


def public_url(url):
    if not image_url_allowed(url):
        raise ValueError("unsupported_or_profile_url")
    host = urlparse(url).hostname
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("non_public_image_host")


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def check_image(url):
    result = {"url": url, "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        from PIL import Image
        public_url(url)
        opener = urllib.request.build_opener(PublicRedirect)
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "Where2Go-DSS/2.0 image validation"}), timeout=10) as response:
            kind = response.headers.get_content_type()
            result.update(final_url=response.url, content_type=kind)
            if not kind.startswith("image/"):
                raise ValueError("not_image_content")
            content = response.read(5_000_001)
            if len(content) > 5_000_000:
                raise ValueError("image_too_large")
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
            img.verify()
        result.update(width=width, height=height)
        if width < 200 or height < 120:
            raise ValueError("thumbnail_or_icon_too_small")
        result["status"] = "valid"
    except Exception as error:
        result.update(status="unavailable", error=str(error)[:240])
    return result


def validate(catalog, cache, limit=None, retry=False, refresh=False):
    checks = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    with connect(catalog, readonly=True) as db:
        urls = [r[0] for r in db.execute("SELECT DISTINCT url FROM poi_images WHERE validation_status<>'rejected_url' AND identity_status IN ('entity_panel','legacy_entity_link') ORDER BY url")]
    pending = [url for url in urls if refresh or url not in checks or (retry and checks[url]["status"] != "valid")]
    if limit is not None:
        pending = pending[:limit]
    cache.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(check_image, url): url for url in pending}
        for number, future in enumerate(as_completed(futures), 1):
            checks[futures[future]] = future.result()
            if number % 25 == 0 or number == len(futures):
                temp = cache.with_suffix(".tmp")
                temp.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
                temp.replace(cache)
                print(json.dumps({"checked": number, "pending": len(futures), "valid_total": sum(r["status"] == "valid" for r in checks.values())}), flush=True)
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--cache", type=Path, default=ROOT / "data/cache/image_checks_v2.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Recheck previously valid URLs as well")
    args = parser.parse_args()
    validate(args.catalog, args.cache, args.limit, args.retry, args.refresh)
