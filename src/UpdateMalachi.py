# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Updates Malachi from GitHub repository, whilst maintaining user-generated files and settings.

IMPORTANT: DO NOT RUN this script from /src, only run when script has been copied to /
"""

from tqdm import tqdm
from distutils import dir_util, file_util
import io
import json
import logging
import os
import requests
import shutil
import signal
import subprocess
import sys
import zipfile
from datetime import datetime

SHA_PAGE = 'http://www.crossroad.org.uk/malachi/sha.txt'
UPDATER_DIR = './updater_files'
UPDATE_BASE = UPDATER_DIR + '/malachi-master'
GLOBAL_SETTINGS_FILE = 'global_settings.json'
MALACHI_ZIP = 'malachi.zip'
OS_REQUIREMENTS_CALLS = {
    'win32': ['python', '-m', 'pip', 'install', '-r', 'requirements.txt'],
    'linux': ['sudo', 'python', '-m', 'pip', 'install', '-r', 'linux_requirements.txt'],
    'raspbian': ['python', '-m', 'pip', 'install', '-r', 'pi_requirements.txt'],
    'darwin': ['python', '-m', 'pip', 'install', '-r', 'mac_requirements.txt']
}
OS_MALACHI_CALLS = {
    'win32': ['python', './Malachi.py'],
    'linux': ['python', './Malachi.py'],
    'raspbian': ['python', './Malachi.py'],
    'darwin': ['python', './Malachi.py']
}
DEPRECATED_FILES = ['Update Malachi.bat', 'update_malachi_linux', 'update_malachi_pi']
PERMISSION_FILES = ['./install_malachi_linux', './install_malachi_pi', './run_malachi_linux', './run_malachi_pi']
# Copy of src/StreamToLogger.py, added here to avoid problems when patching /src
class StreamToLogger(object):
   """
   Fake file-like stream object that redirects writes to a logger instance.
   """
   def __init__(self, logger, level):
      self.logger = logger
      self.level = level
      self.linebuf = ''
      self.stdout = sys.stdout

   def write(self, buf):
      try:
         for line in buf.rstrip().splitlines():
            self.stdout.write(line + '\n')
            self.logger.log(self.level, line.rstrip())
      except UnicodeEncodeError as _:
         print("UnicodeEncodeError encountered")

   def flush(self):
      pass

# https://raspberrypi.stackexchange.com/questions/5100/detect-that-a-python-program-is-running-on-the-pi
def is_raspberry_pi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

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
    # Patch root content
    print("Patching / ...")
    for root_obj in os.listdir(UPDATE_BASE):
        if os.path.isfile(UPDATE_BASE + "/" + root_obj):
            file_util.copy_file(UPDATE_BASE + "/" + root_obj, './' + root_obj)

    # Clear /src and replace with contents of updater_files/malachi-master/src
    print("Patching /src ...")
    shutil.rmtree('./src')
    shutil.copytree(UPDATE_BASE + '/src', './src')

    # Clear /html and replace with contents of updater_files/malachi-master/html
    print("Patching /html ...")
    shutil.rmtree('./html')
    shutil.copytree(UPDATE_BASE + '/html', './html')

    # Patching Bibles
    print("Patching Bibles ...")
    for obj in os.listdir(UPDATE_BASE + "/data"):
        if obj.endswith(".sqlite") and obj not in ['songs.sqlite']:
            file_util.copy_file(UPDATE_BASE + "/data/" + obj, "./data/" + obj)

    # Patch content drop-off directories, keeping user generated files
    for obj in os.listdir(UPDATE_BASE):
        if os.path.isdir(UPDATE_BASE + "/" + obj) and obj not in ['data', 'html', 'src']:
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

def store_sha():
    sha_page = requests.get(SHA_PAGE)
    if sha_page.status_code == 200:
        latest_sha = sha_page.text
        with open('./sha.txt', 'w') as sha_file:
            sha_file.write(latest_sha)

def update_needed():
    sha_page = requests.get(SHA_PAGE)
    if sha_page.status_code == 200:
        latest_sha = sha_page.text
        old_sha = 0
        if os.path.isfile('sha.txt'):
            with open('sha.txt', 'r') as old_sha_file:
                old_sha = old_sha_file.read()
        if old_sha == latest_sha:
            print("The latest version of Malachi is already installed!")
            return False
        if old_sha == "-1":
            print("Developer testing mode - update skipped")
            return False
    return True


if __name__ == "__main__":
    # Setup logging of terminal output
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename='./logs/updater-' + datetime.now().strftime("%Y%m%d_%H%M%S") + '.log',
        filemode='a'
        )
    log = logging.getLogger('malachi-updater')
    logging.raiseExceptions = False;
    sys.stdout = StreamToLogger(log,logging.INFO)
    sys.stderr = StreamToLogger(log,logging.ERROR)

    os_version = 'win32'
    if sys.platform == 'linux':
        if is_raspberry_pi():
            os_version = 'raspbian'
        else:
            os_version = 'linux'
    elif sys.platform == 'darwin':
        os_version = 'darwin'
    
    # Ensure http server is released by killing Malachi.py Python process (not on win32)
    if os_version != 'win32':
        pid = int(sys.argv[1])
        try:
            print("Terminating process {p} from process {u}.".format(p=str(pid), u=str(os.getpid())))
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError as _:
            print("Process {p} already terminated.".format(p=str(pid)))
        print("Continuing with installation process...")

    if update_needed():
        result = download_malachi_repo()

        if result:
            extract_malachi()
            patch_malachi()
            patch_settings()
            store_sha()
            # Clean up extracted files
            print()
            print("Cleaning up ...")
            shutil.rmtree(UPDATER_DIR)
            # Run pip
            print()
            print("Installing new Python modules...")
            subprocess.call(OS_REQUIREMENTS_CALLS[os_version])
            print()
            if os_version == "linux" or os_version == "raspbian":
                print("Setting permissions...")
                for f in PERMISSION_FILES:
                    subprocess.check_call(['chmod', '+x', f])
                print()
            print("Removing deprecated files...")
            for f in DEPRECATED_FILES:
                if os.path.exists(f):
                    os.remove(f)
            print()
            print("Malachi has been successfully updated!")

        # Clean up downloaded file
        if os.path.exists(MALACHI_ZIP):
            os.remove(MALACHI_ZIP)

    print()
    print("Re-opening Malachi...")
    subprocess.Popen(OS_MALACHI_CALLS[os_version])
