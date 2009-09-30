import simplejson
import cPickle as pickle
import urllib
from wsgiproxy import protocol_version
from wsgiproxy.secretloader import get_secret
from paste import httpexceptions

__all__ = ['WSGIProxyMiddleware']

class WSGIProxyMiddleware(object):

    """
    Fixes up the environment given special headers set by WSGIProxy,
    or by configuration.

    Accepts the configuration:

    ``secret_file``:
    
        A location where a secret is kept, used to sign the request
        when its coming from ``wsgiproxy.app``

    ``trust_ips``:

        Instead of ``secret_file`` you can give a list of IPs that are
        trusted.  Trusted hosts can send pickle headers.

    ``prefix``:

        This is used for explicitly configuring the value of
        SCRIPT_NAME.  A request to ``/foo`` with ``prefix='/bar'``
        will result in a SCRIPT_NAME of ``'/bar'`` and a PATH_INFO of
        ``'/foo'``.

    ``pop_prefix``:

        This is a prefix that is popped off the actual request path,
        and put into SCRIPT_NAME.  A request to ``/bar/foo`` where
        ``pop_prefix='/bar'`` will result in a SCRIPT_NAME of
        ``'/bar'`` and a PATH_INFO of ``'/foo'``.

    ``scheme``:

        Force the scheme; e.g., to ``'https'``

    ``host``:

        Force the host (including port!).  You must give something
        like ``foo.com:80``.  This will replace the ``HTTP_HOST``
        value, as well as ``SERVER_NAME`` and ``SERVER_PORT``.

    ``domain``:

        Force the domain (not including port).  If you give
        ``foo.com`` it will rewrite ``HTTP_HOST`` to be
        ``foo.com:{port}``, with whatever port was used for the actual
        request.  Usually ``host`` will be more useful.  Also
        ``SERVER_NAME`` will be set.

    ``port``:

        Force the port (not including domain).  If you give ``80`` it
        will set ``SERVER_PORT`` and the port portion of
        ``HTTP_HOST``.
    """

    def __init__(self, application,
                 secret_file=None,
                 trust_ips=None,
                 prefix=None,
                 pop_prefix=None,
                 scheme=None,
                 host=None,
                 domain=None,
                 port=None):
        self.application = application
        self.secret_file = secret_file
        if trust_ips is not None:
            if isinstance(trust_ips, basestring):
                trust_ips = [trust_ips]
            self.trust_ips = trust_ips
        else:
            self.trust_ips = None
        if prefix is not None:
            self.prefix = prefix.rstrip('/')
        else:
            self.prefix = None
        if pop_prefix is not None:
            assert self.prefix is None, (
                "You cannot give both prefix and pop_prefix values")
            self.pop_prefix = pop_prefix.rstrip('/')
        else:
            self.pop_prefix = None
        if scheme is not None:
            self.scheme = scheme.lower()
        else:
            self.scheme = None
        self.host = host
        if self.host is not None:
            assert ':' in self.host, (
                "The host argument must contain a port (use domain otherwise)")
            assert port is None, (
                "You cannot give both a port and host argument")
            assert domain is None, (
                "You cannot give both a domain and host argument")
        self.domain = domain
        if port is not None:
            self.port = str(port)
        else:
            self.port = None

    def __call__(self, environ, start_response):
        self._fixup_environ(environ)
        try:
            self._fixup_configured(environ)
        except httpexceptions.HTTPException, exc:
            return exc(environ, start_response)
        return self.application(environ, start_response)

    def _fixup_environ(self, environ):
        # @@: Obviously better errors here:
        if 'HTTP_X_WSGIPROXY_VERSION' in environ:
            version = environ.pop('HTTP_X_WSGIPROXY_VERSION')
            assert version == protocol_version
        secure = False
        if self.secret_file is not None:
            secret = get_secret(self.secret_file)
            # @@: Should catch error:
            check_request(environ, secret)
            secure = True
        if self.trust_ips:
            ip = environ.get('REMOTE_ADDR')
            if ip in trust_ips:
                # @@: Should allow ranges and whatnot:
                secure = True
        if 'HTTP_X_FORWARDED_SERVER' in environ:
            environ['HTTP_HOST'] = environ.pop('HTTP_X_FORWARDED_SERVER')
        if 'HTTP_X_FORWARDED_SCHEME' in environ:
            environ['wsgi.url_scheme'] = environ.pop('HTTP_X_FORWARDED_SCHEME')
        if 'HTTP_X_FORWARDED_FOR' in environ:
            environ['REMOTE_ADDR'] = environ.pop('HTTP_X_FORWARDED_FOR')
        script_name = environ.get('SCRIPT_NAME', '')
        path_info = environ.get('PATH_INFO', '')
        if 'HTTP_X_TRAVERSAL_PATH' in environ:
            traversal_path = environ['HTTP_X_TRAVERSAL_PATH'].rstrip('/')
            if traversal_path == path_info:
                path_info = ''
            elif not path_info.startswith(traversal_path+'/'):
                exc = httpexceptions.HTTPBadRequest(
                    "The header X-Traversal-Path gives the value %r but "
                    "the path is %r (it should start with "
                    "X-Traversal-Path)" % (traversal_path, path_info))
                return exc(environ, start_response)
            else:
                path_info = path_info[len(traversal_path):]
        if 'HTTP_X_SCRIPT_NAME' in environ:
            add_script_name = environ.pop('HTTP_X_SCRIPT_NAME').rstrip('/')
            if not add_script_name.startswith('/'):
                exc = httpexceptions.HTTPBadRequest(
                    "The header X-Script-Name gives %r which does not "
                    "start with /" % add_script_name)
                return exc(environ, start_response)
            script_name = add_script_name + script_name
        environ['SCRIPT_NAME'] = script_name
        environ['PATH_INFO'] = path_info
        for header, key in [
            ('HTTP_HOST', 'HTTP_HOST'),
            ('SCRIPT_NAME', 'SCRIPT_NAME'),
            ('PATH_INFO', 'PATH_INFO'),
            ('QUERY_STRING', 'QUERY_STRING'),
            ('WSGI_URL_SCHEME', 'wsgi.url_scheme')]:
            header = 'HTTP_X_WSGIPROXY_%s' % header
            if header in environ:
                environ[key] = environ.pop(header)
        for prefix, decoder, is_secure in [
            ('STR', self.str_decode, True),
            ('UNICODE', self.unicode_decode, True),
            ('JSON', self.json_decode, True),
            ('PICKLE', self.pickle_decode, False)]:
            expect = 'HTTP_X_WSGIPROXY_%s' % prefix
            for key in environ:
                if key.startswith(expect):
                    if not is_secure and not secure:
                        # Better error again!
                        assert 0
                    key_name, value = environ[key].split(None, 1)
                    key_name = urllib.unquote(key_name)
                    value = decoder(value)
                    environ[key_name] = value

    def _fixup_configured(self, environ):
        path_info = environ['PATH_INFO']
        script_name = environ['SCRIPT_NAME']
        if self.prefix is not None:
            environ['SCRIPT_NAME'] = self.prefix
        elif self.pop_prefix is not None:
            if self.pop_prefix == path_info:
                path_info = ''
                script_name = script_name + self.pop_prefix
            elif path_info.startswith(self.pop_prefix + '/'):
                path_info = path_info[len(self.pop_prefix):]
                script_name = script_name + self.pop_prefix
            else:
                exc = httpexception.HTTPBadRequest(
                    "It was expected that all requests would start with "
                    "the path %r, but I got a request with %r"
                    % (self.pop_prefix, path_info))
                raise exc
        if self.scheme is not None:
            environ['wsgi.url_scheme'] = self.scheme
        if self.host is not None:
            domain, port = self.host.split(':', 1)
            environ['HTTP_HOST'] = self.host
            environ['SERVER_NAME'] = domain
            environ['SERVER_PORT'] = port
        if self.port is not None:
            environ['SERVER_PORT'] = self.port
            if self.domain is None:
                host = environ['HTTP_HOST'].split(':', 1) + ':' + self.port
                environ['HTTP_HOST'] = host
        if self.domain is not None:
            host = self.domain + ':' + environ['SERVER_PORT']
            environ['HTTP_HOST'] = host
            environ['SERVER_NAME'] = self.domain

    def str_decode(self, value):
        if value.startswith('b64'):
            return value[3:].decode('base64')
        else:
            return value

    def unicode_decode(self, value):
        return self.str_decode(value).decode('utf8')

    def json_decode(self, value):
        return simplejson.loads(self.str_decode(value))

    def pickle_decode(self, value):
        return pickle.loads(self.str_decode(value))
    
