#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from setuptools.command.install import install
import pkg_resources
from distutils import log
import os


class install_with_post(install):
    def run(self):
        install.run(self)

        cfg_filename = 'youpinitel-demo.json'
        src = pkg_resources.resource_filename('youpinitel', 'data/' + cfg_filename)
        dstdir = '/etc' if os.getuid() == 0 else os.path.expanduser('~/.youpinitel')

        if not os.path.exists(os.path.join(dstdir, cfg_filename)):
            log.info('Installing configuration file')
            if not os.path.exists(dstdir):
                os.mkdir(dstdir)
            self.copy_file(src, dstdir)
        else:
            log.info('Configuration file already installed: keeping it unchanged')

setup(
    name='pybot_youpinitel',
    version='1.0',
    description='Demonstration of a vintage arm controlled by a vintage Minitel',
    install_requires=['pybot-minitel', 'pybot-youpi'],
    license='LGPL',
    author='Eric Pascual',
    author_email='eric@pobot.org',
    url='http://www.pobot.org',
    packages=find_packages("src"),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'youpinitel-demo = youpinitel:entry_points.demo_main',
        ]
    },
    package_data={
        "youpinitel": [
            'data/*.json'
        ]
    },
    cmdclass={'install': install_with_post}
)
