from flask import Flask, render_template, send_file
from PIL import Image
from PIL import ImageDraw
import io, os
from collections import defaultdict
from imagediff import has_image_difference, image_diff
from pathlib import Path
from config import SCREENSHOTS_DIR

app = Flask(__name__)

@app.route('/')
def index():
    targets_info = {}

    for target in [d for d in os.listdir(SCREENSHOTS_DIR)
                   if os.path.isdir(os.path.join(SCREENSHOTS_DIR, d))]:

        target_path = os.path.join(SCREENSHOTS_DIR, target)
        builds = sorted([b for b in os.listdir(target_path)
                         if os.path.isdir(os.path.join(target_path, b))],
                        reverse=True)

        # Get all movie names across all builds
        all_movies = set()
        build_movies = {}

        for build in builds:
            build_path = os.path.join(target_path, build)
            movie_files = [f for f in os.listdir(build_path)
                           if os.path.isfile(os.path.join(build_path, f))]

            movie_names = set()
            for file in movie_files:
                # Split by hyphen and take the first part as the movie name
                if "-" in file:
                    movie_name = file.split("-")[0]
                    movie_names.add(movie_name)

            build_movies[build] = movie_names
            all_movies.update(movie_names)

        # Convert set to sorted list for consistent display
        all_movies = sorted(list(all_movies))

        targets_info[target] = {
            "builds": builds,
            "movies": all_movies,
            "build_movies": build_movies
        }

    return render_template('index.html', targets_info=targets_info)

@app.route('/image')
def dynamic_image():

    img = Image.new('RGB', (700, 400), color = (73, 109, 137))

    #draw rectangle
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 300, 300], fill=(255, 255, 255), outline=(0, 0, 0))
   
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)  
    
   
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/alldiff')
def alldiff():
   
    path = os.path.dirname(os.path.abspath(__file__))
    print(path)
    versions = [d for d in os.listdir(f'{path}/pic') if os.path.isdir(f'{path}/pic/{d}')]
    versions.sort()
   
    movies = defaultdict(list)
    for version in versions:
        for file in os.listdir(f'{path}/pic/{version}'):
            movie = file.split('-')[0]
            movies[movie].append(file)

    diffs = defaultdict(list)
    now_path = os.path.dirname(os.path.abspath(__file__))
    for i, version in enumerate(versions):
        for movie, files in movies.items():
            cnt = 0
            if i == 0:
                diffs[movie].append('gray')
                continue
            for file in files:
                current_file_path = f'{now_path}//pic//{version}//{file}'
                previous_file_path = f'{now_path}//pic//{versions[i-1]}//{file}'
                if file not in os.listdir(f'{now_path}//pic//{versions[i-1]}'):
                    cnt += 1
                    continue
                if file not in os.listdir(f'{now_path}//pic//{version}'):
                    cnt += 1
                    continue
                diff_result = image_diff(current_file_path, previous_file_path)
                if diff_result:
                    diffs[movie].append('red')
                    print('red')
                    break
                
            if cnt == len(files):
                diffs[movie].append('white')
                print('white')
            else:
                diffs[movie].append('green')
                print('green')

    return render_template('alldiff.html', **dict(diffs=diffs, movies=movies, versions=versions))


@app.route('/movie/<movie>')
def movie(movie):
    path = os.path.dirname(os.path.abspath(__file__))
    versions = [d for d in os.listdir(f'{path}/pic') if os.path.isdir(f'{path}/pic/{d}')]
    versions.sort()
    movies = defaultdict(list)
    for version in versions:
        for file in os.listdir(f'{path}/pic/{version}'):
            if file.startswith(movie):
                movies[version].append(file)
    frames = defaultdict(list)
    for version, files in movies.items():
        for file in files:
            frame = file.split('-')[1].split('.')[0]
            frames[frame].append(version)
    return render_template('movie.html', **dict(movies=movies, movie=movie, frames=frames, movie_name=movie, versions=versions))

@app.route('/version/<version>')
def version(version):
    path = os.path.dirname(os.path.abspath(__file__))
    
    versions = [d for d in os.listdir(f'{path}/pic') if os.path.isdir(f'{path}/pic/{d}')]
    versions.sort()
    previous_version = versions[versions.index(version) - 1] if version != versions[0] else None
    movies = set()
    for it in versions:
        for file in os.listdir(f'{path}/pic/{it}'):
            movies.add(file.split('.')[0])
    diffs = defaultdict(bool)
    movies = sorted(list(movies))
    for movie in movies:
        if previous_version:
            res = image_diff(f'{path}/{version}/{movie}', f'{path}/{previous_version}/{movie}')
            if res != {}:
                diffs[movie] = True
        else:
            diffs[movie] = False
            
    return render_template('version.html', **dict(version=version, diffs=diffs, movies=movies, previous_version=previous_version))


@app.route('/diff/<version1>/<version2>/<movie>/<frame>')
def diff(version1, version2, movie, frame):
    path = os.path.dirname(os.path.abspath(__file__))
    file1 = f'{path}/pic/{version1}/{movie}-{frame}.png'
    file2 = f'{path}/pic/{version2}/{movie}-{frame}.png'
    diff_result = image_diff(file1, file2)
    return render_template('diff.html', **dict(diff_result=diff_result, version1=version1, version2=version2, movie=movie, frame=frame))


if __name__ == '__main__':
    app.run(debug=True, port=5001)