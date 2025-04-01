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
    target_builds = {}

    # Scan through all targets
    for target in os.listdir (SCREENSHOTS_DIR):
        target_path = os.path.join (SCREENSHOTS_DIR, target)
        if os.path.isdir (target_path):
            # Scan through all builds in this target
            builds_with_movie = []

            builds = sorted ([b for b in os.listdir (target_path)
                              if os.path.isdir (os.path.join (target_path, b))],
                             reverse=True)

            for build in builds:
                build_path = os.path.join (target_path, build)
                # Check if this build contains the movie
                movie_files = [f for f in os.listdir (build_path)
                               if os.path.isfile (os.path.join (build_path, f))]

                # Check if any files start with the movie name
                has_movie = any (f.startswith (f"{movie}-") for f in movie_files)

                if has_movie:
                    builds_with_movie.append (build)

            # Only add this target if it has at least one build with the movie
            if builds_with_movie:
                target_builds[target] = builds_with_movie

    return render_template ('movie.html', movie=movie, target_builds=target_builds)

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