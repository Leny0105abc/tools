# Leny Utility Hub

A local/self-hosted Flask web app with five tools:

1. YouTube -> MP4 for videos you own or have permission to download
2. MP4/video -> MP3
3. `LastName, FirstName MiddleName` -> `FirstName MiddleName LastName`
4. `FirstName MiddleName LastName` -> `LastName, FirstName MiddleName`
5. Remove an Excel workbook's open password when the correct current password is supplied

## Windows setup

### 1. Install Python
Install Python 3.11+ and make sure "Add Python to PATH" is checked.

### 2. Install FFmpeg
Install FFmpeg and add its `bin` folder to Windows PATH.

Verify:
```bat
ffmpeg -version
```

### 3. Install Python packages
Open Command Prompt inside this project folder:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Verify yt-dlp:
```bat
yt-dlp --version
```

### 4. Start
Double-click `start.bat`, or run:

```bat
.venv\Scripts\activate
python app.py
```

Open:
http://127.0.0.1:5000

## Notes

- YouTube downloading must only be used for content you own or are authorized to download.
- The Excel tool requires the correct existing password. It does not crack or bypass an unknown password.
- Uploaded and generated files are temporary and are deleted after the response is sent.
- The app limits uploads to 500 MB.
- Standard shared hosting may not permit FFmpeg or long-running media conversion. A VPS, local PC, or container-capable host is better for the media tools.

## Production

For a Linux VPS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Install system FFmpeg separately, for example on Ubuntu:
```bash
sudo apt update
sudo apt install ffmpeg
```
