# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016
# @modified 2018/02/18 11:27:17

def add_builtin(name, func):
    __builtins__[name] = func
 
# string methods.
def ljust(self, num):
    num = int(num)
    if len(self) >= num: return self
    rest = num - len(self)
    return self + rest * ' '
def rjust(self, num):
    num = int(num)
    if len(self) >= num: return self
    rest = num - len(self)
    return rest * ' ' + self
def center(self, num):
    num = int(num)
    if len(self) >= num: return self
    right = (num - len(self)) / 2
    right = int(right)
    left = num - right - len(self)
    return left * ' ' + self + right * ' '
def sformat0(args):
    fmt = args[0]
    if len(args) == 1: return fmt
    fmt_len = len(fmt)
    i = 0
    args_cnt = 0
    is_char = 1
    dest = ""
    left = 0
    while i < fmt_len:
        is_char = 1
        if fmt[i] == '%':
            i+=1
            c = fmt[i]
            if c == '-' and (i+1 < fmt_len) and fmt[i+1] in '1234567890':
                i += 1
                c = fmt[i]
                left = 1
            if c in ('s', 'd', 'o'):
                flag = c
                args_cnt += 1
                dest+=str(args[args_cnt])
            elif c in '1234567890':
                n = 0
                while fmt[i] in '1234567890':
                    n = n * 10 + ord(fmt[i]) - ord('0')
                    i += 1
                if fmt[i] == 's':
                    args_cnt += 1
                    if left:
                        dest+=str(args[args_cnt]).ljust(n)
                        left = 0
                    else:
                        dest+=str(args[args_cnt]).rjust(n)
                else:
                    raise("format error")
            else:
                dest+=fmt[i]
                i-=1
        else:
            dest+=fmt[i]
        i += 1
    return dest
    
def sformat(*narg):
    return sformat0(narg)

def str_join(sep, list):
    text = ''
    for i in range(len(list)):
        if i != 0:
            text += sep + str(list[i])
        else:
            text += list[i]
    return text

def list_join(list, sep):
    return str_join(sep, list)
    
def _list_copy(self):
    l = []
    for item in self:
        l.append(item)
    return l
add_obj_method("list", "copy", _list_copy)
  
def printf(*args):
    write(sformat0(args))

add_builtin("printf", printf)

def uncode16(a,b):
    return ord(a) * 256 + ord(b)

def escape(text):
    if gettype(text) != 'string':
        raise "<function escape> expect a string"
    des = ""
    for c in text:
        if c == '\r':des+='\\r'
        elif c == '\n':des+='\\n'
        elif c == '\b':des += '\\b'
        elif c == '\\':des += '\\\\'
        elif c == '\"':des += '\\"'
        elif c == '\0':des += '\\0'
        else:des+=c
    return des


def quote(obj):
    if gettype(obj) == 'string':
        return '"' + escape(obj) + '"'
    else:
        return str(obj)


''' file system tools '''
def copy(src, des):
    bin = load(src)
    save(des, bin)
    
def mtime(fname):
    import os
    obj = os.stat(fname)
    return obj.st_mtime

'''
tools for tinyvm to bootstrap
'''

def _import(des_glo, fname, tar = None):
    'this _import function can not prevent import circle'
    if fname in __modules__:
        pass
    else:
        import os
        exists = os.exists
        # printf("try to load module %s\n", fname)
        from encode import *
        # can not find file in current dir.
        if not exists(fname + '.py'):
            # try to find in PATH defined in file.
            if 'PATH' in des_glo:
                fname = des_glo["PATH"] + FILE_SEP + fname
            # still can not be found? find in LIB_PATH
            if not exists(fname + '.py'):
                libname = LIB_PATH + FILE_SEP + fname
            if not exists(libname + ".py"):
                raise(sformat("import error, can not open file \"%s.py\"", fname))
            else:
                fname = libname
        try:
            #__modules__[fname] = {}
            _code = compilefile(fname + '.py')
        except Exception as e:
            #del __modules__[fname]
            raise(sformat('import error: fail to compile file "%s.py":\n\t%s', fname, e))
        load_module(fname, _code)
    g = __modules__[fname]
    if tar == '*':
        for k in g:
            # _ stands for private variable
            # and #N is a special variable created by tinyvm compiler
            if k[0] != '_' and k[0] != '#':
                des_glo[k] = g[k]
    elif tar == None:
        des_glo[fname] = g
    else:
        if tar not in g:
            raise(sformat("import error, no definition named '%s'", tar))
        des_glo[tar] = g[tar]
    # return g, return none

def hasattr(obj, name):
    return name in obj

def Exception(e):
    return e

class Lib:
    def __init__(self, name, path, load = 1):
        self.name = name
        self.path = path
        self.load = load

# built-in functions.
#_libs = [
    #Lib("builtins", "libs/builtins.py"),
    #Lib("dis", "libs/tools/dis.py", 1),
    #Lib("printast", "libs/tools/printast.py", 1), 
    #Lib("repl", "libs/tools/repl.py"),
    #Lib("pyeval", "libs/tools/pyeval.py"),
    #Lib("test", "libs/tools/test.py")
#]

def require(path, name = None):
    'for modules which can not import by import statement'
    if path in __modules__:
        return __modules__[path]
    code = compilefile(path)
    if name == None:
        name = path
    m = load_module(name, code)
    __modules__[path] = m
    return m

if getosname() == "nt":
    FILE_SEP = '\\'
else:
    FILE_SEP = '/'

def split_path(path):
    cached_pathes = []
    name = ''
    for c in path:
        if c == '/' or c == '\\':
            cached_pathes.append(name)
            name = ''
        else:
            name += c
    if name != '':cached_pathes.append(name)
    return cached_pathes

# join a list like ['home', 'usr'] to a dir "home/usr"
# also handle pathes like 'home/usr/../proc' to "home/proc"
def join_path(path_list):
    if len(path_list) == 0: return ""
    else: lastdir = path_list.pop()
    path = ''
    cleanpath = []
    for item in path_list:
        if item == '..':
            cleanpath.pop()
        elif item == '.':
            pass
        else:
            cleanpath.append(item)
    for item in cleanpath:
        path += item + FILE_SEP
    return path + lastdir


def resolvepath(path):
    if not ('/' in path or '\\' in path):
        return path
    import os
    fs1 = split_path(os.getcwd())
    fs2 = split_path(path)
    fname = fs2.pop()
    parent = join_path(fs1+fs2)
    os.chdir(parent)
    return fname
    
def execfile(path, chdir = True):
    from encode import *
    if chdir:
        fname = resolvepath(path)
    else:
        fname = path
    _code = compilefile(fname)
    # printf("run file %s ...\n", fname)
    load_module(fname, _code, '__main__')

def to_fixed(num, length):
    return str(num).rjust(length).replace(' ', '0')

def dis(path):
    from encode import *
    from tmcode import *
    ins_list = compile_to_list(load(path), path)
    for index, item in enumerate(ins_list):
        op = int(item[0])
        line = to_fixed(index+1, 4) + ' ' + tmcodes[op].ljust(22) + str(item[1])
        print(line)

def _assert(exp, err = None):
    if not exp: 
        msg = ""
        if err is not None:
            msg = str(err)
        raise "AssertionError, " + msg
    
def __debug__(fidx):
    info = vmopt("frame.info", fidx)
    lcnt = info.maxlocals
    print(info.fname, info.lineno)
    for i in range(lcnt):
        printf("#"+str(i))
        repl_print(vmopt("frame.local", fidx, i))
    input("continue")
    
# add_obj_method("str", "format", sformat)
add_obj_method('str', 'ljust', ljust)
add_obj_method('str', 'rjust', rjust)
add_obj_method('str', 'center', center)
add_obj_method('str', 'join', str_join)
add_obj_method('list', 'join', list_join)
add_builtin("uncode16", uncode16)
add_builtin("add_builtin", add_builtin)
add_builtin("Exception", Exception)
add_builtin("hasattr", hasattr)
add_builtin("_import", _import)
add_builtin("copy", copy)
add_builtin("mtime", mtime)
add_builtin("sformat0", sformat0)
add_builtin("sformat", sformat)
add_builtin("escape", escape)
add_builtin("quote", quote)
add_builtin("execfile", execfile)
add_builtin("assert", _assert)
add_builtin("__debug__", __debug__)
add_builtin("require", require)

    
LIB_PATH = ''
def boot(loadlibs=True):
    from lex import *
    from encode import *
    from repl import *
    import sys
    import os
    global LIB_PATH
    argv = sys.argv
    argc = len(argv)
    pathes = split_path(os.getcwd())
    pathes.append("libs")
    LIB_PATH = join_path(pathes)
    if argc == 0:
        repl()
    else:
        if os.exists(argv[0]):
            execfile(argv[0])
        elif argv[0] == "-dis":
            dis(argv[1])
        else:
            print("file not exists, exit")
            