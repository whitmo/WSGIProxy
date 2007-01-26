from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='WSGIProxy',
      version=version,
      description="HTTP proxying tools for WSGI apps",
      long_description="""\
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

      [paste.filter_app_factory]
      main = wsgiproxy.wsgiapp:make_middleware
      """,
      )
      
