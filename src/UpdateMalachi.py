# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Updates Malachi from GitHub repository, whilst maintaining user-generated files and settings.

IMPORTANT: DO NOT RUN this script from /src, only run when script has been copied to /
"""

from tqdm import tqdm
from distutils import dir_util, file_util
import json
import os
import requests
import shutil
import zipfile

UPDATER_DIR = './updater_files'
UPDATE_BASE = UPDATER_DIR + '/malachi-master'
GLOBAL_SETTINGS_FILE = 'global_settings.json'
MALACHI_ZIP = 'malachi.zip'

def download_malachi_repo():
    # Code from https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests
    url = "https://github.com/crossroadchurch/malachi/archive/refs/heads/master.zip"
    response = requests.get(url, stream=True)
    total_size_in_bytes= int(response.headers.get('content-length', 0))
    block_size = 1024 #1 Kibibyte
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True, desc="Downloading Malachi", colour='green')
    with open(MALACHI_ZIP, 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    print()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("There was an error whilst downloading Malachi.  Aborting update.")
        return False
    return True

def extract_malachi():
    with zipfile.ZipFile(MALACHI_ZIP, 'r') as zipped:
        zipped.extractall(UPDATER_DIR)

def patch_malachi():
    # Patch root content with exception of 'Update Malachi.bat' which is being executed whilst
    # running this update script
    print("Patching / ...")
    for root_obj in os.listdir(UPDATE_BASE):
        if os.path.isfile(root_obj) and root_obj not in ['Update Malachi.bat']:
            file_util.copy_file(UPDATE_BASE + "/" + root_obj, './' + root_obj)

    # Clear /src and replace with contents of updater_files/malachi-master/src
    print("Patching /src ...")
    shutil.rmtree('./src')
    shutil.copytree(UPDATE_BASE + '/src', './src')

    # Clear /html and replace with contents of updater_files/malachi-master/html
    print("Patching /html ...")
    shutil.rmtree('./html')
    shutil.copytree(UPDATE_BASE + '/html', './html')

    # Patch content drop-off directories, keeping user generated files
    for obj in os.listdir(UPDATE_BASE):
        if os.path.isdir(obj) and obj not in ['data', 'html', 'src']:
            print("Patching /" + obj + " ...")
            dir_util.copy_tree(UPDATE_BASE + "/" + obj, './' + obj)

def patch_settings():
    print("Patching settings ...")
    with open('./data/' + GLOBAL_SETTINGS_FILE) as cur_settings:
        cur_json_data = json.load(cur_settings)

    with open(UPDATE_BASE + '/data/' + GLOBAL_SETTINGS_FILE) as new_settings:
        new_json_data = json.load(new_settings)

    for key in new_json_data:
        if key != "style":
            if key in cur_json_data:
                new_json_data[key] = cur_json_data[key]
    for style_key in new_json_data["style"]:
        if style_key in cur_json_data["style"]:
                new_json_data["style"][style_key] = cur_json_data["style"][style_key]

    with open('./data/' + GLOBAL_SETTINGS_FILE, "w") as out_settings:
        out_settings.write(json.dumps(new_json_data, indent=2))

result = download_malachi_repo()
if result:
    extract_malachi()
    patch_malachi()
    patch_settings()
    # Clean up extracted files
    print()
    print("Cleaning up ...")
    shutil.rmtree(UPDATER_DIR)
# Clean up downloaded file
if os.path.exists(MALACHI_ZIP):
    os.remove(MALACHI_ZIP)
