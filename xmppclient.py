import sleekxmpp
import logging

class XmppClient(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password, muc, nickname):
        super(XmppClient, self).__init__(jid, password)
        
        self.MUC = muc
        self.NICKNAME = nickname
        
        # logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
        self.register_plugin('xep_0045')
        
        self.add_event_handler('session_start', self.start)
        self.add_event_handler("on_message", self.message)

    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.plugin['xep_0045'].joinMUC(self.MUC, self.NICKNAME)

    def on_message(self, msg):
        print "RECEIVED %s" %(msg)
        
    def message(self, to, msg):
        return self.send_message(mto=to, mbody=msg, mtype="chat")
        
    def muc_message(self, to, msg):
        return self.send_message(mto=to, mbody=msg, mtype="groupchat")
