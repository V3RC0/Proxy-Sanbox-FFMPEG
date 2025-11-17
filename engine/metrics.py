import subprocess
import shlex
import time
from pathlib import Path


# ======================
# SIZE
# ======================
def get_size(path):
    try:
        return Path(path).stat().st_size
    except:
        return None


# ======================
# PSNR
# ======================
def calc_psnr(original, encoded):
    cmd = [
        "ffmpeg",
        "-i", str(original),
        "-i", str(encoded),
        "-lavfi", "psnr",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        log = result.stderr

        for line in log.splitlines():

            # Format lama: "average:36.18"
            if "average:" in line:
                try:
                    return float(line.split("average:")[-1].split()[0])
                except:
                    pass

            # Format baru: "psnr_avg:36.18"
            if "psnr_avg:" in line:
                try:
                    return float(line.split("psnr_avg:")[-1].split()[0])
                except:
                    pass

        # jika tetap tidak ketemu
        return None

    except:
        return None



# ======================
# SSIM
# ======================
def calc_ssim(original, encoded):
    """
    Menghitung SSIM menggunakan ffmpeg
    Output format: "All:0.992..."
    """
    cmd = [
        "ffmpeg",
        "-i", str(original),
        "-i", str(encoded),
        "-lavfi", "ssim",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        log = result.stderr

        for line in log.splitlines():
            if "All:" in line:
                part = line.split("All:")[-1]
                return float(part.split()[0].strip())
    except:
        return None

    return None


# ======================
# MEASURE ENCODE TIME
# ======================
def measure_encode(run_func, *args, **kwargs):
    """
    Helper untuk mengukur durasi encode.
    run_func harus fungsi encode yang ada di engine.
    """
    start = time.time()
    result = run_func(*args, **kwargs)
    dur = time.time() - start
    return result, dur
