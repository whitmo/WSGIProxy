from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='WSGIProxy',
      version=version,
      description="HTTP proxying tools for WSGI apps",
      long_description="""\
WSGIProxy gives tools to proxy arbitrary(ish) WSGI requests to other
processes over HTTP.

This will encode the WSGI request CGI-style environmental variables
(which must be strings), plus a configurable set of other variables.
It also sends values like ``HTTP_HOST`` and ``wsgi.url_scheme`` which
are often obscured by the proxying process, as well as values like
``SCRIPT_NAME``.  On the receiving end, a WSGI middleware fixes up the
environment to represent the state of the original request.  This
makes HTTP more like FastCGI or SCGI, which naturally preserve these
values.
""",
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Paste",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
      ],
      keywords='wsgi paste http proxy',
      author='Ian Bicking',
      author_email='ianb@colorstudy.com',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'Paste',
      ],
      entry_points="""
      [paste.app_factory]
      main = wsgiproxy.wsgiapp:make_app
      real_proxy = wsgiproxy.wsgiapp:make_real_proxy

      [paste.filter_app_factory]
      main = wsgiproxy.wsgiapp:make_middleware
      """,
      )
      
