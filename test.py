#!/usr/bin/python

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from xmppclient import *

from time import sleep
import os
import uuid
import random
import ConfigParser

class Test:
    MAX_DELAY = 10
    
    def initialize(self):
        config = ConfigParser.RawConfigParser()
        config.read('config.ini')
        
        self.CONVERSE_JID = config.get('xmpp', 'converse_jid')
        self.CONVERSE_PASS = config.get('xmpp', 'converse_pass')
        self.BOT_JID = config.get('xmpp', 'bot_jid')
        self.BOT_PASS = config.get('xmpp', 'bot_pass')
        self.MUC = config.get('xmpp', 'muc_jid')
        self.CONVERSE_URL = config.get('xmpp', 'converse_url')

        os.system("sudo /opt/ejabberd-19.09.1/bin/ejabberdctl delete_old_mam_messages all 0")
        os.system("killall geckodriver")
        os.system("rm screenshots/*.png")
        os.system("rm geckodriver.log")
        os.system("ps aux|grep Xvfb|grep -v grep > /dev/null || Xvfb :10 -ac &")
        
        os.environ['DISPLAY'] = ':10'

    def connect(self):
        self.xmpp_client = XmppClient(self.BOT_JID, self.BOT_PASS, self.MUC, 'bot1')
        self.xmpp_client.connect()
        self.xmpp_client.process(block=False)

        self.driver = webdriver.Firefox()
        self.driver.set_window_size(1000,1500)
        
        self.driver.get(self.CONVERSE_URL)

        assert "Converse chat" in self.driver.title

        jid = self.driver.find_element_by_id("converse-login-jid")
        password = self.driver.find_element_by_id("converse-login-password")

        jid.send_keys(self.CONVERSE_JID)
        password.send_keys(self.CONVERSE_PASS)
        password.submit()

        status_element = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "xmpp-status"))
        )

        assert "I am online" == status_element.text

        # XXX: otherwise some kind of weird "cant click this" error, fix with proper wait
        print "We are online! Waiting 1 second before commencing"
        sleep(1)

    def cleanup(self):
        self.driver.save_screenshot("screenshots/end.png")

        self.xmpp_client.disconnect(wait=True)
        self.driver.close()

        self.start_nginx()
            
    def test_online(self, count = 1):
        delay = random.randint(0, self.MAX_DELAY)
        print "Testing %s online messages with disconnect delay %i.." %(count, delay)
        
        self.stop_nginx()
        sleep(delay)
        self.start_nginx()
        
        private_messages = []
        muc_messages = []
        
        # private
        for i in range(count):
            private_messages.append(self.sendPrivateMessage())
            
        self.checkPrivateMessages(private_messages)
            
        if self.check_duplicates(private_messages):
            print "  WARNING: duplicate private messages!"
        
        # muc     
        for i in range(count):
            muc_messages.append(self.sendMucMessage())
            
        self.checkMucMessages(muc_messages)
            
        if self.check_duplicates(muc_messages):
            print "  WARNING: duplicate muc messages!"
            
    def test_offline(self, count = 1):
        delay = random.randint(1, self.MAX_DELAY)
        print "Testing %s offline messages with disconnect delay %i.." %(count, delay)
        
        self.stop_nginx()
        sleep(delay / 2)
        
        private_messages = []
        muc_messages = []
        
        for i in range(count):
            private_messages.append(self.sendPrivateMessage())
            
        for i in range(count):
            muc_messages.append(self.sendMucMessage())
        
        sleep(delay / 2)
        self.start_nginx()
        
        # private
        self.checkPrivateMessages(private_messages)
            
        if self.check_duplicates(private_messages):
            print "  WARNING: duplicate private messages!"
        
        # muc   
        self.checkMucMessages(muc_messages)
        
        if self.check_duplicates(muc_messages):
            print "  WARNING: %s duplicate muc messages!" %(self.check_duplicates(muc_messages))
        
    def sendPrivateMessage(self):
        message = uuid.uuid4().hex
        self.xmpp_client.message(self.CONVERSE_JID, message)
        
        return message
        
    def sendMucMessage(self):
        message = uuid.uuid4().hex
        self.xmpp_client.muc_message(self.MUC, message)
        
        return message
    
    def checkMucMessages(self, messages):
        muc_handle = WebDriverWait(self.driver, 1, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//a[text()='testmuc']"))
        )
        muc_handle.click()
        
        for message in messages:
            self.checkMucMessage(message)
            
        self.driver.save_screenshot("screenshots/muc.png")
        
    def checkMucMessage(self, message):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[text()='%s']" %(message)))
            )
        except:
            raise Exception("MUC message %s was not received" %(message))
            
    def checkPrivateMessages(self, messages):
        user_handle = WebDriverWait(self.driver, 1, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'contact-name') and text()='bot1']/../.."))
        )
        user_handle.click()
        
        for message in messages:
            self.checkPrivateMessage(message)
            
        self.driver.save_screenshot("screenshots/private.png")
        
    def checkPrivateMessage(self, message):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[text()='%s']" %(message)))
            )
        except:
            raise Exception("Private message %s was not received" %(message))
             
    def check_duplicates(self, messages):
        duplicates = 0
        
        for message in messages:
            messages = self.driver.find_elements_by_xpath("//div[text()='%s']" %(message))
            
            if len(messages) > 1:
                duplicates = duplicates + 1
                
        return duplicates
        
    def stop_nginx(self):
        os.system("sudo nginx -s stop")
        
    def start_nginx(self):
        os.system("sudo service nginx start")
        
test = Test()
test.initialize()

try:
    test.connect()

    # run two iterations, each testing both "online messages" and "offline messages" with a message count of 15
    for i in range(2):
        test.test_online(15)
        test.test_offline(15)
finally:
    test.cleanup()
