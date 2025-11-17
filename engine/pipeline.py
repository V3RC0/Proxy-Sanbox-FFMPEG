from pathlib import Path
from .proxy import proxy_multi
from .encode import encode_multi, encode_single
from .validator import load_and_validate_recipes
from .utils import ensure_folder
from .ffmpeg_check import check_ffmpeg


# ───────────────────────────────────────────────
# 1. PROXY AND TEST
# ───────────────────────────────────────────────
def proxy_and_test(input_file, start_list, duration, recipes_json,
                   pick=None, outdir="test_out", log=None):

    # 1. CHECK FFMPEG FIRST
    ff = check_ffmpeg()
    if not ff["ok"]:
        return {"ok": False, "error": ff["error"], "data": None}
    
    input_file = Path(input_file)
    outdir = Path(outdir)

    # Validate input exists
    if not input_file.is_file():
        return {"ok": False, "error": f"Input not found: {input_file}"}

    # Load & validate recipes
    v = load_and_validate_recipes(recipes_json)
    if not v["ok"]:
        return {"ok": False, "error": v["error"]}

    recipes_dict = v["data"]

    # Ensure output folder
    outdir.mkdir(parents=True, exist_ok=True)

    # PROXY MULTI
    proxy_pattern = outdir / "proxy.mp4"
    proxy_res = proxy_multi(input_file, start_list, duration, proxy_pattern, log=log)

    if not proxy_res["ok"]:
        return proxy_res  # pass-through error

    proxy_list = proxy_res["data"]

    # TEST ENCODE FOR EACH PROXY
    all_results = []

    for p in proxy_list:
        pdata = p["data"]
        proxy_file = pdata["output_file"]
        idx = pdata["index"]

        # folder for each proxy
        each_out = outdir / f"proxy_{idx:02d}"
        each_out.mkdir(parents=True, exist_ok=True)

        enc_res = encode_multi(
            proxy_file=proxy_file,
            recipes_dict=recipes_dict,
            pick_raw=pick,
            outdir=each_out,
            log=log
        )
        all_results.append(enc_res)

        # Remove proxy file after use
        try:
            Path(proxy_file).unlink()
        except:
            pass

    return {
        "ok": True,
        "data": {
            "input": str(input_file),
            "proxies": proxy_list,
            "results": all_results,
            "output_folder": str(outdir),
        }
    }


# ───────────────────────────────────────────────
# 2. APPLY SINGLE
# ───────────────────────────────────────────────
def apply_single(input_file, recipe_id, recipes_json,
                 output_file, log=None):

    # 1. CHECK FFMPEG FIRST
    ff = check_ffmpeg()
    if not ff["ok"]:
        return {"ok": False, "error": ff["error"], "data": None}
    
    input_file = Path(input_file)
    output_file = Path(output_file)

    if not input_file.is_file():
        return {"ok": False, "error": f"Input not found: {input_file}"}

    # Load recipes
    v = load_and_validate_recipes(recipes_json)
    if not v["ok"]:
        return {"ok": False, "error": v["error"]}

    recipes = v["data"]
    if recipe_id not in recipes:
        return {"ok": False, "error": f"Recipe '{recipe_id}' not found"}

    recipe = recipes[recipe_id]

    # encode full video
    return encode_single(
        proxy_file=input_file,
        recipe_id=recipe_id,
        recipe_dict=recipe,
        output_file=output_file,
        log=log
    )


# ───────────────────────────────────────────────
# 3. APPLY MULTI
# ───────────────────────────────────────────────
def apply_multi(input_files, recipe_id, recipes_json,
                output_dir, log=None):

    # 1. CHECK FFMPEG FIRST
    ff = check_ffmpeg()
    if not ff["ok"]:
        return {"ok": False, "error": ff["error"], "data": None}
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load recipe
    v = load_and_validate_recipes(recipes_json)
    if not v["ok"]:
        return v

    recipes = v["data"]
    if recipe_id not in recipes:
        return {"ok": False, "error": f"Recipe '{recipe_id}' not found"}

    recipe = recipes[recipe_id]

    results = []

    for infile in input_files:
        infile_path = Path(infile)

        if not infile_path.is_file():
            results.append({
                "ok": False,
                "error": f"Input not found: {infile_path}",
                "data": None
            })
            continue

        out_name = infile_path.stem + "_" + recipe_id + ".mp4"
        out_file = output_dir / out_name

        res = encode_single(
            proxy_file=infile_path,
            recipe_id=recipe_id,
            recipe_dict=recipe,
            output_file=out_file,
            log=log
        )

        results.append(res)

    all_ok = all(r["ok"] for r in results)

    return {
        "ok": all_ok,
        "data": results,
        "error": None if all_ok else "Some files failed to process."
    }
