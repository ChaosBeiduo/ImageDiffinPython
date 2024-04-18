from flask import Flask, render_template, request, send_from_directory, abort
import os
from file_browser import display_directory_content, get_version_and_movie_data, has_difference
from imagediff import image_diff

app = Flask(__name__)

@app.route('/')
def index():
    dir_path = request.args.get('dir', '.')
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        abort(404)
    files, breadcrumbs = display_directory_content(dir_path)
    return render_template('index.html', files=files, breadcrumbs=breadcrumbs, current_dir=dir_path)

@app.route('/movie/<string:movie_name>')
def movie_details(movie_name):
    data = get_version_and_movie_data(movie_name=movie_name)
    return render_template('movie_details.html', data=data, movie_name=movie_name)

@app.route('/version/<int:version>')
def version_details(version):
    files, has_diffs = has_difference(version)
    return render_template('version_details.html', files=files, has_diffs=has_diffs, version=version)

@app.route('/display_images/<int:version>/<string:movie>/<int:frame_number>')
def display_images(version, movie, frame_number):
    image_path = f"{version}/{movie}-{frame_number}.png"
    diff_results = image_diff(image_path)
    return render_template('display_images.html', diff_results=diff_results, image_path=image_path)

if __name__ == '__main__':
    app.run(debug=True)