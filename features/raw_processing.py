import rawpy
import cv2

def load_raw_image(path):
    with rawpy.imread(path) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=False
        )

    image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return image
