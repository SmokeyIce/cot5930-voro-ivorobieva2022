import hashlib
import struct

import pytest
from PIL import Image

from steganography import (
    CapacityError,
    CorruptedMessageError,
    HEADER,
    MAGIC,
    NoMessageError,
    VERSION,
    available_capacity,
    decode_message,
    encode_message,
)


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
@pytest.mark.parametrize("message", ["Hello, world!", "", "Zażółć gęślą jaźń 你好 🌱"])
def test_round_trip(mode, message):
    image = Image.new(mode, (80, 80), (41, 106, 52) if mode == "RGB" else (41, 106, 52, 73))

    encoded = encode_message(image, message)

    assert decode_message(encoded) == message
    assert encoded.size == image.size
    if mode == "RGBA":
        assert encoded.getchannel("A").tobytes() == image.getchannel("A").tobytes()


def test_exact_capacity_succeeds_and_next_byte_is_rejected():
    image = Image.new("RGB", (10, 10), (0, 0, 0))
    capacity = available_capacity(image)
    assert capacity == 12
    assert decode_message(encode_message(image, "x" * capacity)) == "x" * capacity
    with pytest.raises(CapacityError):
        encode_message(image, "x" * (capacity + 1))


def test_image_too_small_for_header_has_zero_capacity():
    image = Image.new("RGB", (2, 2))
    assert available_capacity(image) == 0
    with pytest.raises(CapacityError):
        encode_message(image, "")
    with pytest.raises(NoMessageError):
        decode_message(image)


def test_image_without_magic_has_no_message():
    with pytest.raises(NoMessageError):
        decode_message(Image.new("RGB", (20, 20), (0, 0, 0)))


@pytest.mark.parametrize("carrier_index", [HEADER.size * 8, 9 * 8])
def test_checksum_or_payload_corruption_is_detected(carrier_index):
    image = Image.new("RGB", (80, 80), (12, 34, 56))
    encoded = encode_message(image, "a message")
    pixels = bytearray(encoded.tobytes())
    pixel_index, channel_index = divmod(carrier_index, 3)
    byte_index = pixel_index * 3 + channel_index
    pixels[byte_index] ^= 1
    corrupted = Image.frombytes("RGB", image.size, bytes(pixels))

    with pytest.raises(CorruptedMessageError):
        decode_message(corrupted)


def test_invalid_utf8_is_rejected_after_checksum_validation():
    image = Image.new("RGB", (80, 80), (0, 0, 0))
    payload = b"\xff"
    length_bytes = struct.pack(">I", len(payload))
    checksum = hashlib.sha256(MAGIC + bytes((VERSION,)) + length_bytes + payload).digest()[:16]
    packet = HEADER.pack(MAGIC, VERSION, len(payload), checksum) + payload
    pixels = bytearray(image.tobytes())
    for carrier_index in range(len(packet) * 8):
        pixel_index, channel_index = divmod(carrier_index, 3)
        bit = (packet[carrier_index // 8] >> (7 - carrier_index % 8)) & 1
        byte_index = pixel_index * 3 + channel_index
        pixels[byte_index] = (pixels[byte_index] & 0xFE) | bit
    encoded = Image.frombytes("RGB", image.size, bytes(pixels))

    with pytest.raises(CorruptedMessageError):
        decode_message(encoded)


def test_unsupported_image_mode_is_rejected():
    with pytest.raises(ValueError):
        encode_message(Image.new("L", (20, 20)), "hello")