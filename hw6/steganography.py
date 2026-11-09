from __future__ import annotations

import hashlib
import hmac
import struct

from PIL import Image

MAGIC = b"STEG"
VERSION = 1
CHECKSUM_SIZE = 16
HEADER = struct.Struct(">4sBI16s")
HEADER_SIZE = HEADER.size


class CapacityError(ValueError):
    """The image does not have enough room for the message and header."""


class NoMessageError(ValueError):
    """The image does not contain this application's magic header."""


class CorruptedMessageError(ValueError):
    """The image contains a malformed or corrupted encoded message."""


def available_capacity(image: Image.Image) -> int:
    _validate_image_mode(image)
    width, height = image.size
    carrier_bytes = (width * height * 3) // 8
    return max(0, carrier_bytes - HEADER_SIZE)


def encode_message(image: Image.Image, message: str) -> Image.Image:
    _validate_image_mode(image)
    if not isinstance(message, str):
        raise TypeError("The message must be text.")
    payload = message.encode("utf-8")
    capacity = available_capacity(image)
    if image.width * image.height * 3 < HEADER_SIZE * 8:
        raise CapacityError("This image is too small to hold the message header.")
    if len(payload) > capacity:
        raise CapacityError(
            f"Message is {len(payload)} bytes; this image holds at most {capacity} bytes."
        )

    length_bytes = struct.pack(">I", len(payload))
    checksum = _checksum(VERSION, length_bytes, payload)
    packet = HEADER.pack(MAGIC, VERSION, len(payload), checksum) + payload

    channels_per_pixel = len(image.getbands())
    pixels = bytearray(image.tobytes())
    carrier_index = 0
    for byte_value in packet:
        for shift in range(7, -1, -1):
            pixel_index, channel_index = divmod(carrier_index, 3)
            pixel_byte_index = pixel_index * channels_per_pixel + channel_index
            bit = (byte_value >> shift) & 1
            pixels[pixel_byte_index] = (pixels[pixel_byte_index] & 0xFE) | bit
            carrier_index += 1

    encoded = Image.frombytes(image.mode, image.size, bytes(pixels))
    encoded.info.update(image.info)
    return encoded


def decode_message(image: Image.Image) -> str:
    _validate_image_mode(image)
    total_carriers = image.width * image.height * 3
    if total_carriers < HEADER_SIZE * 8:
        raise NoMessageError("The image is too small to contain a message header.")

    pixels = image.tobytes()
    channels_per_pixel = len(image.getbands())
    header_bytes = _extract_bytes(pixels, channels_per_pixel, HEADER_SIZE)
    magic, version, payload_length, checksum = HEADER.unpack(header_bytes)
    if magic != MAGIC:
        raise NoMessageError("No message header was found.")
    if version != VERSION:
        raise CorruptedMessageError("Unsupported message version.")
    if payload_length > available_capacity(image):
        raise CorruptedMessageError("The declared message length exceeds image capacity.")

    packet_size = HEADER_SIZE + payload_length
    if packet_size * 8 > total_carriers:
        raise CorruptedMessageError("The encoded message is incomplete.")
    packet = _extract_bytes(pixels, channels_per_pixel, packet_size)
    payload = packet[HEADER_SIZE:]
    length_bytes = struct.pack(">I", payload_length)
    if not hmac.compare_digest(checksum, _checksum(version, length_bytes, payload)):
        raise CorruptedMessageError("The message checksum does not match.")
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise CorruptedMessageError("The payload is not valid UTF-8.") from error


def _extract_bytes(pixels: bytes, channels_per_pixel: int, byte_count: int) -> bytes:
    output = bytearray(byte_count)
    carrier_index = 0
    for output_index in range(byte_count):
        value = 0
        for _ in range(8):
            pixel_index, channel_index = divmod(carrier_index, 3)
            pixel_byte_index = pixel_index * channels_per_pixel + channel_index
            value = (value << 1) | (pixels[pixel_byte_index] & 1)
            carrier_index += 1
        output[output_index] = value
    return bytes(output)


def _checksum(version: int, length_bytes: bytes, payload: bytes) -> bytes:
    return hashlib.sha256(MAGIC + bytes((version,)) + length_bytes + payload).digest()[:CHECKSUM_SIZE]


def _validate_image_mode(image: Image.Image) -> None:
    if image.mode not in {"RGB", "RGBA"}:
        raise ValueError("Only RGB and RGBA images are supported.")