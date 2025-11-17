import json
from pathlib import Path

VALID_CODECS = ["libx264", "libx265", "libvpx-vp9"]

PRESETS = {
    "libx264": ["ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow"],
    "libx265": ["ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow","placebo"],
}

VP9_DEADLINES = ["good", "best", "realtime"]


def load_and_validate_recipes(path):
    path = Path(path)

    if not path.is_file():
        return {"ok": False, "error": f"recipes.json not found: {path}"}

    # Load JSON
    try:
        recipes = json.load(open(path, "r", encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}

    # Basic structure must be a dict
    if not isinstance(recipes, dict):
        return {"ok": False, "error": "recipes.json must be a dictionary {id: {...}}."}

    # Validate each recipe
    for rname, config in recipes.items():
        if not isinstance(config, dict):
            return {"ok": False, "error": f"Recipe '{rname}' is not a dictionary object."}

        # 'codec' is required
        if "codec" not in config:
            return {"ok": False, "error": f"Recipe '{rname}' does not contain 'codec'."}

        codec = config["codec"]
        if codec not in VALID_CODECS:
            return {"ok": False, "error": f"Recipe '{rname}': codec '{codec}' is not valid."}

        # CRF (optional but common)
        if "crf" in config:
            if not isinstance(config["crf"], int):
                return {"ok": False, "error": f"Recipe '{rname}': crf must be an integer."}

            crf = config["crf"]
            if codec in ["libx264", "libx265"] and not (0 <= crf <= 51):
                return {"ok": False, "error": f"Recipe '{rname}': crf {crf} is out of range 0–51."}

            if codec == "libvpx-vp9" and not (0 <= crf <= 63):
                return {"ok": False, "error": f"Recipe '{rname}': crf {crf} is out of range 0–63."}

        # Preset (x264/x265 only)
        if "preset" in config:
            preset = config["preset"]
            if codec not in PRESETS:
                return {"ok": False, "error": f"Recipe '{rname}': preset not supported for codec {codec}."}

            if preset not in PRESETS[codec]:
                return {"ok": False, "error": f"Recipe '{rname}': preset '{preset}' is not valid for {codec}."}

        # Deadline (VP9 only)
        if "deadline" in config:
            if codec != "libvpx-vp9":
                return {"ok": False, "error": f"Recipe '{rname}': deadline is only for codec libvpx-vp9."}
            if config["deadline"] not in VP9_DEADLINES:
                return {"ok": False, "error": f"Recipe '{rname}': deadline '{config['deadline']}' is not valid."}

        # bitrate (optional)
        if "b:v" in config:
            if not isinstance(config["b:v"], str):
                return {"ok": False, "error": f"Recipe '{rname}': b:v must be a string, e.g. '0' or '2000k'."}

    return {"ok": True, "data": recipes}
