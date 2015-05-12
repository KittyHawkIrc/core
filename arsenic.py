#!/usr/bin/env python

import os
import sys
import imp
import sqlite3
import errno
import ConfigParser
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log
import cProfile, pstats, StringIO
pr = cProfile.Profile()

config_dir = ''

cfile = open(os.path.join(config_dir, 'kgb.conf'), 'r')
config = ConfigParser.ConfigParser()
config.readfp(cfile)
cfile.close

oplist = config.get('main','op').split(',')

modlook = {}
modules = config.get('main','mod').split(',')

mod_declare_privmsg = {}

class conf(Exception):

    """Automatically generated"""

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

    def kickedFrom(self, channel, kicker, message):
        self.join(channel)
        user = user.split('^', 1)[0]
        self.kick(channel, user.split('!',1)[1], reason="How dare you kick a bot")

    def privmsg(self, user, channel, msg):
        user = user.split('^', 1)[0]
        if user == self.nickname: 
            return

        user_host = user.split('!',1)[1]

        try: #needed for non message op commands
            c = conn.execute('select * from op where username = ?',(user_host,))
        except:
            c = None

        if c != None:

            if user_host in oplist:
                auth = True

            elif c.fetchone() is not None:
                auth = True

            else:
                auth = False

        else:
            if user_host in oplist:
                auth = True

            else:
                auth = False

#Start module execution

        command = msg.split(' ', 1)[0]

        if channel == self.nickname:

            if command in mod_declare_privmsg:
                modlook[mod_declare_privmsg[command]].callback(self, "privmsg", auth, msg, user, channel)

            #private commands
            self.msg('#THE_KGB', user + " said " + msg)

            if auth:
                if msg.startswith('op'):

                    host = msg.split(' ',1)[1]
                    extname = host.split('!',1)[0]
                    c = conn.execute('insert into op(username) values (?)',
                                 (host.split('!',1)[1],))
                    conn.commit()

                    self.msg(user.split('!',1)[0],'Added user %s to the op list' % (extname))
                    self.msg(extname, "You've been added to my op list")

                elif msg.startswith('deop'):

                    host = msg.split(' ',1)[1]
                    extname = host.split('!',1)[0]
                    c = conn.execute('delete from op where username = ?',
                                 (host.split('!',1)[1],))
                    conn.commit()

                    self.msg(user.split('!',1)[0],'Removed user %s from the op list' % (extname))

                elif msg.startswith('add'):

                    cmd = msg.split(' ',2)[1]
                    data= msg.split(' ',2)[2]

                    print cmd
                    print data

                    conn.execute(('insert or replace into command(name, response) '
                              'values (?, ?)'),
                             (cmd, data))
                    conn.commit()

                    self.msg(user.split('!',1)[0],'Added the command %s with value %s' % (cmd, data))

                elif msg.startswith('del'):

                    cmd = msg.split(' ')[1]

                    conn.execute('delete from command where name = ?',
                             (cmd,))
                    conn.commit()

                    self.msg(user.split('!',1)[0],'Removed command %s' % (cmd))

                elif msg.startswith('restart'):
                    args = sys.argv[:]
                    args.insert(0, sys.executable)
                    #os.chdir(_startup_cwd)
                    os.execv(sys.executable, args)

                elif msg.startswith('join'):
                    self.join(msg.split(' ')[1])

                    u = user.split('!',1)[0]
                    self.msg(u, 'joined ' + msg.split(' ')[1])

                elif msg.startswith('leave'):
                    self.leave(msg.split(' ')[1])

                    u = user.split('!',1)[0]
                    self.msg(u, 'left ' + msg.split(' ')[1])

                elif msg.startswith('prof_on'):
                    pr.enable()
                    u = user.split('!',1)[0]
                    self.msg(u, 'profiling on')

                elif msg.startswith('prof_off'):
                    pr.disable()
                    u = user.split('!',1)[0]
                    self.msg(u, 'profiling on')

                elif msg.startswith('prof_stat'):
                    u = user.split('!',1)[0]
                    s = StringIO.StringIO()
                    sortby = 'cumulative'
                    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                    ps.print_stats()
                    self.msg(u, s.getvalue())

                elif msg.startswith('nick'):
                    self.setNick(msg.split(' ')[1])

                    u = user.split('!',1)[0]
                    self.msg(u, 'now known as ' + msg.split(' ')[1])

                elif msg.startswith('kick'):
                    channel = msg.split(' ')[1]
                    user = msg.split(' ')[2]
                    try:
                        reason = msg.split(' ', 3)[3]
                        self.kick(channel, user, reason=reason)
                    except:
                        self.kick(channel, user)

                    u = user.split('!',1)[0]
                    self.msg(u, 'kicked ' + user)

                elif msg.startswith('ban'):
                    channel = msg.split(' ')[1]
                    hostmask = msg.split(' ')[2]
                    self.mode(channel ,True, 'b', mask=hostmask)

                    u = user.split('!',1)[0]
                    self.msg(u, 'banned ' + hostmask)

                elif msg.startswith('msg'):
                    channel = msg.split(' ')[1]
                    msg = msg.split(' ', 2)[2]
                    self.msg(channel, msg)

                elif msg.startswith('topic'):
                    channel = msg.split(' ')[1]
                    topic = msg.split(' ', 2)[2]
                    self.topic(channel, topic=topic)

                    u = user.split('!',1)[0]
                    self.msg(u, 'topic set to ' + topic)

                elif msg.startswith('unban'):
                    channel = msg.split(' ')[1]
                    hostmask = msg.split(' ')[2]
                    self.mode(channel ,False , 'b', mask=hostmask)

                    u = user.split('!',1)[0]
                    self.msg(u, 'unbanned ' + hostmask)

                elif msg.startswith('help'):
                    u = user.split('!',1)[0]
                    self.msg(u, 'Howdy, %s, you silly operator.' % (u))
                    self.msg(u, 'You have access to the following commands:')
                    self.msg(u, 'add {command} {value}, del {command}')
                    self.msg(u, 'join {channel}, leave {channel}')
                    self.msg(u, 'nick {nickname}, kick {channel} {name} {optional reason}')
                    self.msg(u, 'ban/unban {channel} {hostmask}')
                    self.msg(u, 'msg {channel} {message}, topic {channel} {topic}')

            else:
                u = user.split('!',1)[0]
                self.msg(u, 'I only accept commands from bot operators')


        elif msg.startswith('^'):
            command
            if command[1:] in mod_declare_privmsg:
                modlook[mod_declare_privmsg[command[1:]]].callback(self, "privmsg", auth, msg, user, channel)

            if msg.startswith('^help'):
                    u = user.split('!',1)[0]

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
                c = conn.execute('select response from command where name == ?',(command,))

                r = c.fetchone()
                if r is not None:
                    try:
                        u = msg.split(' ')[1]
                        self.msg(channel,"%s: %s" % (u,str(r[0])))

                    except:
                        self.msg(channel,str(r[0]))

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
        if sys.argv[1].startswith('--config='):
            config_dir = sys.argv[1].split('=', 1)[1]
            if config_dir == '':
                raise conf('No path specified')
            else:
                if not os.path.isdir(config_dir):
                    raise conf('config path not found')
                    raise
        else:
            raise
    except:
        raise conf('arsenic takes a single argument, --config=/path/to/config/dir')

    for mod in modules:
        mod_src = open(config_dir + '/app/' + mod + '.py')
        mod_bytecode = compile(mod_src.read(), '<string>', 'exec')
        mod_src.close()

        modlook[mod] = imp.new_module(mod)
        sys.modules[mod] = modlook[mod]
        exec mod_bytecode in modlook[mod].__dict__
        
        declare_table = modlook[mod].declare()
        for i in declare_table:

            if i == 'privmsg':
                mod_declare_privmsg[declare_table[i]] = mod


    try:
        channel = config.get('main','channel').split(',')
        f = LogBotFactory(conn, channel[0],config.get('main', 'name'), config.get('main','password'))
    except IndexError:
        sys.exit(1)

    reactor.connectSSL(config.get('network', 'hostname'), int(config.get('network', 'port')), f, ssl.ClientContextFactory())

    reactor.run()
