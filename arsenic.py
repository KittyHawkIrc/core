#!/usr/bin/env python

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log

import sys

class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    nickname = 'bt_bot'

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.msg('NickServ', 'identify ' + self.factory.nspassword)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)


    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        for tick in msg.translate(None, '+-'):
                if tick != '^':
                        return
        self.msg(channel,msg + '^')


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, username, nspassword):
        self.channel = channel

        self.username = username
        self.nspassword = nspassword

    def buildProtocol(self, addr):
        p = LogBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':

    # create factory protocol and application
    try:
        f = LogBotFactory('#bitcoin-otc', 'bt_bot', sys.argv[1])
    except IndexError:
        print 'Usage: arsenic.py password'
        sys.exit(1)

    # connect factory to this host and port
    reactor.connectSSL("chat.freenode.net", 7000, f, ssl.ClientContextFactory())

    # run bot
    reactor.run()
