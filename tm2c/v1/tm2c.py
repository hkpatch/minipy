from parse import *
import sys
from tmtokenize import *
from boot import *

tm_obj = "Object "
tm_const = "Object const_"

tm_pusharg = "tm_pusharg("
tm_call = "tm_call("

tm_num = "tm_number("
tm_str = "string_new("
tm_get_glo = "tm_get_global("
tm_define = "def_func"

func_bool = "is_true_obj"
func_add = "obj_add"
func_sub = "obj_sub"
func_mul = "obj_mul"
func_div = "obj_div"
func_mod = "obj_mod"
func_cmp = "obj_cmp"
func_not = "obj_not"
func_neg = "obj_neg"
func_get = "obj_get"
func_set = "obj_set"
func_list = "array_to_list"
func_method = "def_method"

op_bool = [">", ">=", "<", "<+", "==", "!=", "and", "or", "in", "not"]

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

        
class Scope:
    def __init__(self, prev):
        self.vars = []
        self.g_vars = []
        self.prev = prev
        self.temp = 0
    def add_global_var(self, name):
        if name not in self.g_vars:
            self.g_vars.append(name)
        
class Env:
    def __init__(self, fname, prefix = None):
        self.consts = []
        self.scope = Scope(None)
        self.global_scope = self.scope
        self.indent = 0
        self.fname = fname
        self.func_defines = []
        self.func_cnt = 0
        if prefix == None:
            self.prefix = get_valid_code_name(fname) + "_"
        else:
            self.prefix = get_valid_code_name(prefix) + "_"

        self.builtin_dict = {
            "print": "bf_print",
            "str"  : "bf_str"
        }
    
    def new_scope(self):
        scope = Scope(self.scope)
        self.scope = scope
        
    def exit_scope(self, func_define):
        if self.scope != None:
            self.scope = self.scope.prev
        else:
            raise "fatal error"
        self.func_defines.append(func_define)
        self.func_cnt += 1
        
    def get_c_func_name(self, name):
        # return self.prefix + "F" + str(self.func_cnt) 
        if name in self.builtin_dict:
            return self.builtin_dict[name]
        return self.prefix + name

    def get_mod_name(self):
        return self.fname
            
    def get_const(self, val):
        if val not in self.consts:
            self.consts.append(val)
        return self.prefix+ "C" + str(self.consts.index(val))
        
    def get_var_name(self, name):
        return self.prefix + "V" + name

    def get_temp_var_name(self):
        temp = new_temp(self)
        return self.prefix + "V" + temp

    # you must declare temp var in your scope
    def get_temp_ptr_name(self):
        temp = new_temp(self)
        return self.prefix + "P" + temp
        
    def locals(self):
        if self.scope != None:
            return self.scope.vars
            
    def get_globals(self):
        return self.prefix + "0g";
            
    def has_var(self, name):
        scope = self.scope
        while scope != None:
            if name in scope.vars:
                return True
            scope = scope.prev
        return False
        
    def def_var(self, name):
        if self.has_var(name):
            pass
        else:
            self.scope.vars.append(name)

    def def_global_var(self, name):
        self.scope.add_global_var(name)

    def is_global_var(self, name):
        return self.scope == self.global_scope or \
            name in self.scope.g_vars




def get_valid_code_name(fname):
    fname = fname.replace("-", "_")
    fname = fname.replace(".", "_")
    return fname
        

class AstNode:
    def __init__(self, type, first = None, second = None):
        self.type = type
        self.first = first
        self.second = second



def get_string_def(value):
    return '"' + escape(str(value)) + '"'

class Generator:

    def __init__(self, env):
        self.env = env


    def process(self, lines):
        
        env = self.env
        define_lines = []
        # assign constants
        # define_lines.append("  " + env.get_globals() + "=dict_new();");
        define_lines.append(env.get_globals() + "=dict_new();")
        

        for const in env.consts:
            h = env.get_const(const) + "="
            if gettype(const) == "number":
                body = "tm_number(" + str(const) + ");"
            elif gettype(const) == "string":
                body = "string_new(" + get_string_def(str(const)) + ');'
            define_lines.append(h+body)
        define_lines.append("tm_def_mod(\"{}\", {});".format(env.get_mod_name(), env.get_globals()))
            
        lines = define_lines + lines
            
        head = "#define TM_NO_BIN 1\n"
        head += '#include "../tm2c.c"\n'
        head += "/* DEFINE START */\n"
        # define constants
        for const in env.consts:
            head += "Object " + env.get_const(const) + ";\n";
        head += "Object " + env.get_globals() + ";\n"
        # do vars
        for var in env.locals():
            head += "Object " + env.get_var_name(var) + ";\n"
        head += "/* DEFINE END */\n\n"
        
        # function define.
        for func_define in env.func_defines:
            head += func_define + "\n\n"
        
        # global 
        head += "void " + env.prefix + "main(){\n"
        code =  head + "\n".join(lines)+"\n}\n"

        # main entry
        code += sformat("\nint main(int argc, char* argv[]) {\ntm_run_func(argc, argv, \"%s\", %smain);\n}\n", env.get_mod_name(), env.prefix)
        self.code = code

    def get_code(self):
        return self.code


def new_temp(env):
    c = env.scope.temp
    env.scope.temp += 1
    name = str(c)
    env.def_var(name)
    return name

def do_assign(item, env, right = None):
    left = item.first
    if istype(left, "list"):
        raise "multi-assignment not implemented"
    if right == None:
        right = do_item(item.second, env)
    if left.type == 'name':
        name = left.val
        if not env.has_var(name):
            env.def_var(name)
        code = env.get_var_name(name) + "=" + right + ";"
        if env.is_global_var(name):
            code += "\n" + "obj_set({}, {}, {});".format(env.get_globals(), \
                do_const(left, env), env.get_var_name(name))
        return code
    elif left.type == ",":
        return "// not implemented"
    elif left.type == "get":
        print("assign get")
        return sformat("%s(%s,%s,%s);", func_set, do_name(left.first, env), do_const(left.second, env), right)
    elif left.type == "attr":
        lfirst = Token("string", left.first.val)
        return sformat("%s(%s,%s,%s);", func_set, do_name(lfirst,env), do_const(left.second,env), right)

def do_const(item, env):
    val = item.val
    if val not in env.consts:
        env.consts.append(val)
    return env.get_const(val) # "const_" + str(env.consts.index(val))
    
def do_name(item, env):
    if env.has_var(item.val):
        return env.get_var_name(item.val)
    item = Token("string", item.val)
    return tm_get_glo + env.get_globals() + "," + do_const(item, env) + ")"

def do_none(item, env):
    return "NONE_OBJECT"
    
def do_list(item, env):
    v = item.first
    cnt = 0
    if v == None:
        cnt = 0
        return sformat("%s(0)", func_list)
    newlist = []
    if istype(v, "list"):
        for item in v:
            code = do_item(item, env)
            newlist.append(code)
        cnt = len(newlist)
    else:
        newlist.append(do_item(v, env))
        cnt = 1
    if cnt == 0:
        return sformat("%s(0)", func_list)
    else:
        return sformat("%s(%s,%s)", func_list, cnt, ",".join(newlist)) 
    
def do_bool(item, env):
    if item.type in op_bool:
        return do_item(item, env)
    return func_bool + "(" + do_item(item, env) + ")"
    
def do_block(list, env, indent=0):
    lines = []
    for exp in list:
        if exp.type == "string": continue
        line = do_item(exp, env, indent + 2)
        if exp.type == "call": line += ";"
        lines.append(line)
    return lines
    
def do_if(item, env, indent=0):
    cond = do_bool(item.first, env)
    lines = do_block(item.second, env, indent)
    third = item.third
    head = sformat("if(%s) %s", cond, format_block(lines, indent))
    if third == None:
        pass
    elif gettype(third) == "list":
        return head + "else" + format_block(do_block(third, env, 2),indent)
    else:
        # lines.append(do_item(third, env, indent))
        return head + "else " + do_item(third, env, 2)
    return head

def do_for(item, env, indent=0):
    temp = env.get_temp_var_name()
    temp_ptr = env.get_temp_ptr_name()
    expr = item.first
    block = item.second

    names = expr.first
    assert len(names) == 1, "only support 1 item for statement"
    _keyname = names[0].val

    iterator = do_item(expr.second, env)

    env.def_var(_keyname)
    keyname = env.get_var_name(_keyname)
    
    key = do_name(names[0], env);
    init = sformat("%s = iter_new(%s);", temp, iterator)
    init += "\n" + "Object* " + temp_ptr + ";";
    get_next = "{} = next_ptr({});".format(temp_ptr, temp)
    head = "while ({} != NULL)".format(temp_ptr)
    head = get_next + "\n" + head
    lines = do_block(block, env)
    key_assignment = "{} = *{};".format(keyname, temp_ptr)
    lines.insert(0, key_assignment)
    lines.append(get_next)
    return sformat("%s\n%s %s", init, head, format_block(lines))

    
def do_while(item, env, indent=0):
    cond = do_bool(item.first, env)
    lines = do_block(item.second, env, indent)
    return sformat("while(%s) %s", cond, format_block(lines, indent))

def do_args(item, env):
    if item == None:
        return ""
    elif istype(item, "list"):
        args = "";
        for i in item:
            args += ", " + do_item(i, env)
        return args
    return "," + do_item(item, env)

def get_line_no(item):
    if hasattr(item, "pos"):
        return item.pos[0]
    elif hasattr(item, "first"):
        return get_line_no(item.first)
    
def do_call(item, env):
    if item.first.type == "name":
        name = env.get_c_func_name(item.first.val)
        fmt = "tm_call_native({}, {}, {} {})"
    else:
        name = do_item(item.first, env)
        fmt = "tm_call({}, {}, {} {})"
    if item.second == None:
        n = 0
    elif istype(item.second, "list"):
        n = len(item.second)
    else:
        n = 1
    args = do_args(item.second, env)
    # tm_call(lineno, func, nargs, args)
    return fmt.format(get_line_no(item), name, n, args)
    # return tm_call + name + "," + + "," + str(n) + args + ")"
    
def format_block(lines, indent=0):
    text = "{\n";
    for line in lines: 
        if line != None:
            text += line + "\n"
    # return text + indent * " " + "}\n"
    return text + "}\n"
    
def do_getargs(list, env, indent):
    r = []
    for item in list:
        if item.type == "varg":
            node = AstNode("=", item.first, item.second)
            code = do_assign(node, env)
            r.append(code)
        line = do_assign(item, env, "tm_take_arg()")
        r.append(line)
    return r
    
def do_def(item, env, indent=0, obj=None):
    env.new_scope()
    name = item.first.val
    args = do_getargs(item.second, env, 2)
    lines = args + do_block(item.third, env, 0)
    cname = env.get_c_func_name(name)
    if obj!=None:
        obj.name = cname
        obj.constname = env.get_const(name)
    locs = env.locals()
    vars = ["// " + name]
    for var in locs:
        vars.append("Object " + env.get_var_name(var) + ";")
    # lines = ['puts("enter function %s");'.format(name)] + lines
    func_define = "Object " + cname + "() " + format_block(vars+lines, 0)
    env.exit_scope(func_define)
    return sformat("%s(%s,%s, %s);", 
        tm_define, env.get_globals(), env.get_const(name), cname)
    
def do_return(item, env, indent=0):
    ret = do_item(item.first, env, 0)
    if ret == "":
        return "return NONE_OBJECT;"
    else:
        return "return " + ret + ";"
    
def do_class(item, env, indent=0):
    class_define = do_assign(item, env, "dict_new()")
    class_name = do_name(item.first, env)
    obj = newobj()
    lines = []
    for class_item in item.second:
        type = class_item.type
        if type == "pass": continue
        assert type == "def"
        do_def(class_item, env, indent+2, obj)
        lines.append(sformat("%s(%s,%s,%s);", func_method, class_name, obj.constname, obj.name))
    text = class_define + "\n"
    for line in lines:
        text += line + "\n"
    return text
    
def do_op(item, env, func):
    return func + "(" + do_item(item.first, env) + "," + do_item(item.second, env) + ")";

def do_or(item, env):
    return "(" + do_item(item.first, env) + "||" + do_item(item.second, env) + ")"
    
def do_and(item, env):
    return "(" + do_item(item.first, env) + "&&" + do_item(item.second, env) + ")"
    
def do_mul(item, env):
    return do_op(item, env, func_mul)
    
def do_div(item, env):
    return do_op(item, env, func_div)
    
def do_mod(item, env):
    return do_op(item, env, func_mod)
    
def do_add(item, env):
    return do_op(item, env, func_add)
    
def do_sub(item, env):
    return do_op(item, env, func_sub)
    
def do_lt(item, env):
    return do_op(item, env, func_cmp) + "<0"
    
def do_gt(item, env):
    return do_op(item, env, func_cmp) + ">0"
    
def do_le(item, env):
    return do_op(item, env, func_cmp) + "<=0"
    
def do_ge(item, env):
    return do_op(item, env, func_cmp) + ">=0"

def do_ne(item, env):
    return "(" + do_op(item, env, "!obj_equals") + ")"
    
def do_eq(item, env):
    return do_op(item, env, "obj_equals")
    
def do_not(item, env):
    value = do_item(item.first, env)
    if not value.startswith("is_true_obj"):
        return "!is_true_obj(" + value + ")"
    return sformat("!(%s)", value)

def do_neg(item, env):
    return sformat("%s(%s)", func_neg, do_item(item.first, env))
    
def do_get(item, env):
    return do_op(item, env, func_get)
    
def do_attr(item, env):
    second = item.second
    item.second = Token("string", second.val)
    item.second.pos = second.pos
    return do_op(item, env, func_get)

def do_in(item, env):
    return do_op(item, env, "obj_in")
    
def do_inplace_op(item, env, op):
    item2 = AstNode(op, item.first, item.second)
    tk = AstNode("=", item.first, item2)
    return do_assign(tk, env)
    
def do_inplace_add(item, env):
    return do_inplace_op(item, env, "+")
    
def do_inplace_sub(item, env):
    return do_inplace_op(item, env, "-")
    
def do_inplace_mul(item, env):
    return do_inplace_op(item, env, "*")
    
def do_inplace_div(item, env):
    return do_inplace_op(item, env, "/")
    
def do_inplace_mod(item, env):
    return do_inplace_op(item, env, '%')


def do_import(item, env):
    mod = do_const(item.first, env)
    return "tm_import({}, {});".format(env.get_globals(), mod)

def do_from(item, env):
    mod = do_const(item.first, env)
    return "tm_import_all({}, {});".format(env.get_globals(), mod)    

def do_global(item, env):
    g_name = item.first.val
    env.def_global_var(g_name)
    # name = do_const(item.first, env)
    code = "// global " + g_name
    # code += "obj_set(%s, %s, NONE_OBJECT);".format(env.get_globals(), name)
    return code

def do_break(item, env):
    return "break;"

def do_continue(item, env):
    return "continue;"

_handlers = {
    "if": do_if,
    "while": do_while,
    "def": do_def,
    "return": do_return,
    "class": do_class,
    "for": do_for,

    # items
    "number": do_const,
    "string": do_const,
    "name": do_name,
    "None": do_none,
    "list": do_list,
    "=": do_assign,
    "+": do_add,
    "-": do_sub,
    "*": do_mul,
    "/": do_div,
    "%": do_mod,
    "<": do_lt,
    ">": do_gt,
    ">=": do_ge,
    "<=": do_le,
    "!=": do_ne,
    "==": do_eq,
    "+=": do_inplace_add,
    "-=": do_inplace_sub,
    "*=": do_inplace_mul,
    "/=": do_inplace_div,
    "%=": do_inplace_mod,
    "or": do_or,
    "and": do_and,
    "not": do_not,
    "neg": do_neg,
    "call": do_call,
    "get": do_get,
    "attr": do_attr,
    "in": do_in,
    "import": do_import,
    "from": do_from,
    "global": do_global,
    "break": do_break,
    "continue": do_continue
}

def do_item(item, env, indent = 0):
    func = None
    env.token = item
    if item == None:
        return ""
    if not hasattr(item, "type"):
        repl_print(item, 1, 4)
        raise
    if item.type in _handlers:
        func = _handlers[item.type]
        code = func(item, env)
    if func != None:
        # if indent > 0: code = " " * indent + code
        return code

# env
# consts, globals, scopes.

def do_program(tree, env, indent):
    try:
        return do_block(tree, env, 0)
    except Exception as e:
        # repl_print(tree, 2, 5)
        # print_ast(tree)
        compile_error(env.fname, env.src, env.token, e)

def tm2c(fname, src, prefix=None):
    tree = parse(src)
    # repl_print(tree, 0, 5)
    #env = {"vars": [], "consts": [], "funcs": [], "globals":[]}
    words = fname.split(".")
    mod_name = words[0]
    # mod_name = fname.substring(0, len(fname)-3)
    env = Env(fname, prefix)
    env.src = src

    init_main = AstNode("=")
    init_main.first = Token("name", "__name__")
    init_main.second = Token("string", "__main__")
    init__name__  = do_item(init_main, env)

    lines = do_program(tree, env, 0)
    lines = [init__name__] + lines

    generator = Generator(env)
    generator.process(lines)
    return generator.get_code()
    
if __name__ == "__main__":
    name = sys.argv[1]
    # path = "../test/tm2c/" + name
    path = name
    text = load(path)
    pathes = path.split('/')
    if len(pathes) > 1:
        name = pathes[-1]
    mod = name.split(".")[0]
    code = tm2c(name, text, mod)
    save("output/" + mod + ".c", code)
    # save("bin/" + mod + ".c", code)
