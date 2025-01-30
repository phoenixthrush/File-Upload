from flask import Flask, render_template, request, send_from_directory, abort
import os
import uuid
import random
import string
from datetime import datetime

app = Flask(__name__)


def get_upload_path():
    now = datetime.now()
    return os.path.join(os.getcwd(), 'uploads', str(now.year), f'{now.month:02}')


def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        files = request.files.getlist('fileToUpload[]')
        total_size = sum([file.content_length for file in files])
        total_files = len(files)

        if total_files > 100:
            return render_template('index.html', error="You can upload a maximum of 100 files at once.")

        if total_size > 500 * 1024 * 1024:
            return render_template('index.html', error="Total upload size exceeds the 500MB limit.")

        upload_path = get_upload_path()
        hashed_timestamp = str(uuid.uuid4())
        target_dir = os.path.join(upload_path, hashed_timestamp)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        allowed_types = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'mp4', 'avi', 'mov', 'mkv', 'webm'}
        upload_ok = True
        uploaded_files = []

        for file in files:
            filename = file.filename
            file_extension = filename.rsplit('.', 1)[-1].lower()

            if file_extension not in allowed_types:
                upload_ok = False
                continue

            unique_filename = f"{hashed_timestamp}_{str(uuid.uuid4())}.{file_extension}"
            file_path = os.path.join(target_dir, unique_filename)

            file.save(file_path)
            uploaded_files.append(unique_filename)

        if upload_ok:
            token = generate_token()
            token_file_path = os.path.join(target_dir, 'token')
            with open(token_file_path, 'w') as token_file:
                token_file.write(token)

            links = [
                f"/uploads/{datetime.now().year}/{datetime.now().month:02}/{hashed_timestamp}/{file}?token={token}"
                for file in uploaded_files
            ]

            return render_template('view.html', links=links, token=token)

        return render_template('index.html', error="Some files were not valid or could not be uploaded.")

    return render_template('index.html')


@app.route('/view', methods=['GET'])
def view_album():
    token = request.args.get('token')

    if not token:
        return render_template('view.html', error="Invalid token.")

    uploads_root = os.path.join(os.getcwd(), 'uploads')

    target_path = None
    for year in os.listdir(uploads_root):
        year_path = os.path.join(uploads_root, year)
        if not os.path.isdir(year_path):
            continue
        for month in os.listdir(year_path):
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
            for album in os.listdir(month_path):
                album_path = os.path.join(month_path, album)
                token_file = os.path.join(album_path, 'token')
                if os.path.exists(token_file):
                    with open(token_file, 'r') as f:
                        if f.read().strip() == token:
                            target_path = album_path
                            break
            if target_path:
                break
        if target_path:
            break

    if not target_path:
        return render_template('view.html', error="Album not found or invalid token.")

    uploaded_files = [f for f in os.listdir(target_path) if f != 'token']
    year, month, album = target_path.split(os.sep)[-3:]

    links = [
        f"/uploads/{year}/{month}/{album}/{file}?token={token}" for file in uploaded_files
    ]

    return render_template('view.html', links=links, token=token, year=year, month=month, album=album)


@app.route('/uploads/<year>/<month>/<hashed_timestamp>/<filename>')
def serve_file(year, month, hashed_timestamp, filename):
    file_path = os.path.join(os.getcwd(), 'uploads', year, month, hashed_timestamp, filename)
    token = request.args.get('token')

    if not token:
        return abort(403)

    token_file_path = os.path.join(os.getcwd(), 'uploads', year, month, hashed_timestamp, 'token')
    if not os.path.exists(token_file_path):
        return abort(403)

    with open(token_file_path, 'r') as token_file:
        stored_token = token_file.read()

    if stored_token != token:
        return abort(403)

    if not os.path.exists(file_path):
        return abort(404)

    return send_from_directory(os.path.dirname(file_path), filename)


if __name__ == '__main__':
    app.run(debug=True)
