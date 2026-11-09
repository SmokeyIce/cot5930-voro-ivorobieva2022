from io import BytesIO

import pytest
from PIL import Image

from app import MAX_REQUEST_BYTES, app as flask_app
import image_io
from image_io import InvalidImageError


@pytest.fixture()
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def png_bytes(mode="RGB", size=(80, 80)):
    image = Image.new(mode, size, (55, 96, 72) if mode == "RGB" else (55, 96, 72, 81))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_index_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Encode" in response.data
    assert b"Decode" in response.data


def test_encode_download_then_decode(client):
    response = client.post(
        "/encode",
        data={"image": (BytesIO(png_bytes()), "not-trusted.jpg"), "message": "Hello 世界"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers["Content-Disposition"].endswith('filename=encoded.png')

    decoded = client.post(
        "/decode",
        data={"image": (BytesIO(response.data), "encoded.png")},
        content_type="multipart/form-data",
    )
    assert decoded.status_code == 200
    assert "Hello 世界" in decoded.get_data(as_text=True)


def test_rgba_encode_preserves_alpha(client):
    original_png = png_bytes("RGBA")
    with Image.open(BytesIO(original_png)) as original:
        expected_alpha = original.getchannel("A").tobytes()
    response = client.post(
        "/encode",
        data={"image": (BytesIO(original_png), "alpha.png"), "message": "alpha"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    with Image.open(BytesIO(response.data)) as encoded:
        assert encoded.size == (80, 80)
        assert encoded.getchannel("A").tobytes() == expected_alpha


@pytest.mark.parametrize("payload", [b"not an image", b"\x89PNG\r\n\x1a\ntruncated"])
def test_malformed_or_non_png_upload_is_rejected(client, payload):
    response = client.post(
        "/decode",
        data={"image": (BytesIO(payload), "image.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"Traceback" not in response.data


def test_png_content_is_checked_not_extension(client):
    response = client.post(
        "/decode",
        data={"image": (BytesIO(png_bytes()), "image.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"No message" in response.data


def test_unsupported_mode_is_rejected(client):
    output = BytesIO()
    Image.new("L", (20, 20)).save(output, format="PNG")
    response = client.post(
        "/decode",
        data={"image": (BytesIO(output.getvalue()), "gray.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_animated_png_is_rejected(client):
    output = BytesIO()
    first = Image.new("RGB", (20, 20), "red")
    second = Image.new("RGB", (20, 20), "blue")
    first.save(output, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    response = client.post(
        "/decode",
        data={"image": (BytesIO(output.getvalue()), "animated.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_image_dimension_limit_is_enforced(client):
    response = client.post(
        "/decode",
        data={"image": (BytesIO(png_bytes(size=(4001, 1))), "wide.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_decompression_bomb_warning_is_rejected(monkeypatch):
    monkeypatch.setattr(image_io.Image, "MAX_IMAGE_PIXELS", 300)
    with pytest.raises(InvalidImageError):
        image_io.load_png_image(png_bytes(size=(20, 20)))


def test_image_file_size_limit_is_enforced(client):
    payload = png_bytes() + b"0" * (5 * 1024 * 1024 + 1 - len(png_bytes()))
    response = client.post(
        "/decode",
        data={"image": (BytesIO(payload), "large.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413


def test_multipart_request_size_limit_is_enforced(client):
    response = client.post(
        "/decode",
        data={"image": (BytesIO(b"x" * MAX_REQUEST_BYTES), "large.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    assert b"Traceback" not in response.data


def test_empty_message_is_allowed(client):
    response = client.post(
        "/encode",
        data={"image": (BytesIO(png_bytes()), "image.png"), "message": ""},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200


def test_flask_debug_is_disabled():
    assert flask_app.debug is False