def declare():
    return {"hello": "privmsg"}

def callback(self, type, isop, command="", msg="", user="", channel="", mode=""):

    if channel.startswith('#'):

        if isop:
            self.msg(channel, "And a hello to you too, operator %s!" % (user))
        else:
            self.msg(channel, "And a hello to you too, %s!" % (user))
