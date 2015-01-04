def reply(msg, user, channel):
    return {"type": "msg", "channel": channel, "data": "And a hello to you too, %s!" % (user)}
