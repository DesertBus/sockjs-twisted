from setuptools import setup
import txsockjs
import os

setup(
    author="Christopher Gamble",
    author_email="chris@chrisgamble.net",
    name="txsockjs",
    version=txsockjs.__version__,
    description="Twisted SockJS wrapper",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    url="http://github.com/Fugiman/sockjs-twisted",
    license='BSD License',
    platforms=['OS Independent'],
    packages=["txsockjs","txsockjs.protocols"],
    install_requires=[
        "Twisted",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet",
    ],
)