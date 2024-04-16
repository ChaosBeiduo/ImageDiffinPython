from flask import Flask, render_template, request, send_from_directory, abort
import os
from file_browser import display_directory_content
from imagediff import image_diff

app = Flask(__name__)

@app.route('/')
def index():
    dir_path = request.args.get('dir', '.')
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        abort(404)
    files, breadcrumbs = display_directory_content(dir_path)
    return render_template('index.html', files=files, breadcrumbs=breadcrumbs, current_dir=dir_path)

@app.route('/display_images')
def display_images():
    image_path = request.args.get('image', '')
    if not os.path.isfile(image_path):
        abort(404)
    diff_results = image_diff(image_path)
    return render_template('display_images.html', diff_results=diff_results, image_path=image_path)

if __name__ == '__main__':
    app.run(debug=True)