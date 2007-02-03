import simplejson
import cPickle as pickle
import urllib
from wsgiproxy import protocol_version
from wsgiproxy.secretloader import get_secret

class WSGIProxyMiddleware(object):

    def __init__(self, application,
                 secret_file=None,
                 trust_ips=None):
        self.application = application
        self.trust_ips = trust_ips

    def __call__(self, environ, start_response):
        self._fixup_environ(environ)
        return self.application(environ, start_response)

    def _fixup_environ(self, environ):
        # @@: Obviously better errors here:
        version = environ.pop('HTTP_X_WSGIPROXY_VERSION')
        assert version == protocol_version:
        secure = False
        if self.secret_file is not None:
            secret = get_secret(self.secret_file)
            # @@: Should catch error:
            check_request(environ, secret)
            secure = True
        if self.trust_ips:
            ip = environ.get('REMOTE_ADDR')
            for trust_ip in trust_ips:
                # @@: Should allow ranges and whatnot:
                if ip == trust_ip:
                    secure = True
                    break
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
    
