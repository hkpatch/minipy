# -*- coding:utf-8 -*-
# @author xupingmao
# @since 2016
# @modified 2018/02/18 11:27:51

from boot import *
cheader = '''/*
* @author xupingmao<578749341@qq.com>
* @generated by Python
* @date %s
*/
#ifndef INSTRUCTION_H_
#define INSTRUCTION_H_
'''
ctail = "\n#endif\n\n"

_opcode_names = [
    'OP_STRING', 'OP_NUMBER',
    "OP_IMPORT",
    'OP_ADD', 'OP_SUB', 'OP_MUL', 'OP_DIV', 'OP_MOD', 'OP_NEG',
    'OP_NOT', 'OP_GT', 'OP_LT', 'OP_GTEQ', 'OP_LTEQ', 'OP_EQEQ', 'OP_NOTEQ', 'OP_IN', 'OP_NOTIN',
    'OP_AND', 'OP_OR', 'OP_SET', 
    'OP_GET',
    'OP_SLICE',
    'OP_NONE', 'OP_STORE_LOCAL', 'OP_STORE_GLOBAL', 'OP_LOAD_LOCAL', 'OP_LOAD_GLOBAL', 'OP_CONSTANT',
    #'LOAD_GLOBALS', 
    'OP_POP', 
    'OP_DICT_SET',
    'OP_LIST', 'OP_DICT', 
    'OP_APPEND',
    'OP_JUMP', 'OP_UP_JUMP', 'OP_POP_JUMP_ON_FALSE', 'OP_JUMP_ON_FALSE', 'OP_JUMP_ON_TRUE',
    #TAGSIZE
    'OP_UNPACK', 'OP_ROT', 'OP_DEL', 'OP_FOR', 'OP_NEXT', 'OP_ITER', 'OP_LOAD_EX',
    'OP_SETJUMP', 
    
    'OP_CALL', 
    'OP_TAILCALL',
    'OP_APPLY', # apply(a, b)
    'OP_DEF', 'OP_RETURN', 

    'OP_LOAD_PARAMS', 'OP_LOAD_NARG', "OP_LOAD_PARG",

    'OP_EOF',
    "OP_CLR_JUMP",
    'OP_EOP',
    # mulity assignment, eg. x,y = 1,2
    'OP_DEBUG',
    'OP_LINE',
    'OP_TAG', 
    # instructions for vm to optimize.
    'OP_FAST_ST_GLO',
    'OP_FAST_LD_GLO',
    'OP_FILE',
    # unused instructions
    #'LT_JUMP_ON_FALSE', 
    #'GT_JUMP_ON_FALSE',
    #'LTEQ_JUMP_ON_FALSE',
    #'GTEQ_JUMP_ON_FALSE',
    #'EQEQ_JUMP_ON_FALSE',
    #'NOTEQ_JUMP_ON_FALSE',
]

# update global values.
i = 0
tmcodes = {}
while i < len(_opcode_names):
    name = _opcode_names[i]
    globals()[name] = i + 1
    tmcodes[i+1] = name
    i += 1

def export_clang_define(des, self = None):
    # check modified time
    # if src is modified before des and cdes, do not convert.
    if self == None:
        self = ARGV[0]
    if not exists(des):
        pass
    elif mtime(self) < mtime(des):
        return
    defines = []
    i = 0
    while i < len(_opcode_names):
        x = _opcode_names[i]
        defines.append('#define '+ x + ' ' + str(i+1))
        i += 1
    ctext = cheader % str(asctime()) + '\n'.join(defines) + ctail
    save(des, ctext)
    # save('../include/instruction.h', ctext)

if __name__ == '__main__':
    export_clang_define('instruction.h')
