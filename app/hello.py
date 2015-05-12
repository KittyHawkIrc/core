def declare():
    return {"hello": "privmsg"}

def callback(self, type, command, isop, msg="", user="", channel="", mode=""):

    if channel.startswith('#'):
        username = user.split('!',1)[0]

        if isop:
            self.msg(channel, "And a hello to you too, operator %s!" % (username))
        else:
            self.msg(channel, "And a hello to you too, %s!" % (username))
