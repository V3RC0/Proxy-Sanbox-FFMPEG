import subprocess

def check_ffmpeg():
    """
    Checks whether 'ffmpeg' can be executed from PATH.
    Does not handle logs, does not display anything.
    Only returns ok/error for the GUI.
    """
    try:
        # Run ffmpeg -version (discard output)
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return {"ok": True}

    except FileNotFoundError:
        return {
            "ok": False,
            "error": "FFmpeg not found in PATH."
        }

    except subprocess.CalledProcessError:
        # ffmpeg found but error occurred (rare case)
        return {
            "ok": False,
            "error": "FFmpeg found, but could not be executed."
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Error while running FFmpeg: {e}"
        }
