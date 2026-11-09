#
# Creating a Web-Based steganography tool
# port 3000 for Node.js, React, and express
# port 4200 Angular dev servers
# port 5000/8000 flask, django, FastAPI servers
# port 5173 vite

# stenanography -- encoding information into images,audio,text.
# image function first. If time try audio. Maybe audio would be easier though?
# images are matrices. lots of points to keep track if image is rotated/resized

# PNG
# Encode: LSB
# PNG'

# PNG'
# Decode: LSB
# PNG

# Site security : file size limits image security limits, user authentication,
#

# env py 3.12
# img processing pillow
# web frame work flask
# front end html dont worry about cs
# encrpy alg lsbc steganography
# coding agent copilot

from __future__ import annotations

from io import BytesIO

from flask import Flask, abort, render_template, request, send_file
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from image_io import InvalidImageError, MAX_UPLOAD_BYTES, load_png_image
from steganography import (
	CapacityError,
	CorruptedMessageError,
	NoMessageError,
	decode_message,
	encode_message,
)

MAX_REQUEST_BYTES = 6 * 1024 * 1024


def create_app() -> Flask:
	application = Flask(__name__)
	application.config.update(
		DEBUG=False,
		MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
		MAX_FORM_MEMORY_SIZE=MAX_UPLOAD_BYTES,
		TRUSTED_HOSTS=["localhost", "127.0.0.1"],
	)

	@application.get("/")
	def index():
		return render_template("index.html")

	@application.post("/encode")
	def encode():
		try:
			image = _read_uploaded_image()
			message = request.form.get("message")
			if message is None:
				abort(400)
			encoded = encode_message(image, message)
			output = BytesIO()
			encoded.save(output, format="PNG")
			output.seek(0)
			return send_file(
				output,
				mimetype="image/png",
				as_attachment=True,
				download_name="encoded.png",
			)
		except CapacityError as error:
			return render_template("index.html", error=str(error)), 400
		except InvalidImageError:
			return render_template("index.html", error="Upload a valid RGB or RGBA PNG image."), 400

	@application.post("/decode")
	def decode():
		try:
			image = _read_uploaded_image()
			message = decode_message(image)
			return render_template("index.html", message=message)
		except InvalidImageError:
			return render_template("index.html", error="Upload a valid RGB or RGBA PNG image."), 400
		except NoMessageError:
			return render_template("index.html", error="No message from this application was found."), 200
		except CorruptedMessageError:
			return render_template("index.html", error="The encoded message is invalid or corrupted."), 200

	@application.errorhandler(RequestEntityTooLarge)
	def request_too_large(_error):
		return render_template("index.html", error="The request exceeds the allowed size."), 413

	@application.errorhandler(Exception)
	def unexpected_error(error):
		if isinstance(error, HTTPException):
			return error
		application.logger.exception("Unhandled application error")
		return render_template("index.html", error="The request could not be completed."), 500

	return application


def _read_uploaded_image():
	uploaded_file = request.files.get("image")
	if uploaded_file is None:
		abort(400)
	image_data = uploaded_file.stream.read(MAX_UPLOAD_BYTES + 1)
	if len(image_data) > MAX_UPLOAD_BYTES:
		raise RequestEntityTooLarge()
	try:
		return load_png_image(image_data)
	except InvalidImageError:
		raise


app = create_app()


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=False)