#include "vm.c"

#ifdef TM_USE_CACHE
    #include "cache_interp.c"
    #include "cache_bin.c"
#else
    #include "interp.c"
    #include "bin.c"
#endif


#ifdef TM_USE_CACHE

int main(int argc, char *argv[])
{
    /* start vm with bin */
    int ret = vm_init(argc, argv);
    if (ret != 0) { 
        return ret;
    }
    // tm->code = bin;

    /* use first frame */
    int code = setjmp(tm->frames->buf);
    if (code == 0) {
        // printf("load modules\n");
        /* init modules */
        time_mod_init();
        sys_mod_init();
        math_mod_init();
        os_mod_init();
        
        tm_load_module2("init", init_bin);
        tm_load_module2("lex", lex_bin);
        tm_load_module2("parse", parse_bin);
        tm_load_module2("tmcode", tmcode_bin);
        tm_load_module2("encode", cache_encode_bin);
        tm_load_module2("pyeval", pyeval_bin);
        tm_load_module2("repl", repl_bin);
        dict_set_by_str(tm->builtins, "TM_USE_CACHE", tm_number(1));
 
        if (tm_hasattr(tm->modules, "init")) {
            call_mod_func("init", "boot");
        } else if (tm_hasattr(tm->modules, "main")) {
            // adjust sys.argv
            call_mod_func("main", "_main");
        }
    } else if (code == 1){
        traceback();
    } else if (code == 2){
    }
    vm_destroy();
    return 0;
}

#else
int main(int argc, char *argv[])
{
    /* start vm with bin */
    int ret = vm_init(argc, argv);
    if (ret != 0) { 
        return ret;
    }
    tm->code = bin;

    /* use first frame */
    int code = setjmp(tm->frames->buf);
    if (code == 0) {
        /* init modules */
        time_mod_init();
        sys_mod_init();
        math_mod_init();
        os_mod_init();
    
        load_binary();
        dict_set_by_str(tm->builtins, "TM_USE_CACHE", tm_number(1));
 
        if (tm_hasattr(tm->modules, "init")) {
            call_mod_func("init", "boot");
        } else if (tm_hasattr(tm->modules, "main")) {
            // adjust sys.argv
            
            call_mod_func("main", "_main");
        }
    } else if (code == 1){
        traceback();
    } else if (code == 2){
        
    }
    vm_destroy();
    return 0;
}
#endif
