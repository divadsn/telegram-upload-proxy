#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging

from telethon.sync import TelegramClient
from quart import Quart, Response, request
from werkzeug.utils import secure_filename

is_debug = bool(os.environ.get('DEBUG', False))

# enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# you must get your own api_id and app_hash
# from https://my.telegram.org, under API Development.
app_id = os.environ.get('APP_ID', None)
app_hash = os.environ.get('APP_HASH', None)

client = TelegramClient("proxy", app_id, app_hash)
client.start()

# Initialize Flask app
app = Quart(__name__)

app.config.update({
    'DEBUG': True,
    'SECRET_KEY': os.environ['SECRET_KEY'],
    'UPLOAD_FOLDER': "/tmp/tg_proxy",
    'MAX_CONTENT_LENGTH': 1536 * 1024 * 1024, # 1.5 GB allowed by Telegram
})

@app.route("/proxy.php/upload_file", methods=['GET', 'POST'])
async def upload_file():
    auth_token = os.environ.get('AUTH_TOKEN', "thequickbrownfoxjumpsoverthelazydog")

    # check if app is authorized to use the proxy
    if request.headers.get("X-Auth-Token") != auth_token and not is_debug:
        return show_error(401, "You are not allowed to use the proxy here!")

    if request.method == 'POST':
        files = await request.files

        # check if the post request has the file part
        if 'file' not in files:
            return show_error(400, "No file part")

        file = files['file']

        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return show_error(400, "No selected file")

        filename = secure_filename(file.filename)

        # save file to uploads
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # upload file via Telegram
        input_file = await client.upload_file(file=file_path, part_size_kb=512, file_name=filename)

        return response({ "id": input_file.id, "filename": filename }, 200)

    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
        <p><input type=file name=file>
            <input type=submit value=Upload>
        </form>
    '''

def show_error(error_code, description):
    return response({
            "error_code": error_code,
            "description": description
        }, error_code) 

def response(output, status):
    headers = { "X-Powered-By": "divadsn/telegram-upload-proxy" }
    return Response(response=json.dumps(output), status=status, headers=headers, mimetype="application/json")

# Run the app!
if __name__ == "__main__":
    app.run(host=os.environ.get('LISTEN_ADDR', "localhost"), port=os.environ.get('PORT', "3000"))