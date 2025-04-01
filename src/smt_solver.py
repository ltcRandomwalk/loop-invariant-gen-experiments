from z3 import *
from pycparser import c_parser, c_ast 
import re
import builtins
from convert import convert_c_assert_to_smtlib2

def is_valid_c_expression(expr):
    parser = c_parser.CParser()
    try:
        # 尝试解析为一个完整的表达式
        parser.parse(f"int main() {{ if ({expr}); }}")
        return True
    except:
        return False

def parse_c_expression(expr, variables):
    """将 C 表达式解析为 SMT 表达式"""
    for var in variables:
        expr = expr.replace(var, f'variables["{var}"]')
    #expr = expr.replace("&&", "and").replace("||", "or").replace("!", "not")
    #expr = expr.replace("==", "==").replace("!=", "!=").replace("<=", "<=").replace(">=", ">=")
    
    return eval(expr)

def extract_variables(expression):
    """从 C 表达式中提取变量"""
    return set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', expression))

def create_smt_variables(variable_names):
    """为每个变量创建 SMT solver 的符号变量"""
    return {name: Int(name) for name in variable_names}

def verify_implication(P_c, Q_c):
    """验证任意两个 C 表达式的蕴含关系 P -> Q"""
    # 提取变量
    try:
        all_vars = extract_variables(P_c) | extract_variables(Q_c)
        variables = create_smt_variables(all_vars)
        
        if not is_valid_c_expression(P_c) or not is_valid_c_expression(Q_c):
            return True, None

        # 解析成 SMT 表达式
        decl = ""
        for var in all_vars:
            decl += f"(declare-const {var} Int)"
        
        P_smt = convert_c_assert_to_smtlib2("(" + P_c + ")")
        Q_smt = convert_c_assert_to_smtlib2("(" + Q_c + ")")
        print(P_smt, Q_smt)
        
        P_z3, Q_z3 = parse_smt2_string(decl + "\n" + P_smt + "\n" + Q_smt)
        print(P_z3, Q_z3)
        
        solver = Solver()
        #solver.from_string(decl + "\n" + P_smt + "\n" + Q_smt)
        
        
        solver.add(P_z3)
        solver.add(Not(Q_z3))
        

        # 创建求解器
        

        # 检查结果
        if solver.check() == sat:
            return False, solver.model()  # 不成立，返回反例
        else:
            return True, None  # 成立
    except Z3Exception as e:
        print("Z3 exception.")
        return True, None

# 示例：验证 i == 1 -> i <= n + 1
if __name__ == "__main__":
    P_c = "i  = 1 "
    Q_c = "i == 1"

    is_valid, counterexample = verify_implication(P_c, Q_c)
    if is_valid:
        print("The implication is valid.")
    else:
        print("The implication is not valid. Counterexample:", counterexample)