# is_nick(string) takes 'string' and determines if it is a valid IRC nickname
# is_nick: Str -> Bool
# requires: isinstance(string, str)
def is_nick(string):
    for i, char in enumerate(string):
        if ((i > 0 and (char.isdigit() or char == '-')) or
            char.isalpha() or char in '_-\[]{}^`|'):
            continue
        else:
            return False
    return True
    
# is_float(object_) takes any object 'object_' and returns a boolean for
#   whether it can be converted into a float
# is_float: Any -> Bool
def is_float(object_):
    try:
        float(object_)
        return True
    except:
        return False

