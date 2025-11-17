from pathlib import Path

def parse_list(value, allow_none=False):
    """
    Converts 'a,b,c' → ['a','b','c'].
    allow_none=True → empty result becomes None.
    """
    if value is None:
        return None if allow_none else []

    s = str(value).strip()
    if not s:
        return None if allow_none else []

    parts = [p.strip() for p in s.split(",") if p.strip()]

    if not parts and allow_none:
        return None

    return parts



def ensure_folder(folder):
    """
    Ensures the folder exists.
    Return: {"ok": True} or {"ok": False, "error": "..."}
    """
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}



def parse_output_pattern(pattern):
    """
    Produces (parent folder, filename stem, extension).
    No extension → defaults to .mp4
    """
    p = Path(pattern)

    parent = p.parent if str(p.parent) != "" else Path(".")
    stem = p.stem if p.suffix else p.name
    suffix = p.suffix if p.suffix else ".mp4"

    return parent, stem, suffix
