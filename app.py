from flask import Flask, request, send_file, jsonify
import subprocess, os, glob, shlex
from flask_cors import CORS
from flask_cors import cross_origin

app = Flask(__name__)
CORS(app)  # Allow requests from frontend

def run_command(cmd):
    subprocess.run(shlex.split(cmd), check=True)

def download_youtube_audio(youtube_url):
    os.makedirs("output", exist_ok=True)
    run_command(f"yt-dlp -f bestaudio -o 'output/audio.%(ext)s' {youtube_url}")
    webm_files = sorted(glob.glob("output/*.webm"), key=os.path.getmtime, reverse=True)
    if not webm_files:
        raise FileNotFoundError("No .webm file found.")
    return webm_files[0]

def run_basic_pitch(filename):
    # Delete any existing MIDI files to avoid overwrite errors
    for mid_file in glob.glob("output/*.mid"):
        try:
            os.remove(mid_file)
        except Exception as e:
            print(f"Could not delete {mid_file}: {e}")

    # Run basic-pitch inference
    run_command(f'basic-pitch output/ "{filename}"')

    # Get the most recent .mid file
    mid_files = sorted(glob.glob("output/*.mid"), key=os.path.getmtime, reverse=True)
    if not mid_files:
        raise FileNotFoundError("No MIDI file generated.")
    return mid_files[0]

def generate_pdf_with_musescore(mid_file):
    # output PDF name same as MIDI file base name
    base = os.path.splitext(os.path.basename(mid_file))[0]
    output_pdf = f"output/{base}.pdf"
    
    # Make sure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # MuseScore CLI command:
    # --export-to exports to file (pdf here)
    # --force to overwrite existing output file
    cmd = f'mscore --export-to "{output_pdf}" --force "{mid_file}"'
    
    run_command(cmd)
    return output_pdf

@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    url = data.get("url")

    try:
        webm_file = download_youtube_audio(url)
        midi_file = run_basic_pitch(webm_file)
        pdf_file = generate_pdf_with_musescore(midi_file)

        abs_pdf_path = os.path.abspath(pdf_file)
        print(f"[✅ PDF ready] {abs_pdf_path}")
        
        return jsonify({"pdfPath": abs_pdf_path})
    except Exception as e:
        print(f"[❌ ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["GET"])
@cross_origin()
def download_pdf():
    relative_path = request.args.get("path")
    if not relative_path:
        return "Missing path parameter", 400

    abs_path = os.path.abspath(relative_path)

    if os.path.exists(abs_path):
        return send_file(abs_path)
    else:
        return f"File not found: {abs_path}", 404