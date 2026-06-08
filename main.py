import knime.scripting.io as knio
import pandas as pd
import time
import shlex
from collections import deque

nodes_df = knio.input_tables[0].to_pandas()
edges_df = knio.input_tables[1].to_pandas()


node_id_col = nodes_df.columns[0]
node_label_col = nodes_df.columns[1]

edge_source_col = edges_df.columns[0]
edge_target_col = edges_df.columns[1]

possible_arg_vars = ["args_BFS", "args_DFS", "args_IDS", "args_DLS"]

args_string = ""
used_var = ""

for var_name in possible_arg_vars:
    if var_name in knio.flow_variables:
        args_string = str(knio.flow_variables[var_name])
        used_var = var_name
        break

if args_string is None:
    args_string = ""

try:
    tokens = shlex.split(args_string, posix=False)
except Exception:
    tokens = str(args_string).split()

tokens = [str(t).strip('"').strip("'") for t in tokens]


def parse_args(tokens, used_var):

    if len(tokens) >= 6:
        directed_input = tokens[2]
        start_input = tokens[3]
        target_input = tokens[4]
        algorithm_choice = tokens[5]
        depth_limit = int(tokens[6]) if len(tokens) >= 7 else 10

    elif len(tokens) >= 4:
        directed_input = tokens[0]
        start_input = tokens[1]
        target_input = tokens[2]
        algorithm_choice = tokens[3]
        depth_limit = int(tokens[4]) if len(tokens) >= 5 else 10

    else:
        directed_input = "0"
        start_input = ""
        target_input = ""
        depth_limit = 10

        if used_var == "args_BFS":
            algorithm_choice = "1"
        elif used_var == "args_DFS":
            algorithm_choice = "2"
        elif used_var == "args_IDS":
            algorithm_choice = "3"
        elif used_var == "args_DLS":
            algorithm_choice = "4"
        else:
            algorithm_choice = "1"

    return directed_input, start_input, target_input, algorithm_choice, depth_limit


try:
    directed_input, start_input, target_input, algorithm_choice, depth_limit = parse_args(tokens, used_var)
except Exception:
    directed_input = "0"
    start_input = ""
    target_input = ""
    depth_limit = 10

    if used_var == "args_BFS":
        algorithm_choice = "1"
    elif used_var == "args_DFS":
        algorithm_choice = "2"
    elif used_var == "args_IDS":
        algorithm_choice = "3"
    elif used_var == "args_DLS":
        algorithm_choice = "4"
    else:
        algorithm_choice = "1"

directed = True if str(directed_input).strip() == "1" else False


id_to_label = {}
label_to_id = {}
adj_list = {}

def trim(value):
    return str(value).strip(" \t\r\n")

def make_error(error_name, algo_name="ERROR"):
    return pd.DataFrame([{
        "Algorithm": algo_name,
        "Found": "false",
        "PathLength": 0,
        "Path": "",
        "Iterations": 0,
        "MaxStatesStored": 0,
        "TimeMS": 0,
        "Message": error_name
    }])

def get_algo_name(choice):
    if str(choice) == "1":
        return "BFS"
    if str(choice) == "2":
        return "DFS"
    if str(choice) == "3":
        return "IDS"
    if str(choice) == "4":
        return "DLS"
    return "ERROR"

def get_label(node_id):
    return id_to_label.get(node_id, node_id)

def get_neighbors(node_id):
    return adj_list.get(node_id, [])

def build_path(target_id, parent):
    path = []
    current = target_id

    while current != "":
        path.append(get_label(current))
        if current not in parent:
            break
        current = parent[current]

    path.reverse()
    return path

def path_to_string(path):
    return " -> ".join(path)

def result_row(algo_name, found, target_id, parent, iterations, max_states_stored, ms):
    if not found:
        return pd.DataFrame([{
            "Algorithm": algo_name,
            "Found": "false",
            "PathLength": 0,
            "Path": "",
            "Iterations": iterations,
            "MaxStatesStored": max_states_stored,
            "TimeMS": ms,
            "Message": "Target non trovato"
        }])

    path = build_path(target_id, parent)

    return pd.DataFrame([{
        "Algorithm": algo_name,
        "Found": "true",
        "PathLength": max(0, len(path) - 1),
        "Path": path_to_string(path),
        "Iterations": iterations,
        "MaxStatesStored": max_states_stored,
        "TimeMS": ms,
        "Message": "OK"
    }])


for _, row in nodes_df.iterrows():
    node_id = trim(row[node_id_col])
    label = trim(row[node_label_col])

    if node_id == "" or label == "":
        continue

    if node_id not in id_to_label:
        id_to_label[node_id] = label

    if label not in label_to_id:
        label_to_id[label] = node_id

    if node_id not in adj_list:
        adj_list[node_id] = []

for _, row in edges_df.iterrows():
    source = trim(row[edge_source_col])
    target = trim(row[edge_target_col])

    if source == "" or target == "":
        continue

    if source not in id_to_label or target not in id_to_label:
        continue

    adj_list.setdefault(source, []).append(target)

    if not directed:
        adj_list.setdefault(target, []).append(source)

def get_node_id_from_input(user_input):
    cleaned = trim(user_input)

    if cleaned in label_to_id:
        return True, label_to_id[cleaned]

    if cleaned in id_to_label:
        return True, cleaned

    return False, ""


def run_BFS(start_id, target_id):
    t0 = time.perf_counter()

    q = deque()
    visited = set()
    parent = {}

    q.append(start_id)
    visited.add(start_id)
    parent[start_id] = ""

    found = False
    iterations = 0
    max_states_stored = len(q) + len(visited) + len(parent)

    while q:
        current_states = len(q) + len(visited) + len(parent)
        if current_states > max_states_stored:
            max_states_stored = current_states

        current = q.popleft()
        iterations += 1

        if current == target_id:
            found = True
            break

        for neighbor in get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                q.append(neighbor)

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return result_row("BFS", found, target_id, parent, iterations, max_states_stored, duration_ms)


def run_DFS(start_id, target_id):
    t0 = time.perf_counter()

    stack = []
    visited = set()
    inserted = set()
    parent = {}

    stack.append(start_id)
    inserted.add(start_id)
    parent[start_id] = ""

    found = False
    iterations = 0
    max_states_stored = len(stack) + len(visited) + len(inserted) + len(parent)

    while stack:
        current_states = len(stack) + len(visited) + len(inserted) + len(parent)
        if current_states > max_states_stored:
            max_states_stored = current_states

        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)
        iterations += 1

        if current == target_id:
            found = True
            break

        for neighbor in get_neighbors(current):
            if neighbor not in visited and neighbor not in inserted:
                parent[neighbor] = current
                stack.append(neighbor)
                inserted.add(neighbor)

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return result_row("DFS", found, target_id, parent, iterations, max_states_stored, duration_ms)


def DLS_recursive(current, target, limit, parent, path_visited, stats):
    stats["iterations"] += 1

    current_states = len(parent) + len(path_visited)
    if current_states > stats["max_states_stored"]:
        stats["max_states_stored"] = current_states

    if current == target:
        return True

    if limit == 0:
        return False

    for neighbor in get_neighbors(current):
        if neighbor not in path_visited:
            parent[neighbor] = current
            path_visited.add(neighbor)

            if DLS_recursive(neighbor, target, limit - 1, parent, path_visited, stats):
                return True

            path_visited.remove(neighbor)
            parent.pop(neighbor, None)

    return False

def run_DLS(start_id, target_id, limit):
    t0 = time.perf_counter()

    parent = {start_id: ""}
    path_visited = {start_id}
    stats = {
        "iterations": 0,
        "max_states_stored": 0
    }

    found = DLS_recursive(start_id, target_id, limit, parent, path_visited, stats)

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return result_row(
        "DLS",
        found,
        target_id,
        parent,
        stats["iterations"],
        stats["max_states_stored"],
        duration_ms
    )

def run_IDS(start_id, target_id, max_depth):
    t0 = time.perf_counter()

    found = False
    total_iterations = 0
    max_states_stored = 0
    final_parent = {}
    last_parent = {}

    for limit in range(max_depth + 1):
        parent = {start_id: ""}
        path_visited = {start_id}
        stats = {
            "iterations": 0,
            "max_states_stored": 0
        }

        result = DLS_recursive(start_id, target_id, limit, parent, path_visited, stats)

        total_iterations += stats["iterations"]

        if stats["max_states_stored"] > max_states_stored:
            max_states_stored = stats["max_states_stored"]

        last_parent = parent

        if result:
            found = True
            final_parent = parent
            break

    duration_ms = int((time.perf_counter() - t0) * 1000)

    return result_row(
        "IDS",
        found,
        target_id,
        final_parent if found else last_parent,
        total_iterations,
        max_states_stored,
        duration_ms
    )


algo_name = get_algo_name(algorithm_choice)

if len(id_to_label) == 0:
    output_df = make_error("ERROR_EMPTY_NODES_FILE", algo_name)

else:
    ok_start, start_id = get_node_id_from_input(start_input)
    ok_target, target_id = get_node_id_from_input(target_input)

    if not ok_start:
        output_df = make_error("ERROR_START_NODE_NOT_FOUND", algo_name)

    elif not ok_target:
        output_df = make_error("ERROR_TARGET_NODE_NOT_FOUND", algo_name)

    elif str(algorithm_choice) == "1":
        output_df = run_BFS(start_id, target_id)

    elif str(algorithm_choice) == "2":
        output_df = run_DFS(start_id, target_id)

    elif str(algorithm_choice) == "3":
        output_df = run_IDS(start_id, target_id, depth_limit)

    elif str(algorithm_choice) == "4":
        output_df = run_DLS(start_id, target_id, depth_limit)

    else:
        output_df = make_error("ERROR_INVALID_ALGORITHM", algo_name)


knio.output_tables[0] = knio.Table.from_pandas(output_df)