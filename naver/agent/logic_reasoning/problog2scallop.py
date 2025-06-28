import re


def translate_problog_rule_to_scallop(problog_rule):

    # Function to split the body into predicates, respecting parentheses
    def split_predicates(body):
        predicates = []
        current_pred = ''
        level = 0  # Parentheses nesting level
        in_string = False
        i = 0
        while i < len(body):
            char = body[i]
            if char == '"':
                in_string = not in_string
                current_pred += char
            elif char == '(' and not in_string:
                level += 1
                current_pred += char
            elif char == ')' and not in_string:
                level -= 1
                current_pred += char
            elif char == ',' and level == 0 and not in_string:
                predicates.append(current_pred.strip())
                current_pred = ''
            else:
                current_pred += char
            i += 1
        if current_pred.strip():
            predicates.append(current_pred.strip())
        return predicates

    # Remove any leading or trailing whitespace
    problog_rule = problog_rule.strip()

    # Split the rule into head and body
    if ':-' in problog_rule:
        head, body = problog_rule.split(':-')
        head = head.strip()
        body = body.strip().rstrip('.')
    else:
        raise ValueError("Invalid Problog rule format")

    # Extract head predicate and variables
    head_match = re.match(r'(\w+)\((.*)\)', head)
    if head_match:
        head_pred = head_match.group(1)
        head_vars = head_match.group(2).strip()
    else:
        raise ValueError("Invalid head in Problog rule")

    # Use the split_predicates function to correctly split the body
    predicates = split_predicates(body)

    scallop_rule = f'rel {head_pred}({head_vars}) = '
    conditions = []
    for pred in predicates:
        pred_match = re.match(r'(\w+)\((.*)\)', pred)
        if pred_match:
            pred_name = pred_match.group(1)
            pred_args = pred_match.group(2)
            # Process arguments
            arg_str = pred_args.strip()
            # Handle commas inside strings or nested parentheses
            args = []
            arg = ''
            level = 0
            in_string = False
            j = 0
            while j < len(arg_str):
                c = arg_str[j]
                if c == '"':
                    in_string = not in_string
                    arg += c
                elif c == '(' and not in_string:
                    level += 1
                    arg += c
                elif c == ')' and not in_string:
                    level -= 1
                    arg += c
                elif c == ',' and level == 0 and not in_string:
                    args.append(arg.strip())
                    arg = ''
                else:
                    arg += c
                j += 1
            if arg.strip():
                args.append(arg.strip())
            # Replace Problog anonymous variables (_) with Scallop's _
            args = [a if a != '_' else '_' for a in args]
            pred_args_str = ', '.join(args)
            conditions.append(f'{pred_name}({pred_args_str})')
        else:
            raise ValueError(f"Invalid predicate in Problog rule: {pred}")

    scallop_rule += ' and '.join(conditions)
    return scallop_rule
