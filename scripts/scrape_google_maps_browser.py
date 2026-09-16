import asyncio
import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd

try:
    from playwright.async_api import async_playwright
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
except ModuleNotFoundError:
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None


DEFAULT_INPUT = "data/vietnam_destinations.xlsx"
DEFAULT_OUTPUT = "data/vietnam_destinations_google_maps_browser.xlsx"
DEFAULT_NAME_COL = "Tên địa điểm"
RATING_COLUMN_NAME = "Đánh giá"
IMAGE_COLUMN_NAME = "Ảnh"

RESULT_COLUMNS = [
    "maps_match_status",
    "maps_result_name",
    "maps_destination_type",
    "maps_review_count",
    "maps_review_label",
    "maps_first_open_hours",
    "maps_open_hours",
    "maps_url",
    "maps_error",
]

FILL_MISSING_ONLY_COLUMNS = [
    "maps_destination_type",
    "maps_review_count",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Open Google Maps in a browser, search destination names from an Excel/CSV "
            "file, and fill missing place type and review count."
        )
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input Excel/CSV file.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output Excel/CSV file.")
    parser.add_argument("--name-col", default=DEFAULT_NAME_COL, help="Destination name column.")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N matching rows.")
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Zero-based dataframe index to start from. Useful for resuming.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=(
            "Kept for compatibility. Existing values are always preserved; only missing "
            "maps_destination_type and maps_review_count are filled."
        ),
    )
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between searches.")
    parser.add_argument("--workers", type=int, default=5, help="Number of parallel browser tabs.")
    parser.add_argument("--save-every", type=int, default=25, help="Save after every N scraped rows.")
    parser.add_argument("--timeout-ms", type=int, default=15000, help="Per-action timeout.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without showing the browser. Default is headed, as requested.",
    )
    parser.add_argument(
        "--browser-channel",
        default=None,
        help='Optional installed browser channel, for example "chrome" or "msedge".',
    )
    parser.add_argument(
        "--user-data-dir",
        default="data/google_maps_browser_profile",
        help="Persistent browser profile directory.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Leave the browser open after the script finishes.",
    )
    return parser.parse_args()


def read_table(path):
    suffix = Path(path).suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input format: {suffix}")


def write_table(df, path):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    target_path = output_path
    for attempt in range(3):
        try:
            if suffix in [".xlsx", ".xls"]:
                df.to_excel(target_path, index=False)
                return target_path
            if suffix == ".csv":
                df.to_csv(target_path, index=False, encoding="utf-8-sig")
                return target_path
        except PermissionError:
            if attempt < 2:
                time.sleep(1)
                continue
            target_path = output_path.with_name(f"{output_path.stem}_autosave{output_path.suffix}")
            print(
                f"Cannot write {output_path}; saving progress to {target_path}. "
                "Close the workbook to save to the original file.",
                file=sys.stderr,
                flush=True,
            )
            if suffix in [".xlsx", ".xls"]:
                df.to_excel(target_path, index=False)
                return target_path
            if suffix == ".csv":
                df.to_csv(target_path, index=False, encoding="utf-8-sig")
                return target_path
    raise ValueError(f"Unsupported output format: {suffix}")


def xpath_literal(value):
    text = str(value)
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    return "concat(" + ', "\'", '.join(f"'{part}'" for part in text.split("'")) + ")"


def parse_review_count(label):
    if not value_present(label):
        return None
    if isinstance(label, (int, float)) and not pd.isna(label):
        return int(label)
    cleaned = str(label).replace("\xa0", " ")
    match = re.search(r"([\d][\d,.\s]*)", cleaned)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


async def safe_text(locator, timeout_ms=1500):
    try:
        text = await locator.inner_text(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return None
    except Exception:
        return None
    text = " ".join(text.split())
    return text or None


async def maybe_click_consent(page):
    button_names = [
        "Accept all",
        "I agree",
        "Reject all",
        "Chấp nhận tất cả",
        "Tôi đồng ý",
        "Từ chối tất cả",
    ]
    for name in button_names:
        try:
            await page.get_by_role("button", name=re.compile(name, re.I)).click(timeout=100)
            await page.wait_for_timeout(50)
            return
        except Exception:
            continue


async def wait_for_place_loaded(page, timeout_ms):
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        try:
            if await page.locator("xpath=(//h1)[1]").count() > 0:
                return True
        except Exception:
            pass
        await page.wait_for_timeout(100)
    return False


async def click_named_result_if_present(page, destination_name, timeout_ms):
    escaped_name = xpath_literal(destination_name)
    result_link = page.locator(f"xpath=(//a[contains(@aria-label,{escaped_name})])[1]")
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        try:
            if await result_link.count() > 0:
                await result_link.first.click(timeout=2500)
                return True
        except Exception:
            pass
        await page.wait_for_timeout(100)
    return False


async def collect_type_candidates(page):
    buttons = page.locator('xpath=//div[@class="fontBodyMedium"]//button')
    candidates = []
    try:
        count = await buttons.count()
    except Exception:
        return candidates

    ignored_fragments = [
        "directions",
        "save",
        "nearby",
        "send",
        "share",
        "reviews",
        "photos",
        "call",
        "website",
        "chỉ đường",
        "lưu",
        "lân cận",
        "gửi",
        "chia sẻ",
        "bài đánh giá",
        "ảnh",
        "gọi",
        "trang web",
    ]
    for index in range(count):
        text = await safe_text(buttons.nth(index), timeout_ms=200)
        if not text:
            continue
        lower_text = text.lower()
        if any(fragment in lower_text for fragment in ignored_fragments):
            continue
        if text not in candidates:
            candidates.append(text)
    return candidates


async def collect_review_label(page):
    selectors = [
        'xpath=(//span[contains(@aria-label,"reviews")])[1]',
        'xpath=(//span[contains(@aria-label,"review")])[1]',
        'xpath=(//span[contains(@aria-label,"bài đánh giá")])[1]',
        'xpath=(//span[contains(@aria-label,"lượt đánh giá")])[1]',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            label = await locator.get_attribute("aria-label", timeout=500)
        except Exception:
            label = None
        if label:
            return " ".join(label.split())
    return None


async def scrape_destination(page, destination_name, timeout_ms):
    search_url = f"https://www.google.com/maps/search/{quote_plus(destination_name)}"
    await page.goto(search_url, timeout=timeout_ms, wait_until="domcontentloaded")
    await maybe_click_consent(page)

    clicked_result = await click_named_result_if_present(page, destination_name, timeout_ms=1000)
    if clicked_result:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)

    place_loaded = await wait_for_place_loaded(page, timeout_ms)
    await page.wait_for_timeout(200)

    result_name = await safe_text(page.locator("xpath=(//h1)[1]").first)
    type_candidates = await collect_type_candidates(page)
    review_label = await collect_review_label(page)

    status = "matched" if place_loaded or result_name else "not_found"
    return {
        "maps_match_status": status,
        "maps_destination_type": type_candidates[0] if type_candidates else None,
        "maps_review_count": parse_review_count(review_label),
    }


def normalize_column_name(name):
    normalized = " ".join(str(name).split()).casefold()
    return re.sub(r"\.\d+$", "", normalized)


def merge_duplicate_target_columns(df, expected_name):
    normalized_expected = normalize_column_name(expected_name)
    matching_columns = [
        column
        for column in df.columns
        if normalize_column_name(column) == normalized_expected
    ]
    if not matching_columns:
        raise KeyError(f"Input file does not contain required column: {expected_name}")

    primary_column = matching_columns[0]
    duplicate_columns = matching_columns[1:]
    for duplicate_column in duplicate_columns:
        missing_primary = df[primary_column].map(lambda value: not value_present(value))
        duplicate_has_value = df[duplicate_column].map(value_present)
        df.loc[missing_primary & duplicate_has_value, primary_column] = df.loc[
            missing_primary & duplicate_has_value,
            duplicate_column,
        ]

    if duplicate_columns:
        df.drop(columns=duplicate_columns, inplace=True)
    return primary_column


def value_present(value):
    if pd.isna(value):
        return False
    return str(value).strip() != ""


def apply_result_to_dataframe(df, row_index, result, needed_columns):
    for column in needed_columns:
        value = result.get(column)
        if value_present(value):
            df.at[row_index, column] = value


async def scrape_worker(
    worker_id,
    page,
    queue,
    df,
    df_lock,
    save_state,
    args,
    total,
):
    while True:
        try:
            ordinal, row_index, destination_name, needed_columns = queue.get_nowait()
        except asyncio.QueueEmpty:
            return

        try:
            print(f"[{ordinal}/{total}] Tab {worker_id}: Searching {destination_name}", flush=True)
            try:
                result = await scrape_destination(page, destination_name, args.timeout_ms)
            except Exception:
                result = {
                    "maps_match_status": "error",
                    "maps_destination_type": None,
                    "maps_review_count": None,
                }

            async with df_lock:
                apply_result_to_dataframe(
                    df,
                    row_index,
                    result,
                    needed_columns,
                )
                save_state["dirty"] += 1
                save_every = max(1, args.save_every)
                if save_state["dirty"] >= save_every:
                    saved_path = write_table(df, args.output)
                    save_state["dirty"] = 0
                    save_state["last_save_path"] = str(saved_path)

            print(
                "[{}/{}] Tab {}: {} -> {} filled={} type={} reviews={}".format(
                    ordinal,
                    total,
                    worker_id,
                    destination_name,
                    result.get("maps_match_status"),
                    ",".join(needed_columns),
                    result.get("maps_destination_type"),
                    result.get("maps_review_count"),
                ),
                flush=True,
            )
            if args.sleep > 0:
                await asyncio.sleep(args.sleep)
        finally:
            queue.task_done()


async def main_async():
    args = parse_args()
    if async_playwright is None:
        print(
            "Missing dependency: playwright. Run `pip install -r requirements.txt` "
            "and then `python -m playwright install chromium`.",
            file=sys.stderr,
        )
        sys.exit(2)

    df = read_table(args.input)
    if args.name_col not in df.columns:
        raise KeyError(f"Input file does not contain required column: {args.name_col}")
    merge_duplicate_target_columns(df, RATING_COLUMN_NAME)
    merge_duplicate_target_columns(df, IMAGE_COLUMN_NAME)

    for column in RESULT_COLUMNS:
        if column not in df.columns:
            df[column] = None

    indices = list(df.index[df.index >= args.start_index])
    if args.limit is not None:
        indices = indices[: args.limit]

    profile_dir = Path(args.user_data_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    queue = asyncio.Queue()
    total = len(indices)
    for ordinal, row_index in enumerate(indices, start=1):
        row = df.loc[row_index]
        destination_name = str(row.get(args.name_col, "")).strip()
        if not destination_name or destination_name.lower() == "nan":
            continue

        if not value_present(row.get("maps_review_count")):
            parsed_review_count = parse_review_count(row.get("maps_review_label"))
            if parsed_review_count is not None:
                df.at[row_index, "maps_review_count"] = parsed_review_count
                row = df.loc[row_index]

        needed_columns = [
            column for column in FILL_MISSING_ONLY_COLUMNS
            if not value_present(row.get(column))
        ]
        if not needed_columns:
            print(f"[{ordinal}/{total}] {destination_name} -> skipped")
            continue
        queue.put_nowait((ordinal, row_index, destination_name, needed_columns))

    if queue.empty():
        saved_path = write_table(df, args.output)
        print("No rows need maps_destination_type/maps_review_count scraping.")
        print(f"Saved: {saved_path}")
        return

    workers = max(1, args.workers)
    workers = min(workers, queue.qsize())

    async with async_playwright() as playwright:
        launch_options = {
            "headless": args.headless,
            "viewport": {"width": 1400, "height": 950},
            "locale": "en-US",
        }
        if args.browser_channel:
            launch_options["channel"] = args.browser_channel

        context = await playwright.chromium.launch_persistent_context(
            str(profile_dir),
            **launch_options,
        )
        pages = [await context.new_page() for _ in range(workers)]
        df_lock = asyncio.Lock()
        save_state = {"dirty": 0, "last_save_path": None}

        try:
            print(f"Scraping with {workers} parallel tab(s).", flush=True)
            tasks = [
                asyncio.create_task(
                    scrape_worker(
                        worker_id,
                        page,
                        queue,
                        df,
                        df_lock,
                        save_state,
                        args,
                        total,
                    )
                )
                for worker_id, page in enumerate(pages, start=1)
            ]
            await asyncio.gather(*tasks)
            async with df_lock:
                saved_path = write_table(df, args.output)
                save_state["dirty"] = 0
                save_state["last_save_path"] = str(saved_path)
        finally:
            if args.keep_open:
                print("Browser left open. Press Ctrl+C here when you are done.")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
            await context.close()

    print(f"Saved: {save_state['last_save_path']}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user.", file=sys.stderr)
        sys.exit(130)
