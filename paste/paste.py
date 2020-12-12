import json
import os
import uuid
from typing import Union, List

import magic
import aiofiles
from quart import request

import settings


class Pastes:
    @staticmethod
    async def read_album_uid(uid: Union[str, uuid.UUID]) -> Union[dict, None]:
        """
        Return album by uuid
        :return: metadata dict
        """
        fn = await Pastes.find_by_uid(uid)
        if not fn:
            return

        return await Pastes.read_album_path(fn)

    @staticmethod
    async def read_plain_uid(uid: Union[str, uuid.UUID]) -> Union[dict, None]:
        """
        Return paste by uuid
        :return: metadata dict
        """
        fn = await Pastes.find_by_uid(uid)
        if not fn:
            return

        return await Pastes.read_plain_path(fn)

    @staticmethod
    async def read_image_uid(uid: Union[str, uuid.UUID]) -> Union[None, bytes]:
        """
        Return a single image by uuid
        :param uid:
        :return:
        """
        path = await Pastes.find_by_uid(uid)
        if not path:
            return

        async with aiofiles.open(path, mode="rb") as f:
            return await f.read()

    @staticmethod
    async def write_plain(contents: bytes, expiration: int = 0, syntax: str = None) -> str:
        """
        Creates a new paste
        :param contents: bytes
        :param expiration: in seconds
        :param syntax: syntax highlighting
        :return: uid
        """
        uid = str(uuid.uuid4())
        out_dir = os.path.join(settings.cwd, "data")
        out_path = os.path.join(out_dir, f"{uid}.{'expires.' if expiration > 0 else ''}paste")

        metadata = json.dumps({
            "ip": request.remote_addr,
            "mimetype": "text/plain",
            "syntax": syntax,
            "uid": uid,
            "expiration": expiration
        }, sort_keys=True)

        async with aiofiles.open(out_path, mode="wb") as f:
            await f.write(metadata.encode())
            await f.write(b"\n")
            await f.write(contents)

        return uid

    @staticmethod
    async def write_image(contents: bytes, expiration: int = 0) -> dict:
        """
        Creates a new image paste
        :param contents: bytes
        :param expiration: in seconds
        :return: metadata dict
        """
        from paste.utils import image_sanitize

        mime = magic.from_buffer(contents, mime=True)
        if not mime.startswith("image"):
            raise Exception(f"An image with for uploader {request.remote_addr} "
                            f"has an invalid mimetype of {mime}")
        extension = mime.split("/", 1)[1]

        # exif removal
        if mime in ["image/jpeg", "image/jpg", "image/png"]:
            contents = await image_sanitize(contents, extension)

        uid = str(uuid.uuid4())
        out_path = os.path.join(settings.cwd, "data", f"{uid}.png")

        async with aiofiles.open(out_path, mode="wb") as f:
            await f.write(contents)

        metadata = {
            "ip": request.remote_addr,
            "mimetype": mime,
            "uid": uid,
            "filepath": out_path,
            "filename": os.path.basename(out_path),
            "expiration": expiration
        }

        return metadata

    @staticmethod
    async def write_album(images: List[bytes], expiration: int = 0) -> str:
        """
        Writes a collection of images
        :param images:
        :param expiration:
        :return: uuid
        """
        data = []
        for image in images:
            metadata = await Pastes.write_image(image, expiration)
            if not metadata:
                continue
            data.append(metadata)

        if not data:
            raise Exception("no content")

        uid = str(uuid.uuid4())
        metadata = json.dumps(data, sort_keys=True)
        out_dir = os.path.join(settings.cwd, "data")
        out_path = os.path.join(out_dir, f"{uid}.{'expires.' if expiration > 0 else ''}album")

        async with aiofiles.open(out_path, mode="wb") as f:
            await f.write(metadata.encode())

        return uid

    @staticmethod
    async def read_plain_path(path: str):
        """Return paste by path"""
        if not os.path.exists(path):
            raise Exception("path not found")

        try:
            async with aiofiles.open(path, mode="rb") as f:
                content = await f.read()

            metadata, content = content.split(b"\n", 1)
            metadata = json.loads(metadata.decode())
        except Exception as ex:
            from paste.factory import app
            app.logger.error(f"Could not read {path}; {ex}")
            return

        return {
            "_type": "p",
            "uid": metadata.get("uid", ""),
            "content": content.decode('utf-8', 'ignore'),
            "syntax": metadata.get("syntax", ""),
            "expiration": metadata.get("expiration")
        }

    @staticmethod
    async def read_album_path(path: str) -> dict:
        if not os.path.exists(path):
            raise Exception("path not found")

        try:
            async with aiofiles.open(path, mode="rb") as f:
                content = await f.read()
            return json.loads(content.decode())
        except Exception as ex:
            from paste.factory import app
            app.logger.error(f"Could not read {path}; {ex}")

    @staticmethod
    async def find_by_uid(uid: Union[str, uuid.UUID]) -> str:
        """
        :param uid: paste/album/img uuid
        :return: path as string
        """
        if isinstance(uid, uuid.UUID):
            uid = str(uid)

        data_dir = os.path.join(settings.cwd, "data")
        cmd = f"""
        find {data_dir} -name "{uid}.*"
        """.strip()

        try:
            return next(l.strip() for l in os.popen(cmd).read().split("\n") if l.strip())
        except:
            pass
