#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KMINE Python CLI
----------------
Sostituto del programma C++ KMINE.cpp con la stessa interfaccia a riga di comando.

Parametri:
    argv[1] = file nodi CSV
    argv[2] = file archi CSV
    argv[3] = grafo diretto: 1 = diretto, 0 = non diretto
    argv[4] = nodo iniziale (ID o label)
    argv[5] = nodo obiettivo (ID o label)
    argv[6] = algoritmo:
              1 = BFS
              2 = DFS
              3 = IDS
              4 = DLS
    argv[7] = opzionale: limite profondità per IDS/DLS (default 10)
    argv[8] = opzionale: file output CSV (default risultati.csv)

Output CSV compatibile con il workflow KNIME costruito sul C++:
    Algorithm,Found,PathLength,Path,Iterations,MaxStatesStored,TimeMS,Message
"""

from __future__ import annotations
import csv
import sys
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple, Set

sys.setrecursionlimit(10000)

# =========================
# GLOABALI GRAFO
# =========================
id_to_label: Dict[str, str] = {}
label_to_id: Dict[str, str] = {}
adj_list: Dict[str, List[str]] = {}
output_file: str = "risultati.csv"


# =========================
# UTILS
# =========================
def trim(value: str) -> str:
    return str(value).strip(" \t\r\n")


def save_error_csv(error_name: str) -> None:
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Algorithm",
            "Found",
            "PathLength",
            "Path",
            "Iterations",
            "MaxStatesStored",
            "TimeMS",
            "Message",
        ])
        writer.writerow([error_name, "false", 0, "", 0, 0, 0, error_name])


def node_exists(node_id: str) -> bool:
    return node_id in id_to_label


def get_label(node_id: str) -> str:
    return id_to_label.get(node_id, node_id)


def get_neighbors(node_id: str) -> List[str]:
    return adj_list.get(node_id, [])


def build_path(target_id: str, parent: Dict[str, str]) -> List[str]:
    path: List[str] = []
    current = target_id
    while current != "":
        path.append(get_label(current))
        if current not in parent:
            break
        current = parent[current]
    path.reverse()
    return path


def path_to_string(path: List[str]) -> str:
    return " -> ".join(path)


def save_results_csv(
    algo_name: str,
    found: bool,
    target_id: str,
    parent: Dict[str, str],
    iterations: int,
    max_states_stored: int,
    ms: int,
) -> None:
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Algorithm",
            "Found",
            "PathLength",
            "Path",
            "Iterations",
            "MaxStatesStored",
            "TimeMS",
            "Message",
        ])

        if not found:
            writer.writerow([
                algo_name,
                "false",
                0,
                "",
                iterations,
                max_states_stored,
                ms,
                "Target non trovato",
            ])
        else:
            path = build_path(target_id, parent)
            path_length = max(0, len(path) - 1)
            writer.writerow([
                algo_name,
                "true",
                path_length,
                path_to_string(path),
                iterations,
                max_states_stored,
                ms,
                "OK",
            ])


def safe_int(value: str):
    try:
        return True, int(value)
    except Exception:
        return False, None


# =========================
# CARICAMENTO DATI
# =========================
def load_nodes(filename: str) -> bool:
    global id_to_label, label_to_id, adj_list
    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # salta header
            for row in reader:
                if len(row) < 2:
                    continue
                node_id = trim(row[0])
                label = trim(row[1])
                if not node_id or not label:
                    continue
                if node_id in id_to_label:
                    continue
                id_to_label[node_id] = label
                if label not in label_to_id:
                    label_to_id[label] = node_id
                if node_id not in adj_list:
                    adj_list[node_id] = []
        return True
    except Exception:
        return False


def load_edges(filename: str, directed: bool) -> bool:
    global adj_list
    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # salta header
            for row in reader:
                if len(row) < 2:
                    continue
                source = trim(row[0])
                target = trim(row[1])
                if not source or not target:
                    continue
                if not node_exists(source) or not node_exists(target):
                    continue
                adj_list.setdefault(source, []).append(target)
                if not directed:
                    adj_list.setdefault(target, []).append(source)
        return True
    except Exception:
        return False


# =========================
# RISOLUZIONE INPUT -> ID NODO
# Mantengo la stessa logica del C++ originale:
# prima tenta come label, poi come ID.
# =========================
def get_node_id_from_input(user_input: str):
    cleaned = trim(user_input)
    if cleaned in label_to_id:
        return True, label_to_id[cleaned]
    if cleaned in id_to_label:
        return True, cleaned
    return False, ""


# =========================
# ALGORITMI
# =========================
def run_BFS(start_id: str, target_id: str) -> None:
    t0 = time.perf_counter()
    q: deque[str] = deque()
    visited: Set[str] = set()
    parent: Dict[str, str] = {}

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
    save_results_csv("BFS", found, target_id, parent, iterations, max_states_stored, duration_ms)


def run_DFS(start_id: str, target_id: str) -> None:
    t0 = time.perf_counter()
    stack: List[str] = []
    visited: Set[str] = set()
    inserted: Set[str] = set()
    parent: Dict[str, str] = {}

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
    save_results_csv("DFS", found, target_id, parent, iterations, max_states_stored, duration_ms)


def DLS_recursive(
    current: str,
    target: str,
    limit: int,
    parent: Dict[str, str],
    path_visited: Set[str],
    stats: Dict[str, int],
) -> bool:
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


def run_DLS(start_id: str, target_id: str, limit: int) -> None:
    t0 = time.perf_counter()
    parent: Dict[str, str] = {start_id: ""}
    path_visited: Set[str] = {start_id}
    stats = {"iterations": 0, "max_states_stored": 0}

    found = DLS_recursive(start_id, target_id, limit, parent, path_visited, stats)

    duration_ms = int((time.perf_counter() - t0) * 1000)
    save_results_csv(
        "DLS",
        found,
        target_id,
        parent,
        stats["iterations"],
        stats["max_states_stored"],
        duration_ms,
    )


def run_IDS(start_id: str, target_id: str, max_depth: int) -> None:
    t0 = time.perf_counter()
    found = False
    total_iterations = 0
    max_states_stored = 0
    final_parent: Dict[str, str] = {}
    last_parent: Dict[str, str] = {}

    for limit in range(max_depth + 1):
        parent = {start_id: ""}
        path_visited = {start_id}
        stats = {"iterations": 0, "max_states_stored": 0}

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
    save_results_csv(
        "IDS",
        found,
        target_id,
        final_parent if found else last_parent,
        total_iterations,
        max_states_stored,
        duration_ms,
    )


# =========================
# MAIN
# =========================
def main(argv: List[str]) -> int:
    global output_file

    if len(argv) < 7:
        save_error_csv("ERROR_MISSING_ARGUMENTS")
        return 1

    nodes_file = argv[1]
    edges_file = argv[2]
    directed_input = argv[3]
    start_input = argv[4]
    target_input = argv[5]
    choice = argv[6]
    depth_limit = 10

    if len(argv) >= 8:
        ok, depth_value = safe_int(argv[7])
        if not ok or depth_value is None or depth_value < 0:
            save_error_csv("ERROR_INVALID_DEPTH_LIMIT")
            return 1
        depth_limit = depth_value

    if len(argv) >= 9:
        output_file = argv[8]

    if directed_input == "1":
        directed = True
    elif directed_input == "0":
        directed = False
    else:
        save_error_csv("ERROR_INVALID_DIRECTED_PARAMETER")
        return 1

    if not load_nodes(nodes_file):
        save_error_csv("ERROR_NODES_FILE_NOT_FOUND")
        return 1

    if not load_edges(edges_file, directed):
        save_error_csv("ERROR_EDGES_FILE_NOT_FOUND")
        return 1

    if not id_to_label:
        save_error_csv("ERROR_EMPTY_NODES_FILE")
        return 1

    ok_start, start_id = get_node_id_from_input(start_input)
    if not ok_start:
        save_error_csv("ERROR_START_NODE_NOT_FOUND")
        return 1

    ok_target, target_id = get_node_id_from_input(target_input)
    if not ok_target:
        save_error_csv("ERROR_TARGET_NODE_NOT_FOUND")
        return 1

    if choice == "1":
        run_BFS(start_id, target_id)
    elif choice == "2":
        run_DFS(start_id, target_id)
    elif choice == "3":
        run_IDS(start_id, target_id, depth_limit)
    elif choice == "4":
        run_DLS(start_id, target_id, depth_limit)
    else:
        save_error_csv("ERROR_INVALID_ALGORITHM")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
