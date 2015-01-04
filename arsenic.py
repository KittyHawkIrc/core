#!/usr/bin/env python

import sys
import imp
import sqlite3
import ConfigParser
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log

cfile = open('kgb.conf', 'r')
config = ConfigParser.ConfigParser()
config.readfp(cfile)
cfile.close

modlook = {}
modules = config.get('main','mod').split(',')

for mod in modules:
    mod_src = open('app/' + mod + '.py')
    mod_bytecode = compile(mod_src.read(), '<string>', 'exec')
    mod_src.close()

    modlook[mod] = imp.new_module(mod)
    sys.modules[mod] = modlook[mod]
    exec mod_bytecode in modlook[mod].__dict__

class LogBot(irc.IRCClient):

    nickname = config.get('main','name')

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.msg('NickServ', 'identify ' + self.factory.nspassword)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)


    # callbacks for events
    def signedOn(self):
        for i in channel:
            self.join(i)

    def privmsg(self, user, channel, msg):
        user = user.split('^', 1)[0]
        if user == self.nickname: 
            return

        if channel == self.nickname:
            #private commands
            print "private command"

        elif msg.startswith('^'):
            command = msg[1:].split(' ', 1)[0]

            if command in modlook:
                osy = modlook[command].reply(msg, user, channel)
                
                if osy['type'] == 'msg':
                    self.msg(osy['channel'],osy['data'])
            else:

                c = conn.execute('select response from command where name == ?',
                                 (command,))
                r = c.fetchone()
                if r is not None:
                    self.msg(str(r[0]))



class LogBotFactory(protocol.ClientFactory):

    def __init__(self, conn, channel, username, nspassword):
        self.conn = conn
        self.channel = channel

        self.username = username
        self.nspassword = nspassword

    def buildProtocol(self, addr):
        p = LogBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    conn = sqlite3.connect('arsenic.db')
    log.startLogging(sys.stdout)

    try:
        channel = config.get('main','channel').split(',')
        f = LogBotFactory(conn, channel[0],config.get('main', 'name'), config.get('main','password'))
    except IndexError:
        sys.exit(1)

    reactor.connectSSL(config.get('network', 'hostname'), int(config.get('network', 'port')), f, ssl.ClientContextFactory())

    reactor.run()