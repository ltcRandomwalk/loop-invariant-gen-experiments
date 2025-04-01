from z3 import *

def is_valid_expression(e):
    """
    递归检查Z3表达式是否符合要求：
    1. 不包含True或BoolVal(True)
    2. 所有原子子句均为比较操作（如x > 0），而非单独的变量
    """
    if is_true(e):
        # 检测到true常量
        return False
    if is_not(e):
        # 处理逻辑非，检查子表达式
        return is_valid_expression(e.arg(0))
    if is_and(e) or is_or(e):
        # 处理逻辑与/或，递归检查所有子表达式
        return all(is_valid_expression(c) for c in e.children())
    if is_comparison(e):
        # 比较表达式（如x > 0）合法
        return True
    if is_const(e) and e.sort() == BoolSort():
        # 单独的布尔变量非法
        return False
    # 其他情况（如算术表达式）非法
    return False

def check_c_expression(expr_str, variables):
    """
    检查C表达式是否合法
    :param expr_str: 表达式字符串，如 "(x > 0) && (y < 5)"
    :param variables: 变量名到类型的字典，如 {'x': Int('x'), 'y': Int('y')}
    :return: (是否合法, 错误信息)
    """
    # 检查是否含有"true"
    if 'true' in expr_str.lower():
        return False, "Expression contains 'true' literal"
    
    # 尝试解析表达式为Z3格式
    try:
        # 将变量添加到环境，供eval使用
        env = {k: v for k, v in variables.items()}
        # 使用z3的eval解析表达式
        parsed_expr = eval(expr_str, {}, env)
    except Exception as e:
        return False, f"Parse error: {str(e)}"
    
    # 检查表达式结构
    if is_valid_expression(parsed_expr):
        return True, "Valid expression"
    else:
        return False, "Invalid subclause (contains bare variable or disallowed structure)"

# 示例用法
if __name__ == "__main__":
    # 定义变量（根据实际情况调整）
    x = Int('x')
    y = Int('y')
    b = Bool('b')
    variables = {'x': x, 'y': y, 'b': b}
    
    # 测试用例
    test_cases = [
        ("(x > 0) && (y < 5)", True),   # 合法
        ("b || (x == 0)", False),        # b是单独变量
        ("(x + y > 0) || true", False), # 含有true
        ("(x > 0) && (y)", False),       # y单独出现（但y是Int，无法作为布尔表达式，解析会失败）
        ("(x < 10) || (y > 5)", True),  # 合法
        ("! (x == 0)", True),            # 合法
        ("!b", False)                    # b是单独变量
    ]
    
    for expr, expected in test_cases:
        valid, msg = check_c_expression(expr, variables)
        print(f"Expression: {expr}")
        print(f"Expected: {expected}, Result: {valid}, Message: {msg}")
        print("------")