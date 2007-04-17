import httplib
from urllib import quote as url_quote
import socket
from paste import httpexceptions

# Remove these headers from response (specify lower case header
# names):
filtered_headers = (     
    'transfer-encoding',    
)

def filter_paste_httpserver_proxy(app):
    """
    Maps the ``paste.httpserver`` proxy environment keys to
    SERVER_NAME and SERVER_PORT.  This allows you to use
    ``paste.httpserver`` as a real HTTP proxy (wrapping
    ``proxy_exact_request`` with this middleware).
    """
    def filter_app(environ, start_response):
        filter_paste_httpserver_proxy_environ(environ)
        return app(environ, start_response)
    return filter_app

def filter_paste_httpserver_proxy_environ(environ):
    if 'paste.httpserver.proxy.scheme' in environ:
        environ['wsgi.url_scheme'] = environ['paste.httpserver.proxy.scheme']
    if 'paste.httpserver.proxy.host' in environ:
        host = environ['paste.httpserver.proxy.host']
        scheme = environ['wsgi.url_scheme']
        if ':' in host:
            host, port = value.split(':', 1)
        elif scheme == 'http':
            port = '80'
        elif scheme == 'https':
            port = '443'
        else:
            assert 0
        environ['SERVER_NAME'] = host
        environ['SERVER_PORT'] = port
    

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
    if scheme == 'http':
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
    try:
        conn.request(environ['REQUEST_METHOD'],
                     path, body, headers)
    except socket.error, exc:
        if exc.args[0] == -2:
            # Name or service not known
            exc = httpexceptions.HTTPBadGateway(
                "Name or service not known (bad domain name: %s)"
                % environ['SERVER_NAME'])
            return exc(environ, start_response)
        raise
    res = conn.getresponse()
    headers_out = parse_headers(res.msg)
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

def parse_headers(message):
    """
    Turn a Message object into a list of WSGI-style headers.
    """
    headers_out = []        
    for full_header in message.headers:
        if not full_header:            
            # Shouldn't happen, but we'll just ignore
            continue                     
        if full_header[0].isspace():
            # Continuation line, add to the last header
            if not headers_out:                        
                raise ValueError(
                    "First header starts with a space (%r)" % full_header)
            last_header, last_value = headers_out.pop()                   
            value = last_value + ' ' + full_header.strip()
            headers_out.append((last_header, value))      
            continue                                
        try:        
            header, value = full_header.split(':', 1)
        except:                                      
            raise ValueError("Invalid header: %r" % full_header)
        value = value.strip()                                   
        if header.lower() not in filtered_headers:
            headers_out.append((header, value))   
    return headers_out
