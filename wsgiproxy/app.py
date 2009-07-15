import simplejson
import cPickle as pickle
import urllib
import urlparse
import re
from wsgiproxy.signature import sign_request
from wsgiproxy import protocol_version
from wsgiproxy.secretloader import get_secret
from wsgiproxy.exactproxy import proxy_exact_request

__all__ = ['WSGIProxyApp']

def base64encode(value):
    return value.encode('base64').replace('\n', '')

class WSGIProxyApp(object):
    """Acts as a WSGI application that sends all its requests to
    another host

    This rewrites incoming requests and sends them to another host
    (identified by `href`).  By default it will set a few standard
    headers::

    ``X-Forwarded-Server``: The host name where the request originated

    ``X-Forwarded-Scheme``: The original scheme (e.g., http)

    ``X-Forwarded-For``: The address of the original client (REMOTE_ADDR)

    ``X-Forwarded-Script-Name``: The value of SCRIPT_NAME
    
    ``X-Traversal-Path``: The portion of the *destination* (`href`)
    path that is being forwarded to; this part of the path was *not*
    in the original request

    ``X-Traversal-Query-String``: Any portion of the query string that
    was not in the original request
    """

    def __init__(self, href, secret_file=None,
                 string_keys=None, unicode_keys=None,
                 json_keys=None, pickle_keys=None):
        self.href = href
        self.secret_file = secret_file
        self.string_keys = string_keys or ()
        self.unicode_keys = unicode_keys or ()
        self.json_keys = json_keys or ()
        self.pickle_keys = pickle_keys or ()

    header_map = {
        'HTTP_HOST': 'X_FORWARDED_SERVER',
        'SCRIPT_NAME': 'X_FORWARDED_SCRIPT_NAME',
        'wsgi.url_scheme': 'X_FORWARDED_SCHEME',
        'REMOTE_ADDR': 'X_FORWARDED_FOR',
        }

    def href__get(self):
        return self._href

    def href__set(self, href):
        self._href = href
        self.href_scheme, self.href_netloc, self.href_path, self.href_query, self.href_fragment = urlparse.urlsplit(href, 'http')
        assert self.href_scheme in ('http', 'https')
        if ':' not in self.href_netloc:
            if self.href_scheme == 'http':
                self.href_netloc += ':80'
            else:
                self.href_netloc += ':443'
        # The trailing / is implicit:
        self.href_path = self.href_path.lstrip('/')

    href = property(href__get, href__set)

    def __call__(self, environ, start_response):
        environ = self.encode_environ(environ)
        self.setup_forwarded_environ(environ)
        self.forward_request(environ, start_response)

    def forward_request(self, environ, start_response):
        return proxy_exact_request(environ, start_response)

    def setup_forwarded_environ(self, environ):
        # Now we fix the request up so that refers to the target
        # server that we are proxying to
        environ['wsgi.url_scheme'] = self.href_scheme
        environ['HTTP_HOST'] = self.href_netloc
        environ['SERVER_NAME'], environ['SERVER_PORT'] = self.href_netloc.split(':', 1)
        environ['SCRIPT_NAME'] = self.href_path
        if self.href_path:
            environ['HTTP_X_TRAVERSAL_PATH'] = self.href_path
        if self.href_query:
            if environ['QUERY_STRING']:
                environ['QUERY_STRING'] += '&' + self.href_query
            else:
                environ['QUERY_STRING'] = self.href_query
            environ['HTTP_X_TRAVERSAL_QUERY_STRING'] = self.href_query

    def encode_environ(self, environ):
        # I don't want to totally overwrite things in the current
        # environment, so we copy:
        for name in ['QUERY_STRING', 'SCRIPT_NAME', 'PATH_INFO']:
            if name not in environ:
                environ[name] = ''
        orig_environ = environ
        environ = environ.copy()
        environ['wsgiproxy.orig_environ'] = orig_environ
        if self.secret_file is not None:
            secret = get_secret(self.secret_file)
            sign_request(environ)
        for key in environ.keys():
            if key.startswith('HTTP_X_WSGIPROXY'):
                # Conflicting header...
                del environ[key]
        for key, dest in self.header_map.items():
            environ['HTTP_%s' % dest] = environ[key]
        for prefix, keys, encoder in [
            ('STR', self.string_keys, self.str_encode),
            ('UNICODE', self.unicode_keys, self.unicode_encode),
            ('JSON', self.json_keys, self.json_encode),
            ('PICKLE', self.pickle_keys, self.pickle_encode)]:
            for count, key in enumerate(keys):
                if key not in environ:
                    continue
                key = 'HTTP_X_WSGIPROXY_%s_%s' % (prefix, count)
                environ[key] = '%s %s' % (
                    urllib.quote(key), encoder(environ[key]))
        environ['HTTP_X_WSGIPROXY_VERSION'] = protocol_version
        return environ

    safe_str_re = re.compile(r'^[^\x00-\x1f]*$')

    def str_encode(self, value):
        assert isinstance(value, str)
        if (not safe_str_re.search(value) or value.startswith('b64')
            or value.strip() != value):
            value = 'b64'+base64encode(value)
        return value

    def unicode_encode(self, value):
        assert isinstance(value, basestring)
        value = unicode(value).encode('utf8')
        return self.str_encode(value)
    
    def json_encode(self, value):
        v = simplejson.dumps(value)
        return self.str_encode(v)

    def pickle_encode(self, value):
        v = pickle.dumps(value)
        return self.str_encode(v)
