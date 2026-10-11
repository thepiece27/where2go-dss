"""Package the project without Git history, environments or disposable caches."""

import json
import os
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    '.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
    '.ruff_cache', '.ipynb_checkpoints', '.mypy_cache', 'submission',
    '.aws', '.codex', '.agents',
}
PRIVATE_DIRS = {'data/private', 'data/google_maps_browser_profile'}
REQUIRED = {
    'README.md', 'docs/huong_dan_ban_nop.md', 'where2go/api.py',
    'requirements-app.lock.txt', 'data/catalog.sqlite', 'data/catalog_v2.sqlite',
    'data/routing/manifest.json', 'web/data/basemap-manifest.json',
    'web/data/basemap-danang.json.gz', 'web/data/basemap-hanoi.json.gz',
    'docs/tong_hop_khoa_hoc_poi_rs.md', 'notebooks/phan_tich_du_lieu_poi.ipynb',
    'docs/assets/screenshots/01_trang_chu_nhu_cau_preset.png',
    'docs/assets/screenshots/02_top_k_va_giai_thich.png',
    'docs/assets/screenshots/03_kham_pha_ban_do_poi.png',
    'docs/assets/screenshots/04_lap_lich_tham_khao.png',
}


def main():
    files = []
    for parent, dirs, names in os.walk(ROOT, followlinks=False):
        parent = Path(parent)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS
                         and not (parent / d).is_symlink()
                         and not (parent / d).is_junction()
                         and (parent / d).relative_to(ROOT).as_posix() not in PRIVATE_DIRS)
        for name in sorted(names):
            path = parent / name
            if (path.is_symlink() or name == '.env' or name.startswith('.env.')
                    or path.suffix in {'.pyc', '.pyo'}):
                continue
            files.append(path)
    relative_names = {p.relative_to(ROOT).as_posix() for p in files}
    missing = REQUIRED - relative_names
    if missing:
        raise SystemExit(f'Missing required submission files: {sorted(missing)}')
    # Do not copy a database while a write transaction may be in progress.
    for path in ROOT.glob('data/*.sqlite*'):
        if path.name.endswith(('-wal', '-journal')) and path.stat().st_size:
            raise SystemExit(f'Stop database writers before packaging: {path}')
    output = ROOT / 'submission'
    output.mkdir(exist_ok=True)
    archive = output / f'where2go-dss_nop_bai_{datetime.now():%Y%m%d_%H%M%S}.zip'
    prefix = 'where2go-dss/'
    with ZipFile(archive, 'x', compression=ZIP_DEFLATED, compresslevel=9) as package:
        for path in files:
            package.write(path, prefix + path.relative_to(ROOT).as_posix())
    with ZipFile(archive) as package:
        bad = package.testzip()
        if bad:
            raise SystemExit(f'Archive CRC check failed: {bad}')
        assert {prefix + name for name in REQUIRED} <= set(package.namelist())
        assert len(package.namelist()) == len(files)
    print(json.dumps({
        'archive': str(archive), 'files': len(files), 'crc_check': 'PASS',
        'input_mib': round(sum(p.stat().st_size for p in files) / 2**20, 2),
        'zip_mib': round(archive.stat().st_size / 2**20, 2),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
