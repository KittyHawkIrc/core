import time
import os.path

header1 = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /logs/private/html</title>
 </head>
 <body>
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tox IRC logs</title>
<style>
    body {
        width: auto;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
<link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">

<link rel="stylesheet" href="https://apollo.unglinux.org/assets/css/all.min.css">

<script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
</head>

<body>
<center>
<div class="container">
"""
header2="""
<br><br><p>
<pre>
<table width="100%">
  <tr>
    <th width="15%">Name</th>
    <th>Message</th>
    <th width="15%">Time</th>
  </tr>
"""

def logged(a):
    if a == "#tox":
        return True
    elif a == "#tox-dev":
        return True
    elif a == "#tox-ontopic":
        return True
    elif a == "#tox-gsoc-students":
        return True
    else:
        return False
def write(a,b):
    if os.path.isfile("logs/" + a + "_" + time.strftime("%d%m%y") + ".html"):
        fh = open("logs/" + a + "_" + time.strftime("%d%m%y") + ".html","a")
    else:
        fh = open("logs/" + a + "_" + time.strftime("%d%m%y") + ".html","a")

        fh.write(header1 + "<h2>{} {}/{}/{}</h2>".format(a,time.strftime("%d"),time.strftime("%m"),time.strftime("%y")) + header2)
    fh.write( b + '<td><a id="{0}" href="#{0}">{0}</a></td></tr>'.format(time.strftime("%H:%M:%S")) + "\n")
    fh.close()

def rwrite(a,b):
    fh = open("logs/" + a + ".txt","a")
    fh.write( b + "\n")
    fh.close()

def  msg(a,b,c):
    if logged(a):
        if b == "SyncBot":
            user = c.split(':',1)[0]
            msg = c.split(':',1)[1]
            write(a,"<tr><td>Tox/{}</td><td>{}</td>".format(user,msg))
        else:
            write(a,"<tr><td>{}</td><td>{}</td>".format(b,c))

def notice(a,b,c):
    if logged(a):
        write(a,"<tr><td>! {}</td><td>{}</td>".format(b,c))

def join(a,b):
    if logged(a):
        write(a,"<tr><td>* {1}</td><td>has joined {0}</td>".format(a,b))

def part(a,b):
    if logged(a):
        write(a,"<tr><td>* {1}</td><td>has left {0}</td>".format(a,b))

#def quit(a,b,c):
#        write(a,"* " + b + " has quit (" + c + ")")

def raw(a):
    rwrite("raw",a)	

def kick(a,b,c,d):
    if logged(a):
        write(a,"<tr><td>* {}</td><td>was kicked by {} ({})</td>".format(b,c,d))

def topic(a,b,c):
    if logged(a):
       	write(a,"<tr><td>* {}</td><td>changed the topic to {}</td>".format(b,c))

def action(a,b,c):
    if logged(a):
        if b == "SyncBot":
            user = c.split(':',1)[0]
            msg = c.split(':',1)[1]
            write(a,"<tr><td>- Tox/{}</td><td>{}</td>".format(b,c))
        else:
            write(a,"<tr><td>- {}</td><td>{}</td>".format(b,c))

def mode(a,b,c,d,e):
    if logged(a):
        if c:
            set = '+'
        else:
            set = '-'

        if e == 'None':
            e = a

        write(a,"<tr><td>* {}</td><td>set mode {}{} on {}</td>".format(b,set,d,e))
