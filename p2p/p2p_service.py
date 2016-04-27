#!/usr/bin/python
#p2p_service.py
#
# <<<COPYRIGHT>>>
#
#
#
#

"""
.. module:: p2p_service

This serves requests from peers:

    * Data          - save packet to a file      (a commands.Data() packet)
    * Retrieve      - read packet from a file    (a commands.Data() packet)
    * ListFiles     - list files we have for customer
    * Delete        - delete a file
    * Identity      - contact or id server sending us a current identity
    * Ack           - response from remote peer after my request
    * Message       - a message from remote peer
    * Correspondent - request to be my correspondent

For listed customers we will save and retrieve data up to their specified limits.
BitDust tells us who our customers are and limits, we get their identities.
If a customer does not contact us for more than 30 hours (or something) then we can process
requests from that customers scrubbers.

Security:

    * Transport_control has checked that it is signed by a contact, 
      but we need to check that this is a customer.

    * Since we have control over suppliers, and may not change them much,
      it feels like customers are more of a risk.

    * Code treats suppliers and customers differently.  Fun that stores
      have customers come in the front door and suppliers in the back door.
    
    * But I don't see anything really worth doing.
      On Unix machines we could run customers in a chrooted environment.
      There would be a main code and any time it got a change
      in the list of customers, it could restart the customer code.
      The customer code could be kept very small this way.
      Again, I doubt it.  We only have XML and binary.
   
    * Real risk is probably the code for SSH, Email, Vetex, etc.
      Once it is a packet object, we are probably ok.

    * We will store in a file and be able to read it back when requested.
      Request comes as a packet and we just verify it signature to be sure about sender.

    * Resource limits.
      A ``local_tester`` checks that someone is not trying to use more than they are supposed to
      and we could also do it here

"""

import os
import sys
import cStringIO
import zlib

try:
    from twisted.internet import reactor
except:
    sys.exit('Error initializing twisted.internet.reactor in p2p_service.py')

#------------------------------------------------------------------------------ 

from logs import lg

from system import bpio

from userid import my_id
from contacts import contactsdb

from userid import identity

from contacts import identitycache

from p2p import commands

from lib import misc
from lib import packetid
from lib import nameurl

from crypt import signed

from main import settings

from transport import gateway
from transport import callback 

from services import driver

#------------------------------------------------------------------------------

def init():
    lg.out(4, 'p2p_service.init')
    callback.append_inbox_callback(inbox)

#------------------------------------------------------------------------------

def inbox(newpacket, info, status, error_message):
    """
    """
    if newpacket.CreatorID != my_id.getLocalID() and newpacket.RemoteID != my_id.getLocalID():
        # packet is NOT for us, skip  
        return False

    commandhandled = False
    if newpacket.Command == commands.Ack():
        # a response from remote node, typically handled in other places
        Ack(newpacket)   
        commandhandled = False 
    elif newpacket.Command == commands.Fail():
        # some operation was failed on other side
        Fail(newpacket) 
        commandhandled = False
    elif newpacket.Command == commands.Retrieve():
        # retrieve some packet customer stored with us
        Retrieve(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.RequestService():
        # other node send us a request to get some service
        RequestService(newpacket, info)
        commandhandled = True
    elif newpacket.Command == commands.CancelService():
        # other node wants to stop the service we gave him
        CancelService(newpacket, info) 
        commandhandled = True    
    elif newpacket.Command == commands.Data():
        # new packet to store for customer
        Data(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.ListFiles():
        # customer wants list of their files
        ListFiles(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.Files():
        # supplier sent us list of files
        Files(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.DeleteFile():
        # will Delete a customer file for them
        DeleteFile(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.DeleteBackup():
        # will Delete all files starting in a backup
        DeleteBackup(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.RequestIdentity():
        # contact asking for our current identity
        RequestIdentity(newpacket) 
        commandhandled = True
    elif newpacket.Command == commands.Message():
        # contact asking for our current identity
        if driver.is_started('service_private_messages'):
            from chat import message
            message.Message(newpacket) 
            commandhandled = True
    elif newpacket.Command == commands.Correspondent():
        # contact asking for our current identity
        Correspondent(newpacket) 
        commandhandled = True
    
    return commandhandled


def outbox(outpacket):
    lg.out(6, "p2p_service.outbox [%s] to %s" % (outpacket.Command, nameurl.GetName(outpacket.RemoteID)))
    return True

#------------------------------------------------------------------------------ 

def constructFilename(customerID, packetID):
    customerDirName = nameurl.UrlFilename(customerID)
    customersDir = settings.getCustomersFilesDir()
    if not os.path.exists(customersDir):
        bpio._dir_make(customersDir)
    ownerDir = os.path.join(customersDir, customerDirName)
    if not os.path.exists(ownerDir):
        bpio._dir_make(ownerDir)
    filename = os.path.join(ownerDir, packetID)
    return filename

def makeFilename(customerID, packetID):
    """
    Must be a customer, and then we make full path filename for where this packet is stored locally.
    """
    if not packetid.Valid(packetID): # SECURITY
        if packetID not in [settings.BackupInfoFileName(), 
                            settings.BackupInfoFileNameOld(), 
                            settings.BackupInfoEncryptedFileName(), 
                            settings.BackupIndexFileName() ]:
            # lg.out(1, "p2p_service.makeFilename ERROR failed packetID format: " + packetID )
            return ''
    if not contactsdb.is_customer(customerID):  # SECURITY
        lg.warn("%s is not a customer" % (customerID))
        return ''
    return constructFilename(customerID, packetID)

#------------------------------------------------------------------------------

def SendAck(packettoack, response='', wide=False, callbacks={}, packetid=None):
    result = signed.Packet(
        commands.Ack(), 
        my_id.getLocalID(), 
        my_id.getLocalID(), 
        packetid or packettoack.PacketID,
        response, 
        packettoack.OwnerID)
    lg.out(8, "p2p_service.SendAck %s to %s    response: %s ..." % (result.PacketID, result.RemoteID, str(response)[:15]))
    gateway.outbox(result, wide=wide, callbacks=callbacks)
    return result
    

def Ack(newpacket):
    lg.out(8, "p2p_service.Ack %s from [%s] : %s" % (newpacket.PacketID, newpacket.CreatorID, newpacket.Payload))
     
    
def SendFail(request, response='', remote_idurl=None):
    if remote_idurl is None:
        remote_idurl = request.OwnerID 
    result = signed.Packet(commands.Fail(), my_id.getLocalID(), my_id.getLocalID(), 
                                 request.PacketID, response, remote_idurl)
    lg.out(8, "p2p_service.SendFail %s to %s    response: %s ..." % (result.PacketID, result.RemoteID, str(response)[:15]))
    gateway.outbox(result)
    return result
    
    
def SendFailNoRequest(remoteID, packetID, response):
    result = signed.Packet(commands.Fail(), my_id.getLocalID(), my_id.getLocalID(), 
        packetID, response, remoteID)
    lg.out(8, "p2p_service.SendFailNoRequest %s to %s" % (result.PacketID, result.RemoteID))
    gateway.outbox(result)
    return result


def Fail(newpacket):
    lg.out(8, "p2p_service.Fail from [%s]: %s" % (newpacket.CreatorID, newpacket.Payload))
 
#------------------------------------------------------------------------------ 

def Identity(newpacket):
    """
    Contact or identity server is sending us a new copy of an identity for a contact of ours.
    Checks that identity is signed correctly.
    """
    newxml = newpacket.Payload
    newidentity = identity.identity(xmlsrc=newxml)
    # SECURITY - check that identity is signed correctly
    # if not newidentity.Valid():
    #     lg.out(1,"p2p_service.Identity ERROR has non-Valid identity")
    #     return
    idurl = newidentity.getIDURL()
    if not identitycache.UpdateAfterChecking(idurl, newxml):
        lg.out(1,"p2p_service.Identity ERROR has non-Valid identity")
        return False
    # if contacts.isKnown(idurl):
        # This checks that old public key matches new
    #     identitycache.UpdateAfterChecking(idurl, newxml)
    # else:
        # TODO
        # may be we need to make some temporary storage
        # for identities who we did not know yet
        # just to be able to receive packets from them
    #     identitycache.UpdateAfterChecking(idurl, newxml)
    # Now that we have ID we can check packet
    if not newpacket.Valid():
        # If not valid do nothing
        lg.warn("not Valid packet from %s" % idurl)
        # TODO: send Fail ?
        return False
    if newpacket.OwnerID == idurl:
        # wide=True : a small trick to respond to all contacts if we receive pings  
        SendAck(newpacket, wide=True)
        lg.out(8, "p2p_service.Identity from [%s], sent wide Acks" % nameurl.GetName(idurl))
    else:
        lg.out(8, "p2p_service.Identity from [%s]" % nameurl.GetName(idurl))
    return True


def RequestIdentity(request):
    """
    Someone is requesting a copy of our current identity.
    Already verified that they are a contact.
    Can also be used as a sort of "ping" test to make sure we are alive.
    """
    lg.out(6, "p2p_service.RequestIdentity starting")
    MyID = my_id.getLocalID()
    RemoteID = request.OwnerID
    PacketID = request.PacketID
    identitystr = my_id.getLocalIdentity().serialize()
    lg.out(8, "p2p_service.RequestIdentity returning ")
    result = signed.Packet(commands.Identity(), MyID, MyID, PacketID, identitystr, RemoteID)
    gateway.outbox(result, False)
       
def SendIdentity(remote_idurl, wide=False, callbacks={}):
    """
    """
    lg.out(8, "p2p_service.SendIdentity to %s" % nameurl.GetName(remote_idurl))
    result = signed.Packet(
        commands.Identity(), my_id.getLocalID(), 
        my_id.getLocalID(), 'identity', 
        my_id.getLocalIdentity().serialize(), remote_idurl)
    gateway.outbox(result, wide=wide, callbacks=callbacks)
    return result       
    
#------------------------------------------------------------------------------ 

def RequestService(request, info):
    words = request.Payload.split(' ')
    if len(words) < 1:
        lg.warn("got wrong payload in %s" % request)
        return SendFail(request, 'wrong payload')
    service_name = words[0]
    lg.out(8, "p2p_service.RequestService %s : %s" % (request.OwnerID, service_name))
    # TODO: - temporary keep that for backward compatibility
    if service_name == 'storage':
        if not driver.is_started('service_supplier'):
            return SendFail(request, 'supplier service is off')
        return driver.request('service_supplier', request, info)
    if not driver.is_exist(service_name):
        lg.warn("got wrong payload in %s" % request)
        return SendFail(request, 'service %s not exist' % service_name)
    if not driver.is_started(service_name):
        return SendFail(request, 'service %s is off' % service_name)
    return driver.request(service_name, request, info)
    
def SendRequestService(remote_idurl, service_info, wide=False, callbacks={}):
    lg.out(8, "p2p_service.SendRequestService to %s [%s]" % (
        nameurl.GetName(remote_idurl), service_info.replace('\n',' ')[:20]))
    result = signed.Packet(
        commands.RequestService(), 
        my_id.getLocalID(), 
        my_id.getLocalID(), 
        packetid.UniqueID(),
        service_info,
        remote_idurl)
    gateway.outbox(result, wide=wide, callbacks=callbacks)
    return result       

def CancelService(request, info):
    lg.out(8, "p2p_service.CancelService")
    words = request.Payload.split(' ')
    if len(words) <= 1:
        lg.warn("got wrong payload in %s" % request)
        return SendFail(request, 'wrong payload')
    service_name = words[0]
    # TODO: - temporary keep that for backward compatibility
    if service_name == 'storage':
        if not driver.is_started('service_supplier'):
            return SendFail(request, 'supplier service is off')
        return driver.cancel('service_supplier', request, info)
    if not driver.is_exist(service_name):
        lg.warn("got wrong payload in %s" % request)
        return SendFail(request, 'service %s not exist' % service_name)
    if not driver.is_started(service_name):
        return SendFail(request, 'service %s is off' % service_name)
    return driver.cancel(service_name, request, info)

def SendCancelService(remote_idurl, service_info, callbacks={}):
    lg.out(8, "p2p_service.SendCancelService [%s]" % service_info)
    result = signed.Packet(commands.CancelService(), my_id.getLocalID(), my_id.getLocalID(), 
                                  packetid.UniqueID(), service_info, remote_idurl)
    gateway.outbox(result, callbacks=callbacks)
    return result   

#------------------------------------------------------------------------------ 

def ListFiles(request):
    """
    We will want to use this to see what needs to be resent, 
    and expect normal case is very few missing.
    This is to build the ``Files()`` we are holding for a customer.
    """
    if not driver.is_started('service_supplier'):
        return SendFail(request, 'supplier service is off')
    MyID = my_id.getLocalID()
    RemoteID = request.OwnerID
    PacketID = request.PacketID
    Payload = request.Payload
    lg.out(8, "p2p_service.ListFiles from [%s], format is %s" % (nameurl.GetName(request.OwnerID), Payload))
    custdir = settings.getCustomersFilesDir()
    ownerdir = os.path.join(custdir, nameurl.UrlFilename(request.OwnerID))
    if not os.path.isdir(ownerdir):
        lg.out(8, "p2p_service.ListFiles did not find customer dir " + ownerdir)
        src = PackListFiles('', Payload)
        result = signed.Packet(commands.Files(), MyID, MyID, PacketID, src, RemoteID)
        gateway.outbox(result)
        return result
    plaintext = TreeSummary(ownerdir)
    lg.out(14, '\n%s' % (plaintext))
    src = PackListFiles(plaintext, Payload)
    result = signed.Packet(commands.Files(), MyID, MyID, PacketID, src, RemoteID)
    gateway.outbox(result)
    return result       


def Files(newpacket):
    """
    A directory list came in from some supplier.
    """
    lg.out(8, "p2p_service.Files from [%s]" % nameurl.GetName(newpacket.OwnerID))
    from storage import backup_control
    backup_control.IncomingSupplierListFiles(newpacket)
   
#------------------------------------------------------------------------------ 

def Data(request):
    """
    This is when we 
        1) save my requested data to restore the backup 
        2) or save the customer file on our local HDD
    """
    # 1. this is our Data! 
    if request.OwnerID == my_id.getLocalID():
        lg.out(8, "p2p_service.Data %r for us from %s" % (
            request, nameurl.GetName(request.RemoteID)))
        if driver.is_started('service_backups'):
            if request.PacketID in [ settings.BackupIndexFileName(), ]:
                from storage import backup_control
                backup_control.IncomingSupplierBackupIndex(request)
#        if driver.is_started('service_proxy_server'):
#            # 3. we work as a proxy server and received a packet for third node
#            if request.PacketID == 'routed_packet':
#                from transport.proxy import proxy_router
#                proxy_router.A('routed-inbox-packet-received', request) 
        return
    # 2. this Data is not belong to us
    if not driver.is_started('service_supplier'):
        return SendFail(request, 'supplier service is off')
    if not contactsdb.is_customer(request.OwnerID):  # SECURITY
        lg.warn("%s not a customer, packetID=%s" % (request.OwnerID, request.PacketID))
        SendFail(request, 'not a customer')
        return
    filename = makeFilename(request.OwnerID, request.PacketID)
    if filename == "":
        lg.warn("got empty filename, bad customer or wrong packetID? ")
        SendFail(request, 'empty filename')
        return
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        try:
            bpio._dirs_make(dirname)
        except:
            lg.out(2, "p2p_service.Data ERROR can not create sub dir " + dirname)
            SendFail(request, 'write error')
            return 
    data = request.Serialize()
    donated_bytes = settings.getDonatedBytes()
    if not os.path.isfile(settings.CustomersSpaceFile()):
        bpio._write_dict(settings.CustomersSpaceFile(), {'free': donated_bytes})
        lg.out(6, 'p2p_service.Data created a new space file')
    space_dict = bpio._read_dict(settings.CustomersSpaceFile())
    if request.OwnerID not in space_dict.keys():
        lg.warn("no info about donated space for %s" % request.OwnerID)
        SendFail(request, 'no info about donated space')
        return
    used_space_dict = bpio._read_dict(settings.CustomersUsedSpaceFile(), {})
    if request.OwnerID in used_space_dict.keys():
        try:
            bytes_used_by_customer = int(used_space_dict[request.OwnerID])
            bytes_donated_to_customer = int(space_dict[request.OwnerID])  
            if bytes_donated_to_customer - bytes_used_by_customer < len(data):
                lg.warn("no free space for %s" % request.OwnerID)
                SendFail(request, 'no free space')
                return
        except:
            lg.exc()
    if not bpio.WriteFile(filename, data):
        lg.out(2, "p2p_service.Data ERROR can not write to " + str(filename))
        SendFail(request, 'write error')
        return
    SendAck(request, str(len(request.Payload)))
    from supplier import local_tester
    reactor.callLater(0, local_tester.TestSpaceTime)
    del data
    lg.out(8, "p2p_service.Data saved from [%s/%s] to %s" % (
        nameurl.GetName(request.OwnerID), nameurl.GetName(request.CreatorID), filename,))


def SendData(raw_data, ownerID, creatorID, remoteID, packetID, callbacks={}):
    """
    """
    # TODO:
    newpacket = signed.Packet(
        commands.Data(), 
        ownerID, 
        creatorID, 
        packetID, 
        raw_data, 
        remoteID)
    result = gateway.outbox(newpacket, callbacks=callbacks)     
    return result


def Retrieve(request):
    """
    Customer is asking us for data he previously stored with us.
    We send with ``outboxNoAck()`` method because he will ask again if he does not get it
    """
    if not driver.is_started('service_supplier'):
        return SendFail(request, 'supplier service is off')
    if not contactsdb.is_customer(request.OwnerID):
        lg.warn("had unknown customer " + request.OwnerID)
        SendFail(request, 'not a customer')
        return
    filename = makeFilename(request.OwnerID, request.PacketID)
    if filename == '':
        lg.warn("had empty filename")
        SendFail(request, 'empty filename')
        return
    if not os.path.exists(filename):
        lg.warn("did not find requested packet " + filename)
        SendFail(request, 'did not find requested packet')
        return
    if not os.access(filename, os.R_OK):
        lg.warn("no read access to requested packet " + filename)
        SendFail(request, 'no read access to requested packet')
        return
    data = bpio.ReadBinaryFile(filename)
    if not data:
        lg.warn("empty data on disk " + filename)
        SendFail(request, 'empty data on disk')
        return
    outpacket = signed.Unserialize(data)
    del data 
    if outpacket is None:
        lg.warn("Unserialize fails, not Valid packet " + filename)
        SendFail(request, 'unserialize fails')
        return
    if not outpacket.Valid():
        lg.warn("unserialized packet is not Valid " + filename)
        SendFail(request, 'unserialized packet is not Valid')
        return
    lg.out(8, "p2p_service.Retrieve sending %r back to %s" % (outpacket, nameurl.GetName(outpacket.CreatorID)))
    gateway.outbox(outpacket)

#------------------------------------------------------------------------------ 

def DeleteFile(request):
    """
    Delete one ore multiple files or folders on my machine.
    """
    if not driver.is_started('service_supplier'):
        return SendFail(request, 'supplier service is off')
    if request.Payload == '':
        ids = [request.PacketID]
    else:
        ids = request.Payload.split('\n')
    filescount = 0
    dirscount = 0
    for pathID in ids:
        filename = makeFilename(request.OwnerID, pathID)
        if filename == "":
            filename = constructFilename(request.OwnerID, pathID)
            if not os.path.exists(filename):
                lg.warn("had unknown customer: %s or pathID is not correct or not exist: %s" % (nameurl.GetName(request.OwnerID), pathID))
                return SendFail(request, 'not a customer, or file not found')
        if os.path.isfile(filename):
            try:
                os.remove(filename)
                filescount += 1
            except:
                lg.exc()
        elif os.path.isdir(filename):
            try:
                bpio._dir_remove(filename)
                dirscount += 1
            except:
                lg.exc()
        else:
            lg.warn("path not found %s" % filename)
    lg.out(8, "p2p_service.DeleteFile from [%s] with %d IDs, %d files and %d folders were removed" % (
        nameurl.GetName(request.OwnerID), len(ids), filescount, dirscount))
    SendAck(request)
    

def SendDeleteFile(SupplierID, pathID):
    lg.out(8, "p2p_service.SendDeleteFile SupplierID=%s PathID=%s " % (SupplierID, pathID))
    MyID = my_id.getLocalID()
    PacketID = pathID
    RemoteID = SupplierID
    result = signed.Packet(commands.DeleteFile(),  MyID, MyID, PacketID, "", RemoteID)
    gateway.outbox(result)
    return result
    
    
def SendDeleteListPaths(SupplierID, ListPathIDs):
    lg.out(8, "p2p_service.SendDeleteListPaths SupplierID=%s PathIDs number: %d" % (SupplierID, len(ListPathIDs)))
    MyID = my_id.getLocalID()
    PacketID = packetid.UniqueID()
    RemoteID = SupplierID
    Payload = '\n'.join(ListPathIDs)
    result = signed.Packet(commands.DeleteFile(),  MyID, MyID, PacketID, Payload, RemoteID)
    gateway.outbox(result)
    return result

#------------------------------------------------------------------------------ 

def DeleteBackup(request):
    """
    Delete one or multiple backups on my machine.
    """
    if not driver.is_started('service_supplier'):
        return SendFail(request, 'supplier service is off')
    if request.Payload == '':
        ids = [request.PacketID]
    else:
        ids = request.Payload.split('\n')
    count = 0
    for backupID in ids:
        filename = makeFilename(request.OwnerID, backupID)
        if filename == "":
            filename = constructFilename(request.OwnerID, backupID)
            if not os.path.exists(filename):
                lg.warn("had unknown customer " + request.OwnerID + " or backupID " + backupID)
                return SendFail(request, 'not a customer, or file not found')
        if os.path.isdir(filename):
            try:
                bpio._dir_remove(filename)
                count += 1
            except:
                lg.exc()
        elif os.path.isfile(filename):
            try:
                os.remove(filename)
                count += 1
            except:
                lg.exc()
        else:
            lg.warn("path not found %s" % filename)
    SendAck(request)
    lg.out(8, "p2p_service.DeleteBackup from [%s] with %d IDs, %d were removed" % (nameurl.GetName(request.OwnerID), len(ids), count))


def SendDeleteBackup(SupplierID, BackupID):
    lg.out(8, "p2p_service.SendDeleteBackup SupplierID=%s  BackupID=%s " % (SupplierID, BackupID))
    MyID = my_id.getLocalID()
    PacketID = BackupID
    RemoteID = SupplierID
    result = signed.Packet(commands.DeleteBackup(),  MyID, MyID, PacketID, "", RemoteID)
    gateway.outbox(result)
    return result

def SendDeleteListBackups(SupplierID, ListBackupIDs):
    lg.out(8, "p2p_service.SendDeleteListBackups SupplierID=%s BackupIDs number: %d" % (SupplierID, len(ListBackupIDs)))
    MyID = my_id.getLocalID()
    PacketID = packetid.UniqueID()
    RemoteID = SupplierID
    Payload = '\n'.join(ListBackupIDs)
    result = signed.Packet(commands.DeleteBackup(),  MyID, MyID, PacketID, Payload, RemoteID)
    gateway.outbox(result)
    return result

#------------------------------------------------------------------------------ 

def Correspondent(request):
    lg.out(8, "p2p_service.Correspondent")
    MyID = my_id.getLocalID()
    RemoteID = request.OwnerID
    PacketID = request.PacketID
    Msg = misc.decode64(request.Payload)
    # TODO: need to connect users here

#------------------------------------------------------------------------------ 

def ListCustomerFiles(customer_idurl):
    filename = nameurl.UrlFilename(customer_idurl)
    customer_dir = os.path.join(settings.getCustomersFilesDir(), filename)
    result = cStringIO.StringIO()
    def cb(realpath, subpath, name):
        if os.path.isdir(realpath):
            result.write('D%s\n' % subpath)
        else:
            result.write('F%s\n' % subpath)
        return True
    bpio.traverse_dir_recursive(cb, customer_dir)
    src = result.getvalue()
    result.close()
    return src

def ListCustomerFiles1(customerNumber):
    """
    On the status form when clicking on a customer, 
    find out what files we're holding for that customer
    """
    idurl = contactsdb.customer(customerNumber)
    filename = nameurl.UrlFilename(idurl)
    customerDir = os.path.join(settings.getCustomersFilesDir(), filename)
    if os.path.exists(customerDir) and os.path.isdir(customerDir):
        backupFilesList = os.listdir(customerDir)
        if len(backupFilesList) > 0:
            return ListSummary(backupFilesList)
    return "No files stored for this customer"


def RequestListFilesAll():
    r = []
    for supi in range(contactsdb.num_suppliers()):
        r.append(RequestListFiles(supi))
    return r


def RequestListFiles(supplierNumORidurl):
    if not str(supplierNumORidurl).isdigit():
        RemoteID = supplierNumORidurl
    else:
        RemoteID = contactsdb.supplier(supplierNumORidurl)
    if not RemoteID:
        lg.warn("RemoteID is empty supplierNumORidurl=%s" % str(supplierNumORidurl))
        return None
    lg.out(8, "p2p_service.RequestListFiles [%s]" % nameurl.GetName(RemoteID))
    MyID = my_id.getLocalID()
    PacketID = packetid.UniqueID()
    Payload = settings.ListFilesFormat()
    result = signed.Packet(commands.ListFiles(), MyID, MyID, PacketID, Payload, RemoteID)
    gateway.outbox(result)
    return result

#------------------------------------------------------------------------------ 

def ListSummary(dirlist):
    """
    Take directory listing and make summary of format::
        BackupID-1-Data 1-1873 missing for 773,883,
        BackupID-1-Parity 1-1873 missing for 777,982,
    """
    BackupMax={}
    BackupAll={}
    result=""
    for filename in dirlist:
        if not packetid.Valid(filename):       # if not type we can summarize
            result += filename + "\n"            #    then just include filename
        else:
            BackupID, BlockNum, SupNum, DataOrParity = packetid.BidBnSnDp(filename)
            LocalID = BackupID + "-" + str(SupNum) + "-" + DataOrParity
            blocknum = int(BlockNum)
            BackupAll[(LocalID,blocknum)]=True
            if LocalID in BackupMax:
                if BackupMax[LocalID] < blocknum:
                    BackupMax[LocalID] = blocknum
            else:
                BackupMax[LocalID] = blocknum
    for BackupName in sorted(BackupMax.keys()):
        missing = []
        thismax = BackupMax[BackupName]
        for blocknum in range(0, thismax):
            if not (BackupName, blocknum) in BackupAll:
                missing.append(str(blocknum))
        result += BackupName + " from 0-" + str(thismax)
        if len(missing) > 0:
            result += ' missing '
            result += ','.join(missing)
#            for m in missing:
#                result += str(m) + ","
        result += "\n"
    return result

def TreeSummary(ownerdir):
    out = cStringIO.StringIO()
    def cb(result, realpath, subpath, name):
        if not os.access(realpath, os.R_OK):
            return False
        if os.path.isfile(realpath):
            try:
                filesz = os.path.getsize(realpath)
            except:
                filesz = -1
            result.write('F%s %d\n' % (subpath, filesz))
            return False
        if not packetid.IsCanonicalVersion(name):
            result.write('D%s\n' % subpath)
            return True
        maxBlock = -1
        versionSize = {}
        dataBlocks = {}
        parityBlocks = {}
        dataMissing = {}
        parityMissing = {}
        for filename in os.listdir(realpath):
            packetID = subpath + '/' + filename
            pth = os.path.join(realpath, filename)
            try:
                filesz = os.path.getsize(pth)
            except:
                filesz = -1
            if os.path.isdir(pth):
                result.write('D%s\n' % packetID)
                continue
            if not packetid.Valid(packetID):
                result.write('F%s %d\n' % (packetID, filesz))
                continue
            pathID, versionName, blockNum, supplierNum, dataORparity = packetid.SplitFull(packetID)
            if None in [pathID, versionName, blockNum, supplierNum, dataORparity]:
                result.write('F%s %d\n' % (packetID, filesz))
                continue
            if dataORparity != 'Data' and dataORparity != 'Parity':
                result.write('F%s %d\n' % (packetID, filesz))
                continue
            if maxBlock < blockNum:
                maxBlock = blockNum
            if not versionSize.has_key(supplierNum):
                versionSize[supplierNum] = 0
            if not dataBlocks.has_key(supplierNum):
                dataBlocks[supplierNum] = {}
            if not parityBlocks.has_key(supplierNum):
                parityBlocks[supplierNum] = {}
            if dataORparity == 'Data':
                dataBlocks[supplierNum][blockNum] = filesz
            elif dataORparity == 'Parity':
                parityBlocks[supplierNum][blockNum] = filesz
        for supplierNum in versionSize.keys():
            dataMissing[supplierNum] = set(range(maxBlock+1))
            parityMissing[supplierNum] = set(range(maxBlock+1))
            for blockNum in range(maxBlock+1):
                if blockNum in dataBlocks[supplierNum].keys():
                    versionSize[supplierNum] += dataBlocks[supplierNum][blockNum]
                    dataMissing[supplierNum].discard(blockNum)
                if blockNum in parityBlocks[supplierNum].keys():
                    versionSize[supplierNum] += parityBlocks[supplierNum][blockNum]
                    parityMissing[supplierNum].discard(blockNum)
        suppliers = set(dataBlocks.keys() + parityBlocks.keys())
        for supplierNum in suppliers:
            versionString = '%s %d 0-%d %d' % (
                subpath, supplierNum, maxBlock, versionSize[supplierNum])
            if len(dataMissing[supplierNum]) > 0 or len(parityMissing[supplierNum]) > 0:
                versionString += ' missing'
                if len(dataMissing[supplierNum]) > 0:
                    versionString += ' Data:' + (','.join(map(str, dataMissing[supplierNum])))
                if len(parityMissing[supplierNum]) > 0:
                    versionString += ' Parity:' + (','.join(map(str, parityMissing[supplierNum])))
            result.write('V%s\n' % versionString)
        del dataBlocks
        del parityBlocks
        del dataMissing
        del parityMissing
        return False
    bpio.traverse_dir_recursive(lambda realpath, subpath, name: cb(out, realpath, subpath, name), ownerdir)
    src = out.getvalue()
    out.close()
    return src

def PackListFiles(plaintext, method):
    if method == "Text":
        return plaintext 
    elif method == "Compressed":
        return zlib.compress(plaintext)
    return ''

def UnpackListFiles(payload, method): 
    if method == "Text":
        return payload
    elif method == "Compressed":
        return zlib.decompress(payload)
    return payload

#------------------------------------------------------------------------------ 

def RequestDeleteBackup(BackupID):
    """
    Need to send a "DeleteBackup" command to all suppliers.
    """
    lg.out(8, "p2p_service.RequestDeleteBackup with BackupID=" + str(BackupID))
    for supplier in contactsdb.suppliers():
        if not supplier:
            continue
        prevItems = [] # transport_control.SendQueueSearch(BackupID)
        found = False
        for workitem in prevItems:
            if workitem.remoteid == supplier:
                found = True
                break
        if found:
            continue
        SendDeleteBackup(supplier, BackupID)


def RequestDeleteListBackups(backupIDs):
    lg.out(8, "p2p_service.RequestDeleteListBackups wish to delete %d backups" % len(backupIDs))
    for supplier in contactsdb.suppliers():
        if not supplier:
            continue
        found = False
        # for workitem in transport_control.SendQueue():
        #     if workitem.command == commands.DeleteBackup() and workitem.remoteid == supplier:
        #         found = True
        #         break
        if found:
            continue
        SendDeleteListBackups(supplier, backupIDs)


def RequestDeleteListPaths(pathIDs):
    lg.out(8, "p2p_service.RequestDeleteListPaths wish to delete %d paths" % len(pathIDs))
    for supplier in contactsdb.suppliers():
        if not supplier:
            continue
        found = False
        # for workitem in transport_control.SendQueue():
        #     if workitem.command == commands.DeleteFile() and workitem.remoteid == supplier:
        #         found = True
        #         break
        if found:
            continue
        SendDeleteListPaths(supplier, pathIDs)


def CheckWholeBackup(BackupID):
    lg.out(8, "p2p_service.CheckWholeBackup with BackupID=" + BackupID)

#-------------------------------------------------------------------------------

def message2gui(proto, text):
    pass
#    statusline.setp(proto, text)


def getErrorString(error):
    try:
        return error.getErrorMessage()
    except:
        if error is None:
            return ''
        return str(error)


def getHostString(host):
    try:
        return str(host.host)+':'+str(host.port)
    except:
        if host is None:
            return ''
        return str(host)

if __name__ == '__main__':
    settings.init()

