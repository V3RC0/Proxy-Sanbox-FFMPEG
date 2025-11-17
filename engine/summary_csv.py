import csv
from pathlib import Path

def write_summary_csv(rows, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "summary.csv"

    header = [
        "proxy_index",
        "recipe_id",
        "size_original",
        "size_encoded",
        "encode_time",
        "psnr",
        "ssim"
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    return csv_path
