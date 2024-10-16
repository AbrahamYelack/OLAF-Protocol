import os
import uuid
from flask import Blueprint, request, jsonify, abort

# Create a blueprint for your routes
routes_bp = Blueprint("routes_bp", __name__)

# Set upload folder and allowed file size
UPLOAD_FOLDER = "./uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to generate a unique filename
def generate_unique_filename(filename):
    unique_id = uuid.uuid4().hex
    ext = os.path.splitext(filename)[1]
    return unique_id + ext


@routes_bp.route("/api/upload", methods=["POST"])
def upload_file():
    print("File upload request received")
    # Check if the POST request has the file part
    if "file" not in request.files:
        print("No file dropping message")
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # Check if a file was selected
    if file.filename == "":
        print("No file dropping message")
        return jsonify({"error": "No selected file"}), 400

    # Generate a unique filename and save the file
    unique_filename = generate_unique_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"error": "Failed to save file", "details": str(e)}), 500

    # Return the URL where the file can be retrieved
    file_url = f"http://{request.host}/{unique_filename}"
    return jsonify({"file_url": file_url}), 200


@routes_bp.route("/<path:filename>", methods=["GET"])
def get_file(filename):
    print(f"File download request received: {filename}")
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # return the file contents bytes
    bytes = open(file_path, "rb").read()
    return bytes


# Error handling for large files
@routes_bp.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large, max size is 10MB"}), 413
