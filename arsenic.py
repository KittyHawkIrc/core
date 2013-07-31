#!/usr/bin/env python

import sqlite3

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import sys


class LogBot(irc.IRCClient):
    """A logging IRC bot."""

    nickname = 'Arsenic'

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
        user = user.split('!', 1)[0]
        if user == 'Arsenic': return

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            # There's no private message commands that don't need op, so check
            # for that first:
            c = conn.execute('select * from op where username = ?',
                                (user,))
            if c.fetchone() is None and user != 'TotempaaltJ':
                return

            # Add someone to the op table
            if msg.startswith('op'):
                try:
                    username = msg.split(' ', 1)[1]
                except IndexError:
                    return

                c = conn.execute('insert into op(username) values (?)',
                                 (username,))
                conn.commit()
                self.notice(user, "You have successfully added {0} to op!"\
                                  .format(username))
                self.notice(username, "You are my new boss!")

            # Remove someone to the op table
            elif msg.startswith('deop'):
                try:
                    username = msg.split(' ', 1)[1]
                except IndexError:
                    return

                c = conn.execute('delete from op where username = ?',
                                 (username,))
                conn.commit()
                self.notice(user, "You have successfully deleted {0} from op!"\
                               .format(username))
                self.notice(username, "You are no longer my boss!")

            # Add a command
            elif msg.startswith('add'):
                name, response = msg[4:].split(' ', 1)

                conn.execute(('insert or replace into command(name, response) '
                              'values (?, ?)'),
                             (name, response))
                conn.commit()
                self.notice(user, "You have successfully added the command!")

            # Guess what? Removea command
            elif msg.startswith('remove'):
                name = msg.split(' ', 1)[1]

                conn.execute('delete from command where name = ?',
                             (name,))
                conn.commit()
                self.notice(user, "You have successfully deleted the command!")
            return

        res = ''
        # These are the actual #tox commands:
        if msg.startswith('!help'):
            self.notice(user, "Hello, I'm Arsenic, the #tox bot!")
            self.notice(user, "I respond well to the following commands:")

            commands = []
            c = conn.execute('select name from command')
            for command in c:
                commands.append("!" + str(command[0]))
            self.notice(user, ', '.join(commands))

            # I'm so annoying about that 79-character limit...
            about = ("My creator and overlord is TotempaaltJ. You can find "
                     "him on http://totempaal.tj/.")
            self.notice(user, about)
            about = ("You can find me on "
                     "https://github.com/TotempaaltJ/Arsenic")
            self.notice(user, about)

            self.notice(user, "I usually follow the Three Laws of Robotics.")
            return

        elif msg.startswith('!'):
            command = msg[1:].split(' ', 1)[0]
            print command
            c = conn.execute('select response from command where name == ?',
                             (command,))
            r = c.fetchone()
            if r is not None:
                res = str(r[0])

        if res != '':
            self.msg(channel, res)


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

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
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    conn = sqlite3.connect('arsenic.db')

    # initialize logging
    log.startLogging(sys.stdout)

    # create factory protocol and application
    try:
        f = LogBotFactory(conn, '#' + sys.argv[1], sys.argv[2], sys.argv[3])
    except IndexError:
        print 'Usage: arsenic.py channel username nickserpassword'
        print 'Do not put a # in front of the channel name!'
        sys.exit(1)

    # connect factory to this host and port
    reactor.connectTCP("irc.freenode.net", 6667, f)

    # run bot
    reactor.run()
