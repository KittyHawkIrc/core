import json, random, urllib2

def declare():
    return {"guess": "privmsg"}

def callback(self, type, isop, command="", msg="", user="", channel="", mode=""):

    fd = urllib2.urlopen("https://www.reddit.com/r/SwordOrSheath/new.json")
    reddit_api = json.loads(fd.read())
    fd.close()

    cringe = []

    for i in reddit_api['data']['children']:
        url = i['data']['url']

        if 'imgur' in url:

            if 'http://i.imgur.com' in url:  #force https
                url = 'https://i.imgur.com/%s' % (url.split('/')[3])

            if 'http://' in url and '/a/' not in url:   #direct URLs
                url = 'https://i.imgur.com/%s.jpg' % (url.split('/')[3])

            cringe.append(url)

    try:
        u = str(msg.split(' ', 1)[1])
        self.msg(channel, u + ": Am I male or female? " + str(random.choice(cringe)))
    except:
        self.msg(channel, "Am I male or female? " + str(random.choice(cringe)))
