from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    paces = request.form['paces']
    time = request.form['time']
    is_loop = 'loop' if request.form.get('loop') == 'true' else ''

    # Save the uploaded file temporarily
    file_path = os.path.join('/tmp', file.filename)
    file.save(file_path)

    # Run the Python script with the flags
    try:
        result = subprocess.run(
            ['python', 'dp_alg.py', '-f', file_path, '-t', time, '-p', paces] + ([is_loop] if is_loop else []),
            capture_output=True,
            text=True
        )
        output = result.stdout
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.remove(file_path)  # Clean up the file

    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(debug=True)
