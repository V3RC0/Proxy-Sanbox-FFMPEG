from pathlib import Path
from .utils import ensure_folder
from .utils import parse_list
from .run_command import run_command


# Mapping key → ffmpeg option output
RECIPE_MAP = {
    "codec": ("-c:v",),
    "crf": ("-crf",),
    "preset": ("-preset",),
    "b:v": ("-b:v",),
    "deadline": ("-deadline",),
}


# ─────────────────────────────────────────────────────────────
#  ENCODE (single)
# ─────────────────────────────────────────────────────────────
def encode_single(proxy_file, recipe_id, recipe_dict, output_file, log=None):
    proxy_file = Path(proxy_file)
    output_file = Path(output_file)

    # 1. Validate proxy file
    if not proxy_file.is_file():
        return {
            "ok": False,
            "error": f"Proxy file not found: {proxy_file}",
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

    # 3. Build encode command
    cmd = ["ffmpeg", "-y", "-i", str(proxy_file)]

    for key, val in recipe_dict.items():
        if key in RECIPE_MAP:
            cmd.extend([RECIPE_MAP[key][0], str(val)])
        else:
            # ignore unknown keys
            continue

    # always copy audio
    cmd.extend(["-c:a", "copy", str(output_file)])

    desc = f"Encode using recipe '{recipe_id}'"
    result = run_command(cmd, desc, log_callback=log)

    # If failed → return directly
    if not result["ok"]:
        return result

    # 4. Calculate size
    size_kb = output_file.stat().st_size / 1024 if output_file.exists() else None

    # 5. Return universal result
    result["data"]["output_file"] = str(output_file)
    result["data"]["size_kb"] = round(size_kb, 2) if size_kb else None
    result["data"]["recipe_id"] = recipe_id
    return result



# ─────────────────────────────────────────────────────────────
#  ENCODE (multi)
# ─────────────────────────────────────────────────────────────
def encode_multi(proxy_file, recipes_dict, pick_raw=None, outdir="out", log=None):
    outdir = Path(outdir)

    # 1. Ensure output folder exists
    folder_ok = ensure_folder(outdir)
    if not folder_ok["ok"]:
        return {
            "ok": False,
            "error": f"Failed to create output folder: {folder_ok['error']}",
            "data": None
        }

    # 2. Filter recipes if pick list is provided
    picks = parse_list(pick_raw, allow_none=True)

    if picks:
        # Take only selected recipes
        invalid = [x for x in picks if x not in recipes_dict]
        if invalid:
            return {
                "ok": False,
                "error": f"Recipe ID not found: {invalid}",
                "data": None
            }
        selected_recipes = {rid: recipes_dict[rid] for rid in picks}
    else:
        selected_recipes = recipes_dict.copy()

    results = []

    # 3. Loop through all recipes
    for recipe_id, recipe in selected_recipes.items():
        out_file = outdir / f"{recipe_id}.mp4"

        res = encode_single(
            proxy_file=proxy_file,
            recipe_id=recipe_id,
            recipe_dict=recipe,
            output_file=out_file,
            log=log
        )

        results.append(res)

    # 4. Combine OK state
    all_ok = all(r["ok"] for r in results)

    return {
        "ok": all_ok,
        "error": None if all_ok else "One or more encode operations failed.",
        "data": results
    }
