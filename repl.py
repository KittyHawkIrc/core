# coding=utf-8

import IPython
from IPython.core import ultratb

from arsenic import *

sys.excepthook = ultratb.FormattedTB(mode='Verbose',
                                     color_scheme='Linux', call_pdb=1)


class repl:
    debug = True

    file_log = 'stdout'
    log.startLogging(sys.stdout, setStdout=False)
    log.msg("Faux Arsenic [" + VER + "]")

    ### BEGIN SIMULATED STARTUP ###

    oplist = config.get('main', 'op')
    if oplist:
        oplist = oplist.replace(' ', '').split(',')
        for user in oplist:
            if user.startswith('!'):
                oplist.remove(user)
                oplist.add(encoder.decode(user))

    ownerlist = oplist
    modlook = {}

    modules = config.get('main', 'mod').replace(' ', '').split(',')

    if not modules:
        log.err('Unable to read modules, assuming none')
        modules = []

    updateconfig = config.getboolean('main', 'updateconfig')

    if not updateconfig:
        cfile.close()  # Close this if we don't need it later

    salt = config.get('main', 'salt')

    if not salt:
        salt = uuid.uuid4().hex
        config.set('main', 'salt', salt)
        log.msg("Notice: a new salt was generated")

    mod_declare_privmsg = {}
    mod_declare_userjoin = {}
    mod_declare_syncmsg = {}

    sync_channels = {}

    __sync_channel__ = config.get('main', 'sync_channel')

    if __sync_channel__:
        for lists in __sync_channel__.split(','):
            items = lists.split('>')
            sync_channels[items[0]] = items[1]

    key = config.get('main', 'command_key', '^')

    isconnected = False

    cache_state = 1

    for mod in modules:
        mod_src = open('.' + '/modules/' + mod + '.py')
        mod_bytecode = compile(
                mod_src.read().replace(u"\u2018", "").replace(u"\u2019", "").replace(u"\u201c", "").replace(u"\u201d",
                                                                                                            ""),
                '<string>', 'exec')
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

        channel_list = config.get(
                'main', 'channel').replace(' ', '').split(',')

    def msg(self, Arsenic, user, message, length=None):
        self.output = "[%s] %s" % (user, message)
        log.msg(self.output)

    def join(self, Arsenic, channel, key=None):
        log.msg("[ %s] joined" % (channel))

    def sendLine(self, Arsenic, raw):
        self.data = '[RAW:] %s' % (raw)
        log.msg(self.output)

    def __init__(self, *args, **kwargs):
        self.Arsenic = Arsenic(Profile(sqlite3.connect("arsenic.db")), anydbm.open('.cache', 'c'), unittest=self)

    ### END SIMULATED STARTUP ###

    # self.obj.privmsg("fake!is@op", "#test_channel", "^hello")


r = repl()


def m(channel, message):
    r.Arsenic.privmsg("fake!is@op", channel, message)


log.msg("##### [Notice] Running Arsenic in REPL, this is NOT CONNECTED TO A NETWORK #####")

IPython.embed()
