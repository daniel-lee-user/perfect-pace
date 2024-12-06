from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import shutil
import os
import tempfile
import zipfile
from flask_cors import CORS
import sys
#from flask_limiter import Limiter
#from flask_limiter.util import get_remote_address
import logging

app = Flask(__name__)
CORS(app, origins=["https://daniel-lee-user.github.io", "http://127.0.0.1:5500"], methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('waitress')
#limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

@app.route('/upload', methods=['POST'])
#@limiter.limit("10 per minute")
def upload_file():
    logger.info("RECEIVED REQUEST")
    file = request.files.get('file')
    filename = request.form.get('filename')
    save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')

    # If file is not provided, check for the filename
    if not file:
        if not filename:
            return jsonify({'error': 'No file or filename provided'}), 400
        # Try to load the file from disk using the provided filename
        file_path = os.path.join(save_directory, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'File {filename} not found on the server'}), 404
    else:
        # If file is provided, save it temporarily
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        file_path = os.path.join(save_directory, file.filename)
        file.save(file_path)

    time = request.form['time']
    
    # Paths for the output JSON and TXT files
    output_base_path = os.path.join(save_directory, 'results')

    try:
        # Run the Python script with the flags
        logger.info(file_path)
        file_path = os.path.realpath(file_path)
        os.chdir("src/")
        result = subprocess.run(
            ['python', 'segment_script.py', '-f', file_path, '-t', time, '-o', output_base_path],
            capture_output=True,
            text=True
        )
        logger.info(result)
    except Exception as e:
        logger.info(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

    os.chdir("..")
    # Prepare paths for the generated frontend files
    preset_segments_path = os.path.join(output_base_path, 'presetSegments.json')
    optimal_paces_path = os.path.join(output_base_path, 'optimalPaces.json')
    segment_lengths_path = os.path.join(output_base_path, 'segmentLengths.json')
    coordinates_path = os.path.join(output_base_path, 'coordinates.json')

    # Verify all required files are generated
    required_files = [
        preset_segments_path,
        optimal_paces_path,
        segment_lengths_path,
        coordinates_path,
    ]
    for required_file in required_files:
        if not os.path.exists(required_file):
            logger.error(f"Missing required file: {required_file}")
            return jsonify({'error': f"Missing required file: {os.path.basename(required_file)}"}), 500
    
    # Create a zip file containing all the required frontend files
    zip_filename = f"{file.filename.split('.')[0]}_results.zip"
    zip_file_path = os.path.join(save_directory, zip_filename)
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for required_file in required_files:
            zipf.write(required_file, os.path.basename(required_file))

    logger.info(f"Generated zip file: {zip_file_path}")

    # Return the zip file to the frontend
    return send_file(zip_file_path, as_attachment=True, mimetype='application/zip')

@app.route('/delete', methods=['DELETE'])
#@limiter.limit("10 per minute")
def delete_files():
    try:
        # Extract data from the request
        logger.info("DELETING FILES")
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'Missing required data (filename)'}), 400

        # Base save directory for generated files
        save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')
        gpx_filepath = os.path.join(save_directory, filename)

        # Delete the gpx file
        if os.path.exists(gpx_filepath):
            os.remove(gpx_filepath)
            logger.info(f"Deleted GPX file: {gpx_filepath}")

        # Define the base directory based on filename
        base_filename = filename.split('.')[0]  # Remove the file extension
        
        base_dir = os.path.join(save_directory, 'results')
        # Check if the results directory exists
        if os.path.exists(base_dir):
            # Delete all files in the directory
            try:
                shutil.rmtree(base_dir)
                logger.info(f"Deleted all files in directory: {base_dir}")
            except:
                logger.error(f"Error deleting files in directory: {base_dir}")

            # Check if the `results` directory is empty and delete it if so
            if os.path.exists(base_dir) and not os.listdir(base_dir):
                os.rmdir(base_dir)
                logger.info(f"Deleted directory: {base_dir}")

        # Check for the zip file created by the upload process
        zip_filename = f"{base_filename}_results.zip"
        zip_file_path = os.path.join(save_directory, zip_filename)
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
            logger.info(f"Deleted zip file: {zip_file_path}")

        return jsonify({'message': 'Files and directories deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/")
#@limiter.limit("10 per minute")
def health():
    return "Healthy"

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000, threads=8, channel_timeout=400)
    #app.run(host="0.0.0.0", port=5000)
