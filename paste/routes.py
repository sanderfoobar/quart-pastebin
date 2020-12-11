import magic
import re
from quart import render_template, request, redirect, url_for, jsonify

from paste.factory import app
from paste.utils import sanitize_expiration
from paste.paste import Pastes


@app.route('/')
async def index():
    return await render_template("index.html")


@app.route("/<path:_type>/<uuid:uid>")
@app.route("/<path:_type>/<uuid:uid>/<path:raw>")
async def paste_view(_type, uid, raw=None):
    if _type == "p":
        paste = await Pastes.read_plain_uid(uid)
        if not paste:
            raise Exception("Paste by that id not found :(")
        if raw:
            return paste["content"], {
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            }
        return await render_template("paste.html", _type=_type, paste=paste)
    elif _type == "a":
        images = await Pastes.read_album_uid(uid)
        return await render_template("album.html", _type=_type, album=images)
    elif _type == "i":
        image = await Pastes.read_image_uid(uid)
        return image, {
            "Content-Type": magic.from_buffer(image, mime=True),
            "Content-Disposition": f"inline; filename={str(uid)}.png"
        }
    raise Exception("bad URL")


@app.route("/paste/plain", methods=["POST"])
async def paste_plain():
    content = await request.form
    body = content.get("paste[body]", "").encode()
    lang = re.sub("[^0-9a-zA-Z]+", "", content.get("paste[lang]", "plain"))
    expiration = sanitize_expiration(content.get("paste[expir]", 0))

    if not body:
        raise Exception("No content")

    uid = await Pastes.write_plain(
        syntax=lang,
        expiration=expiration,
        contents=body)

    return redirect(url_for("paste_view", _type="p", uid=uid))


@app.route("/paste/img", methods=["POST"])
async def paste_img():
    allowed_extensions = [".png", ".jpg", ".gif", ".webm"]
    expiration = sanitize_expiration(request.args.get("expiration", 86400))

    files = await request.files
    files = files.getlist("files[]")
    if not files:
        raise Exception("no content")

    images = []
    for file in files:
        for ext in allowed_extensions:
            if not file.filename.endswith(ext):
                continue
            images.append(file.read())

    if not images:
        raise Exception("no content")

    album_uid = await Pastes.write_album(images, expiration)
    images = await Pastes.read_album_uid(album_uid)

    if len(images) > 1:
        url = url_for("paste_view", _type="a", uid=album_uid)
    else:
        url = url_for("paste_view", _type="i", uid=images[0]['uid'], raw="raw")

    return jsonify({
        "success": True,
        "redirect": url
    })


@app.errorhandler(404)
@app.errorhandler(500)
async def error(e):
    return await render_template("error.html", message=str(e))


@app.route("/favicon.ico")
async def favicon():
    return "ok", 200
