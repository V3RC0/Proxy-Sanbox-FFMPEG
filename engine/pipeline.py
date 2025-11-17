from pathlib import Path
from .proxy import proxy_multi
from .encode import encode_multi, encode_single
from .validator import load_and_validate_recipes
from .utils import ensure_folder
from .ffmpeg_check import check_ffmpeg
from .metrics import get_size, calc_psnr, calc_ssim
from .summary_csv import write_summary_csv


# ───────────────────────────────────────────────
# 1. PROXY AND TEST
# ───────────────────────────────────────────────
def proxy_and_test(input_file, start_list, duration, recipes_json,
                   pick=None, outdir="test_out", log=None, keep_proxy=False):


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
    summary_rows = []
    all_results = []

    for p in proxy_list:
        pdata = p["data"]
        proxy_file = pdata["output_file"]
        idx = pdata["index"]

        # get original proxy size (in bytes)
        size_original = get_size(proxy_file)

        # create a dedicated output folder for this proxy index
        each_out = outdir / f"proxy_{idx:02d}"
        each_out.mkdir(parents=True, exist_ok=True)

        # run all recipes for this proxy clip
        enc_res = encode_multi(
            proxy_file=proxy_file,
            recipes_dict=recipes_dict,
            pick_raw=pick,
            outdir=each_out,
            log=log,
        )
        all_results.append(enc_res)

        for item in enc_res.get("data", []):
            d = item.get("data", {})

            recipe_id = d.get("recipe_id", "UNKNOWN")
            encoded_file = d.get("output_file")
            size_encoded = get_size(encoded_file) if encoded_file else None
            encode_time = d.get("elapsed_sec")

            # compute PSNR & SSIM between original proxy and encoded result
            psnr = calc_psnr(proxy_file, encoded_file)
            ssim = calc_ssim(proxy_file, encoded_file)

            summary_rows.append([
                idx,            # proxy_index
                recipe_id,      # recipe_id
                size_original,  # original proxy size (bytes)
                size_encoded,   # encoded file size (bytes)
                encode_time,    # encode duration (seconds)
                psnr,
                ssim,
            ])

        # remove the temporary proxy file after all tests for this proxy
        if not keep_proxy:
            try:
                Path(proxy_file).unlink()
            except OSError:
                pass


    
    # Generate CSV (fail-safe)
    try:
        write_summary_csv(summary_rows, outdir)
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
