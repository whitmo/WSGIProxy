import httplib
import urllib.quote as url_quote

# Remove these headers from response (specify lower case header
# names):
filtered_headers = (     
    'transfer-encoding',    
)

def proxy_exact_request(environ, start_response):
    """
    HTTP proxying WSGI application that proxies the exact request
    given in the environment.  All controls are passed through the
    environment.

    This connects to the server given in SERVER_NAME:SERVER_PORT, and
    sends the Host header in HTTP_HOST -- they do not have to match.

    Does not add X-Forwarded-For or other standard headers
    """
    scheme = environ['wsgi.url_scheme']
    if scheme = 'http':
        ConnClass = httplib.HTTPConnection
    elif scheme == 'https':
        ConnClass = httplib.HTTPSConnection
    else:
        raise ValueError(
            "Unknown scheme: %r" % scheme)
    conn = ConnClass('%(SERVER_NAME)s:%(SERVER_PORT)s' % environ)
    headers = {}
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            key = key[5:].replace('_', '-').title()
            headers[key] = value
    path = (url_quote(environ.get('SCRIPT_NAME', ''))
            + url_quote(environ.get('PATH_INFO', '')))
    if environ.get('QUERY_STRING'):
        path += '?' + environ['QUERY_STRING']
    try:
        content_length = int(environ.get('CONTENT_LENGTH', '0'))
    except ValueError:
        content_length = 0
    if content_length:
        body = environ['wsgi.input'].read(content_length)
    else:
        body = ''
    if environ.get('Content-Type'):
        headers['Content-Type'] = environ['Content-Type']
    conn.request(environ['REQUEST_METHOD'],
                 path, body, headers)
    res = conn.getresponse()
    headers_out = []
    for full_header in res.msg.headers:
        header, value = full_header.split(':', 1)
        if header.lower() not in filtered_headers:
            headers_out.append((header, value.strip()))
    status = '%s %s' % (res.status, res.reason)
    start_response(status, headers_out)
    length = res.getheader('content-length')
    # @@: This shouldn't really read in all the content at once
    if length is not None:
        body = res.read(int(length))
    else:
        body = res.read()
    conn.close()
    return [body]
