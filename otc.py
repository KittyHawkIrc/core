def tick(a,b,c):
    if a == 'help':
        msg = '^otc {currency}, specify a 2nd currency for rates, add --last/high/low etc for that alone.'
        return msg
    import urllib2,json,StringIO
    a = a.lower()
    b = b.lower()
    c = c.lower()

    if b.startswith('-'):
        c = b
        b = 'usd'

    if b == 'none':
        b = 'usd'

    btce = urllib2.Request('https://btc-e.com/api/2/' + a + '_' + b + '/ticker')
    get = urllib2.urlopen(btce)
    parse = get.read()
    if parse == '{"error":"invalid pair"}':
        b = 'btc'
        btce = urllib2.Request('https://btc-e.com/api/2/' + a + '_' + b + '/ticker')
        get = urllib2.urlopen(btce)
        parse = get.read()

    try:
        ticker3 = "{" + parse.split('{',2)[2].split('}',2)[0] + "}".replace('"','\'').replace(':',':"').replace(',','",').replace('}','"}')
        ticker2 = ticker3.replace(':',':"').replace(',','",')
        ticker = json.loads(ticker2)
    except:
        return 'Unknown currency'

    if c == 'none':
        msg = 'BTC-E ' + a.upper() + b.upper() + ' ticker | High: ' + ticker['high'] + ', Low: ' + ticker['low'] + ', avg: ' + ticker['avg'] + ', Last: ' + ticker['last'] + ', Buy: ' + ticker['buy'] + ', Sell: ' + ticker['sell']

    elif c.startswith('--'):
        msg = ticker[c[2:]]

    else:
        msg = 'That flag does not exist'

    return msg
