#!/usr/bin/python
#restore.py
#
# Copyright (C) 2008-2016 Veselin Penev, http://bitdust.io
#
# This file (restore.py) is part of BitDust Software.
#
# BitDust is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BitDust Software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with BitDust Software.  If not, see <http://www.gnu.org/licenses/>.
#
# Please contact us if you have any questions at bitdust.io@gmail.com
#
#
#
#

"""
.. module:: restore

.. raw:: html

    <a href="http://bitdust.io/automats/restore/restore.png" target="_blank">
    <img src="http://bitdust.io/automats/restore/restore.png" style="max-width:100%;">
    </a>
    

At least for now we will work one block at a time, though packets in parallel.
We ask transport_control for all the data packets for a block then see if we
get them all or need to ask for some parity packets.  We do this till we have
gotten a block with the "LastBlock" flag set.  If we have tried several times
and not gotten data packets from a supplier we can flag him as suspect-bad
and start requesting a parity packet to cover him right away.

When we are missing a data packet we pick a parity packet where we have all the
other data packets for that parity so we can recover the missing data packet .
This network cost for this is just as low as if we read the data packet .
But most of the time we won't bother reading the parities.  Just uses up bandwidth.

We don't want to fire someone till
after we have finished a restore in case we have other problems and they might come
back to life and save us.  However, we might keep packets for a node we plan to fire.
This would make replacing them very easy.

At the "tar" level a user will have choice of full restore (to new empty system probably)
or to restore to another location on disk, or to just recover certain files.  However,
in this module we have to read block by block all of the blocks.


How do we restore if we lost everything?
Our ( public/private-key and eccmap) could be:

    1)  at BitDust  (encrypted with pass phrase)
    2)  on USB in safe or deposit box   (encrypted with passphrase or clear text)
    3)  with friends or scrubbers (encrypted with passphrase)
                
The other thing we need is the backupIDs which we can get from our suppliers with the ListFiles command.
The ID is something like ``F200801161206`` or ``I200801170401`` indicating full or incremental.


EVENTS:
    * :red:`block-restored`
    * :red:`init`
    * :red:`instant`
    * :red:`packet-came-in`
    * :red:`raid-done`
    * :red:`raid-failed`
    * :red:`request-done`
    * :red:`request-failed`
    * :red:`timer-01sec`
    * :red:`timer-1sec`
    * :red:`timer-5sec`
"""

import os
import sys
import time
import gc

try:
    from twisted.internet import reactor
except:
    sys.exit('Error initializing twisted.internet.reactor in restore.py')

from twisted.internet.defer import Deferred

#------------------------------------------------------------------------------ 

if __name__ == "__main__":
    import os.path as _p
    sys.path.append(_p.join(_p.dirname(_p.abspath(sys.argv[0])), '..'))

#------------------------------------------------------------------------------ 

from logs import lg

from system import bpio
from system import tmpfile

from main import settings
from main import events

from lib import packetid

from contacts import contactsdb
from userid import my_id

from automats import automat

from raid import raid_worker
from raid import eccmap

from crypt import encrypted

from p2p import contact_status

#------------------------------------------------------------------------------ 

class restore(automat.Automat):

    def set_packet_in_callback(self, cb):
        self.packetInCallback = cb

    def set_block_restored_callback(self, cb):
        self.blockRestoredCallback = cb

    def abort(self): 
        # for when user clicks the Abort restore button on the gui
        lg.out(4, "restore.Abort " + self.BackupID)
        self.AbortState = True

    timers = {
        'timer-1sec': (1.0, ['REQUEST']),
        'timer-01sec': (0.1, ['RUN']),
        'timer-5sec': (5.0, ['REQUEST']),
        }

    def __init__(self, BackupID, OutputFile): # OutputFileName 
        self.CreatorID = my_id.getLocalID()
        self.BackupID = BackupID
        self.PathID, self.Version = packetid.SplitBackupID(self.BackupID)
        self.File = OutputFile
        # is current active block - so when add 1 we get to first, which is 0
        self.BlockNumber = -1
        self.BytesWritten = 0          
        self.OnHandData = []
        self.OnHandParity = []
        self.AbortState = False
        self.Done = False
        self.EccMap = eccmap.Current()
        self.Started = time.time()
        self.LastAction = time.time()
        self.InboxPacketsQueue = []
        self.InboxQueueWorker = None
        self.RequestFails = []
        self.InboxQueueDelay = 1
        # For anyone who wants to know when we finish
        self.MyDeferred = Deferred()       
        self.packetInCallback = None
        self.blockRestoredCallback = None
        
        automat.Automat.__init__(self, 'restore_%s' % self.BackupID, 'AT_STARTUP', 4)
        events.info('restore', '%s start restoring' % self.BackupID)
        # lg.out(6, "restore.__init__ %s, ecc=%s" % (self.BackupID, str(self.EccMap)))

    def state_changed(self, oldstate, newstate, event_string, arg):
        if newstate == 'RUN':
            self.automat('instant')

    def A(self, event, arg):
        #---AT_STARTUP---
        if self.state == 'AT_STARTUP':
            if event == 'init' :
                self.state = 'RUN'
        #---RUN---
        elif self.state == 'RUN':
            if ( event == 'timer-01sec' or event == 'instant' ) and self.isAborted(arg) :
                self.state = 'ABORTED'
                self.doDeleteAllRequests(arg)
                self.doCloseFile(arg)
                self.doReportAborted(arg)
                self.doDestroyMe(arg)
            elif ( event == 'timer-01sec' or event == 'instant' ) and not self.isAborted(arg) :
                self.state = 'REQUEST'
                self.doStartNewBlock(arg)
                self.doReadPacketsQueue(arg)
                self.doScanExistingPackets(arg)
                self.doRequestPackets(arg)
        #---REQUEST---
        elif self.state == 'REQUEST':
            if event == 'packet-came-in' and self.isPacketValid(arg) and self.isCurrentBlock(arg) :
                self.doSavePacket(arg)
            elif event == 'timer-1sec' and self.isAborted(arg) :
                self.state = 'ABORTED'
                self.doPausePacketsQueue(arg)
                self.doDeleteAllRequests(arg)
                self.doCloseFile(arg)
                self.doReportAborted(arg)
                self.doDestroyMe(arg)
            elif ( event == 'timer-1sec' or event == 'request-done' ) and not self.isAborted(arg) and self.isBlockFixable(arg) :
                self.state = 'RAID'
                self.doPausePacketsQueue(arg)
                self.doReadRaid(arg)
            elif event == 'timer-5sec' and not self.isAborted(arg) and self.isTimePassed(arg) :
                self.doScanExistingPackets(arg)
                self.doRequestPackets(arg)
            elif event == 'request-failed' and not self.isStillCorrectable(arg) :
                self.state = 'FAILED'
                self.doDeleteAllRequests(arg)
                self.doRemoveTempFile(arg)
                self.doCloseFile(arg)
                self.doReportFailed(arg)
                self.doDestroyMe(arg)
        #---RAID---
        elif self.state == 'RAID':
            if event == 'raid-done' :
                self.state = 'BLOCK'
                self.doRestoreBlock(arg)
            elif event == 'raid-failed' :
                self.state = 'FAILED'
                self.doDeleteAllRequests(arg)
                self.doRemoveTempFile(arg)
                self.doCloseFile(arg)
                self.doReportFailed(arg)
                self.doDestroyMe(arg)
        #---BLOCK---
        elif self.state == 'BLOCK':
            if event == 'block-restored' and self.isBlockValid(arg) and not self.isLastBlock(arg) :
                self.state = 'RUN'
                self.doWriteRestoredData(arg)
                self.doDeleteBlockRequests(arg)
                self.doRemoveTempFile(arg)
            elif event == 'block-restored' and self.isBlockValid(arg) and self.isLastBlock(arg) :
                self.state = 'DONE'
                self.doWriteRestoredData(arg)
                self.doDeleteAllRequests(arg)
                self.doRemoveTempFile(arg)
                self.doCloseFile(arg)
                self.doReportDone(arg)
                self.doDestroyMe(arg)
            elif event == 'block-restored' and not self.isBlockValid(arg) :
                self.state = 'FAILED'
                self.doDeleteAllRequests(arg)
                self.doRemoveTempFile(arg)
                self.doCloseFile(arg)
                self.doReportFailed(arg)
                self.doDestroyMe(arg)
        #---ABORTED---
        elif self.state == 'ABORTED':
            pass
        #---FAILED---
        elif self.state == 'FAILED':
            pass
        #---DONE---
        elif self.state == 'DONE':
            pass
        return None

    def isAborted(self, arg):
        return self.AbortState

    def isTimePassed(self, arg):
        return time.time() - self.LastAction > 60
    
    def isPacketValid(self, NewPacket):
        if not NewPacket.Valid():
            return False
        if NewPacket.DataOrParity() not in ['Data', 'Parity']:
            return False
        return True
    
    def isCurrentBlock(self, NewPacket):
        return NewPacket.BlockNumber() == self.BlockNumber
    
    def isBlockFixable(self, arg):
        return self.EccMap.Fixable(self.OnHandData, self.OnHandParity)
    
    def isStillCorrectable(self, arg):
        return len(self.RequestFails) <= eccmap.GetCorrectableErrors(self.EccMap.NumSuppliers())
    
    def isBlockValid(self, arg):
        NewBlock = arg[0]
        if NewBlock is None:
            return False
        return NewBlock.Valid()
    
    def isLastBlock(self, arg):
        NewBlock = arg[0]
        return NewBlock.LastBlock
    
    def doStartNewBlock(self, arg):
        self.LastAction = time.time()
        self.BlockNumber += 1    
        lg.out(6, "restore.doStartNewBlock " + str(self.BlockNumber))
        self.OnHandData = [False] * self.EccMap.datasegments
        self.OnHandParity = [False] * self.EccMap.paritysegments
        self.RequestFails = []

    def doScanExistingPackets(self, arg):
        for SupplierNumber in range(self.EccMap.datasegments):
            PacketID = packetid.MakePacketID(self.BackupID, self.BlockNumber, SupplierNumber, 'Data')
            self.OnHandData[SupplierNumber] = os.path.exists(os.path.join(settings.getLocalBackupsDir(), PacketID))
        for SupplierNumber in range(self.EccMap.paritysegments):
            PacketID = packetid.MakePacketID(self.BackupID, self.BlockNumber, SupplierNumber, 'Parity')
            self.OnHandParity[SupplierNumber] = os.path.exists(os.path.join(settings.getLocalBackupsDir(), PacketID))
        
    def doRequestPackets(self, arg):
        from customer import io_throttle
        packetsToRequest = []
        for SupplierNumber in range(self.EccMap.datasegments):
            SupplierID = contactsdb.supplier(SupplierNumber) 
            if not SupplierID:
                continue
            if not self.OnHandData[SupplierNumber] and contact_status.isOnline(SupplierID):
                packetsToRequest.append((SupplierID, packetid.MakePacketID(self.BackupID, self.BlockNumber, SupplierNumber, 'Data')))
        for SupplierNumber in range(self.EccMap.paritysegments):
            SupplierID = contactsdb.supplier(SupplierNumber) 
            if not SupplierID:
                continue
            if not self.OnHandParity[SupplierNumber] and contact_status.isOnline(SupplierID):
                packetsToRequest.append((SupplierID, packetid.MakePacketID(self.BackupID, self.BlockNumber, SupplierNumber, 'Parity')))
        for SupplierID, packetID in packetsToRequest:
            io_throttle.QueueRequestFile(
                self._packet_came_in, 
                self.CreatorID, 
                packetID, 
                self.CreatorID, 
                SupplierID)
        lg.out(6, "restore.doRequestPackets requested %d packets for block %d" % (len(packetsToRequest), self.BlockNumber))
        del packetsToRequest
        self.automat('request-done')
    
    def doReadRaid(self, arg):
        fd, filename = tmpfile.make('restore', 
            prefix=self.BackupID.replace('/','_')+'_'+str(self.BlockNumber)+'_')
        os.close(fd)
        task_params = (filename, eccmap.CurrentName(), self.Version, self.BlockNumber, 
            os.path.join(settings.getLocalBackupsDir(), self.PathID))
        raid_worker.add_task('read', task_params,            
            lambda cmd, params, result: self._blockRestoreResult(result, filename))
         
    def doReadPacketsQueue(self, arg):
        reactor.callLater(0, self._process_inbox_queue)
    
    def doPausePacketsQueue(self, arg):
        if self.InboxQueueWorker is not None:
            if self.InboxQueueWorker.active():
                self.InboxQueueWorker.cancel()
            self.InboxQueueWorker = None
    
    def doSavePacket(self, NewPacket):
        packetID = NewPacket.PacketID
        pathID, version, packetBlockNum, SupplierNumber, dataORparity = packetid.SplitFull(packetID)
        if dataORparity == 'Data':
            self.OnHandData[SupplierNumber] = True
        elif NewPacket.DataOrParity() == 'Parity':
            self.OnHandParity[SupplierNumber] = True
        filename = os.path.join(settings.getLocalBackupsDir(), packetID)
        dirpath = os.path.dirname(filename)
        if not os.path.exists(dirpath):
            try:
                bpio._dirs_make(dirpath)
            except:
                lg.exc()
        # either way the payload of packet is saved
        if not bpio.WriteFile(filename, NewPacket.Payload):
            lg.warn("unable to write to %s" % filename)
            return
        lg.out(6, "restore.doSavePacket %s saved" % packetID)
        if self.packetInCallback is not None:
            self.packetInCallback(self.BackupID, NewPacket)
    
    def doRestoreBlock(self, arg):
        filename = arg
        blockbits = bpio.ReadBinaryFile(filename)
        if not blockbits:
            self.automat('block-restored', (None, filename))
            return 
        splitindex = blockbits.index(":")
        lengthstring = blockbits[0:splitindex]
        try:
            datalength = int(lengthstring)                                  # real length before raidmake/ECC
            blockdata = blockbits[splitindex+1:splitindex+1+datalength]     # remove padding from raidmake/ECC
            newblock = encrypted.Unserialize(blockdata)                      # convert to object
        except:
            datalength = 0
            blockdata = ''
            newblock = None
        self.automat('block-restored', (newblock, filename))
    
    def doWriteRestoredData(self, arg):
        NewBlock = arg[0]
        data = NewBlock.Data()
        # Add to the file where all the data is going
        try:
            os.write(self.File, data)
            self.BytesWritten += len(data)
        except:
            lg.exc()
            #TODO Error handling...
            return
        if self.blockRestoredCallback is not None:
            self.blockRestoredCallback(self.BackupID, NewBlock)
    
    def doDeleteAllRequests(self, arg):
        from customer import io_throttle
        io_throttle.DeleteBackupRequests(self.BackupID)
                                         
    def doDeleteBlockRequests(self, arg):
        from customer import io_throttle
        io_throttle.DeleteBackupRequests(self.BackupID + "-" + str(self.BlockNumber))

    def doRemoveTempFile(self, arg):
        try:
            filename = arg[1]
        except:
            return 
        tmpfile.throw_out(filename, 'block restored')
        if settings.getBackupsKeepLocalCopies():
            return
        import backup_rebuilder
        import backup_matrix
        if not backup_rebuilder.ReadStoppedFlag():
            if backup_rebuilder.A().currentBackupID is not None:
                if backup_rebuilder.A().currentBackupID == self.BackupID:
                    lg.out(6, 'restore.doRemoveTempFile SKIP because rebuilding in process')
                    return
        count = 0
        for supplierNum in xrange(contactsdb.num_suppliers()):
            supplierIDURL = contactsdb.supplier(supplierNum)
            if not supplierIDURL:
                continue
            for dataORparity in ['Data', 'Parity']:
                packetID = packetid.MakePacketID(self.BackupID, self.BlockNumber, 
                                                 supplierNum, dataORparity)
                filename = os.path.join(settings.getLocalBackupsDir(), packetID)
                if os.path.isfile(filename):
                    try:
                        os.remove(filename)
                    except:
                        lg.exc()
                        continue
                    count += 1
        backup_matrix.LocalBlockReport(self.BackupID, self.BlockNumber, arg)
        lg.out(6, 'restore.doRemoveTempFile %d files were removed' % count)

    def doCloseFile(self, arg):
        os.close(self.File)
    
    def doReportAborted(self, arg):
        lg.out(6, "restore.doReportAborted " + self.BackupID)
        self.Done = True
        self.MyDeferred.callback(self.BackupID+' aborted')
        events.info('restore', '%s restoring were aborted' % self.BackupID)
    
    def doReportFailed(self, arg):
        lg.out(6, "restore.doReportFailed ERROR %s : the block does not look good" % str(arg))
        self.Done = True
        self.MyDeferred.errback(self.BackupID+' failed')
        events.notify('restore', '%s failed to restore block number %d' % (self.BackupID, self.BlockNumber))
    
    def doReportDone(self, arg):
        # lg.out(6, "restore.doReportDone - restore has finished. All is well that ends well !!!")
        self.Done = True
        self.MyDeferred.callback(self.BackupID+' done')
        events.info('restore', '%s restored successfully' % self.BackupID)
    
    def doDestroyMe(self, arg):
        if self.InboxQueueWorker is not None:
            if self.InboxQueueWorker.active():
                self.InboxQueueWorker.cancel()
            self.InboxQueueWorker = None
        self.OnHandData = None
        self.OnHandParity = None
        self.EccMap = None
        self.LastAction = None
        self.InboxPacketsQueue = None
        self.RequestFails = None
        self.MyDeferred = None
        self.File = None
        self.destroy()
        collected = gc.collect()
        # lg.out(6, 'restore.doDestroyMe collected %d objects' % collected)

    #------------------------------------------------------------------------------ 

    def _blockRestoreResult(self, restored_blocks, filename):
        if restored_blocks is None:
            self.automat('raid-failed', (None, filename))
        else:
            self.automat('raid-done', filename)

    def _packet_came_in(self, NewPacket, state):
        if state == 'received':
            self.InboxPacketsQueue.append(NewPacket)
        elif state == 'failed':
            self.RequestFails.append(NewPacket)
            self.automat('request-failed', NewPacket)

    def _process_inbox_queue(self):
        if len(self.InboxPacketsQueue) > 0:
            NewPacket = self.InboxPacketsQueue.pop(0)
            self.automat('packet-came-in', NewPacket)
        self.InboxQueueWorker = reactor.callLater(self.InboxQueueDelay, self._process_inbox_queue)
    
#------------------------------------------------------------------------------ 

def main():
    lg.set_debug_level(24)
    backupID = sys.argv[1]
    raid_worker.A('init')
    outfd, outfilename = tmpfile.make('restore', '.tar.gz', backupID.replace('/','_')+'_')
    r = restore(backupID, outfd)
    r.MyDeferred.addBoth(lambda x: reactor.stop())
    reactor.callLater(1, r.automat, 'init')
    reactor.run()
    
if __name__ == "__main__":
    main()
