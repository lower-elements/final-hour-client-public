import contextlib


def parse_data(data):
    parsed = {}
    lines = data.split("\n")
    stack = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.endswith("{"):
            obj_type = line[:-1].strip()
            obj = {}
            if stack:
                if obj_type not in stack[-1]:
                    stack[-1][obj_type] = []
                stack[-1][obj_type].append(obj)
            else:
                if obj_type not in parsed:
                    parsed[obj_type] = []
                parsed[obj_type].append(obj)
            stack.append(obj)
        elif line == "}":
            stack.pop()
        else:
            split_line = line.split("=", 1)
            name, value = split_line[0], "=".join(split_line[1:])
            name = name.strip()
            value = to_value(value.strip())
            stack[-1][name] = value
    return parsed


def to_value(text):
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    with contextlib.suppress(ValueError):
        return int(text)
    with contextlib.suppress(ValueError):
        return float(text)
    return text
