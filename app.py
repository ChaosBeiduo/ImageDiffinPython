from flask import Flask, render_template, request, send_from_directory, abort
import os
from file_browser import display_directory_content, get_version_directories, get_movie_frame_versions
from imagediff import image_diff, has_image_difference

app = Flask(__name__)

@app.route('/')
def index():
    version_dirs = get_version_directories()
    movies = get_movie_frame_versions(version_dirs)
    return render_template('index.html', movies=movies, version_dirs=version_dirs)

@app.route('/movie_details/<movie_name>')
def movie_details(movie_name):
    version_dirs = get_version_directories()
    frames = get_movie_frame_versions(version_dirs, movie_name)
    return render_template('movie_details.html', movie_name=movie_name, frames=frames, version_dirs=version_dirs)

@app.route('/version_details/<version>')
def version_details(version):
    previous_version = str(int(version) - 1)  # Assuming version naming is sequential integers
    diffs = has_image_difference(version, previous_version)
    return render_template('version_details.html', version=version, diffs=diffs)

@app.route('/display_images')
def display_images():
    image_path = request.args.get('image', '')
    if not os.path.isfile(image_path):
        abort(404)
    diff_results = image_diff(image_path)
    return render_template('display_images.html', diff_results=diff_results, image_path=image_path)

if __name__ == '__main__':
    app.run(debug=True)