import os

def get_human_readable_size(size):
    for unit in ['', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']:
        if abs(size) < 1024.0:
            return "%3.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f YiB" % size

def display_directory_content(dir_path):
    files = []
    breadcrumbs = []
    if dir_path != '.':
        breadcrumbs = [{'name': part, 'path': os.path.join(*part[:i+1])} for i, part in enumerate(dir_path.split(os.sep)) if part]
    for item in sorted(os.listdir(dir_path), key=lambda s: s.lower()):
        item_path = os.path.join(dir_path, item)
        if os.path.isdir(item_path):
            item_type = 'directory'
        elif os.path.isfile(item_path):
            item_type = 'file'
        else:
            continue
        files.append({
            'name': item,
            'path': item_path,
            'size': get_human_readable_size(os.path.getsize(item_path)) if item_type == 'file' else '-',
            'type': item_type
        })
    return files, breadcrumbs

def get_version_directories(base_path='.'):
    """Retrieve directories that are named with integer version numbers."""
    return sorted([d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and d.isdigit()], key=int)

def get_movie_frame_versions(version_dirs, movie_name=None):
    """
    Fetch all movies and their frames across versions.
    If movie_name is specified, filter to include only that movie's frames.
    """
    movie_frames = {}
    for version in version_dirs:
        path = os.path.join('.', version)
        files = os.listdir(path)
        for file in files:
            if movie_name and not file.startswith(movie_name):
                continue
            movie, frame = os.path.splitext(file)[0].split('-')
            if movie not in movie_frames:
                movie_frames[movie] = {}
            if version not in movie_frames[movie]:
                movie_frames[movie][version] = {'frames': [], 'color': 'green', 'text': 'No Changes'}  # Example data
            movie_frames[movie][version]['frames'].append(frame)
    return movie_frames