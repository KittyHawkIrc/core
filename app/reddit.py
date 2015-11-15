import json, random, urllib2

def declare():
    return {"reddit": "privmsg"}

def callback(self, type, isop, command="", msg="", user="", channel="", mode=""):

    try:
        u = str(msg.split(' ', 1)[1])
    except:
        self.msg(channel, "Please specify a subreddit!")
        return

    try:

        req = urllib2.Request("https://www.reddit.com/r/" + u + "/new.json", headers={ 'User-Agent': 'UNIX:the_kgb:0.157 http://github.com/stqism/THE_KGB' })
        fd = urllib2.urlopen(req)
        reddit_api = json.loads(fd.read())
        fd.close()

        cringe = []

        for i in reddit_api['data']['children']:
            url = i['data']['url']
            title = i['data']['title']

            if 'imgur' in url:

                if 'http://i.imgur.com' in url:  #force https
                    url = 'https://i.imgur.com/%s' % (url.split('/')[3])

                if 'http://' in url and '/a/' not in url:   #direct URLs
                    if 'gallery' in url:
                        url = 'https://i.imgur.com/%s.jpg' % (url.split('/')[4])
                    else:
                        url = 'https://i.imgur.com/%s.jpg' % (url.split('/')[3])

            cringe.append([title, url])

        item = random.choice(cringe)
        self.msg(channel, str(item[0] + " " + item[1]))

    except Exception, e:
        self.msg('#the_kgb', str(e))
