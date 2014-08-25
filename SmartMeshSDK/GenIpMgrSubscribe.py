#============================ adjust path =====================================

import sys
import os
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..'))

#============================ imports =========================================

from   SmartMeshSDK import ApiException
from   SmartMeshSDK.ApiDefinition.IpMgrDefinition    import IpMgrDefinition

#============================ templates =======================================

TMPL = '''# Warning: Do NOT edit this file directly. Your changes may be overwritten. 
# This file is automatically generated by GenIpMgrSubscribe.py

import threading

from   SmartMeshSDK import ApiException

class IpMgrSubscribe(object):
    \'\'\'
    \\brief {BRIEF_DESCRIPTION}
    \'\'\'
    
    class SubscribeError(Exception) :
        def __init__(self, msg) :
            self.msg = msg
        def __str__(self):
            return self.msg
    
{CONST_NAME}
    _trNotifNameTable = {{
{EVENT_DICT}
    }}
    
    #======================== public ==========================================
    
    def __init__(self, ipMgrConnector) :
        # Structure of self._callback :
        #     Notification Name : 
        #         [0] - subscription mask mask, 
        #         [1] - cb-function. Notification is subscribed if [1]!=None, 
        #         [2] - transport for notification: True - reliable, false - unreliable
        self._callback = {{
{SUBSCRIBE_DICT}        
        }}
        self._con    = ipMgrConnector
        self._thread = None
        self._mask = self._unrlblMask = 0
        self._isStarted = False
        self._lock = threading.Lock()
        
    def start(self):
        \'\'\'
        \\brief Start the subscriber _thread.
        \'\'\'
        
        if self._thread :   # Wait finish disconnect process
            try :
                self._thread.join(1.0)
                if  self._thread.isAlive() :
                    raise ApiException.ConnectionError("Already connected")
            except RuntimeError :
                pass    # Ignore join error
            self._thread = None 
        
        # Clear _callback table
        for i in self._callback :
            self._callback[i][1] = None
            self._callback[i][2] = True
        self._mask = self._unrlblMask = 0
        self._thread = threading.Thread(target = self._process) 
        self._thread.name = "IpMgrSubscribe"
        self._thread.start()
        self._isStarted = True
        
    def subscribe(self, notifTypes, fun, isRlbl):
        \'\'\'
        \\brief Subscribe to notification(s).
        
        Calling this function multiple times will not cancel the effects of
        the previous calls.
        
        \pre Call start() before calling this function.
        
        \param notifTypes Type(s) of notification(s) to subscribe to. This can
            be a single string (when subscribing to a single notification), or
            a list of strings (when subscribing to multiple notifications).
            The list of possible types is:
{COMMENT_NOTIF_TYPE}
        \param fun The function to call when any of the notification types
            specified in the notifTypes parameter occurs. If you wish to assign
            a different _callback function to different notification types,
            call this function multiple times. The signature of the function
            needs to be fun(<notification name>, <notification parameter>),
            as described below.
        \param isRlbl define type of transport using for delivery 
             notification: reliable (True) or best effort (False)
        The _callback function is called with a notification name and a
        notification parameter. Depending on the type of notification, the
        parameter will be of a different format, according to the table below.
        
{COMMENT_FUN}
        
        \exception IpMgrSubscribe.SubscribeError The subscriber hasn't been
            started, or the notification type(s) specified is (are) not valid.
        \'\'\'
        
        if not self._isStarted :
            raise self.SubscribeError("Error: subscriber is not started")
        if isinstance(notifTypes, str) :
            notifTypes = [notifTypes]
        for nType in notifTypes :  # subscribe type validation
            if nType not in self._callback :
                raise self.SubscribeError("Error subscribe type: {{0}}".format(nType))
        
        self._lock.acquire()
        for nType in notifTypes :
            self._callback[nType][1] = fun
            self._callback[nType][2] = isRlbl
        self._lock.release()
        
        mask = unrlblMask = 0
        # Structure of self._callback.values() :
        #     [0] - subscription mask mask, 
        #     [1] - cb-function. Notification is subscribed if [1]!=None, 
        #     [2] - transport for notification: True - reliable, false - unreliable
        for cb in self._callback.values() :
            if cb[1] :
                mask = mask | cb[0]
            if cb[2] == False :
                unrlblMask = unrlblMask | cb[0] 
        if mask != self._mask or unrlblMask != self._unrlblMask :
            self._mask = mask
            self._unrlblMask = unrlblMask
            self._con.dn_subscribe([0,self._mask], [0,self._unrlblMask])

    #======================== private =========================================
    
    def _process(self):
        while True :
            try :
                notif = self._con.getNotification()
                name = notif[0]
                if name in self._trNotifNameTable :
                    name = self._trNotifNameTable[name]
                self._processOneNotif(name, notif[0], notif[1])
            except ApiException.QueueError:
                self._processOneNotif(self.FINISH, self.FINISH, '')
                self._isStarted = False
                break
            except Exception as ex :
                self._processOneNotif(self.ERROR, self.ERROR, ex)
    
    def _processOneNotif(self, notifType, notifName, payload):
        cb = self._getCallback(notifType)
        if cb : 
            cb(notifName, payload)
    
    def _getCallback(self, name) :
        res = None

        self._lock.acquire()
        if name in self._callback :
            res = self._callback[name][1]
        self._lock.release()
        
        return res
'''

#============================ main ============================================

NOTIFICATION_ID = 20
ERROR_NOTIF     = "error" 
FINISH_NOTIF    = "finish"
ALLNOTIF        = "ALLNOTIF"

_SPACE = ' ' * 80
def indent(pos, s):
    return ''.join([_SPACE[:pos], s])

def genFile(apiDefFileName, fileName, classComment):
    
    
    nameConst = ''
    eventDict = ''
    subscribeDict = ''
    commentNotifType = ''
    commentFun = ''
    notifList = []
    
    apiDefName  = os.path.splitext(os.path.basename(apiDefFileName))[0]
    apiDefClass = globals()[apiDefName]
    apiDef      = apiDefClass()
    notifName   = apiDef.idToName(apiDef.NOTIFICATION, NOTIFICATION_ID)
    notifSubNames = apiDef.getNames(apiDef.NOTIFICATION, [notifName])
    exNotifList = [ERROR_NOTIF, FINISH_NOTIF]  + notifSubNames 
    strListNameConst = []
    for subName in exNotifList:
        strListNameConst.append(indent(4, '{0:20s} = "{1}"\n'.format(subName.upper(), subName)))
        notifList.append(subName)
    strListNameConst.append(indent(4, '{0:20s} = [{1}]\n'.format(ALLNOTIF, ', '.join([n.upper() for n in notifSubNames])))) 
        
    # generate comments with list of notification types     
    commentNotifType = indent(12, ', '.join([n.upper() for n in exNotifList+[ALLNOTIF]])) + '\n'
    
    #Generate subscribe masks
    strList = []
    for subName in exNotifList :
        try :
            val = 1 << apiDef.getDefinition(apiDef.NOTIFICATION, [notifName, subName])['id']
        except ApiException.CommandError:
            val = 0 # Ignore error for two reserved 
        strList.append(indent(12, 'self.{0:17s} : [0x{1:02x}, None, True],\n'.format(subName.upper(), val)))
    subscribeDict = ''.join(strList)
    
    # Generate dictionary for sub-sub notification (events)
    strList = []
    for subNotif in apiDef.getNames(apiDef.NOTIFICATION, [notifName]) :
        try :
            subSubNames = apiDef.getNames(apiDef.NOTIFICATION, [notifName, subNotif])
            notifList.remove(subNotif)
            for name in subSubNames :
                notifList.append(name)
                strListNameConst.append(indent(4, '{0:20s} = "{1}"\n'.format(name.upper(), name)))
                strList.append(indent(4, '"{0}" : "{1}",\n'.format(name, subNotif))) 
        except Exception :
            pass
    nameConst  = ''.join(strListNameConst)
    eventDict  = ''.join(strList)
    
    strList = []
    strList.append(indent(8, '<table>\n'))
    strList.append(indent(12, '<tr><th>{0:20s}</th><th>{1}</th>\n'.format('Notification Name', 'Parameter')))
    for n in notifList :
        if n == ERROR_NOTIF :
            res = 'Exception'
        elif n == FINISH_NOTIF :
            res = "''"
        else :
            res = 'Tuple_' + n
        strList.append(indent(12, '<tr><td>{0:20s}</td><td>{1}</td>\n'.format(n.upper(), res)))
    strList.append(indent(8, '</table>'))
    commentFun  = ''.join(strList)
    
    s = TMPL.format(BRIEF_DESCRIPTION = classComment, 
                    CONST_NAME = nameConst,
                    EVENT_DICT = eventDict,
                    SUBSCRIBE_DICT = subscribeDict,
                    COMMENT_NOTIF_TYPE = commentNotifType,
                    COMMENT_FUN = commentFun)
    
    with open(fileName, "wt") as f :
        f.write(s)
    
def main():
    if len(sys.argv) < 3:
        print("Usage: GenIpMgrSubscribe <apiDefinitionFile> <resultFile> [<comment>]")
        sys.exit(1)
    
    comment = ''
    if len(sys.argv) > 3:
        comment = sys.argv[3]
    genFile(sys.argv[1], sys.argv[2], comment)
    
if __name__ == '__main__':
    main()

