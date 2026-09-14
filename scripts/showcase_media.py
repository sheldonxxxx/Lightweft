#!/usr/bin/env python3
"""Validate the intentionally published showcase JPEGs and their metadata."""
from io import BytesIO
from pathlib import PurePosixPath
import re

JPEG_LIMIT = 2 * 1024 * 1024
SEGMENT = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z')
UUID_NAME = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', re.IGNORECASE)


def is_asset_path(name):
    """Accept generic, relative JPEG names only inside the showcase asset folder."""
    path = PurePosixPath(name)
    parts = path.parts
    return (
        name == path.as_posix() and 3 <= len(parts) <= 6
        and parts[:2] == ('showcase', 'assets') and path.suffix == '.jpg'
        and len(name) <= 160 and not UUID_NAME.search(name)
        and all(SEGMENT.fullmatch(part) for part in (*parts[2:-1], path.stem))
    )


def validate_jpeg(blob, forbidden_patterns=()):
    """Decode pixels and reject metadata segments other than plain JFIF and sRGB ICC."""
    from PIL import Image, ImageCms

    if len(blob) > JPEG_LIMIT:
        raise ValueError('larger than the 2 MiB showcase JPEG limit')
    if not blob.startswith(b'\xff\xd8'):
        raise ValueError('not a JPEG')
    position, in_scan, ended, scans = 2, False, False, 0
    profile_chunks = {}
    profile_count = None
    while position < len(blob):
        if in_scan:
            position = blob.find(b'\xff', position)
            if position < 0:
                raise ValueError('JPEG scan has no end marker')
        if blob[position] != 0xff:
            raise ValueError('invalid JPEG segment boundary')
        while position < len(blob) and blob[position] == 0xff:
            position += 1
        if position >= len(blob):
            raise ValueError('truncated JPEG marker')
        marker = blob[position]
        position += 1
        if in_scan and (marker == 0 or 0xd0 <= marker <= 0xd7):
            continue
        in_scan = False
        if marker == 0xd9:
            if position != len(blob):
                raise ValueError('content after JPEG end marker')
            ended = True
            break
        if marker in {0, 0xd8} or 0xd0 <= marker <= 0xd7:
            raise ValueError('unexpected JPEG marker')
        if position + 2 > len(blob):
            raise ValueError('truncated JPEG segment')
        length = int.from_bytes(blob[position:position + 2], 'big')
        if length < 2 or position + length > len(blob):
            raise ValueError('invalid JPEG segment length')
        payload = blob[position + 2:position + length]
        position += length
        if marker == 0xfe:
            raise ValueError('JPEG comments are not permitted')
        if 0xe0 <= marker <= 0xef:
            if marker == 0xe0:
                if len(payload) != 14 or not payload.startswith(b'JFIF\x00') or payload[-2:] != b'\x00\x00':
                    raise ValueError('only plain JFIF without embedded thumbnails is permitted')
            elif marker == 0xe2 and payload.startswith(b'ICC_PROFILE\x00'):
                if len(payload) < 15:
                    raise ValueError('invalid ICC segment')
                sequence, count = payload[12:14]
                if not 1 <= sequence <= count or sequence in profile_chunks:
                    raise ValueError('invalid ICC sequence')
                if profile_count is not None and profile_count != count:
                    raise ValueError('inconsistent ICC sequence')
                profile_count = count
                profile_chunks[sequence] = payload[14:]
            else:
                raise ValueError('JPEG source metadata is not permitted (APP1, EXIF, XMP, IPTC or other APP data)')
        if marker == 0xda:
            scans += 1
            in_scan = True
    if not ended or not scans:
        raise ValueError('incomplete JPEG')
    if profile_chunks:
        if set(profile_chunks) != set(range(1, profile_count + 1)):
            raise ValueError('incomplete ICC profile')
        profile_bytes = b''.join(profile_chunks[index] for index in range(1, profile_count + 1))
        if len(profile_bytes) > 256 * 1024:
            raise ValueError('ICC profile exceeds the size limit')
        try:
            profile = ImageCms.ImageCmsProfile(BytesIO(profile_bytes))
            description = ImageCms.getProfileDescription(profile)
        except (OSError, ValueError) as error:
            raise ValueError('invalid ICC profile') from error
        if 'srgb' not in description.lower() or any(pattern.search(profile_bytes.decode('latin-1')) for pattern in forbidden_patterns):
            raise ValueError('only a generic sRGB ICC profile is permitted')
    try:
        with Image.open(BytesIO(blob)) as image:
            if image.format != 'JPEG' or image.getexif():
                raise ValueError('invalid JPEG or remaining EXIF metadata')
            image.load()
            if image.width > 12000 or image.height > 12000:
                raise ValueError('showcase JPEG dimensions exceed 12000 pixels')
            return image.size
    except (OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError('JPEG pixels could not be decoded') from error
