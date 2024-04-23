from PIL import Image, ImageChops
import os
import base64
from io import BytesIO

def encode_image(image):
    """Encode an image to a base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def image_diff(src_img_path, cmp_img_path):
    """
    Compute the difference between two images and return the results.
    """
    try:
        src_img = Image.open(src_img_path)
        cmp_img = Image.open(cmp_img_path)
        diff_img = ImageChops.difference(src_img, cmp_img).convert('RGB')
        # if diff_img.getbbox() is None:
        #     return {}
        return {
            'src_img_data': encode_image(src_img),
            'cmp_img_data': encode_image(cmp_img),
            'diff_img_data': encode_image(diff_img)
        }
    except IOError:
        return {}
    
def has_image_difference(current_version, previous_version, base_path='.'):
    """
    Check for differences between images in two versions and return a list of differences.
    """
    current_path = os.path.join(base_path, current_version)
    previous_path = os.path.join(base_path, previous_version)
    current_files = {file for file in os.listdir(current_path) if file.endswith('.png')}
    previous_files = {file for file in os.listdir(previous_path) if file.endswith('.png')}

    diffs = []
    for file in current_files.intersection(previous_files):
        current_file_path = os.path.join(current_path, file)
        previous_file_path = os.path.join(previous_path, file)
        if not os.path.isfile(current_file_path) or not os.path.isfile(previous_file_path):
            continue

        # Compare the images
        diff_result = image_diff(current_file_path, previous_file_path)
        if diff_result:  # Assuming any non-empty result indicates a difference
            diffs.append({
                'file_name': file,
                'has_diff': True,
                'diff_data': diff_result
            })
        else:
            diffs.append({
                'file_name': file,
                'has_diff': False
            })

    return diffs