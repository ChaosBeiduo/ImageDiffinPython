from PIL import Image, ImageChops
import os
import base64
from io import BytesIO

def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def image_diff(src_img_path):
    try:
        src_img = Image.open(src_img_path)
        path_parts = src_img_path.split(os.sep)
        target_dir = os.sep.join(path_parts[:-2])
        src_filename = path_parts[-1]

        builds = sorted([d for d in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, d))], reverse=True)

        diff_results = []
        loop_count = 0
        for build in builds:
            build_path = os.path.join(target_dir, build)
            files = os.listdir(build_path)

            for file in files:
                if loop_count >= 3:
                    break

                cmp_img_path = os.path.join(build_path, file)
                if file == src_filename and cmp_img_path != src_img_path:
                    cmp_img = Image.open(cmp_img_path)
                    diff_img = ImageChops.difference(src_img, cmp_img).convert('RGB')
                    diff_results.append({
                        'src_img_data': encode_image(src_img),
                        'cmp_img_data': encode_image(cmp_img),
                        'diff_img_data': encode_image(diff_img)
                    })
                    loop_count += 1
        return diff_results
    except IOError:
        return []