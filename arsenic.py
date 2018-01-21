#!/usr/bin/env pypy
# -*- coding: utf-8 -*-
# pylint: disable=C0103
# pylint: disable=W0702
# pylint: disable=R0912
# pylint: disable=R0915
# pylint: disable=R0914

"""Arsenic development

This is WIP code under active development.

"""
import ConfigParser
import anydbm
import hashlib
import imp
import os
import platform
import sqlite3
import sys
import time
import types
import urllib2
import uuid

import dill as pickle
from twisted.internet import protocol, reactor, ssl
from twisted.python import log
from twisted.words.protocols import irc

import encoder  # Local module, can be overridden with mod_load

##################
#
# Please do not use this code anywhere else unless you know EXACTLY what you're doing
#
reload(sys)
sys.setdefaultencoding("utf-8")
#
##################

class conf(Exception):
    """Automatically generated"""


VER = '1.4.0b17'

if len(sys.argv) == 2:
    if sys.argv[1].startswith('--config='):
        config_dir = sys.argv[1].split('=', 1)[1]
        if config_dir == '':
            raise conf('No path specified')
        else:
            if not os.path.isdir(config_dir):
                raise conf('config path not found')
else:
    raise SystemExit(1)
    raise conf(
        'arsenic takes a single argument, --config=/path/to/config/dir')

cfile = open(os.path.join(config_dir, 'kgb.conf'), 'r+b')
config = ConfigParser.ConfigParser()
config.readfp(cfile)


def config_save():
    cfile.seek(0)  # This mess is required
    cfile.truncate()  # otherwise we get in to this weird
    cfile.flush()  # situation where we have 2
    config.write(cfile)  # configs in one file
    cfile.flush()


def config_get(module, item, default=False):
    if config.has_option(module, item):
        return config.get(module, item)
    else:
        return default


def config_set(module, item, value):
    if not config.has_section(module):
        config.add_section(module)

    config.set(module, item, value)
    config_save()
    return True


def config_remove(module, item):
    if config.has_section(module) and config.has_option(module, item):
        config.remove_option(module, item)
        config_save()
        return True

    else:
        return False


# relays messages without a log

debug = config.getboolean('main', 'debug')

if debug:
    file_log = 'stdout'
    log.startLogging(sys.stdout)
else:
    log_path = os.path.join(config_dir, 'logs')
    if not os.path.exists(log_path):
        os.makedirs(log_path)
        log.msg("Notice: Created a log directory")

    file_log = log_path + '/' + time.strftime("%Y_%m_%d-%H_%M_%S") + '.log'
    log.startLogging(open(file_log, 'w'))

log.msg("KittyHawk %s, log: %s" % (VER, file_log))


hostname = config_get('network', 'hostname')
if not hostname:
    log.err("Unable to read hostname")
    raise SystemExit(1)

port = config.getint('network', 'port')
if not port:
    log.err("Unable to read port")
    raise SystemExit(2)

oplist = config_get('main', 'op')
if oplist:
    oplist = oplist.replace(' ', '').split(',')
    for user in oplist:
        if user.startswith('!'):
            oplist.remove(user)
            oplist.add(encoder.decode(user))

else:
    log.err('Unable to read ops, assuming none')
    oplist = []

ownerlist = oplist
modlook = {}

modules = config_get('main', 'mod').replace(' ', '').split(',')

if not modules:
    log.err('Unable to read modules, assuming none')
    modules = []

updateconfig = config.getboolean('main', 'updateconfig')

if not updateconfig:
    cfile.close()  # Close this if we don't need it later

salt = config_get('main', 'salt')

if not salt:
    salt = uuid.uuid4().hex
    config_set('main', 'salt', salt)
    log.msg("Notice: a new salt was generated")

mod_declare_privmsg = {}
mod_declare_userjoin = {}
mod_declare_syncmsg = {}

sync_channels = {}

__sync_channel__ = config_get('main', 'sync_channel')

if __sync_channel__:
    for lists in __sync_channel__.split(','):
        items = lists.split('>')
        sync_channels[items[0]] = items[1]

key = config_get('main', 'command_key', '^')

isconnected = False

irc_relay = config_get('main', 'log', '')

if irc_relay == '':
    log.msg("no relay log channel")

db_name = os.path.join(config_dir, config_get('main', 'db'))

if not db_name:
    db_name = ""

cache_name = config_get('main', 'cache', '.cache')

cache_name = os.path.join(config_dir, cache_name)

cache_state = 1

if debug:
    log.msg("Using cache: " + cache_name)

cache_fd = anydbm.open(cache_name, 'c')


if os.path.isfile(db_name) is False:
    log.err("No database found!")
    raise SystemExit(3)

class Profile:
    def __init__(self, connector):
        self.connector = connector

    def __SafeSQL__(self, string):  # Practice safe SQL, wear a sanitizer
        return ''.join(e for e in string if e.isalnum() or e == '@' or e == '!' or e == '.')

    def register(self, usermask):

        nick = usermask.split('!', 1)[0]
        ident = usermask.split('!', 1)[1].split('@', 1)[0]
        hostmask = usermask.split('@', 1)[1]

        c = self.connector.execute('SELECT * FROM users WHERE nickname = ?', (nick,))  # Check if username exists
        if c.fetchone() != None:
            return

        try:
            self.connector.execute('insert into profile(username) values (?)',
                                   (nick,))
            self.connector.execute('insert into users(username, nickname, ident, hostmask) values (?, ?, ?, ?)',
                                   (nick, nick, ident, hostmask,))
            self.connector.commit()

            log.msg("Created user %s" % nick)

            return usermask
        except:
            return False


    def getuser(self, usermask):

        if not usermask:
            return False

        nick = usermask.split('!', 1)[0]
        ident = usermask.split('!', 1)[1].split('@', 1)[0]
        hostmask = usermask.split('@', 1)[1]

        trusted = True

        c = self.connector.execute(
            'SELECT * FROM profile WHERE profile.username = (SELECT username FROM users WHERE hostmask = ?)',
            (hostmask,))

        tmp_u = c.fetchone()

        if tmp_u is None:
            c = self.connector.execute(
                'SELECT * FROM profile WHERE profile.username = (SELECT username from users where nickname = ? and ident = ?)',
                (nick, ident,))

            tmp_u = c.fetchone()
            if tmp_u is None:

                c = self.connector.execute(
                    'SELECT * FROM profile WHERE profile.username = (select username from users where nickname = ? or ident = ?)',
                    (nick, ident,))

                tmp_u = c.fetchone()

                if tmp_u is None:
                    return self.getuser(self.register(usermask))

                else:
                    if debug:
                        log.msg("Notice: %s not trustable" % (usermask))
                    trusted = False
                    u = tmp_u

            else:
                log.msg("Updating hostmask for " + nick)
                self.connector.execute('update users set hostmask = ? where nickname = ?', (hostmask, nick,))
                self.connector.commit()
                return self.getuser(usermask)


        else:
            u = tmp_u  # Turn temp in to actual user info


        username = u[0]

        old_nick_conn = self.connector.execute('SELECT * FROM users WHERE username = ?', (username,))
        old_nick = old_nick_conn.fetchone()[1]

        if nick != old_nick:
            self.connector.execute('update users set nickname = ? where username = ?', (nick, username,))
            self.connector.commit()

        loc_lat = u[1]
        loc_lng = u[2]

        if u[3] is not None:
            if u[3] == 0:
                unit = 'us'
            elif u[3] == 1:
                unit = 'si'
            elif u[3] == 2:
                unit = 'ca'
            elif u[3] == 3:
                unit = 'uk2'
            else:
                unit = 'us'
        else:
            unit = 'us'

        if u[4] == 0:
            gender = False
        elif u[4] == 1:
            gender = True
        else:
            gender = None

        height = u[5]  # cm
        weight = u[6]  # kg

        if u[7] == 1:
            privacy = True
        else:
            privacy = False

        if u[8] == 1:
            isverified = True
        else:
            isverified = False

        if u[9] == 1 and trusted:
            isop = True
        else:
            isop = False

        class user:
            def __init__(self):
                pass

        setattr(user, 'username', username)
        setattr(user, 'nickname', nick)
        setattr(user, 'ident', ident)
        setattr(user, 'hostname', hostmask)
        setattr(user, 'userhost', usermask)
        setattr(user, 'lat', loc_lat)
        setattr(user, 'lon', loc_lng)
        setattr(user, 'unit', unit)
        setattr(user, 'gender', gender)
        setattr(user, 'height', height)
        setattr(user, 'weight', weight)
        setattr(user, 'privacy', privacy)
        setattr(user, 'isverified', isverified)
        setattr(user, 'isop', isop)
        setattr(user, 'trusted', trusted)

        return user

    def getuser_byname(self, username):  # Caution, user not authenticated

        c = self.connector.execute('select * from users where username = ?', (username,))
        u = c.fetchone()

        if u:
            return self.getuser('%s!%s@%s' % (u[1], u[2], u[3]))

        else:
            return False

    def getuser_bynick(self, nickname):  # Caution, user not authenticated

        c = self.connector.execute('SELECT * FROM users WHERE nickname = ?', (nickname,))
        u = c.fetchone()

        if u:
            return self.getuser('%s!%s@%s' % (u[1], u[2], u[3]))

        else:
            return False

    def update(self, username, nickname=None, ident=None, hostname=None, lat=None, lon=None, unit=None, gender=None,
               height=None, weight=None, privacy=None, isverified=None, isop=None):

        if not self.getuser_byname(username):
            return False

        sql_str = 'update profile set'
        sql_user_str = 'update user set'

        if nickname is not None:
            sql_user_str += '  nickname = "%s", ' % (self.__SafeSQL__(nickname))

        if ident is not None:
            sql_user_str += '  ident = "%s", ' % (self.__SafeSQL__(ident))

        if hostname is not None:
            sql_user_str += '  hostname = "%s", ' % (self.__SafeSQL__(hostname))

        if lat is not None:
            try:
                lat = float(lat)  # Check if valid number
                sql_str += '  loc_lat = "%s", ' % lat
            except:
                log.msg("Error, could not turn lat in to float")
                return False

        if lon is not None:
            try:
                lon = float(lon)  # Check if valid number
                sql_str += '  loc_lng = "%s", ' % lon
            except:
                log.msg("Error, could not turn lon in to float")
                return False

        if unit is not None:

            if unit is 'auto':
                value = None
            elif unit == 'us':
                value = 0
            elif unit == 'si':
                value = 1
            elif unit == 'ca':
                value = 2
            elif unit == 'uk2':
                value = 3
            else:
                return False
                log.msg("Incorrect unit supplied")

            sql_str += '  unit = "%s", ' % value  # 5 choices means no sql issues

        if gender is not None:
            if gender:
                gender = 1  # M
            else:
                gender = 0  # F
            sql_str += '  gender = "%s", ' % (gender)

        if height is not None:
            try:
                height = float(height)  # Check if valid number
                sql_str += '  height = "%s", ' % height
            except:
                log.msg("Error, could not turn height in to float")
                return False

        if weight is not None:
            try:
                weight = float(weight)  # Check if valid number
                sql_str += ' weight = "%s", ' % weight
            except:
                log.msg("Error, could not turn weight in to float")
                return False

        if privacy is not None:
            if privacy:
                privacy = 1
            else:
                privacy = 0
            sql_str += '  privacy = "%s", ' % (privacy)

        if isverified is not None:
            if isverified:
                isverified = 1
            else:
                isverified = 0
            sql_str += '  isverified = "%s", ' % (isverified)

        if isop is not None:
            if isop:
                isop = 1
            else:
                isop = 0
            sql_str += '  isop = "%s", ' % (isop)

        if '=' in sql_str:
            sql_str = '%s where username = "%s";' % (sql_str[0:len(sql_str) - 2], self.__SafeSQL__(username))
            self.connector.execute(sql_str)

        if '=' in sql_user_str:
            sql_user_str = '%s where username = "%s";' % (
            sql_user_str[0:len(sql_user_str) - 2], self.__SafeSQL__(username))
            self.connector.execute(sql_user_str)

        try:
            self.connector.commit()
            return True

        except:
            log.msg("Unable to commit profile changes, does the user exist?")
            return False

    def set_password(self, username, password):
        pw = hashlib.sha512(username + password + salt).hexdigest()

        self.connector.execute('UPDATE profile SET password = ? WHERE username = ?', (pw, username,))
        self.connector.commit()

    def check_if_password(self, username):
        c = self.connector.execute('SELECT password FROM profile WHERE username = ?', (username,))
        pw = c.fetchone()[0]

        if pw:
            return True
        else:
            return False

    def validate_password(self, username, password):
        new_pw = hashlib.sha512(username + password + salt).hexdigest()

        c = self.connector.execute('SELECT password FROM profile WHERE username = ?', (username,))
        old_pw = c.fetchone()[0]

        if new_pw == old_pw:
            return True
        else:
            return False

    def link(self, username, password, nickname):
        if self.validate_password(username, password):
            self.connector.execute('UPDATE users SET username = ? WHERE nickname = ?', (username, nickname,))
            self.connector.commit()
            return True
        else:
            return False



def save():
    clist = ''
    slist = ''

    for i in channel_list:
        clist = '%s, %s' % (clist, i)

    if clist[0] != '#':
        clist = clist[2:]

    try:  # silent catched error if not syncing
        for i in sync_channels:
            slist = '%s,%s>%s' % (slist, i, sync_channels[i])

        if slist[0] != '#':
            slist = slist[1:]

        config.set('main', 'sync_channel', slist)

    except:
        pass

    config.set('main', 'channel', clist)
    config_save()


def checkauth(user):
    """Checks if hostmask is bot op"""

    user_host = user.split('!', 1)[1]

    try:  # needed for non message op commands
        c = conn.execute(
            'SELECT * FROM op WHERE username = ?', (user_host,))
    except:
        c = None

    if c is not None:

        # for user in oplist:    #disabled as this is a major DoS
        #    if user.startswith('!'):
        #        oplist.remove(user)
        #        oplist.add(encoder.decode(user))

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


def checkowner(user):
    """Checks if hostmask is bot owner"""

    user_host = user.split('!', 1)[1]

    if user_host in ownerlist:
        return True
    else:
        return False


class Arsenic(irc.IRCClient):
    """Twisted callbacks registered here"""

    def __init__(self, profileManager, cache_fd, extra=False):
        self.profileManager = profileManager
        self.__extra__ = extra
        self.cache_fd = cache_fd
        if extra:
            self.msg = extra.msg

        return

    class persist:
        def __init__(self):
            pass


    save = persist()

    lockerbox = {}

    floodprotect = False

    versionName = 'KittyHawk'
    versionNum = VER
    versionEnv = platform.platform()
    sourceURL = "https://github.com/KittyHawkIRC"

    def ctcp(self, data):
        data = data.strip('\x01')
        if data.startswith('CLIENTINFO'):
            return [('CLIENTINFO', 'ACTION CLIENTINFO PING SOURCE TIME VERSION')]
        elif data.startswith('VERSION'):
            return [('VERSION', '%s %s (%s)' % (self.versionName, self.versionNum, self.versionEnv))]
        elif data.startswith('PING'):
            return [('PING', data.split(' ', 1)[1])]
        elif data.startswith('SOURCE'):
            return [('SOURCE', self.sourceURL)]
        elif data.startswith('TIME'):
            return [('TIME', time.ctime())]
        elif data.startswith('ACTION'):
            return None
        else:
            return [('ERRMSG', '%s :unknown query' % (data))]

    nickname = config_get('main', 'name')

    # Joins channels on invite
    autoinvite = config.getboolean('main', 'autoinvite')

    def join(self, channel):  # hijack superclass join
        if not channel in channel_list:
            channel_list.append(channel)
            if updateconfig:  # Save file every join call
                save()
        irc.IRCClient.join(self, channel)

    def leave(self, channel):  # hijacks superclass leave
        if channel in channel_list:
            channel_list.remove(channel)
            if updateconfig:  # Save file every leave call
                save()
        irc.IRCClient.leave(self, channel)

    def msg(self, user, message, length=None):  # hijacks superclass msg for unicode support
        irc.IRCClient.msg(self, user, message.encode('UTF-8'), length=None)

    def cache_reopen(self):
        self.cache_fd.close()
        self.cache_fd = anydbm.open(cache_name, 'c')

    def cache_save_all(self):

        for item in self.lockerbox:
            self.cache_fd[item] = pickle.dumps(self.lockerbox[item])

        self.cache_reopen()

    def cache_save(self, item):  # save 1 item to reduce overhead

        self.cache_fd[item] = pickle.dumps(self.lockerbox[item])

        self.cache_reopen()


    def cache_load(self):
        # In theory, this should work

        for item in cache_fd.keys():

            try:
                self.lockerbox[item] = pickle.loads(self.cache_fd[item])
            except:
                log.msg("Error loading cache: " + item)



    def cache_status(self):
        if cache_state == 1:
            self.msg(self.channel, 'Cache loaded correctly (%s)' % cache_name)
        elif cache_state == 2:
            self.msg(self.channel, 'Cache loaded read only (%s)' % cache_name)
        elif cache_state == 3:
            self.msg(self.channel, 'A new cache was created (%s)' % cache_name)
        elif cache_state == 0:
            self.msg(self.channel, 'Unable to load cache entirely (%s)' % cache_name)

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.msg('NickServ', 'identify ' + self.factory.nspassword)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        nickname = config_get('main', 'nickname')
        if nickname:
            self.nickname = nickname
            self.setNick(nickname)

        for i in channel_list:
            self.join(i)

        self.cache_load()  # load cached lockerbox

    def kickedFrom(self, channel, user, message):
        time.sleep(3)
        self.join(channel)
        del user

    def syncmsg(self, cbuser, inchannel, outchannel, msg):
        setattr(self, 'type', 'syncmsg')
        setattr(self, 'message', msg)
        setattr(self, 'user', self.profileManager.getuser(cbuser))
        setattr(self, 'incoming_channel', inchannel)
        setattr(self, 'outgoing_channel', outchannel)
        setattr(self, 'ver', VER)
        setattr(self, 'store', save)


        ##### Hijack config object functions to reduce scope

        def __config_get__(item, default=False):  # stubs, basically
            return config_get(mod_declare_privmsg[command], item, default)

        def __config_set__(item, value):
            return config_set(mod_declare_privmsg[command], item, value)

        def __config_remove__(item):
            return config_remove(mod_declare_privmsg[command], item)

        setattr(self, 'config_get', __config_get__)
        setattr(self, 'config_set', __config_set__)
        setattr(self, 'config_remove', __config_remove__)

        for command in mod_declare_syncmsg:
            try:
                self.lockerbox[command]
            except:
                self.lockerbox[command] = self.persist()
            setattr(self, 'locker', self.lockerbox[command])

            modlook[
                mod_declare_syncmsg[command]].callback(
                self)

    def userJoined(self, cbuser, cbchannel):
        setattr(self, 'type', 'userjoin')
        if cbuser != self.nickname:
            setattr(self, 'user', self.profileManager.getuser_bynick(cbuser))
        setattr(self, 'channel', cbchannel)
        setattr(self, 'ver', VER)

        ##### Hijack config object functions to reduce scope

        for command in mod_declare_userjoin:
            modlook[
                mod_declare_userjoin[command]].callback(
                self)

    def privmsg(self, user, channel, msg):

        if not channel.startswith('#'):
            channel = self.nickname

        if msg.startswith('\x01') and msg.endswith('\x01'):
            reply = self.ctcp(msg)
            if reply:
                self.ctcpMakeReply(user.split('!', 1)[0], reply)
                return

        profile = self.profileManager.getuser(user)

        auth = profile.isop
        owner = checkowner(user)  # Config file set value

        # Start module execution

        command = msg.split(' ', 1)[0].lower()

        if type(channel) == 'str':
            lower_channel = channel.lower()
            if lower_channel in sync_channels:  # syncing
                u = profile.nickname
                self.msg(sync_channels[lower_channel], '<%s> %s' % (u, msg))
                self.syncmsg(user, lower_channel,
                             sync_channels[lower_channel], msg)


        iskey = False

        if command.startswith(key):
            command = command.split(key, 1)[1]
            iskey = True
        else:
            command = command

        if iskey or (channel == self.nickname and (
                    auth or command == 'set_password' or command == 'change_password' or command == 'link')):

            setattr(self, 'isop', auth)
            setattr(self, 'isowner', owner)
            setattr(self, 'type', 'privmsg')
            setattr(self, 'command', command)
            setattr(self, 'message', msg)
            setattr(self, 'user', user)  #This will change to a profile object soon!
            setattr(self, 'channel', channel)
            setattr(self, 'ver', VER)
            setattr(self, 'profile', profile)  #Provide profile support to modules (temporary!)

            if command in mod_declare_privmsg:
                try:
                    self.lockerbox[mod_declare_privmsg[command]]
                except:
                    self.lockerbox[mod_declare_privmsg[
                        command]] = self.persist()


                # attributes
                setattr(self, 'store', save)
                setattr(self, 'locker', self.lockerbox[
                    mod_declare_privmsg[command]])

                ##### Hijack config object functions to reduce scope

                def __config_get__(item, default=False):  # stubs, basically
                    return config_get(mod_declare_privmsg[command], item, default)

                def __config_set__(item, value):
                    return config_set(mod_declare_privmsg[command], item, value)

                def __config_remove__(item):
                    return config_remove(mod_declare_privmsg[command], item)

                setattr(self, 'config_get', __config_get__)
                setattr(self, 'config_set', __config_set__)
                setattr(self, 'config_remove', __config_remove__)

            log_data = "Command: %s, user: %s, channel: %s, data: %s" % (
                command, user, channel, msg)
            log.msg(log_data)

            u = user.split('!', 1)[0]

            if channel == self.nickname:
                # private commands

                if irc_relay != "":
                    self.msg(irc_relay, user + " said " + msg)

                if owner:
                    if command == 'op':

                        op = self.profileManager.getuser_byname(msg.split()[1])

                        if op:  # Check if profile exists

                            if not op.isop:  # Make sure the user isn't already an op

                                self.profileManager.update(op, isop=True)
                                self.msg(self.profile.nickname, 'Successfully made %s a bot operator!' % (op.nickname))
                                self.msg(op.nickname, "You're now a bot operator! Message me help for commands.")

                            else:
                                self.msg(self.profile.nickname, '%s is already an operator.' % (op.nickname))

                        else:
                            self.msg(self.profile.nickname, 'Error, no user was found.')


                    elif command == 'deop':

                        op = self.profileManager.getuser_byname(msg.split()[1])

                        if op:  # Check if profile exists

                            if op.isop:  # Make sure the user is an op

                                self.profileManager.update(op, isop=False)
                                self.msg(self.profile.nickname, 'Bot operator status removed from %s.' % (op.nickname))

                            else:
                                self.msg(self.profile.nickname, '%s is not an operator.' % (op.nickname))

                        else:
                            self.msg(self.profile.nickname, 'Error, no user was found.')

                    elif command == 'mod_inject':
                        mod = msg.split(' ')[1]
                        url = msg.split(' ')[2]
                        req = urllib2.Request(
                            url, headers={'User-Agent': 'UNIX:KittyHawk http://github.com/KittyHawkIRC'})

                        fd = urllib2.urlopen(req)
                        mod_src = open(
                            config_dir + '/modules/' + mod + '.py', 'w')

                        data = fd.read()
                        mod_src.write(data)
                        os.fsync(mod_src)

                        fd.close()
                        mod_src.close()

                    elif command == 'mod_load':
                        mod = msg.split(' ')[1]

                        mod_src = open(config_dir + '/modules/' + mod + '.py')
                        mod_bytecode = compile(
                            mod_src.read(), '<string>', 'exec')
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

                            elif cmd_check == 'syncmsg':
                                mod_declare_syncmsg[i] = mod

                    elif command == 'update_inject':
                        try:
                            url = msg.split(' ')[1]
                        except:
                            url = 'https://raw.githubusercontent.com/KittyHawkIRC/core/master/arsenic.py'
                        req = urllib2.Request(
                            url, headers={'User-Agent': 'UNIX:KittyHawk http://github.com/KittyHawkIRC'})

                        fd = urllib2.urlopen(req)
                        mod_src = open(sys.argv[0], 'w')

                        data = fd.read()
                        mod_src.write(data)
                        os.fsync(mod_src)

                        fd.close()
                        mod_src.close()

                    elif command == 'update_restart':
                        try:
                            self.cache_reopen()
                            mod_src = open(sys.argv[0])
                            compile(mod_src.read(), '<string>',
                                    'exec')  # syntax testing

                            args = sys.argv[:]
                            args.insert(0, sys.executable)
                            # os.chdir(_startup_cwd)
                            os.execv(sys.executable, args)
                        except:
                            self.msg(u, 'Syntax error!')

                    elif command == 'update_patch':
                        self.msg(u, 'Starting patch')
                        log.msg('Starting runtime patching!')
                        mod_src = open(sys.argv[0])
                        mod_bytecode = compile(
                            mod_src.read(), '<string>', 'exec')
                        mod_src.close()

                        self.msg(u, 'Bytecode compiled, starting runtime patch')
                        log.msg('Arsenic bytecode compiled, attempting patching')
                        runtime_patch(mod_bytecode)
                        self.msg(u, 'KittyHawk updated to VER %s' % VER)

                    elif command == 'inject':
                        self.lineReceived(msg.split(' ', 1)[1])

                    elif command == 'raw':
                        self.sendLine(msg.split(' ', 1)[1])

                    elif command == 'config_get':
                        opts = msg.split()
                        module = opts[1]
                        item = opts[2]
                        self.msg(u, str(config_get(module, item, False)))

                    elif command == 'config_set':
                        opts = msg.split()
                        module = opts[1]
                        item = opts[2]

                        value_list = opts[3:]
                        value = ''
                        for i in value_list:
                            value += i + ' '

                        self.msg(u, str(config_set(module, item, value[:len(value) - 1])))

                    elif command == 'config_remove':
                        opts = msg.split()
                        module = opts[1]
                        item = opts[2]
                        self.msg(u, str(config_remove(module, item)))

                    elif command == 'config_list':
                        opts = msg.split()
                        module = opts[1]
                        if config.has_section(module):
                            self.msg(u, str(config.options(module)))
                        else:
                            self.msg(u, 'no section for that module!')

                    elif command == 'sync_list':
                        for i in sync_channels:
                            self.msg(u, '%s -> %s' % (i, sync_channels[i]))

                    elif command == 'sync':
                        ch1 = msg.split(' ')[1].lower()
                        ch2 = msg.split(' ')[2].lower()

                        if ch1 in sync_channels:
                            self.msg(u, 'WARNING: %s already syncs to %s, overridden' % (
                                ch1, sync_channels[ch1]))

                        sync_channels[ch1] = ch2

                        self.msg(u, '%s -> %s' % (ch1, ch2))

                    elif command == 'unsync':
                        ch1 = msg.split(' ')[1].lower()

                        if ch1 in sync_channels:
                            del sync_channels[ch1]
                            self.msg(u, '%s -> X' % ch1)
                        else:
                            self.msg(u, 'Channel not currently being synced')

                    elif command == 'cache_save':
                        self.cache_save_all()

                    elif command == 'cache_load':
                        self.cache_load()

                    elif command == 'cache_status':
                        self.cache_status()


                    elif command == 'help_config':
                        self.msg(u, 'KittyHawk Ver: %s' % VER)
                        self.msg(u, 'Config commands: (note: owner only)')
                        self.msg(u, 'config_set {module} {item} {value} (Sets a value for a module)')
                        self.msg(u, 'config_get {module} {item} (Returns a value)')
                        self.msg(u, 'config_remove {module} {item} (Removes a value)')
                        self.msg(u, 'config_list {module} (Lists all items for a module)')

                    elif command == 'help_sysop':
                        self.msg(u, 'KittyHawk Ver: %s' % VER)
                        self.msg(
                            u, "DO NOT USE THESE UNLESS YOU KNOW WHAT YOU'RE DOING")
                        self.msg(u, 'SysOP commands:')
                        self.msg(
                            u, 'op {hostmask}, deop {hostmask}  (add or remove a user)')
                        self.msg(
                            u, 'restart,  (Restarts)')
                        self.msg(
                            u, 'mod_load {module}, mod_reload {module} (Load or reload a loaded module)')
                        self.msg(
                            u, 'mod_inject {module} {url} (Download a module over the internet. (is not loaded))')
                        self.msg(
                            u, 'raw {line}, inject {line} (raw sends a raw line, inject assumes we recieved a line)')
                        self.msg(
                            u, 'update_restart, update_patch (Updates by restarting or patching the runtime)')
                        self.msg(
                            u, 'update_inject {optional:url} Downloads latest copy over the internet, not updated')
                        self.msg(
                            u, 'sync {channel1} {channel2}, unsync {channel1}')
                        self.msg(u, 'sync_list, msg {channel} {message}')
                        self.msg(u, 'cache_save, cache_load, cache_status')

                if auth:
                    if command == 'add':

                        cmd = msg.split(' ', 2)[1].lower()
                        data = msg.split(' ', 2)[2]
                        conn.execute(
                            ('insert or replace into command(name, response) '
                             'values (?, ?)'), (cmd.decode('utf-8'), data.decode('utf-8')))
                        conn.commit()

                        if data.startswith('!'):
                            data = encoder.decode(data)
                        self.msg(
                            user.split(
                                '!', 1)[0], 'Added the command %s with value %s' %
                                            (cmd, data))

                    elif command == 'del':

                        cmd = msg.split(' ')[1].lower()

                        conn.execute('DELETE FROM command WHERE name = ?',
                                     (cmd.decode('utf-8'),))
                        conn.commit()

                        self.msg(
                            user.split(
                                '!',
                                1)[0],
                            'Removed command %s' %
                            cmd)

                    elif msg == 'help':
                        self.msg(u, 'KittyHawk Ver: %s' % VER)
                        self.msg(u, 'Howdy, %s, you silly operator.' % u)
                        self.msg(
                            u, 'You have access to the following commands:')
                        self.msg(u, 'add {command} {value}, del {command}')
                        self.msg(u, 'join {channel}, leave {channel}')
                        self.msg(u, 'nick {nickname}, topic {channel} {topic}')
                        self.msg(u, 'kick {channel} {name} {optional reason}')
                        self.msg(u, 'ban/unban {channel} {hostmask}')

                    elif command == 'mod_update':
                        mod = msg.split(' ')[1]

                        if not mod in modlook:
                            self.msg(u, 'Unknown module! (%s)' % mod)
                            return

                        try:
                            url = modlook[mod].__url__
                        except:
                            self.msg(u, 'Error, module lacks update schema')
                            return

                        try:
                            # Impersonate the first owner, yolo
                            op = 'fake!' + list(ownerlist)[0]
                        except Exception, err:
                            log.err(err)
                            self.msg(u, 'Error, no owners are defined')
                            return

                        inject = 'mod_inject %s %s' % (mod, url)
                        load = 'mod_load %s' % mod

                        try:
                            # It's dirty, but
                            self.privmsg(op, channel, inject)
                            self.privmsg(op, channel, load)  # this shit works
                            self.msg(u, 'Module updated')
                        except:
                            self.msg(u, 'an error occured updating the module')

                if command == 'set_password':
                    if self.profile.trusted:
                        try:
                            password = msg.split(' ')[1]
                        except:
                            self.msg(u, 'Please message me a password after set_password to set your first password')
                            return

                        if self.profileManager.check_if_password(self.profile.username):
                            self.msg(u, 'You have a password set already, please use change_password {old pw} {new pw}')
                            return

                        else:
                            self.profileManager.set_password(self.profile.username, password)
                            self.msg(u, 'Password set! Use link {pw} to link your profile to a new name.')

                elif command == 'change_password':
                    if self.profile.trusted:
                        try:
                            old_pw = msg.split(' ')[1]

                            new_pw = msg.split(' ')[2]
                        except:
                            self.msg(u, 'Please message me your old then new password after change_password.')
                            return

                        if not self.profileManager.check_if_password(self.profile.username):
                            self.msg(u, 'You have no password set, please use set_password {password}')
                            return

                        else:
                            if self.profileManager.validate_password(self.profile.username, old_pw):
                                self.profileManager.set_password(self.profile.username, new_pw)
                                self.msg(u, 'Password set! Use link {pw} to link your profile to a new name.')
                            else:
                                self.msg(u, 'Your password was incorrect.')

                elif command == 'link':
                    try:
                        pw = msg.split(' ')[2]
                        username = msg.split(' ')[1]
                    except:
                        self.msg(u, 'Please message me your username then your password.')
                        return

                    if not self.profileManager.check_if_password(username):
                        self.msg(u, 'You have no password set, please use set_password {password}')
                        return

                    else:
                        if self.profileManager.link(username, pw, self.profile.nickname):
                            self.msg(u, "You've successfully linked your account to " + username)
                        else:
                            self.msg(u, 'Your password was incorrect.')


                elif command in mod_declare_privmsg:
                    modlook[
                        mod_declare_privmsg[
                            command]].callback(
                        self)

            elif msg.startswith(key):

                if command in mod_declare_privmsg:
                    modlook[
                        mod_declare_privmsg[
                            command]].callback(
                        self)
                    self.cache_save(mod_declare_privmsg[command])  # Save the cache only when a module is called

                elif msg.startswith(key + 'help'):

                    self.msg(
                        u, 'Howdy, %s, please visit https://commands.tox.im to view the commands.' % u)
                    self.msg(u,
                             'You can also manage your profile with set_password {pw}, change_password {old pw} {new pw}, or link a new name to a profile with link {username} {pw}')

                else:
                    c = conn.execute(
                        'SELECT response FROM command WHERE name == ?', (command.decode('utf-8'),))

                    r = c.fetchone()
                    if r is not None:
                        rs = str(r[0])
                        if rs.startswith('!'):
                            rs = encoder.decode(rs)

                        if self.floodprotect:  # adds a space every other command. ha
                            rs = rs + ' '
                            self.floodprotect = False
                        else:
                            self.floodprotect = True

                        try:
                            u = msg.split(' ')[1]
                            self.msg(channel, "%s: %s" % (u, rs))

                        except:
                            self.msg(channel, rs)

    def lineReceived(self, line):  # ACTUAL WORK
        # Twisted API emulation

        global isconnected

        data = ''
        channel = ''
        server = ''
        user = ''
        command = ''
        victim = ''

        raw_line = line
        # :coup_de_shitlord!~coup_de_s@fph.commiehunter.coup PRIVMSG #FatPeopleHate :the raw output is a bit odd though
        line = line.split(' ')

        # if True:
        try:
            if line[0].startswith(':'):  # 0 is user, so 1 is command
                user = line[0].split(':', 1)[1]
                command = line[1]

                if not command.isdigit():  # on connect we're spammed with commands that aren't valid

                    if line[2].startswith('#'):  # PRIVMSG or NOTICE in channel
                        channel = line[2]

                        if command == 'KICK':  # It's syntax is normalized for :
                            victim = line[3]
                            data = raw_line.split(' ', 4)[4].split(':', 1)[1]

                        elif command == 'MODE':
                            if len(line) == 4:  # Channel modes
                                victim = line[2]
                                data = line[3]
                            else:
                                victim = line[4]
                                data = line[3]

                        elif command == 'PART':
                            if len(line) == 4:  # Implies part message
                                data = raw_line.split(
                                    ' ', 3)[3].split(':', 1)[1]
                            else:
                                data = ''

                        else:
                            try:
                                if line[3] == ':ACTION':  # /me, act like normal message
                                    data = raw_line.split(
                                        ' ', 4)[4].split(':', 1)[1]
                                else:
                                    data = raw_line.split(
                                        ' ', 3)[3].split(':', 1)[1]
                            except:
                                pass

                    elif line[2].startswith(':#'):  # JOIN/KICK/ETC
                        channel = line[2].split(':', 1)[1]

                    else:  # PRIVMSG or NOTICE via query
                        channel = self.nickname

                        if line[2] == ':ACTION':  # /me, act like normal message
                            data = raw_line.split(' ', 3)[3].split(':', 1)[1]
                        else:
                            data = raw_line.split(' ', 2)[2].split(':', 1)[1]

            else:
                command = line[0]  # command involving server
                server = line[1].split(':', 1)[1]

            if not command.isdigit():

                if ('connected' in data.lower() or '+z' in data.lower()) and isconnected == False:
                    # DIRTY FUCKING HACK
                    # 100% UNSAFE. DO NOT USE THIS IN PRODUCTION
                    # Proposed fixes: No idea,
                    # need to google things

                    self.connectionMade()
                    self.signedOn()
                    isconnected = True  # dirter hack, makes sure this only runs once
                    log.msg("Connected to server!")

                if command == 'PING':
                    self.sendLine('PONG ' + server)

                elif command == 'PRIVMSG':  # privmsg(user, channel, msg)
                    self.privmsg(user, channel, data)

                elif command == 'JOIN':
                    user = user.split('!', 1)[0]
                    self.userJoined(user, channel)

                elif command == 'PART':
                    user = user.split('!', 1)[0]

                elif command == 'QUIT':
                    user = user.split('!', 1)[0]

                elif command == 'KICK':
                    # checks if we got kicked
                    if victim.split('!')[0] == self.nickname:
                        self.kickedFrom(channel, victim, data)

                elif command == 'INVITE':
                    if self.autoinvite:
                        self.join(data)

            elif line[1] == '353':  # NAMES output
                if line[3].startswith('#'):
                    channel = line[3].lower()
                    raw_user = raw_line.split(' ', 4)[4].split(':', 1)[1]
                else:
                    channel = line[4].lower()
                    raw_user = raw_line.split(' ', 5)[5].split(':', 1)[1]

            elif line[1] == '001':
                self.hostname = line[0]
                self._registered = True
                self.nickname = self._attemptedNick
                self.startHeartbeat()

        # else:
        except:
            log.err()

class ArsenicFactory(protocol.ClientFactory):
    """Main irc connector"""

    def __init__(self, conn, channel, username, nspassword):
        self.conn = conn
        self.channel = channel
        self.profileManager = Profile(conn)

        self.username = username
        self.nspassword = nspassword

    def buildProtocol(self, addr):
        p = Arsenic(self.profileManager, cache_fd)
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.err("connection failed: %s" % reason)
        reactor.stop()


def runtime_patch(bytecode):
    global VER
    for i, object in enumerate(bytecode.co_consts):
        if type(object) == types.CodeType:
            log.msg('[%s] Attempting' % (object.co_name))
            exec ('%s.__code__ = object' % (object.co_name))
            log.msg('[%s] Runtime patched!' % (object.co_name))

    if 'RTP' in VER:
        VER = VER.split('_RTP', 1)[0]
    VER = '%s_RTP(%s)' % (VER, time.strftime("%Y%m%d-%H%M"))
    log.msg('Version modifed to %s' % (VER))


if __name__ == '__main__':

    conn = sqlite3.connect(db_name)

    for mod in modules:
        mod_src = open(config_dir + '/modules/' + mod + '.py')
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

            elif cmd_check == 'syncmsg':
                mod_declare_syncmsg[i] = mod

    try:
        channel_list = config_get(
            'main', 'channel').replace(' ', '').split(',')

        f = ArsenicFactory(conn, channel_list[0], config_get('main', 'name'),
                           config_get('main', 'password'))
    except IndexError:
        raise SystemExit(4)

    reactor.connectSSL(hostname, port, f, ssl.ClientContextFactory())

    reactor.run()
