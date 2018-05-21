import sys
import json
import subprocess

b_count = 0 
# used to keep track of BUFFER NUMBERS
# since variable redeclaration is not allowed in C++
# we give each buffer a number to ensure our socket buffers for
# each variable that is being sent or received has a unique name
# 
# INVARIANT: 
# all buffers are generated from the  base case of our recursive function, 
# so it increases if and only if a base case is reached and code for 
# that primitive is generated. For purposes of our code "VOID" is a type
# that generates "" (empty string) as code and also increases the count
# 
# Each READLEN variable also shares this number with its associated counter
# 
# TODO: Although invariant makes it safe to use, probably should turn it into
# a local variable

#read the preamble from template file and change it 
def generate_preamble(filename, is_proxy):
    if is_proxy:
        template_name = "proxy.template"
    else:
        template_name = "stub.template"
    return open(template_name).read().replace('IDL_NAME', filename)

def generate_file(data, filename, is_proxy):
    s = generate_preamble(filename, is_proxy)
    functions_str = ''
    for func_name in data["functions"]:
        function_head = generate_func_head(func_name, data, is_proxy)
        function_args = generate_args(func_name, data, is_proxy)
        function_return = generate_return(func_name, data, is_proxy)
        function = function_head + function_args + function_return
        functions_str += function 
    s = s.replace('FUNCTIONS', functions_str)
    s = s.replace('DISPATCH', generate_dispatch(is_proxy,data))
    s = s.replace("$VAR$", "")
    if (is_proxy):
        s = s.replace('$SOCKET$', "RPCPROXYSOCKET")
        output_name = filename[:-3] + "proxy.cpp"
    else:
        s = s.replace('$SOCKET$', "RPCSTUBSOCKET")
        output_name = filename[:-3] + "stub.cpp"
    open(output_name, 'w').write(s)

#generates the function signature
def generate_func_head(func_name, data, is_proxy):
    value = data["functions"][func_name]
    SEND_FUNC_TEMPLATE = '$SOCKET$->write("+FUNC+", strlen("+FUNC+") + 1);\n\n'
    if (not is_proxy):
        return_type = "void"
        func_name = "__" + func_name
        args = ""
        SEND_FUNC_TEMPLATE = ""
        func_call = '*GRADING << "' + func_name[2:] + '() function call'\
                    ' received"'' << endl;\n\n' #need to escape the quotes
    else:
        return_type = value["return_type"]
        func_call = '*GRADING << "'+ func_name + '() function call sent"'\
                    ' << endl;\n\n'
        args = ""
        for arg in value["arguments"]:
            args += instantiate(arg["name"], arg["type"], data) + ", "
        args = args[:-2]
    s = '//\n//\t' + func_name + ' definition\n//\n'
    s += return_type + " " + func_name + "(" + args + ")" + ' {\n'
    s += SEND_FUNC_TEMPLATE
    s = s.replace("+FUNC+", func_name)
    s += func_call
    return s

#generates the variable declaration
def instantiate(name, ty, data, brackets=''):
    cur_ty = data["types"][ty]
    if (cur_ty["type_of_type"] == "builtin" or 
        cur_ty["type_of_type"] == "struct"):
        return ty + ' ' + name + brackets

    elif cur_ty['type_of_type'] == 'array':
        brackets += '[' + str(cur_ty['element_count']) + ']'
        return instantiate(name, cur_ty['member_type'], data, brackets)

    # THIS SHOULD NOT HAPPEN
    else:
        return ""

#generates the function body which either sends or receives the args
#if we are in proxy it is send
#if we are in stub  it is receive
def generate_args(func_name, data, is_proxy):
    if (is_proxy):
        kind = "send"
    else:
        kind = "receive"
    value = data["functions"][func_name]
    args = ""
    for arg in value["arguments"]:
        if (kind == "receive"):
            arg_declare = instantiate(arg["name"], arg["type"], data) + ";\n"
        else:
            arg_declare = ""
        arg_body = generate_arg(arg["name"], arg["type"], kind, data)
        args += (arg_declare + arg_body)
    return args

#TODO: refactor this and above function into a single function
#return type is the opposite of an arg
#if we are in proxy it is receive
#if we are in stub  it is send
#this also adds the function invoke to stub
#and return statement to proxy    
def generate_return(func_name, data, is_proxy):
    if (is_proxy):
        kind = "receive"
    else:
        kind = "send"
    ret_type = data["functions"][func_name]["return_type"]
    return_str = ""
    arg = ""
    if (kind == 'receive'):
        func_call = ""
        if (ret_type != 'void'):
            arg += instantiate("R3TURN", ret_type, data) +';\n' 
            return_str = "return R3TURN;"
    else:
        func_call = generate_func_call(func_name, data)
    arg += generate_arg("R3TURN", ret_type, kind, data)
    s = func_call + arg + return_str + '\n}\n\n'

    return s

#generates thecode that sends the function name across the wire 
def generate_func_call(func_name, data):
    value = data["functions"][func_name]
    args = ''
    for arg in value["arguments"]:
        args += arg["name"] + ", "
    args = args[:-2]
    s = ""
    if (value["return_type"] != "void"):
        s += value["return_type"] + " R3TURN = "
    s += func_name + '(' + args + ');\n'
    return s;

#heart of the program 
#recursively generates the code associated with an arg
#TODO: AS OF NOW variable names 
#BUFF3R_N (where N is a number) (yes 3 is a delibreate choice to decrease risk 
#                                                               of collusion)
#READL3N_N
#COUNT3R_N 
#R3TURN
#ARE RESERVED FOR internal use. Therefore if a variable or a field in a struct
#shares a name with any of these, our program will break. We can fix this
#by iterating through the json and making sure there is no conflict by
#increaing N. We understand the importance of naming.
def generate_arg(name, ty, kind, data, count = 0):
    cur_ty = data["types"][ty]
    s = ""
    global b_count
    if (cur_ty["type_of_type"] == "builtin"):
        s += get_template(ty, kind)
        s = s.replace("$VAR$", '$VAR$' + name)
        s = s.replace("#K#", str(b_count))
        b_count += 1
    elif (cur_ty["type_of_type"] == "struct"):
        for member in cur_ty["members"]:
            s += generate_arg(member["name"], member["type"], kind, data, 
                              count)
        s = s.replace("$VAR$", '$VAR$' + name +".")
    elif (cur_ty["type_of_type"] == "array"):
         s += get_template("array", kind, cur_ty["element_count"], count)
         member_ty = cur_ty["member_type"]
         s += generate_arg(('[COUNT3R_' + str(count) + ']'), member_ty, 
                             kind, data, count + 1)
         s = s.replace("$VAR$", '$VAR$' + name)
         s += '\n}\n'
    else: #THIS SHOULD NOT HAPPEN
        s += ""

    return s

def get_template(ty, kind, count=0, counter_count=0):
    t = {}
    t['send'] = {}
    t['receive'] = {}
    t['receive']['void']   = ''
    t['send']['void']      = ''
    t['send']['int']       = 'char BUFF3R_#K#[INT_BUFFER_SIZE];\n' \
                             'snprintf(BUFF3R_#K#, sizeof(BUFF3R_#K#), "%d",' \
                             ' $VAR$);\n' \
                             '$SOCKET$->write(BUFF3R_#K#, INT_BUFFER_SIZE);\n'\
                             '*GRADING << "Sent an INT named $VAR$'\
                             ' equal to " << $VAR$ << endl;\n\n'
    t['receive']['int']    = 'char BUFF3R_#K#[INT_BUFFER_SIZE];\n' \
                             '$SOCKET$->read(BUFF3R_#K#, INT_BUFFER_SIZE);\n' \
                             '$VAR$ = atoi(BUFF3R_#K#);\n' \
                             '*GRADING << "Received an INT named $VAR$'\
                             ' equal to " << $VAR$ << endl;\n\n'
    t['send']['string']    = '$SOCKET$->write($VAR$.c_str(), $VAR$.length()'\
                              '+1);\n'\
                             '*GRADING << "Sent a STRING named $VAR$ '\
                             ' equal to " << $VAR$ << endl;\n\n'      
    t['receive']['string'] = 'char BUFF3R_#K#[STRING_BUFFER_SIZE];\n' \
                             'ssize_t READL3N_#K#;\n' \
                             'while (true) {\n' \
                             'READL3N_#K# = $SOCKET$->read(BUFF3R_#K#,'\
                             'STRING_BUFFER_SIZE);\n'\
                             'if (READL3N_#K# == 0 || BUFF3R_#K#[0] == "0" )'\
                             '{\n\tbreak;\n' \
                             '}\n' \
                             '$VAR$ += BUFF3R_#K#[0];\n' \
                             '}\n'\
                             '*GRADING << "Received a STRING named $VAR$ '\
                             ' equal to " << $VAR$ << endl;\n\n'
    t['send']['float']     = 'char BUFF3R_#K#[FLOAT_BUFFER_SIZE];\n' \
                             'snprintf(BUFF3R_#K#, sizeof(BUFF3R_#K#), "'\
                             '%40.40f",''$VAR$);\n' \
                             '$SOCKET$->write(BUFF3R_#K#, '\
                             'FLOAT_BUFFER_SIZE);\n'\
                             '*GRADING << "Sent an FLOAT named $VAR$ '\
                             ' equal to " << $VAR$ << endl;\n\n'
    t['receive']['float']  = 'char BUFF3R_#K#[FLOAT_BUFFER_SIZE];\n' \
                             '$SOCKET$->read(BUFF3R_#K#, '\
                             'FLOAT_BUFFER_SIZE);\n' \
                             '$VAR$ = atof(BUFF3R_#K#);\n' \
                             '*GRADING << "Received a FLOAT named $VAR$'\
                             ' equal to " << $VAR$ << endl;\n\n'
    t['send']['array']     = ('for (int COUNT3R_$N$ = 0; COUNT3R_$N$ < ' +
                              str(count) + '; COUNT3R_$N$++){\n')
    t['receive']['array']  = ('for (int COUNT3R_$N$ = 0; +COUNT3R_$N$ < ' +
                              str(count) + '; COUNT3R_$N$++){\n')
    return t[kind][ty].replace("$N$", str(counter_count))

def generate_dispatch(is_proxy, data):
    if (is_proxy):
        return ""
    functions = data["functions"].keys()
    s = ""
    s += 'if (strcmp(functionNameBuffer,"'
    s += functions[0]
    s += '") == 0)\n'
    s += '\t\t__' + functions[0] + '();\n'

    for func in functions[1:]:
        s += '\t else if (strcmp(functionNameBuffer,"' + func + '") == 0)\n'
        s += '\t\t__' + func + '();\n'
    return s

if __name__ == "__main__":
    for filename in sys.argv[1:]:
        decl = json.loads(subprocess.check_output(["./idl_to_json", filename]))
        generate_file(decl, filename, True) #true is for proxy
        generate_file(decl, filename, False) #false is for stub
