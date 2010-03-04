
class safe(str):
    pass

def escape(arg):
    if isinstance(arg, safe):
        return arg
    return str(arg).replace(r"'", r"''")

def replacetags(string, **kwargs):
    for key, value in kwargs.iteritems():
        string = string.replace('%{' + key + '}', escape(value))
    return string
