import simplejson
import cPickle as pickle
import urllib
import re
from wsgiproxy.signature import sign_request
from wsgiproxy import protocol_version
from wsgiproxy.secretloader import get_secret

def base64encode(value):
    return value.encode('base64').replace('\n', '')

class WSGIProxyApp(object):

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
        'SCRIPT_NAME': 'X_WSGIPROXY_BASE',
        'wsgi.url_scheme': 'X_FORWARDED_SCHEME',
        'REMOTE_ADDR': 'X_FORWARDED_FOR',
        }

    def __call__(self, environ, start_response):
        if self.secret_file is not None:
            secret = get_secret(self.secret_file)
            sign_request(environ)
        for key in environ.keys():
            if key.startswith('HTTP_X_WSGIPROXY'):
                # Conflicting header...
                del environ[key]
        for key, dest in self.header_map.items():
            environ['HTTP_%s' % dest] = environ[key]
        for prefix, encoder, keys in [
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

    safe_str_re = re.compile(r'^[^\x00-\x1f]*$')

    def str_encode(self, value):
        assert isinstance(value, str)
        if not safe_str_re.search(value) or value.startswith('b64'):
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
