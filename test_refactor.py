# 待重构的代码
def calculate(a, b, op):
    if op == 'add':
        return a + b
    elif op == 'sub':
        return a - b
    elif op == 'mul':
        return a * b
    elif op == 'div':
        if b != 0:
            return a / b
        else:
            return None
    else:
        return None

def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result

def format_name(first, last):
    return last + ', ' + first
