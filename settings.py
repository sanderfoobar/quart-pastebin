import os
cwd = os.path.dirname(os.path.realpath(__file__))


def bool_env(val):
    return val is True or (isinstance(val, str) and (val.lower() == 'true' or val == '1'))


debug = bool_env(os.environ.get("PASTE_DEBUG", False))
host = os.environ.get("PASTE_HOST", "127.0.0.1")
port = int(os.environ.get("PASTE_PORT", 2030))

# max data dir filesize, combined (1 GB default)
max_size_data_dir = 1073741824

# any request with a body larger these limits will trigger a Request Entity Too Large, 413 (20 MB default)
max_content_upload = 20971520

# images beyond these bounds get resized
max_image_bounding_box = (3840, 2160)
