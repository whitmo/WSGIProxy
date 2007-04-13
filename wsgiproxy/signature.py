import hmac
import urllib
import time
import itertools
import hmac

counter = itertools.count()

def sign_request(environ, secret):
    """
    Add a X-WSGIProxy-Signature header to a request environment, based
    on the environment and an arbitrary number.
    """
    path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    path = urllib.quote(urllib)
    date = environ.get('HTTP_DATE')
    if not date:
        date = time.gmtime()
        date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', date)
        environ['HTTP_DATE'] = date
    host = environ.get('HTTP_HOST')
    if not host:
        host = environ.get('SERVER_NAME', '')+':'+environ.get('SERVER_PORT')
        environ['HTTP_HOST'] = host
    count = str(counter.next())
    msg = path + ' ' + date + ' ' + secret
    msg = hmac.new(count, msg)
    sig = '%s %s' % (count, msg.hexdigest())
    environ['HTTP_X_WSGIPROXY_SIGNATURE'] = sig

class BadSignature(ValueError):
    """
    Exception raised by check_request
    """

def check_request(environ, secret):
    """
    Checks the environments' signature.  If the signature is not
    correct, raises BadSignatureError.  Removes the signature from the
    request.
    """
    if 'HTTP_DATE' not in environ:
        raise BadSignature(
            "No Date header in request")
    if 'HTTP_X_WSGIPROXY_SIGNATURE' not in environ:
        raise BadSignature(
            "No X-WSGIProxy-Signature header in request")
    # @@: Need to check this isn't terribly old:
    date = environ['HTTP_DATE']
    path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    path = urllib.quote(path)
    host = environ['HTTP_HOST']
    sig = environ.pop('HTTP_X_WSGIPROXY_SIGNATURE')
    msg = path + ' ' + date + ' ' + secret
    count, sig = sig.split(None, 1)
    msg = hmac.new(count, msg)
    expect_sig = msg.hexdigest()
    if sig != expect_sig:
        raise BadSignatureError(
            "Bad signature (hash is not correct)")

    
