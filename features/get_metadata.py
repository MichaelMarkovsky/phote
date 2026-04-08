import subprocess
import json

def get_raw_metadata(path):
    try:
        result = subprocess.run(
            ["exiftool", "-j", path],
            capture_output=True,
            text=True
        )

        data = json.loads(result.stdout)[0]

        return {
            "iso": data.get("ISO", "---"),
            "shutter": data.get("ExposureTime", "---"),
            "aperture": data.get("FNumber", "---"),
            "focal_len": data.get("FocalLength", "---"),
        }

    except Exception as e:
        print("Metadata error:", e)
        return {}
