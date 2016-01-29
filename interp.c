/**
  * date : 2014-9-2
  * 2015-6-16: interpreter for tinyvm bytecode.
 **/

#include "include/interp.h"
#include "include/exception.h"
#include "include/function.h"

#define INTERP_DB 0

Object callFunction(Object func) {
    Object ret;
    if (IS_FUNC(func)) {
        resolveMethodSelf(func);
        /* call native */
        if (GET_FUNCTION(func)->native != NULL) {
            return GET_FUNCTION(func)->native();
        } else {
            TmFrame* f = pushFrame(func);
            /*
            if (GET_FUNCTION(func)->modifier == 0) {
                return tm_eval(f);
            }*/
            L_recall:
            if (setjmp(f->buf)==0) {
                return tm_eval(f);
            } else {
                f = tm->frame;
                /* handle exception in this frame */
                if (f->jmp != NULL) {
                    f->pc = f->jmp;
                    f->jmp = NULL;
                    goto L_recall;
                /* there is no handler, throw to last frame */
                } else {
                    pushException(f);
                    tm->frame--;
                    longjmp(tm->frame->buf, 1);
                }
            }
        }
    } else if (IS_DICT(func)) {
        ret = class_new(func);
        Object *_fnc = dictGetByStr(ret, "__init__");
        if (_fnc != NULL) {
            callFunction(*_fnc);
        }
        return ret;
    }
    tm_raise("File %o, line=%d: callFunction:invalid object %o", GET_FUNCTION_FILE(tm->frame->fnc), 
        tm->frame->lineno, func);
    return NONE_OBJECT;
}


void popFrame() {
    tm->frame --;
}

#define TM_OP(OP_CODE, OP_FUNC) case OP_CODE: \
    *(top-1) = OP_FUNC(*(top-1), *top);--top;\
    break;
    
#define FRAME_CHECK_GC()  \
f->top = top; \
if (tm->allocated > tm->gcThreshold) {   \
    gc_full();                            \
}

TmFrame* pushFrame(Object fnc) {
    /* make extra space for self in method call */
    Object *top = tm->frame->top + 2;
    tm->frame ++ ;
    TmFrame* f = tm->frame;

    /* check oprand stack */
    if (top >= tm->stack + STACK_SIZE) {
        popFrame();
        tm_raise("tm_eval: stack overflow");
    }
    
    /* check frame stack*/
    if (tm->frame >= tm->frames + FRAMES_COUNT-1) {
        popFrame();
        tm_raise("tm_eval: frame overflow");
    }

    f->pc = GET_FUNCTION(fnc)->code;

    f->locals = top;
    f->maxlocals = getFunctionMaxLocals(GET_FUNCTION(fnc));
    f->stack = f->locals + f->maxlocals;
    f->top = f->stack;
    f->fnc = fnc;
 
    // clear local variables
    int i;for(i = 0; i < f->maxlocals; i++) {
        f->locals[i] = NONE_OBJECT;
    }
    *(f->top) = NONE_OBJECT;
    f->jmp = NULL;
    return f;
}


#define PREDICT_JMP(flag) \
    if (!flag && pc[3] == POP_JUMP_ON_FALSE) { \
        top--;\
        pc += 3; \
        i = (pc[1] << 8) | pc[2]; \
        pc += i * 3; \
        continue;\
    } else { \
        *top = tm_number(flag); \
    }

/** 
** evaluate byte code.
** @param f: Frame
** @return evaluated value.
*/
Object tm_eval(TmFrame* f) {
    Object* locals = f->locals;
    Object* top = f->stack;
    Object cur_fnc = f->fnc;
    Object globals = getGlobals(cur_fnc);
    unsigned char* pc = f->pc;

    Object x, k, v;
    Object ret = NONE_OBJECT;
    int i;

    #if INTERP_DB
        printf("File \"%s\": enter function %s\n",getFuncFileSz(cur_fnc), getFuncNameSz(cur_fnc));
    #endif
    while (1) {
        i = (pc[1] << 8) | pc[2];
        
        #if INTERP_DB
            printf("%30s%2d: %d frame = %d, top = %d\n","", pc[0], i, tm->cur, (int) (top - f->stack));
        #endif    
        switch (pc[0]) {

        case NEW_NUMBER: {
            double d = atof((char*)pc + 3);
            pc += i;
            v = tm_number(d);
            /* tm_append(tm->constants,v);*/
            dictSet(tm->constants, v, NONE_OBJECT);
            break;
        }

        case NEW_STRING: {
            v = string_alloc((char*)pc + 3, i);
            pc += i;
            /* tm_append(tm->constants,v); */
            dictSet(tm->constants, v, NONE_OBJECT);
            break;
        }

        case OP_IMPORT: {
            Object import_func = tm_getglobal(globals, string_static("_import"));
            arg_start();
            arg_push(globals);
            if (i == 1) {
                arg_push(TM_POP());
            } else {
                Object b = TM_POP();
                Object a = TM_POP();
                arg_push(a);
                arg_push(b);
            }
            callFunction(import_func);
            break;
        }
        case LOAD_CONSTANT: {
            TM_PUSH(GET_CONST(i));
            /* predict , eg. SET, GET etc. */
            /*
            pc += 3;
            if (pc[0] == SET) {
                // need to check whether is a dict. 
            } else if(pc[0] == GET) {
                
            }
            */
            break;
        }
        
        case LOAD_NONE: {
            TM_PUSH(NONE_OBJECT);
            break;
        }

        case LOAD_LOCAL: {
            TM_PUSH(locals[i]);
            break;
        }

        case STORE_LOCAL:
            locals[i] = TM_POP();
            break;

        case LOAD_GLOBAL: {
            /* tm_printf("load global %o\n", GET_CONST(i)); */
            int idx = dict_get_attr(GET_DICT(globals), i);
            if (idx == -1) {
                idx = dict_get_attr(GET_DICT(tm->builtins), i);
                if (idx == -1) {
                    tm_raise("NameError: name %o is not defined", GET_CONST(i));
                }
                TM_PUSH(GET_DICT(tm->builtins)->nodes[idx].val);
            } else {
                TM_PUSH(GET_DICT(globals)->nodes[idx].val);
                pc[0] = FAST_LD_GLO;
                code16(pc+1, idx);
            }
            break;
        }
        case STORE_GLOBAL: {
            x = TM_POP();
            int idx = dict_set_attr(GET_DICT(globals), i, x);
            pc[0] = FAST_ST_GLO;
            code16(pc+1, idx);
            break;
        }
        case FAST_LD_GLO: {
            TM_PUSH(GET_DICT(globals)->nodes[i].val);
            break;
        }
        case FAST_ST_GLO: {
            GET_DICT(globals)->nodes[i].val = TM_POP();
            break;
        }
        case LIST: {
            TM_PUSH(list_new(2));
            FRAME_CHECK_GC();
            break;
        }
        case LIST_APPEND:
            v = TM_POP();
            x = TM_TOP();
            tmAssertType(x, TYPE_LIST, "tm_eval: LIST_APPEND");
            list_append(GET_LIST(x), v);
            break;
        case DICT_SET:
            v = TM_POP();
            k = TM_POP();
            x = TM_TOP();
            tmAssertType(x, TYPE_DICT, "tm_eval: DICT_SET");
            tm_set(x, k, v);
            break;
        case DICT: {
            TM_PUSH(dict_new());
            FRAME_CHECK_GC();
            break;
        }
        TM_OP(ADD, tm_add)
        TM_OP(SUB, tm_sub)
        TM_OP(MUL, tm_mul)
        TM_OP(DIV, tm_div)
        TM_OP(MOD, tm_mod)
        TM_OP(GET, tm_get)
        case EQEQ: { *(top-1) = tm_number(tm_equals(*(top-1), *top)); top--; break; }
        case NOTEQ: { *(top-1) = tm_number(!tm_equals(*(top-1), *top)); top--; break; }
        case OP_LT: {
            *(top-1) = tm_number(tm_cmp(*(top-1), *top)<0);
            top--;
            // int flag = tm_cmp(*(top-1), *top) < 0;
            // top--;
            // predict
            // PREDICT_JMP(flag);
            break;
        }
        case LTEQ: {
            *(top-1) = tm_number(tm_cmp(*(top-1), *top)<=0);
            top--;
            break;
        }
        case OP_GT: {
            *(top-1) = tm_number(tm_cmp(*(top-1), *top)>0);
            top--;
            break;
        }
        case GTEQ: {
            *(top-1) = tm_number(tm_cmp(*(top-1), *top)>=0);
            top--;
            break;
        }
        case OP_IN: {
            *(top-1) = tm_number(tm_has(*top, *(top-1)));
            top--;
            break;
        }
        case AND: {
            *(top-1) = tm_number(tm_bool(*(top-1)) && tm_bool(*top));
            top--;
            break;
        }
        case OR: {
            *(top-1) = tm_number(tm_bool(*(top-1)) || tm_bool(*top));
            top--;
            break;
        }
        case NOT:{
            *top = tm_number(!tm_bool(*top));
            break;
        }
        case SET:
            k = TM_POP();
            x = TM_POP();
            v = TM_POP();
            #if INTERP_DB
                tm_printf("Self %o, Key %o, Val %o\n", x, k, v);
            #endif
            tm_set(x, k, v);
            break;
        case POP: {
            top--;
            break;
        }
        case NEG:
            TM_TOP() = tm_neg(TM_TOP());
            break;
        case CALL: {
            f->top = top;
            top -= i;
            tm_setArguments(top + 1, i);
            Object func = TM_POP();
            #if INTERP_DB
                printf("call %s\n", getFuncNameSz(func));
            #endif
            TM_PUSH(callFunction(func));
            tm->frame = f;
            FRAME_CHECK_GC();
            break;
        }
        case LOAD_PARAMS: {
            int parg = pc[1];
            int varg = pc[2];
            if (tm->arg_cnt < parg || tm->arg_cnt > parg + varg) {
                tm_raise("ArgError,parg=%d,varg=%d,given=%d", 
                    parg, varg, tm->arg_cnt);
            }
            for(i = 0; i < tm->arg_cnt; i++){
                locals[i] = tm->arguments[i];
            }
            break;
        }
        case TM_NARG: {
            Object list = list_new(tm->arg_cnt);
            for(i = 0; i < tm->arg_cnt; i++) {
                tm_append(list, tm->arguments[i]);
            }
            locals[0] = list;
            break;
        }
        case ITER_NEW: {
            *top = iter_new(*top);
            break;
        }
        case TM_NEXT: {
            Object *next = tm_next(*top);
            if (next != NULL) {
                TM_PUSH(*next);
                break;
            } else {
                pc += i * 3;
                continue;
            }
            break;
        }
        case TM_DEF: {
            Object mod = GET_FUNCTION(cur_fnc)->mod;
            //pc += 3;
            //Code reg_code = parseCode(pc);
            //pc += 3;
            //Code jmp_code = parseCode(pc);
            Object fnc = func_new(mod, NONE_OBJECT, NULL);
            pc = func_resolve(GET_FUNCTION(fnc), pc);
            // GET_FUNCTION(fnc)->code = pc + 3;
            // GET_FUNCTION(fnc)->maxlocals = reg_code.val;
            // GET_FUNCTION(fnc)->maxstack = reg_code.val;
            GET_FUNCTION_NAME(fnc) = GET_CONST(i);
            // pc += jmp_code.val * 3;
            TM_PUSH(fnc);
            continue;
        }
        case RETURN: {
            ret = TM_POP();
            goto end;
        }
        case TM_ROT: {
            int half = i / 2;
            int j;
            for (j = 0; j < half; j++) {
                Object temp = *(top - j);
                *(top-j) = *(top - i + j + 1);
                *(top-i+j+1) = temp;
            }
            break;
        }
        case TM_UNARRAY: {
            x = TM_POP();
            tmAssertType(x, TYPE_LIST, "tm_eval:TM_UNARRAY");
            int j;
            for(j = LIST_LEN(x)-1; j >= 0; j--) {
                TM_PUSH(LIST_GET(x, j));
            }
            break;
        }

        case TM_DEL: {
            k = TM_POP();
            x = TM_POP();
            tm_del(x, k);
            break;
        }

        case POP_JUMP_ON_FALSE: {
            if (!tm_bool(TM_POP())) {
                pc += i * 3;
                continue;
            }
            break;
        }

        case JUMP_ON_TRUE: {
            if (tm_bool(TM_TOP())) {
                pc += i * 3;
                continue;
            }
            break;
        }

        case JUMP_ON_FALSE: {
            if (!tm_bool(TM_TOP())) {
                pc += i * 3;
                continue;
            }
            break;
        }

        case UP_JUMP:
            pc -= i * 3;
            continue;

        case JUMP:
            pc += i * 3;
            continue;

        case TM_EOP:
        case TM_EOF: {
           ret = NONE_OBJECT;
           goto end;
        }

        case LOAD_EX: { top = f->last_top; TM_PUSH(tm->ex); break; }
        case SETJUMP: { f->last_top = top; f->jmp = pc + i * 3; break; }
        case CLRJUMP: { f->jmp = NULL; break;}
        case TM_LINE: { f->lineno = i; break;}

        case TM_DEBUG: {
            Object fdebug = tm_getglobal(globals, string_static("__debug__"));
            f->top = top;
            tm_call(fdebug, 1, tm_number(tm->frame - tm->frames));        
            break;
        }

        default:
            tm_raise("BAD INSTRUCTION, %d\n  globals() = \n%o", pc[0],
                    GET_FUNCTION_GLOBALS(f->fnc));
            goto end;
        }

        pc += 3;
    }

    end:
    /*
    if (top != f->stack) {
        tm_raise("tm_eval: operand stack overflow");
    }*/
    popFrame();
    return ret;
}
