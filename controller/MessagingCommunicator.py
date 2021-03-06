# -*- coding: utf-8 -*-
"""
Created on Mon Aug  1 15:23:28 2016

@author: Heiko
"""

from model.messages.DiscoverMessage import DiscoverMessage
from model.messages.ChatMessage import ChatMessage
from model.messages.BroadcastMessage import BroadcastMessage
from model.messages.QuitMessage import QuitMessage
from model.messages.NewBuddyMessage import NewBuddyMessage
from controller.MessageEncoder import MessageEncoder, asMessage

import socket
import threading
import sys
import json
    
    
class MessagingReceiver:
    
    def __init__(self, port, controller, nickname):
        self.port = port
        self.listenerStop = threading.Event()
        self.clientListenerStop = threading.Event()
        self.inputStop = threading.Event()
        
        self.controller = controller
        self.nickname = nickname
    
    def portListener(self):
        print("start listening on " + str(self.port))    
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', int(self.port)))
        sock.listen(10)
        
        threading.Thread(target = self.endListener, args = (sock,)).start()
    
        #own Thread for every connection
        while not self.listenerStop.is_set():
            try:
                connection, addr = sock.accept()
                threading.Thread(target = self.clientListener, args = (addr, connection)).start()
            except:
                print("Connection has been shutdown.")
                break
        print("listening stopped")
    
    def endListener(self, sock):
        self.listenerStop.wait()
        sock.close()


    def clientListener(self, addr, connection):    
        while not self.clientListenerStop.is_set():
            try:
                data = json.loads(connection.recv(1024).decode('utf-8'), object_hook=asMessage)
                #print("message received: " + data)
                if isinstance(data, QuitMessage):
                    self.controller.removeBuddy(data)
                    break
                elif isinstance(data, BroadcastMessage):
                    self.controller.newMessage("[" + data.timestamp + "]" + data.name + ": " + data.text)
                elif isinstance(data, ChatMessage):
                    self.controller.newMessage("[" + data.timestamp + "]" + data.name + ": " + data.text)
                elif isinstance(data, DiscoverMessage):
                    self.connect(data.addr, data.port, 1)
                elif isinstance(data, NewBuddyMessage):
                    self.controller.newBuddy(connection, data, addr[0])
            except:
                print("Unexpected error:", sys.exc_info()[0])
                #disconnect()
                #buddy_list[buddy_name].shutdown(socket.SHUT_RDWR)
                #buddy_list[buddy_name].close()
                #buddy_list.pop(buddy_name)
                #update()
                #newMessage(buddy_name + ' has disconnected.', "info")
                break
        print("Connection to" + str(addr) + " closed.\n")
    
    def connect(self, addr, port, new=0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        if sock.connect_ex((addr, int(port))) == 0:
            try:
                sock.send(json.dumps(NewBuddyMessage(self.nickname, self.port, new), cls=MessageEncoder).encode('utf-8'))
                data = json.loads(sock.recv(1024).decode('utf-8'), object_hook=asMessage)
                self.controller.addBuddy(data, sock)
            except:
                print("Unexpected error while connecting:", sys.exc_info()[0])
                pass
    
    def discoverThread(self, addr):
        listener = threading.Thread(target = self.portListener, args = ())
        listener.start()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        port = 50000
        while port <= 50005:
            if port != int(self.port) and sock.connect_ex((addr, port)) == 0:
                try:
                    sock.send(json.dumps(NewBuddyMessage(self.nickname, self.port, 2), cls=MessageEncoder).encode('utf-8'))
                    data = json.loads(sock.recv(1024).decode('utf-8'), object_hook=asMessage)
                    self.controller.addBuddy(data, sock)
                    break
                except:
                    print("Unexpected error while discovery:", sys.exc_info()[0])
                    pass
            port += 1
        if port == 50006:
            self.controller.newMessage("No buddy is online.", "info")
        else:
            print('You have connected to ' + addr + ':' + str(port) + '.', "info")
    
    def discover(self, addr):
        self.controller.newMessage("Searching for buddys . . .", "info")
        #print("Searching for buddys . . .", "info")
        threading.Thread(target = self.discoverThread, args = (addr,)).start()


class MessagingSender:
    
    def send(self, sock, message):
        sock.send(json.dumps(message, cls=MessageEncoder).encode('utf-8'))

    def sendAll(self, buddys, message):
        for buddy in buddys:
            buddys[buddy].send(json.dumps(message, cls=MessageEncoder).encode('utf-8'))