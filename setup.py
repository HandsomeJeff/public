
from setuptools import setup
setup(**{'author': 'Veselin Penev',
 'author_email': 'bitdust.io@gmail.com',
 'classifiers': ['Development Status :: 3 - Alpha',
                 'Environment :: Console',
                 'Environment :: No Input/Output (Daemon)',
                 'Framework :: Twisted',
                 'Intended Audience :: Developers',
                 'Intended Audience :: End Users/Desktop',
                 'Intended Audience :: Information Technology',
                 'Intended Audience :: Science/Research',
                 'Intended Audience :: Telecommunications Industry',
                 'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
                 'Natural Language :: English',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 2 :: Only',
                 'Topic :: Communications :: Chat',
                 'Topic :: Internet :: WWW/HTTP',
                 'Topic :: Communications :: File Sharing',
                 'Topic :: Desktop Environment :: File Managers',
                 'Topic :: Internet :: File Transfer Protocol (FTP)',
                 'Topic :: Security :: Cryptography',
                 'Topic :: System :: Archiving :: Backup',
                 'Topic :: System :: Distributed Computing',
                 'Topic :: System :: Filesystems',
                 'Topic :: System :: System Shells',
                 'Topic :: Utilities'],
 'description': 'BitDust is a decentralized on-line storage network for safe, independent and private communications.',
 'include_package_data': True,
 'install_requires': ['pip',
                      'twisted',
                      'pyasn1',
                      'pycrypto',
                      'pyOpenSSL',
                      'pyparsing',
                      'appdirs',
                      'CodernityDB',
                      'cryptography',
                      'service_identity',
                      'psutil',
                      'enum34',
                      'ipaddress',
                      'cffi',
                      'pkgversion',
                      'django>=1.7'],
 'license': 'GNU Affero General Public License v3 or later (AGPLv3+)',
 'long_description': '# BitDust\n[bitdust.io](https://bitdust.io)\n\n\n## English\n* [Main web site](https://bitdust.io/toc.html)\n* [Public Git repository](https://dev.bitdust.io/docs/public/blob/master/README.md)\n* [Mirror in GitHub repository](https://github.com/bitdust-io/docs/blob/master/README.md)\n\n\n## Russian\n\n* [Main web site](https://ru.bitdust.io/toc.html)\n* [Mirror in Public Git repository](https://dev.bitdust.io/docs/public/blob/master/README.md)\n\n\n\n## About\n\n#### BitDust is a peer-to-peer online backup utility.\n\nThis is a distributed network for backup data storage. Each participant of the network provides a portion of his hard drive for other users. In exchange, he is able to store his data on other peers.\n\nThe redundancy in backup makes it so if someone loses your data, you can rebuild what was lost and give it to someone else to hold. And all of this happens without you having to do a thing - the software keeps your data in safe.\n\nAll your data is encrypted before it leaves your computer with a private key your computer generates. No one else can read your data, even BitDust Team! Recover data is only one way - download the necessary pieces from computers of other peers and decrypt them with your private key.\n\nBitDust is written in Python using pure Twisted framework and published under GNU AGPLv3.\n\n\n\n## Install BitDust\n\n\n### Get the software\n\nSeems like in Ubuntu (probably most other distros) you can install all dependencies in that way:\n\n        sudo apt-get install git python-dev python-setuptools python-pip python-virtualenv python-twisted python-django python-crypto python-pyasn1 python-psutil libffi-dev libssl-dev\n\n\nOptionally, you can also install [miniupnpc](http://miniupnp.tuxfamily.org/) tool if you want BitDust automatically deal with UPnPc configuration of your network router so it can also accept incoming connections from other nodes.:\n\n        sudo apt-get install miniupnpc\n\n\nSecond step is to get the BitDust sources:\n\n        git clone https://github.com/bitdust-io/public.git bitdust\n\n\nThen you need to build virtual environment with all required Python dependencies, BitDust software will run fully isolated.\nSingle command should make it for you, all required files will be generated in `~/.bitdust/venv/` sub-folder:\n\n        cd bitdust\n        python bitdust.py install\n\n\nLast step to make BitDust software ready is to make a short alias in your OS, then you can just type `bitdust` in command line to fast access the program:\n        \n        sudo ln -s /home/<user>/.bitdust/bitdust /usr/local/bin/bitdust\n        \n\n\n### Run BitDust\n\nStart using the software by creating an identity for your device in BitDust network:\n       \n        bitdust id create <some nick name>\n       \n\nI recommend you to create another copy of your Private Key in a safe place to be able to recover your data in the future. You can do it with such command:\n\n        bitdust key copy <nickname>.bitdust.key\n\n\nYour settings and local files are located in that folder: ~/.bitdust\n\nType this command to read more info about BitDust commands:\n\n        bitdust help\n\n\nTo run the software type:\n\n        bitdust\n        \n\nStart as background process:\n\n        bitdust detach\n\n\nTo get some more insights or just to know how to start playing with software\nyou can visit [BitDust Commands](https://bitdust.io/commands.html) page. \n\n\n## Dependencies\n\nIf you are installing BitDust on Windows platforms, you may require some binary packages already compiled and packaged for Microsoft Windows platforms, you can check following locations and download needed binaries and libraries:\n\n* cygwin: [cygwin.com](https://cygwin.com/install.html)\n* git: [git-scm.com](https://git-scm.com/download/win)\n* python 2.7 (python3 is not supported yet): [python.org](http://python.org/download/releases)\n* twisted 11.0 or higher: [twistedmatrix.com](http://twistedmatrix.com)\n* pyasn1: [pyasn1.sourceforge.net](http://pyasn1.sourceforge.net)\n* pyOpenSSL: [launchpad.net/pyopenssl](https://launchpad.net/pyopenssl)\n* pycrypto: [dlitz.net/software/pycrypto](https://www.dlitz.net/software/pycrypto/)\n* wxgtk2.8: [wxpython.org](http://wiki.wxpython.org/InstallingOnUbuntuOrDebian)\n* miniupnpc: [miniupnp.tuxfamily.org](http://miniupnp.tuxfamily.org/)\n\n',
 'name': 'bitdust',
 'packages': ['access',
              'automats',
              'broadcast',
              'chat',
              'coins',
              'contacts',
              'crypt',
              'currency',
              'customer',
              'dht',
              'interface',
              'lib',
              'logs',
              'main',
              'p2p',
              'parallelp',
              'raid',
              'services',
              'storage',
              'stun',
              'supplier',
              'system',
              'transport',
              'updates',
              'userid',
              'dht.entangled',
              'dht.entangled.kademlia',
              'lib.fastjsonrpc',
              'lib.txrestapi',
              'lib.txrestapi.txrestapi',
              'parallelp.pp',
              'transport.proxy',
              'transport.tcp',
              'transport.udp'],
 'tests_require': [],
 'url': 'https://github.com/bitdust-io/public.git',
 'version': '0.0.1',
 'zip_safe': False})
