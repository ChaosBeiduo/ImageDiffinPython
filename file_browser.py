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