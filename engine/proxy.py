from pathlib import Path
from .utils import ensure_folder, parse_list, parse_output_pattern
from .run_command import run_command


# ─────────────────────────────────────────────────────────────
#  PROXY (single)
# ─────────────────────────────────────────────────────────────
def proxy_single(input_file, start, duration, output_file, log=None):
    input_file = Path(input_file)
    output_file = Path(output_file)

    # 1. Validate input
    if not input_file.is_file():
        return {
            "ok": False,
            "error": f"Input file not found: {input_file}",
            "data": None
        }

    # 2. Ensure output folder exists
    folder_ok = ensure_folder(output_file.parent)
    if not folder_ok["ok"]:
        return {
            "ok": False,
            "error": f"Failed to create folder: {folder_ok['error']}",
            "data": None
        }

    # 3. Build command
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(input_file),
        "-t", str(duration),
        "-c", "copy",
        str(output_file)
    ]

    desc = f"Create proxy: start={start}, duration={duration}"
    result = run_command(cmd, desc, log_callback=log)

    # 4. If failed → return as is
    if not result["ok"]:
        return result

    # 5. Calculate file size
    size_kb = output_file.stat().st_size / 1024 if output_file.exists() else None

    # 6. Return universal result
    result["data"]["output_file"] = str(output_file)
    result["data"]["size_kb"] = round(size_kb, 2) if size_kb else None
    return result



# ─────────────────────────────────────────────────────────────
#  PROXY (multi)
# ─────────────────────────────────────────────────────────────
def proxy_multi(input_file, starts_raw, duration, out_pattern, log=None):
    # 1. Parse start list
    starts = parse_list(starts_raw)
    if not starts:
        return {
            "ok": False,
            "error": "At least one start value is required.",
            "data": None
        }

    # 2. Parse pattern
    parent, stem, suffix = parse_output_pattern(out_pattern)

    results = []

    # 3. Loop
    for idx, start in enumerate(starts, start=1):
        output_file = parent / f"{stem}_{idx:02d}{suffix}"

        res = proxy_single(
            input_file=input_file,
            start=start,
            duration=duration,
            output_file=output_file,
            log=log
        )

        # Add index metadata
        res["data"] = res.get("data", {})
        res["data"]["index"] = idx

        results.append(res)

    # 4. Combine ok / error status
    all_ok = all(r["ok"] for r in results)

    return {
        "ok": all_ok,
        "error": None if all_ok else "One or more proxies failed to be created.",
        "data": results
    }
