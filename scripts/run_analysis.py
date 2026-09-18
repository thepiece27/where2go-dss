"""Execute the report notebook with this Python environment, without a global kernel install."""
import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=ROOT / "notebooks/phan_tich_du_lieu_poi.ipynb")
    parser.add_argument("--output", type=Path, help="Default: update the notebook with executed outputs")
    args = parser.parse_args()
    notebook = nbformat.read(args.notebook, as_version=4)
    with TemporaryDirectory(prefix="where2go-kernel-") as temp:
        spec = Path(temp) / "kernels/where2go-report"
        spec.mkdir(parents=True)
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Where2Go report", "language": "python",
        }), encoding="utf-8")
        previous = os.environ.get("JUPYTER_PATH")
        os.environ["JUPYTER_PATH"] = temp + (os.pathsep + previous if previous else "")
        try:
            NotebookClient(notebook, timeout=300, kernel_name="where2go-report",
                           resources={"metadata": {"path": str(ROOT)}}).execute()
        finally:
            if previous is None:
                os.environ.pop("JUPYTER_PATH", None)
            else:
                os.environ["JUPYTER_PATH"] = previous
    output = args.output or args.notebook
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output)
    count = sum(cell.cell_type == "code" for cell in notebook.cells)
    print(f"PASS: {count} code cells executed; {output}")


if __name__ == "__main__":
    main()
