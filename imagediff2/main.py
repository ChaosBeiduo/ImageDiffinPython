from flask import Flask, render_template, send_file
from PIL import Image
from PIL import ImageDraw
import io, os
from collections import defaultdict
from imagediff import has_image_difference, image_diff
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',**dict(buttons=[
        dict(top='100', left='100', width='200', height='200',url='asd'),
    ]))

@app.route('/image')
def dynamic_image():
    # 创建一个图像
    img = Image.new('RGB', (700, 400), color = (73, 109, 137))

    #draw rectangle
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 300, 300], fill=(255, 255, 255), outline=(0, 0, 0))
    # 将图像保存到一个BytesIO对象中
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)  # 移动到开始位置，以便send_file可以从头读取
    
    # 发送图像
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/alldiff')
def alldiff():
    # 读取当前目录下pic文件夹中的所有图片
    # 文件夹名字是版本号
    path = os.path.dirname(os.path.abspath(__file__))
    print(path)
    versions = [d for d in os.listdir(f'{path}/pic') if os.path.isdir(f'{path}/pic/{d}')]
    versions.sort()
    # 文件夹里的名字为<movie>-<num>.png
    movies = defaultdict(list)
    for version in versions:
        for file in os.listdir(f'{path}/pic/{version}'):
            movie = file.split('-')[0]
            movies[movie].append(file)

    # 显示前25个版本到横轴
    # 每个movie名称显示在纵轴，只要某个movie的某个版本有变化，就显示红色，若无变化，则显示绿色
    # 如果图片在两个版本均存在，就比较两个图片是否有差异，从而显示红色或绿色
    # 否则，显示灰色
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

# 点进纵坐标的movie，显示该movie的所有版本
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