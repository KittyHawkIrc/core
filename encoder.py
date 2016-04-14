import base64

coding = {'b64':[base64.b64encode, base64.b64decode]}

def encode(code_str):
    try:
        code_func = coding[code_str.split(':')[0]][0]
        return '!' + code_str.split(':')[0] + ':' + code_func(code_str.split(':')[1])
    except:
        return False

def decode(code_str):
    try:
        code_str = code_str.split('!')[1]
        code_func = coding[code_str.split(':')[0]][1]
        return code_func(code_str.split(':')[1])
    except:
        return False
