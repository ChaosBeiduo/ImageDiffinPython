from flask import Flask, render_template, send_file, send_from_directory
from PIL import Image
from PIL import ImageDraw
import io, os
from collections import defaultdict
from imagediff import image_diff, encode_image, movie_diff
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
    all_builds = set()
    diff_matrix = {}

    # Scan through all targets
    for target in os.listdir(SCREENSHOTS_DIR):
        target_path = os.path.join(SCREENSHOTS_DIR, target)
        if os.path.isdir(target_path):
            # Scan through all builds in this target
            builds_with_movie = []

            builds = sorted([b for b in os.listdir(target_path)
                             if os.path.isdir(os.path.join(target_path, b))],
                            reverse=True)  # Sort in descending order

            for build in builds:
                build_path = os.path.join(target_path, build)
                # Check if this build contains the movie
                movie_files = [f for f in os.listdir(build_path)
                               if os.path.isfile(os.path.join(build_path, f))]

                # Check if any files start with the movie name
                has_movie = any(f.startswith(f"{movie}-") for f in movie_files)

                if has_movie:
                    builds_with_movie.append(build)
                    all_builds.add(build)

            for i in range(len(builds_with_movie) - 1):
                current_build = builds_with_movie[i]
                prev_build = builds_with_movie[i + 1]

                has_diff = movie_diff(current_build, prev_build, target, movie)

                if target not in diff_matrix:
                    diff_matrix[target] = {}

                diff_matrix[target][(current_build, prev_build)] = has_diff

            if builds_with_movie:
                target_builds[target] = builds_with_movie

    all_builds = sorted(list(all_builds), reverse=True)

    return render_template('movie.html',
                           movie=movie,
                           target_builds=target_builds,
                           all_builds=all_builds,
                           diff_matrix=diff_matrix)


@app.route('/build/<build>')
def build(build):
    path = os.path.dirname(os.path.abspath(__file__))
    screenshots_dir = f'{path}/screenshots'

    # Find all targets that contain this build
    targets_with_build = []
    for target in os.listdir(screenshots_dir):
        target_path = os.path.join(screenshots_dir, target)
        if os.path.isdir(target_path):
            builds_in_target = [d for d in os.listdir(target_path)
                                if os.path.isdir(os.path.join(target_path, d))]
            if build in builds_in_target:
                targets_with_build.append(target)

    # For each target, find the previous build
    target_details = {}
    for target in targets_with_build:
        target_path = os.path.join(screenshots_dir, target)
        builds_in_target = sorted([d for d in os.listdir(target_path)
                                   if os.path.isdir(os.path.join(target_path, d))])

        # Get previous build for this target
        build_index = builds_in_target.index(build)
        prev_build = builds_in_target[build_index - 1] if build_index > 0 else None

        # Find all movies in this build for this target
        build_path = os.path.join(target_path, build)
        movie_files = [f for f in os.listdir(build_path)
                       if os.path.isfile(os.path.join(build_path, f))]

        # Extract movie names
        movies = set()
        for file in movie_files:
            if "-" in file:
                movie_name = file.split("-")[0]
                movies.add(movie_name)

        # Check for differences with previous build
        diffs = {}
        if prev_build:
            prev_build_path = os.path.join(target_path, prev_build)
            for movie in movies:
                # Check if the movie exists in both builds
                current_frames = [f for f in movie_files if f.startswith(movie + "-")]
                if os.path.exists(prev_build_path):
                    prev_movie_files = [f for f in os.listdir(prev_build_path)
                                        if os.path.isfile(os.path.join(prev_build_path, f))]
                    prev_frames = [f for f in prev_movie_files if f.startswith(movie + "-")]

                    # If you have an image_diff function, use it here
                    try:
                        has_diff = len(current_frames) != len(prev_frames)  # Simple difference check
                        # For a more detailed check, you'd use your image_diff function:
                        # has_diff = image_diff(f'{build_path}/{movie}', f'{prev_build_path}/{movie}') != {}
                        diffs[movie] = has_diff
                    except Exception as e:
                        # Handle any errors in difference checking
                        diffs[movie] = False
                        print(f"Error comparing {movie}: {e}")
                else:
                    diffs[movie] = True  # If previous build doesn't exist, mark as different

        target_details[target] = {
            'prev_build': prev_build,
            'movies': sorted(list(movies)),
            'diffs': diffs
        }

    return render_template('build.html',
                           build=build,
                           targets=targets_with_build,
                           target_details=target_details)

@app.route('/compare/<build1>/<build2>/<target>/<movie>')
def compare(build1, build2, target, movie):
    build1_path = os.path.join(SCREENSHOTS_DIR, target, build1)
    build2_path = os.path.join(SCREENSHOTS_DIR, target, build2)

    # Get all frames for this movie in both builds
    build1_frames = sorted([f for f in os.listdir(build1_path)
                            if os.path.isfile(os.path.join(build1_path, f)) and f.startswith(f"{movie}-")])

    build2_frames = sorted([f for f in os.listdir(build2_path)
                            if os.path.isfile(os.path.join(build2_path, f)) and f.startswith(f"{movie}-")])

    # Helper function to extract frame number from filename
    def get_frame_number(filename):
        parts = filename.split('-')
        if len(parts) > 1:
            try:
                return int(parts[1].split('.')[0])
            except ValueError:
                return 0
        return 0

    # Sort frames by number
    build1_frames.sort(key=get_frame_number)
    build2_frames.sort(key=get_frame_number)

    # Map frame numbers to filenames for easy lookup
    build1_frame_map = {get_frame_number(f): f for f in build1_frames}
    build2_frame_map = {get_frame_number(f): f for f in build2_frames}

    # Get all frame numbers from both builds
    all_frame_numbers = sorted(set(list(build1_frame_map.keys()) + list(build2_frame_map.keys())))

    # For each frame number, create a comparison entry
    frame_comparisons = []
    for frame_num in all_frame_numbers:
        build1_frame = build1_frame_map.get(frame_num)
        build2_frame = build2_frame_map.get(frame_num)

        comparison = {
            'frame_number': frame_num,
            'build1_frame': build1_frame,
            'build2_frame': build2_frame,
            'has_diff': False,
            'diff_data': None
        }

        # Calculate diff if both frames exist
        if build1_frame and build2_frame:
            img1_path = os.path.join(build1_path, build1_frame)
            img2_path = os.path.join(build2_path, build2_frame)

            try:
                diff_result = image_diff(img1_path, img2_path)
                comparison['has_diff'] = diff_result.get('has_diff', False)
                comparison['diff_data'] = diff_result
            except Exception as e:
                print(f"Error comparing images: {e}")
        else:
            # If one frame is missing in either build, mark as different
            comparison['has_diff'] = True
            # Handle case when only build1 has the frame
            if build1_frame and not build2_frame:
                try:
                    img1_path = os.path.join(build1_path, build1_frame)
                    src_img = Image.open(img1_path)
                    comparison['diff_data'] = {
                        'src_img_data': encode_image(src_img),
                        'cmp_img_data': None,
                        'diff_img_data': None  # No diff image needed here
                    }
                except Exception as e:
                    print(f"Error encoding image from build1: {e}")

            # Handle case when only build2 has the frame
            elif not build1_frame and build2_frame:
                try:
                    img2_path = os.path.join(build2_path, build2_frame)
                    cmp_img = Image.open(img2_path)
                    comparison['diff_data'] = {
                        'src_img_data': None,
                        'cmp_img_data': encode_image(cmp_img),
                        'diff_img_data': None  # No diff image needed here
                    }
                except Exception as e:
                    print(f"Error encoding image from build2: {e}")

        frame_comparisons.append(comparison)

    return render_template('compare.html',
                           build1=build1,
                           build2=build2,
                           target=target,
                           movie=movie,
                           comparisons=frame_comparisons)

@app.route('/screenshots/<path:filename>')
def screenshots(filename):
    return send_from_directory(SCREENSHOTS_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)