"""
WSGI application that dispatches all requests to a subprocess.

The subprocess is managed by this process, started on demand (at the
time of the first request) and closed when this process is closed.

See SpawningApplication for more.
"""

import threading
import time
import weakref
import atexit
from wsgiproxy.exactproxy import proxy_exact_request
import logging

__all__ = ['SpawningApplication']

spawn_inited = False
spawn_init_lock = threading.Lock()
def init_spawn():
    _turn_sigterm_into_systemexit()
    atexit.register(_close_subprocesses)

apps = []

class SpawningApplication(object):

    """
    A WSGI application that dispatches requests to a subprocess.

    The subprocess is started with ``start_script``.  This must start
    the subprocess *in the foreground*.  It should not start the
    subprocess with a shell script (unless you use ``exec``) as this
    creates an intermediate process.  The value may include
    ``__PORT__`` which will be substituted with the port that the
    application should start on.

    You can control how the subprocess starts with the ``cwd``
    argument (the current working directory for the subprocess) and
    ``script_env`` (the environment it is run in).

    If you give ``spawned_port`` that will be used; otherwise the
    server will look for a free port.

    If you give ``idle_shutdown`` then the subprocess will be shut
    down after that many seconds of idle (when there are no requests).
    It will be started up again on the next request.

    Note that the Host header will be preserved in the subrequest.
    REMOTE_ADDR is put in X-Forwarded-For, and the scheme is put into
    X-Forwarded-Scheme.  The entire original path is requested, but
    SCRIPT_NAME is put into X-Script-Name.
    """

    spawn_port_start = 10000

    def __init__(self, start_script, cwd=None, script_env=None, spawned_port=None,
                 idle_shutdown=None, logger=None):
        if not spawn_inited:
            spawn_init_lock.acquire()
            try:
                if not spawn_inited:
                    init_spawn()
            finally:
                spawn_init_lock.release()
        self.start_script = start_script
        self.cwd = cwd
        self.script_env = script_env
        self.spawned_port = spawned_port
        self.spawn_lock = threading.Lock()
        self.proc = None
        self.idle_shutdown = idle_shutdown
        self.idle_shutdown_thread = None
        self.idle_shutdown_event = None
        self.last_request = None
        if logger is None:
            logger = logging.getLogger('wsgifilter.spawn')
        if isinstance(logger, basestring):
            logger = logging.getLogger(logger)
        self.logger = logger
        apps.append(weakref.ref(self))

    def __call__(self, environ, start_response):
        if self.proc is None:
            self.spawn_lock.acquire()
            try:
                if self.proc is None:
                    self.spawn_subprocess()
            finally:
                self.spawn_lock.release()
        self.send_to_subprocess(environ, start_response)

    def send_to_subprocess(self, environ, start_response):
        ## FIXME: I should use the WSGIProxy proxying code, not
        ## another copy of it:
        environ['HTTP_X_SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '')
        environ['HTTP_X_FORWARDED_SCHEME'] = environ['wsgi.url_scheme']
        environ['HTTP_X_FORWARDED_FOR'] = environ['REMOTE_ADDR']
        environ['SERVER_NAME'] = '127.0.0.1'
        environ['SERVER_PORT'] = str(self.spawned_port)
        return proxy_exact_request(environ, start_response)

    def spawn_subprocess(self):
        self.logger.info('Spawning subprocess with %s' % self.start_script)
        script = self.start_script
        if self.spawned_port is None:
            self.allocate_port()
        script = script.replace('__PORT__', str(self.spawned_port))
        self.proc = subprocess.Popen(script, cwd=self.cwd,
                                env=self.script_env)
        self.logger.info('Started subprocess with PID %s' % self.proc.pid)
        if self.idle_shutdown:
            self.spawn_shutdown_monitor()
        time_open = time.time()
        self.wait_open()
        self.logger.debug('Waited %s seconds for server to start' % (time.time() - time_open))

    def spawn_shutdown_monitor(self):
        if self.idle_shutdown_thread is not None:
            return
        self.idle_shutdown_event = threading.Event()
        # We already have spawn_lock acquired
        t = threading.Thread(target=self.shutdown_monitor)
        t.setDaemon(True)
        self.idle_shutdown_thread = t
        t.start()

    def shutdown_monitor(self):
        while 1:
            now = time.time()
            if self.proc is None:
                return
            if self.last_request is None:
                wait_time = self.idle_shutdown
            elif now - self.last_request > self.idle_shutdown:
                # Should shut down the subprocess
                self.logger.info('Server idle for %s seconds; shutting down'
                                 % (now - self.last_request))
                self.shutdown_subprocess()
                return
            else:
                wait_time = self.idle_shutdown - (now - self.last_request)
            self.idle_shutdown_event.wait(wait_time)

    def shutdown_subprocess(self):
        self.spawn_lock.acquire()
        try:
            self.close()
            self.idle_shutdown_thread = None
        finally:
            self.spawn_lock.release()

    def find_port(self):
        """
        Finds a free port.
        """
        host = '127.0.0.1'
        port = self.spawn_port_start
        while 1:
            s = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind((host, port))
            except socket.error, e:
                port += 1
            else:
                s.close()
                self.logger.info('Found free port at %s' % port)
                return port

    def allocate_port(self):
        self.spawned_port = self.find_port()

    def wait_open(self):
        # servers don't start up *quite* right away, so we give it a
        # moment to be ready to accept connections
        while 1:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', self.fcgi_port))
            except socket.error, e:
                pass
            else:
                sock.close()
                return
            time.sleep(0.1)

    def close(self):
        if self.proc is not None:
            self.logger.info('Shutting down PID %s' % self.proc.pid)
            import signal
            try:
                os.kill(self.proc.pid, signal.SIGTERM)
            except (OSError, IOError):
                pass
            self.proc = None
            if self.idle_shutdown_event:
                # Trigger shutdown thread to stop:
                self.idle_shutdown_event.set()

    def __del__(self):
        self.close()

def _turn_sigterm_into_systemexit():
    """
    Attempts to turn a SIGTERM exception into a SystemExit exception.
    """
    try:
        import signal
    except ImportError:
        return
    def handle_term(signo, frame):
        raise SystemExit
    signal.signal(signal.SIGTERM, handle_term)

def _close_subprocesses():
    for app in apps:
        app = app()
        if app is None:
            continue
        app.close()
