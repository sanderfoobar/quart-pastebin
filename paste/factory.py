import os
import logging
import asyncio

from quart import Quart

import settings

app = None


def create_app():
    global app
    app = Quart(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = settings.debug
    app.config['MAX_CONTENT_LENGTH'] = settings.max_content_upload
    app.logger.setLevel(logging.INFO)

    data_dir = os.path.join(settings.cwd, "data")
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    @app.before_serving
    async def startup():
        loop = asyncio.get_event_loop()

        from paste.utils import loop_task, Cleanup
        loop.create_task(loop_task(600, Cleanup.task))

        import paste.routes

    return app
