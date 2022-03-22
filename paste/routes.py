import re

import magic
from werkzeug.exceptions import NotFound
from quart import render_template, request, redirect, url_for, jsonify, Blueprint, abort

from paste.utils import sanitize_expiration
from paste.paste import Pastes

bp_routes = Blueprint('routes', __name__)


@bp_routes.route('/')
async def index():
    return await render_template("index.html")


@bp_routes.route("/<any(p, a, i):_type>/<path:uid>")
@bp_routes.route("/<any(p, a, i):_type>/<path:uid>.<path:extension>")
async def paste_view(_type, uid: str, extension=None):
    if not len(uid) == 5:
        return abort(500)

    if _type == "p":
        paste = await Pastes.read_plain_uid(uid)
        if not paste:
            return abort(404, "No such paste.")
        if extension:
            return paste["content"], {
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            }
        return await render_template("paste.html", _type=_type, paste=paste)
    elif _type == "a":
        album = await Pastes.read_album_uid(uid)
        if not album:
            return abort(404, "Album not found.")
        return await render_template("album.html", _type=_type, album=album)
    elif _type == "i":
        image = await Pastes.read_image_uid(uid)
        if not image:
            return abort(404, "Image not found.")
        return image, {
            "Content-Type": magic.from_buffer(image, mime=True),
            "Content-Disposition": f"inline; filename={str(uid)}.png"
        }


@bp_routes.route("/paste/plain", methods=["POST"])
async def paste_plain():
    content = await request.form
    body = content.get("paste[body]", "").encode()
    lang = re.sub("[^0-9a-zA-Z]+", "", content.get("paste[lang]", "plain"))
    expiration = sanitize_expiration(content.get("paste[expir]", 0))

    if not body:
        return abort(422, "incomprehensible content")

    uid = await Pastes.write_plain(
        syntax=lang,
        expiration=expiration,
        contents=body)
    return redirect(url_for("routes.paste_view", _type="p", uid=uid, extension="txt"))


@bp_routes.route("/paste/img", methods=["POST"])
async def paste_img():
    allowed_extensions = [".png", ".jpg", ".gif", ".webm"]
    expiration = sanitize_expiration(request.args.get("expiration", 86400))

    files = await request.files
    files = files.getlist("files[]")
    if not files:
        return abort(400, "no content")

    images = []
    for file in files:
        for ext in allowed_extensions:
            if not file.filename.endswith(ext):
                continue
            images.append(file.read())

    if not images:
        return abort(400, "no content")

    album_uid = await Pastes.write_album(images, expiration)
    images = await Pastes.read_album_uid(album_uid)
    if not images:
        return abort(400, "no content")

    if len(images) > 1:
        url = url_for("routes.paste_view", _type="a", uid=album_uid)
    else:
        url = url_for("routes.paste_view", _type="i", uid=images[0]['uid'], extension=images[0]['extension'])

    return jsonify({
        "success": True,
        "redirect": url
    })


@bp_routes.errorhandler(404)
@bp_routes.errorhandler(500)
async def error(e):
    msg = str(e)
    if isinstance(e, NotFound):
        if e.description:
            msg = f"{msg} - {e.description}"

    return await render_template("error.html", message=msg)


@bp_routes.route("/favicon.ico")
async def favicon():
    return "ok", 200
