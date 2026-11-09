# Quiet Signal

Quiet Signal is a local educational Flask application for hiding UTF-8 text in RGB or RGBA PNG images with least-significant-bit (LSB) steganography. It can also decode PNGs produced by the application.

## Requirements

- Python 3.12 or newer
- `uv` for environment and dependency management

## Install and run

From this directory:

```bash
uv sync --extra test
uv run python app.py
```

Open <http://127.0.0.1:5000>. The server binds to loopback and runs with Flask debug mode disabled. Run the tests with:

```bash
uv run pytest
```

## Use

For encoding, select an RGB or RGBA PNG, enter text, and submit. The browser downloads `encoded.png`. For decoding, select a PNG produced by Quiet Signal and submit; the extracted text is rendered on the page with HTML escaping.

Empty messages and non-English UTF-8 text are supported. Images must be no larger than 5 MiB or 4000 pixels on either dimension. Animated PNGs, palette/grayscale images, and other modes are rejected. Image dimensions and alpha-channel values remain unchanged. Uploaded images and extracted text are processed in memory and are not written to disk.

## Format and design

Pixels are traversed in row-major order, with the red, green, then blue channel of each pixel. Each message begins with a 25-byte header: four-byte magic (`STEG`), one-byte version, four-byte big-endian UTF-8 byte length, and a 16-byte truncated SHA-256 checksum. The checksum covers the magic, version, length, and payload. The header and payload bits are stored most-significant-bit first in channel LSBs. Alpha values are never used as carriers.

For an image of width $W$ and height $H$, there are $3WH$ carrier bits. Payload capacity is `max(0, floor(3 * W * H / 8) - 25)` bytes. Encoding checks the UTF-8 byte count against capacity before changing the image.

Image uploads are checked for a PNG signature and Pillow-detected PNG format, validated and loaded in memory, and restricted to a single frame and RGB/RGBA modes. Both the individual upload and full multipart request have size limits. Dimensions are checked before full decoding, while Pillow decompression-bomb warnings are treated as errors.

## Security limitations

LSB steganography does not encrypt a message. The checksum detects accidental corruption but is not a keyed integrity check and does not prevent deliberate tampering. Anyone familiar with the format can extract the text. Re-encoding may discard nonessential PNG metadata; the pixel dimensions and alpha samples are preserved. This project is intended for local coursework, not as a secure messaging system.