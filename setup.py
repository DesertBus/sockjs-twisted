# When pip installs anything from packages, py_modules, or ext_modules that
# includes a twistd plugin (which are installed to twisted/plugins/),
# setuptools/distribute writes a Package.egg-info/top_level.txt that includes
# "twisted".  If you later uninstall Package with `pip uninstall Package`,
# pip <1.2 removes all of twisted/ instead of just Package's twistd plugins.
# See https://github.com/pypa/pip/issues/355 (now fixed)
#
# To work around this problem, we monkeypatch
# setuptools.command.egg_info.write_toplevel_names to not write the line
# "twisted".  This fixes the behavior of `pip uninstall Package`.  Note that
# even with this workaround, `pip uninstall Package` still correctly uninstalls
# Package's twistd plugins from twisted/plugins/, since pip also uses
# Package.egg-info/installed-files.txt to determine what to uninstall,
# and the paths to the plugin files are indeed listed in installed-files.txt.
from distutils import log
from setuptools import setup
from setuptools.command.install import install


class InstallTwistedPlugin(install, object):
    def run(self):
        super(InstallTwistedPlugin, self).run()

        # Make Twisted regenerate the dropin.cache, if possible.  This is necessary
        # because in a site-wide install, dropin.cache cannot be rewritten by
        # normal users.
        log.info("Attempting to update Twisted plugin cache.")
        try:
            from twisted.plugin import IPlugin, getPlugins
            list(getPlugins(IPlugin))
            log.info("Twisted plugin cache updated successfully.")
        except Exception, e:
            log.warn("*** Failed to update Twisted plugin cache. ***")
            log.warn(str(e))


try:
    from setuptools.command import egg_info
    egg_info.write_toplevel_names
except (ImportError, AttributeError):
    pass
else:
    def _top_level_package(name):
        return name.split('.', 1)[0]

    def _hacked_write_toplevel_names(cmd, basename, filename):
        pkgs = dict.fromkeys(
            [_top_level_package(k)
                for k in cmd.distribution.iter_distribution_names()
                if _top_level_package(k) != "twisted"
            ]
        )
        cmd.write_file("top-level names", filename, '\n'.join(pkgs) + '\n')

    egg_info.write_toplevel_names = _hacked_write_toplevel_names

# Now actually define the setup
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
    packages=["txsockjs","txsockjs.protocols","twisted.plugins"],
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
    cmdclass = {
        'install': InstallTwistedPlugin,
    },
)
