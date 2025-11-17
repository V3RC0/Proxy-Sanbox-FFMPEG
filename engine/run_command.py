import subprocess
import time
import shlex


def run_command(cmd_list, desc="", log_callback=None):
    """
    Main executor: runs ffmpeg, provides real-time logs for the GUI,
    measures execution time, and returns results in a universal format.
    Does not check ffmpeg. If ffmpeg is not available, Popen will raise
    an error and it is handled as a generic error.
    """

    def _log(msg):
        if log_callback:
            log_callback(msg)

    cmd_str = " ".join(shlex.quote(part) for part in cmd_list)

    # ─ Info log
    if desc:
        _log(f"[INFO] {desc}")
    _log(f"[CMD]  {cmd_str}")

    start_time = time.perf_counter()
    stdout_lines = []

    try:
        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            line = line.rstrip()
            stdout_lines.append(line)
            _log(f"[FFMPEG] {line}")

        process.wait()
        returncode = process.returncode

    except Exception as e:
        # Generic error, without special 'ffmpeg not found' message
        elapsed = time.perf_counter() - start_time
        msg = f"Error while running command: {e}"
        _log(f"[ERROR] {msg}")
        return {
            "ok": False,
            "error": msg,
            "data": {
                "command": cmd_str,
                "elapsed_sec": round(elapsed, 6),
                "returncode": -1,
                "stdout_lines": stdout_lines,
            }
        }

    # ─ Finished
    elapsed = time.perf_counter() - start_time
    _log(f"[INFO] Finished in {round(elapsed, 3)} seconds")

    return {
        "ok": (returncode == 0),
        "error": None if returncode == 0 else "Command returned returncode != 0",
        "data": {
            "command": cmd_str,
            "elapsed_sec": round(elapsed, 6),
            "returncode": returncode,
            "stdout_lines": stdout_lines,
        }
    }
