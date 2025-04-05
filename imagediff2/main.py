import os

from PIL import Image
from flask import Flask, render_template, send_from_directory

from config import SCREENSHOTS_DIR
from imagediff import image_diff, encode_image, movie_diff

app = Flask(__name__)

def get_frame_number(filename):
    parts = filename.split('-')
    if len(parts) > 1:
        try:
            return int(parts[1].split('.')[0])
        except ValueError:
            return 0
    return 0

@app.route('/')
def index():
    targets = [d for d in os.listdir(SCREENSHOTS_DIR)
               if os.path.isdir(os.path.join(SCREENSHOTS_DIR, d))]

    return render_template('index.html', targets=targets)

@app.route('/target/<target>')
def target_detail(target):
    target_path = os.path.join(SCREENSHOTS_DIR, target)

    if not os.path.exists(target_path) or not os.path.isdir(target_path):
        return "Target not found", 404

    # 1. Cache the results of filesystem operations
    builds_list = [b for b in os.listdir(target_path)
                   if os.path.isdir(os.path.join(target_path, b))]
    builds = sorted(builds_list, reverse=True)
    builds_ascending = sorted(builds_list)

    # 2. Use dictionary instead of sets to collect movie information, reducing the number of iterations
    all_movies = set()
    build_movie_frames = {}

    # 3. Collect all file information in advance, avoiding multiple directory reads
    build_files = {}
    for build in builds:
        build_path = os.path.join(target_path, build)
        build_files[build] = os.listdir(build_path)

    # 4. Process all movie and frame data at once
    for build in builds:
        build_movie_frames[build] = {}

        for file in build_files[build]:
            if not os.path.isfile(os.path.join(target_path, build, file)):
                continue

            if "-" in file:
                parts = file.split("-")
                movie_name = parts[0]
                frame_num = parts[1].split('.')[0]

                if movie_name not in build_movie_frames[build]:
                    build_movie_frames[build][movie_name] = []

                build_movie_frames[build][movie_name].append(frame_num)
                all_movies.add(movie_name)

    # 5. Pre-calculate the first build appearance for each movie
    first_build_for_movie = {}
    for movie in all_movies:
        for build in builds_ascending:
            if movie in build_movie_frames.get(build, {}):
                first_build_for_movie[movie] = build
                break

    # 6. Pre-calculate reference builds for each movie in each build
    movie_reference_builds = {}
    for movie in all_movies:
        movie_reference_builds[movie] = {}
        for i, current_build in enumerate(builds):
            has_in_current = movie in build_movie_frames.get(current_build, {})

            if not has_in_current:
                reference_build = None
                for j in range(i+1, len(builds)):
                    if movie in build_movie_frames.get(builds[j], {}):
                        reference_build = builds[j]
                        break
                movie_reference_builds[movie][current_build] = reference_build

    # 7. Pre-calculate potential image difference results using lazy loading
    image_diff_cache = {}
    def get_image_diff(current_build, prev_build, movie, frame):
        cache_key = (current_build, prev_build, movie, frame)
        if cache_key not in image_diff_cache:
            current_frame_path = os.path.join(target_path, current_build, f"{movie}-{frame}.png")
            prev_frame_path = os.path.join(target_path, prev_build, f"{movie}-{frame}.png")

            if os.path.exists(current_frame_path) and os.path.exists(prev_frame_path):
                try:
                    image_diff_cache[cache_key] = image_diff(current_frame_path, prev_frame_path)
                except Exception as e:
                    print(f"Error comparing frames {movie}-{frame}: {e}")
                    image_diff_cache[cache_key] = {'has_diff': True}
            else:
                image_diff_cache[cache_key] = {'has_diff': True}

        return image_diff_cache[cache_key]

    # 8. Pre-calculate movie difference results, also using lazy loading
    movie_diff_cache = {}
    def get_movie_diff(current_build, prev_build, target, movie):
        cache_key = (current_build, prev_build, target, movie)
        if cache_key not in movie_diff_cache:
            movie_diff_cache[cache_key] = movie_diff(current_build, prev_build, target, movie)
        return movie_diff_cache[cache_key]

    movies = sorted(list(all_movies))
    continuous_bars = {}

    # 9. Simplify the continuous bar creation logic
    for movie in movies:
        continuous_bars[movie] = []

        for i, current_build in enumerate(builds):
            prev_build = builds[i+1] if i < len(builds)-1 else None

            has_in_current = movie in build_movie_frames.get(current_build, {})
            current_frames = build_movie_frames.get(current_build, {}).get(movie, [])

            prev_frames = []
            if prev_build:
                prev_frames = build_movie_frames.get(prev_build, {}).get(movie, [])

            has_in_prev = len(prev_frames) > 0 if prev_build else False
            is_first_build = (current_build == first_build_for_movie.get(movie))

            # Build entry information
            if is_first_build:
                continuous_bars[movie].append({
                    'build': current_build,
                    'type': 'first'
                })
            elif not has_in_current and prev_build:
                reference_build = movie_reference_builds[movie].get(current_build)

                if reference_build:
                    continuous_bars[movie].append({
                        'build': current_build,
                        'reference_build': reference_build,
                        'type': 'diff',
                        'has_diff': False,
                        'is_skipped': True,
                        'compare_with': reference_build
                    })
                else:
                    continuous_bars[movie].append({
                        'build': current_build,
                        'type': 'missing'
                    })
            elif has_in_current and prev_build:
                if has_in_prev:
                    common_frames = set(current_frames).intersection(set(prev_frames))

                    if len(current_frames) < len(prev_frames):
                        # 10. End the difference checking loop early
                        has_any_diff = False
                        for frame in common_frames:
                            diff_result = get_image_diff(current_build, prev_build, movie, frame)
                            if diff_result.get('has_diff', False):
                                has_any_diff = True
                                break

                        continuous_bars[movie].append({
                            'build': current_build,
                            'has_diff': has_any_diff,
                            'compare_with': prev_build,
                            'type': 'diff',
                            'is_partial': True
                        })
                    else:
                        has_diff = get_movie_diff(current_build, prev_build, target, movie)

                        continuous_bars[movie].append({
                            'build': current_build,
                            'has_diff': has_diff,
                            'compare_with': prev_build,
                            'type': 'diff'
                        })
                else:
                    # Find the last build containing this movie as comparison object
                    reference_build = None
                    for j in range (i + 1, len (builds)):
                        if movie in build_movie_frames.get (builds[j], {}):
                            reference_build = builds[j]
                            break

                    # For all cases, we maintain the readded type, but use a special marker if no comparison build is found
                    continuous_bars[movie].append ({
                        'build': current_build,
                        'type': 'readded',
                        'compare_with': reference_build,
                        'no_reference': reference_build is None  # Add a marker indicating no reference build was found
                    })
            elif not prev_build:
                continuous_bars[movie].append({
                    'build': current_build,
                    'type': 'unknown'
                })

    return render_template('target.html',
                           target=target,
                           builds=builds,
                           movies=movies,
                           continuous_bars=continuous_bars)

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
    target_info = {}

    for target in os.listdir(SCREENSHOTS_DIR):
        target_path = os.path.join(SCREENSHOTS_DIR, target)
        if not os.path.isdir(target_path):
            continue

        builds = sorted([b for b in os.listdir(target_path)
                         if os.path.isdir(os.path.join(target_path, b))],
                        reverse=True)

        # Check if current build exists in this target
        if build not in builds:
            continue

        # Find the previous build
        build_index = builds.index(build)
        prev_build = builds[build_index + 1] if build_index < len(builds) - 1 else None

        # Find all movies in this build
        build_path = os.path.join(target_path, build)
        movie_files = [f for f in os.listdir(build_path)
                       if os.path.isfile(os.path.join(build_path, f))]

        # Extract unique movie names
        movies = set()
        for file in movie_files:
            if "-" in file:
                movie_name = file.split("-")[0]
                movies.add(movie_name)

        # Calculate differences for each movie
        movie_diffs = {}
        if prev_build:
            for movie in movies:
                has_diff = movie_diff(build, prev_build, target, movie)
                movie_diffs[movie] = has_diff

        # Store target information
        target_info[target] = {
            'prev_build': prev_build,
            'movies': sorted(list(movies)),
            'movie_diffs': movie_diffs
        }

    return render_template('build.html',
                           build=build,
                           target_info=target_info)

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

@app.route('/view/<target>/<build>/<movie>')
def view_single_build(target, build, movie):
    """
    Display all frames of a movie from a single build without comparison.
    """

    build_path = os.path.join(SCREENSHOTS_DIR, target, build)

    frames = sorted([f for f in os.listdir(build_path)
                     if os.path.isfile(os.path.join(build_path, f)) and f.startswith(f"{movie}-")])

    # Sort frames by number
    frames.sort(key=get_frame_number)

    # Prepare frame data for the template
    frame_data = []
    for frame in frames:
        frame_path = os.path.join(build_path, frame)
        frame_num = get_frame_number(frame)

        try:
            img = Image.open(frame_path)
            img_data = encode_image(img)

            frame_data.append({
                'frame_number': frame_num,
                'filename': frame,
                'img_data': img_data
            })
        except Exception as e:
            print(f"Error processing frame {frame}: {e}")

    return render_template('view.html',
                           target=target,
                           build=build,
                           movie=movie,
                           frames=frame_data)

@app.route('/screenshots/<path:filename>')
def screenshots(filename):
    return send_from_directory(SCREENSHOTS_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001)