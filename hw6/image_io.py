from __future__ import annotations

from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4000
SUPPORTED_MODES = {"RGB", "RGBA"}


class InvalidImageError(ValueError):
    """The upload is not a supported, safely readable PNG image."""


def load_png_image(data: bytes) -> Image.Image:
    if not isinstance(data, bytes) or not data:
        raise InvalidImageError("The upload is empty or invalid.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise InvalidImageError("The upload exceeds the allowed size.")
    if not data.startswith(PNG_SIGNATURE):
        raise InvalidImageError("The upload is not a PNG image.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                _validate_open_image(probe)
                probe.verify()

            with Image.open(BytesIO(data)) as image:
                _validate_open_image(image)
                image.load()
                return image.copy()
    except InvalidImageError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
    ) as error:
        raise InvalidImageError("The PNG image is malformed or unsafe.") from error


def _validate_open_image(image: Image.Image) -> None:
    if image.format != "PNG":
        raise InvalidImageError("The upload is not a PNG image.")
    width, height = image.size
    if width < 1 or height < 1 or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise InvalidImageError("The image dimensions exceed the allowed limits.")
    if image.mode not in SUPPORTED_MODES:
        raise InvalidImageError("Only RGB and RGBA PNG images are supported.")
    if getattr(image, "n_frames", 1) != 1:
        raise InvalidImageError("Animated PNG images are not supported.")