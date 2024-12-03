from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import shutil
import os
import tempfile
import zipfile
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="https://daniel-lee-user.github.io", methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

@app.route('/upload', methods=['POST'])
def upload_file():
    app.logger.info("RECEIVED REQUEST")
    file = request.files.get('file')
    filename = request.form.get('filename')

    # If file is not provided, check for the filename
    if not file:
        if not filename:
            return jsonify({'error': 'No file or filename provided'}), 400
        # Try to load the file from disk using the provided filename
        save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')
        file_path = os.path.join(save_directory, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'File {filename} not found on the server'}), 404
    else:
        # If file is provided, save it temporarily
        save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        file_path = os.path.join(save_directory, file.filename)
        file.save(file_path)

    paces = request.form['paces']
    time = request.form['time']
    algorithm = request.form['alg']
    is_loop = '-l' if request.form.get('loop') == 'true' else ''

    # Save the uploaded file temporarily
    save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')
    
    # Paths for the output JSON and TXT files
    output_json_path = None
    output_txt_path = None
    output_mile_txt_path = None

    try:
        # Run the Python script with the flags
        app.logger.info(file_path)
        file_path = os.path.realpath(file_path)
        os.chdir("src/")
        result = subprocess.run(
            ['python', 'main.py', '-f', file_path, '-t', time, '-p', paces, '-m', algorithm] + ([is_loop] if is_loop else []),
            capture_output=True,
            text=True
        )
        app.logger.info(result)
        os.chdir("..")
        # Define output file names
        base_filename =  file.filename.split('.')[0] if file != None else filename.split('.')[0]
        #alg_type = 'BFA' if request.form['alg'] == "DP" else 'LP'
        output_json_path = os.path.join('..', 'perfect_pace_data', 'results', base_filename,algorithm, f"{time}min_{paces}p.json")
        output_txt_path = os.path.join('..', 'perfect_pace_data', 'results', base_filename,algorithm, f"{time}min_{paces}p_segments.json")
        output_mile_txt_path = os.path.join('..', 'perfect_pace_data', 'results', base_filename,algorithm, f"{time}min_{paces}p_miles.json")
        app.logger.info(output_json_path)
        # Assume that both files are generated by the script
        if not os.path.exists(output_json_path) or not os.path.exists(output_txt_path) or not os.path.exists(output_mile_txt_path):
            app.logger.info("GEN FILES NOT FOUND")
            return jsonify({'error': 'Generated files not found'}), 500

    except Exception as e:
        app.logger.info(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

    # Create a zip file with both files

    zip_filename = f"{base_filename}_{time}min_{paces}p.zip"
    zip_file_path = os.path.join(save_directory, zip_filename)
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        zipf.write(output_json_path, os.path.basename(output_json_path))
        zipf.write(output_txt_path, os.path.basename(output_txt_path))
        zipf.write(output_mile_txt_path, os.path.basename(output_mile_txt_path))
        
    # Return the zip file
    return send_file(zip_file_path, as_attachment=True, mimetype='application/zip')

@app.route('/delete', methods=['DELETE'])
def delete_files():
    try:
        # Extract data from the request (paces, time, algorithm, file)
        app.logger.info("DELETING FILES")
        data = request.get_json()
        paces = data.get('paces')
        time = data.get('time')
        algorithm = data.get('alg')
        filename = data.get('filename')

        if not all([paces, time, algorithm, filename]):
            return jsonify({'error': 'Missing required data'}), 400

        # Base save directory for generated files
        save_directory = os.path.join(os.path.dirname(__file__), '..', 'perfect_pace_data')

        # Define the base directory based on filename and algorithm
        base_filename = filename.split('.')[0]  # Remove the extension
        base_dir = os.path.join(save_directory, 'results', base_filename)

        # Check if the directory exists
        if os.path.exists(base_dir):
            # Delete all files in the directory
            shutil.rmtree(base_dir)
            app.logger.info(f"Deleted directory: {base_dir}")

            # Check if the `results/base_filename` directory is empty and delete it if so
            base_filename_dir = os.path.join(save_directory, 'results', base_filename)
            if os.path.exists(base_filename_dir) and not os.listdir(base_filename_dir):
                os.rmdir(base_filename_dir)
                app.logger.info(f"Deleted base filename directory: {base_filename_dir}")

            # Attempt to delete the zip file in the save directory
            zip_filename = f"{base_filename}_{time}min_{paces}p.zip"
            zip_file_path = os.path.join(save_directory, zip_filename)
            app.logger.info(zip_file_path)
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)
                app.logger.info(f"Deleted zip file: {zip_file_path}")

            return jsonify({'message': 'Files and directories deleted successfully'}), 200
        else:
            return jsonify({'error': 'No directory found to delete'}), 404

    except Exception as e:
        app.logger.info(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/")
def health():
    return "Healthy"

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
    #app.run(host="0.0.0.0", port=5000)
