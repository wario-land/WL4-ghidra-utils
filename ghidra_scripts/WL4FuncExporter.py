#Auto-generate the patch file which can be used in WL4Editor
#@author shinespeciall
#@category Examples->Python
#@keybinding 
#@menupath 
#@toolbar 

# changelog: 
# v0.1: auto generate then print all the #define lines in the console for functions and global variables used in the TARGET_FUNC
#       it seems the Ghidra cannot parse multiple line comments

# the import here is like shit, but i don't want to find out useless lines manually
from ghidra.app.decompiler import DecompileOptions
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model import listing
from ghidra.program.model.symbol import SymbolUtilities

# change this before using the script
TARGET_FUNC = "Sub_801C43C_GmWarInit"

funcs = getGlobalFunctions(TARGET_FUNC)

# Parse symbols address from the target function
label_list = []
function_list = []
for func in funcs:
    if func.getName() == TARGET_FUNC:
        func_body = func.getBody()
        listing = currentProgram.getListing()
        opiter = listing.getInstructions(func_body, True)
        while opiter.hasNext():
            op = opiter.next()
            raw_pcode = op.toString()

            if (raw_pcode[0:3] == "ldr"):
                tmp_addr_str = raw_pcode[raw_pcode.find("[") + 1 : raw_pcode.find("]")]
                if (tmp_addr_str[0:1] == "r"):
                    continue;
                value = int(tmp_addr_str, 16)
                if value not in label_list:
                    label_list.append(value)

            if (raw_pcode[0:3] == "bl "):
                tmp_addr_str = raw_pcode[3:]
                value = int(tmp_addr_str, 16)
                if value not in function_list:
                    function_list.append(value)
        break

# parse symbols from symbol addresses
symbol_define_str_list = []
function_define_str_list = []

# helper function to get a Ghidra Address type
def getAddress(offset):
    return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(offset)

# Functions
functionManager = currentProgram.getFunctionManager()
ifc = DecompInterface()
ifc.openProgram(currentProgram)
monitor = ConsoleTaskMonitor()
for fun_addr_num in function_list:
    try:
        func_instance = functionManager.getFunctionAt(getAddress(fun_addr_num))
        funcName = func_instance.getName()
    except AttributeError:
        print("cannot parse function address: {}".format(hex(fun_addr_num)))
        pass
    f_prototype_str = func_instance.getSignature().getPrototypeString()
    f_param_str = f_prototype_str[f_prototype_str.find("(") : f_prototype_str.find(")") + 1]
    f_return_type_str = f_prototype_str[0 : f_prototype_str.find(" ")]
    f_define_str = "#define " + funcName + " ((" + f_return_type_str + " (*)" + f_param_str + ") " + hex(fun_addr_num | 1) + ")"
    function_define_str_list.append(f_define_str)

# Global Symbols
# assumse all the ram symbols look like: "addr" + " " + addreess_str
# assumse all the rom symbols look like: "ddw" + " " + addreess_str + "h"
parsed_symbol_name_str = []
for i in range(len(label_list)):
    label_addr_num = label_list[i]
    data_instance = getDataAt(toAddr(label_addr_num))
    data_str = data_instance.toString()
    if (data_str[-1] == "h"):
        data_str = data_str[0: data_str.find("h")]
    data_addr_str = data_str[data_str.find(" ") + 1 : ]
    data_addr_num = int("0x" + data_addr_str, 16)
    data_addr_str = hex(data_addr_num)
    sym_instance = getSymbolAt(toAddr(data_addr_num))
    sym_name = ""
    type_str = "int"
    if sym_instance is not None:
        sym_name = sym_instance.getName()

        # try to infer type by size
        if getSymbolAt(toAddr(data_addr_num + 1)) is not None:
            type_str = "char"
        elif getSymbolAt(toAddr(data_addr_num + 2)) is not None:
            type_str = "short"
    else:
        sym_name = "Data_" + data_addr_str[data_str.find("x") + 1 : ]
    if (sym_name in parsed_symbol_name_str):
        continue
    s_define_str = "#define " + sym_name + " (*( volatile unsigned " + type_str + "*) " + data_addr_str + ")"
    symbol_define_str_list.append(s_define_str)
    parsed_symbol_name_str.append(sym_name)

# test
for entry in symbol_define_str_list:
    print(entry)
print
for entry in function_define_str_list:
    print(entry)
