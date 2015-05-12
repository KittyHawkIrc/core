import sys

def declare():
    return {"restart": "privmsg", "join": "privmsg", "leave": "privmsg", "nick": "privmsg", "kick": "privmsg", "ban": "privmsg", "unban": "privmsg", "msg": "privmsg", "topic": "privmsg"}

def callback(self, type, command, isop, msg="", user="", channel="", mode=""):

    if isop == False:
        return
        
    if channel.startswith('#') == False:
        username = user.split('!',1)[0]

        if command == 'restart':
            args = sys.argv[:]
            args.insert(0, sys.executable)
            #os.chdir(_startup_cwd)
            os.execv(sys.executable, args)

        elif command == 'join':
            self.join(msg.split(' ')[1])

            u = user.split('!',1)[0]
            self.msg(u, 'joined ' + msg.split(' ')[1])

        elif command == 'leave':
            self.leave(msg.split(' ')[1])

            u = user.split('!',1)[0]
            self.msg(u, 'left ' + msg.split(' ')[1])

        elif command == 'nick':
            self.setNick(msg.split(' ')[1])

            u = user.split('!',1)[0]
            self.msg(u, 'now known as ' + msg.split(' ')[1])

        elif command == 'kick':
            channel = msg.split(' ')[1]
            user = msg.split(' ')[2]
            try:
                reason = msg.split(' ', 3)[3]
                self.kick(channel, user, reason=reason)
            except:
                self.kick(channel, user)

            u = user.split('!',1)[0]
            self.msg(u, 'kicked ' + user)

        elif command == 'ban':
            channel = msg.split(' ')[1]
            hostmask = msg.split(' ')[2]
            self.mode(channel ,True, 'b', mask=hostmask)

            u = user.split('!',1)[0]
            self.msg(u, 'banned ' + hostmask)

        elif command == 'msg':
            channel = msg.split(' ')[1]
            msg = msg.split(' ', 2)[2]
            self.msg(channel, msg)

        elif command == 'topic':
            channel = msg.split(' ')[1]
            topic = msg.split(' ', 2)[2]
            self.topic(channel, topic=topic)

            u = user.split('!',1)[0]
            self.msg(u, 'topic set to ' + topic)

        elif command == 'unban':
            channel = msg.split(' ')[1]
            hostmask = msg.split(' ')[2]
            self.mode(channel ,False , 'b', mask=hostmask)

            u = user.split('!',1)[0]
            self.msg(u, 'unbanned ' + hostmask)
