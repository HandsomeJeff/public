BitDust
=============

BitDust is a peer to peer online backup utility.

This is a distributed network for backup data storage. Each participant of the network provides a portion of his hard drive for other users. In exchange, he is able to store his data on other peers.

The redundancy in backup makes it so if someone loses your data, you can rebuild what was lost and give it to someone else to hold. And all of this happens without you having to do a thing - the software keeps your data in safe.

All your data is encrypted before it leaves your computer with a private key your computer generates. No one else can read your data, even BitDust Team! Recover data is only one way - download the necessary pieces from computers of other peers and decrypt them with your private key.

BitDust is written in Python using pure Twisted framework.

http://bitdust.io



Install
=======

Seems like in Ubuntu you just need to install all dependencies at first step:

    sudo apt-get install python python-twisted python-pyasn1 python-openssl python-crypto python-wxgtk2.8 python-imaging


Windows ussers can use links bellow and install packages by hands.

If you installed from sources using command "python setup.py install", can do it this way:
    
    python -c "from bitdust.bitdust import main; main()"

But I recomend to just download and extract sources in any place you want and just run the main script:

    cd bitdust
    python bitdust.py show


You will have to create a new "Identity" for you to be able to communicate with others,
program will ask you to do that during first start. 
If you run on a system without graphical interface you need to register from command line by hands:

    python bitdust.py register <your_nickname>


I recommend you to create another copy of your Private Key in a safe place to be able to recover your data in the future.
You can do it from GUI or type a command:

python bitdust.py key copy <filename>


Your settings and local files placed in the folder ~/.bitdust.
Type this to read more info:

python bitdust.py help



Dependencies
============

python 2.6 or 2.7, python3 is not supported
    http://python.org/download/releases
    
twisted 11.0 or higher: 
    http://twistedmatrix.com
    
pyasn1: 
    http://pyasn1.sourceforge.net
    
pyOpenSSL: 
    https://launchpad.net/pyopenssl
    
pycrypto: 
    https://www.dlitz.net/software/pycrypto/
    
PIL: 
    http://www.pythonware.com/products/pil
    
wxgtk2.8: 
    http://wiki.wxpython.org/InstallingOnUbuntuOrDebian

