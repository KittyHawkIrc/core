# -*- coding: utf-8 -*-
# pylint: disable=C0103
# pylint: disable=W0702
# pylint: disable=R0912
# pylint: disable=R0915
# pylint: disable=R0914

"""Arsenic development

This is WIP code under active development.

"""

import os
import sys
import imp
import sqlite3
import ConfigParser
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log
import cProfile
import pstats
import StringIO

pr = cProfile.Profile()

config_dir = ''

cfile = open(os.path.join(config_dir, 'kgb.conf'), 'r')
config = ConfigParser.ConfigParser()
config.readfp(cfile)
cfile.close()

oplist = config.get('main', 'op').translate(None, " ").split(',')

modlook = {}
modules = config.get('main', 'mod').translate(None, " ").split(',')

mod_declare_privmsg = {}
mod_declare_userjoin = {}

irc_relay = ""

try:
    irc_relay = config.get('main', 'log')
except:
    print "no relay log channel"

db_name = ""

try:
    db_name = config.get('main', 'db')
except:
    db_name = ""

if os.path.isfile(db_name) is False:
    print "##########   No database found!   ##########"
    raise SystemExit(0)
else:
    print db_name


class conf(Exception):

    """Automatically generated"""


class LogBot(irc.IRCClient):

    """Twisted callbacks registered here"""

    def __init__(self):
        return

    nickname = config.get('main', 'name')

    def isauth(self, user):
        """Checks if hostmask is bot op"""

        user_host = user.split('!', 1)[1]

        try:  # needed for non message op commands
            c = conn.execute(
                'select * from op where username = ?', (user_host,))
        except:
            c = None

        if c is not None:

            if user_host in oplist:
                return True

            elif c.fetchone() is not None:
                return True

            else:
                return False

        else:
            if user_host in oplist:
                return True

            else:
                return False

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.msg('NickServ', 'identify ' + self.factory.nspassword)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        for i in channel:
            self.join(i)

    def kickedFrom(self, channel, user, message):
        self.join(channel)
        del user

    def userJoined(self, cbuser, cbchannel):
        for command in mod_declare_userjoin:
            modlook[
                mod_declare_userjoin[command]].callback(
                self,
                "userjoin",
                False,
                user=cbuser,
                channel=cbchannel)

    def privmsg(self, user, channel, msg):
        user = user.split('^', 1)[0]
        if user == self.nickname:
            return

        auth = self.isauth(user)

# Start module execution

        command = msg.split(' ', 1)[0].lower()

        if channel == self.nickname:

            if command in mod_declare_privmsg:
                modlook[
                    mod_declare_privmsg[command]].callback(
                    self,
                    "privmsg",
                    auth,
                    command,
                    msg=msg,
                    user=user,
                    channel=channel)

                self.msg("coup_de_shitlord", "done")

            # private commands
            if irc_relay != "":
                self.msg(irc_relay, user + " said " + msg)

            if auth:
                if msg.startswith('op'):

                    host = msg.split(' ', 1)[1]
                    extname = host.split('!', 1)[0]
                    c = conn.execute('insert into op(username) values (?)',
                                     (host.split('!', 1)[1],))
                    conn.commit()

                    self.msg(
                        user.split(
                            '!',
                            1)[0],
                        'Added user %s to the op list' %
                        (extname))
                    self.msg(extname, "You've been added to my op list")

                elif msg.startswith('deop'):

                    host = msg.split(' ', 1)[1]
                    extname = host.split('!', 1)[0]
                    c = conn.execute('delete from op where username = ?',
                                     (host.split('!', 1)[1],))
                    conn.commit()

                    self.msg(
                        user.split(
                            '!',
                            1)[0],
                        'Removed user %s from the op list' %
                        (extname))

                elif msg.startswith('add'):

                    cmd = msg.split(' ', 2)[1].lower()
                    data = msg.split(' ', 2)[2]

                    conn.execute(
                        ('insert or replace into command(name, response) '
                         'values (?, ?)'), (cmd, data))
                    conn.commit()

                    self.msg(
                        user.split(
                            '!', 1)[0], 'Added the command %s with value %s' %
                        (cmd, data))

                elif msg.startswith('del'):

                    cmd = msg.split(' ')[1].lower()

                    conn.execute('delete from command where name = ?',
                                 (cmd,))
                    conn.commit()

                    self.msg(
                        user.split(
                            '!',
                            1)[0],
                        'Removed command %s' %
                        (cmd))

                elif msg.startswith('prof_on'):
                    pr.enable()
                    u = user.split('!', 1)[0]
                    self.msg(u, 'profiling on')

                elif msg.startswith('prof_off'):
                    pr.disable()
                    u = user.split('!', 1)[0]
                    self.msg(u, 'profiling on')

                elif msg.startswith('prof_stat'):
                    u = user.split('!', 1)[0]
                    s = StringIO.StringIO()
                    sortby = 'cumulative'
                    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                    ps.print_stats()
                    self.msg(u, s.getvalue())

                elif msg.startswith('mod_reload'):
                    mod = msg.split(' ')[1]

                    mod_src = open(config_dir + '/app/' + mod + '.py')
                    mod_bytecode = compile(mod_src.read(), '<string>', 'exec')
                    mod_src.close()

                    exec mod_bytecode in modlook[mod].__dict__

                    declare_table = modlook[mod].declare()

                    for i in declare_table:
                        cmd_check = declare_table[i]

                        if cmd_check == 'privmsg':
                            mod_declare_privmsg[i] = mod

                        elif cmd_check == 'userjoin':
                            mod_declare_userjoin[i] = mod

                elif msg.startswith('mod_load'):
                    mod = msg.split(' ')[1]

                    mod_src = open(config_dir + '/app/' + mod + '.py')
                    mod_bytecode = compile(mod_src.read(), '<string>', 'exec')

                    modlook[mod] = imp.new_module(mod)
                    sys.modules[mod] = modlook[mod]

                    exec mod_bytecode in modlook[mod].__dict__

                    declare_table = modlook[mod].declare()

                    for i in declare_table:
                        cmd_check = declare_table[i]

                        if cmd_check == 'privmsg':
                            mod_declare_privmsg[i] = mod

                        elif cmd_check == 'userjoin':
                            mod_declare_userjoin[i] = mod

                elif msg.startswith('help'):
                    u = user.split('!', 1)[0]
                    self.msg(u, 'Howdy, %s, you silly operator.' % (u))
                    self.msg(u, 'You have access to the following commands:')
                    self.msg(u, 'add {command} {value}, del {command}')
                    self.msg(u, 'join {channel}, leave {channel}')
                    self.msg(u, 'nick {nickname}, topic {channel} {topic}')
                    self.msg(u, 'kick {channel} {name} {optional reason}')
                    self.msg(u, 'ban/unban {channel} {hostmask}')
                    self.msg(u, 'msg {channel} {message}')

            else:
                u = user.split('!', 1)[0]
                self.msg(u, 'I only accept commands from bot operators')

        elif msg.startswith('^'):

            if command[1:] in mod_declare_privmsg:
                modlook[
                    mod_declare_privmsg[
                        command[
                            1:]]].callback(
                    self,
                    "privmsg",
                    auth,
                    command[
                        1:],
                    msg,
                    user,
                    channel)

            elif msg.startswith('^help'):
                u = user.split('!', 1)[0]

                commands = []
                c = conn.execute('select name from command')
                for cmd in modules:
                    commands.append("^" + cmd)

                for command in c:
                    commands.append("^" + str(command[0]))

                self.msg(u, 'Howdy, %s' % (u))
                self.msg(u, 'You have access to the following commands:')

                self.msg(u, ', '.join(commands))

            else:
                command = command[1:]
                c = conn.execute(
                    'select response from command where name == ?', (command,))

                r = c.fetchone()
                if r is not None:
                    try:
                        u = msg.split(' ')[1]
                        self.msg(channel, "%s: %s" % (u, str(r[0])))

                    except:
                        self.msg(channel, str(r[0]))


class LogBotFactory(protocol.ClientFactory):

    """Main irc connector"""

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
    conn = sqlite3.connect(db_name)
    log.startLogging(sys.stdout)

    try:
        if sys.argv[1].startswith('--config='):
            config_dir = sys.argv[1].split('=', 1)[1]
            if config_dir == '':
                raise conf('No path specified')
            else:
                if not os.path.isdir(config_dir):
                    raise conf('config path not found')
                    raise
    except:
        raise conf(
            'arsenic takes a single argument, --config=/path/to/config/dir')

    for mod in modules:
        mod_src = open(config_dir + '/app/' + mod + '.py')
        mod_bytecode = compile(mod_src.read(), '<string>', 'exec')
        mod_src.close()

        modlook[mod] = imp.new_module(mod)
        sys.modules[mod] = modlook[mod]
        exec mod_bytecode in modlook[mod].__dict__

        declare_table = modlook[mod].declare()

        for i in declare_table:
            cmd_check = declare_table[i]

            if cmd_check == 'privmsg':
                mod_declare_privmsg[i] = mod

            elif cmd_check == 'userjoin':
                mod_declare_userjoin[i] = mod

    try:
        channel = config.get('main', 'channel').translate(None, " ").split(',')

        f = LogBotFactory(conn, channel[0], config.get('main', 'name'),
                          config.get('main', 'password'))
    except IndexError:
        raise SystemExit(0)

    reactor.connectSSL(
        config.get(
            'network', 'hostname'), int(
            config.get(
                'network', 'port')), f, ssl.ClientContextFactory())

    reactor.run()
