from pathlib import Path
import re
import os
from io import BytesIO
import sys
import time
from typing import List
import asyncio
from datetime import datetime, timedelta

from PIL import Image

import settings
from paste.paste import Pastes


async def image_sanitize(buffer: bytes, extension: str) -> bytes:
    """
    - Remove EXIF information
    - Resize if the image is large
    """
    if extension not in ["png", "jpg", "jpeg"]:
        raise Exception(f"invalid extension '{extension}'")

    buffer = BytesIO(buffer)
    buffer.seek(0)
    image = Image.open(buffer)

    if max([image.height, image.width]) > settings.max_image_bounding_box[0]:
        image.thumbnail(settings.max_image_bounding_box, Image.BICUBIC)

    data = list(image.getdata())
    image_without_exif = Image.new(image.mode, image.size)
    image_without_exif.putdata(data)

    buffer = BytesIO()
    image_without_exif.save(buffer, extension)
    buffer.seek(0)

    return buffer.read()


async def loop_task(secs: int, func, after_func=None):
    while True:
        result = await func()
        if after_func:
            await after_func(result)
        await asyncio.sleep(secs)


class Cleanup:
    @staticmethod
    async def task():
        from paste.factory import app
        data_dir_size = sum(f.stat().st_size for f in Path('data').glob('*') if f.is_file())
        if data_dir_size > settings.max_size_data_dir:
            app.logger.warning("Max file sized reached for data dir; cleaning")
            data_dir = os.path.join(settings.cwd, 'data')
            os.popen(f"rm {data_dir}/*")
            return

        data_dir = os.path.join(settings.cwd, "data")
        cmd = f"""
        find {data_dir} -name "*.expires.*"
        """.strip()
        output = os.popen(cmd).read()

        for path in [l.strip() for l in output.split("\n") if l.strip()]:
            if not path.strip():
                continue

            if path.endswith(".png"):
                continue

            if path.endswith(".album"):
                album: List[dict] = await Pastes.read_album_path(path)
                if not album:
                    continue
                deleted = False
                for image in album:
                    try:
                        deleted = await Cleanup.try_remove(image['filepath'], image['expiration'])
                    except Exception as ex:
                        pass
                if deleted:
                    try:
                        os.remove(path)
                    except:
                        pass
            else:
                paste = await Pastes.read_plain_path(path)
                if not paste:
                    continue
                expiration = paste.get('expiration', 0)
                if not isinstance(expiration, int) or expiration <= 0:
                    continue
                await Cleanup.try_remove(path, expiration)

    @staticmethod
    async def try_remove(path: str, expires: int):
        """Removes file if it's eligible for deletion"""
        st = os.stat(path)
        delta = (datetime.now() - datetime.fromtimestamp(st.st_mtime)).total_seconds()
        if delta > expires:
            os.remove(path)
            return True


def sanitize_expiration(val):
    val = int(val)
    if val <= 0:
        val = 86400
    if val > 2419200:
        val = 2419200
    return val
