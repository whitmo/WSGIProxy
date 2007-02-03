import os

cached = {}

def get_secret(secret_file):
    mtime = os.stat(secret_file).st_mtime
    if (cached.get(secret_file) is None
        or cached[secret_file][0] > mtime):
        f = open(secret_file, 'rb')
        c = f.read()
        f.close()
        cached[secret_file] = (mtime, c)
    return cached[secret_file][1]
