#!/usr/bin/env python3
"""
MBP Master Layer Generator — Runs all 4 data pipelines and merges results
into the existing graph_data_v7.json (non-destructive: adds new layers).
"""
import json
import os
import sys
import shutil
from datetime import datetime

# Ensure scripts dir is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

GRAPH_DATA_PATH = os.path.join(
    "C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7", "graph_data_v7.json"
)
LAYER_DIR = os.path.join(
    "C:\\Users\\andre\\LitigationOS", "12_WORKSPACE", "THEMANBEARPIG_v7"
)

LAYER_CONFIG_ADDITIONS = {
    "STRATEGIC": {"color": "#e67e22", "shape": "pentagon", "y_band": 0.15},
    "IMPEACHMENT": {"color": "#e74c3c", "shape": "cross", "y_band": 0.35},
    "AUTHORITY_CHAIN": {"color": "#f1c40f", "shape": "hexagon", "y_band": 0.6},
    "TIMELINE": {"color": "#3498db", "shape": "clock", "y_band": 0.8},
}


def run_pipeline(module_name, func_name):
    """Import and run a pipeline module, return its result dict."""
    print(f"\n{'='*60}")
    print(f"Running: {module_name}")
    print(f"{'='*60}")
    try:
        mod = __import__(module_name)
        func = getattr(mod, func_name)
        result = func()
        return result
    except Exception as e:
        print(f"  ERROR in {module_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def merge_into_graph(layer_results):
    """Merge new layer data into existing graph_data_v7.json."""
    # Load existing graph data
    if os.path.exists(GRAPH_DATA_PATH):
        backup_path = GRAPH_DATA_PATH + f".pre_layer_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(GRAPH_DATA_PATH, backup_path)
        print(f"\nBackup: {backup_path}")

        with open(GRAPH_DATA_PATH, "r", encoding="utf-8") as f:
            graph = json.load(f)
    else:
        graph = {"metadata": {}, "nodes": [], "edges": [], "layer_config": {}}

    # Track existing node/edge IDs to avoid duplicates
    existing_node_ids = {n["id"] for n in graph.get("nodes", [])}
    existing_edge_keys = {
        (e["source"], e["target"], e.get("type", ""))
        for e in graph.get("edges", [])
    }

    total_new_nodes = 0
    total_new_edges = 0

    for layer_result in layer_results:
        if not layer_result:
            continue

        layer_name = layer_result.get("layer", "UNKNOWN")

        # Remove old nodes/edges for this layer (clean replacement)
        graph["nodes"] = [n for n in graph["nodes"] if n.get("layer") != layer_name]
        graph["edges"] = [e for e in graph["edges"] if e.get("layer") != layer_name]

        # Rebuild tracking sets after removal
        existing_node_ids = {n["id"] for n in graph["nodes"]}
        existing_edge_keys = {
            (e["source"], e["target"], e.get("type", ""))
            for e in graph["edges"]
        }

        # Add new nodes
        new_nodes = 0
        for node in layer_result.get("nodes", []):
            if node["id"] not in existing_node_ids:
                graph["nodes"].append(node)
                existing_node_ids.add(node["id"])
                new_nodes += 1

        # Add new edges
        new_edges = 0
        for edge in layer_result.get("edges", []):
            edge_key = (edge["source"], edge["target"], edge.get("type", ""))
            if edge_key not in existing_edge_keys:
                graph["edges"].append(edge)
                existing_edge_keys.add(edge_key)
                new_edges += 1

        print(f"  [{layer_name}] Added {new_nodes} nodes, {new_edges} edges")
        total_new_nodes += new_nodes
        total_new_edges += new_edges

    # Update layer_config
    if "layer_config" not in graph:
        graph["layer_config"] = {}
    graph["layer_config"].update(LAYER_CONFIG_ADDITIONS)

    # Update metadata
    if "metadata" not in graph:
        graph["metadata"] = {}
    graph["metadata"]["last_layer_merge"] = datetime.now().isoformat()
    graph["metadata"]["total_nodes"] = len(graph["nodes"])
    graph["metadata"]["total_edges"] = len(graph["edges"])
    graph["metadata"]["layers_merged"] = [
        lr["layer"] for lr in layer_results if lr
    ]

    # Write merged graph
    with open(GRAPH_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    return total_new_nodes, total_new_edges, graph


def main():
    print("=" * 70)
    print("  THEMANBEARPIG v7 — Layer Data Generation Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = []

    # Run all 4 pipelines
    r1 = run_pipeline("mbp_strategic_data", "extract_strategic_data")
    results.append(r1)

    r2 = run_pipeline("mbp_impeachment_data", "extract_impeachment_data")
    results.append(r2)

    r3 = run_pipeline("mbp_authority_data", "extract_authority_data")
    results.append(r3)

    r4 = run_pipeline("mbp_timeline_data", "extract_timeline_data")
    results.append(r4)

    # Merge into graph_data_v7.json
    print("\n" + "=" * 70)
    print("  MERGING INTO graph_data_v7.json")
    print("=" * 70)

    new_nodes, new_edges, graph = merge_into_graph(results)

    # Final report
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)

    # Per-layer breakdown
    layer_node_counts = {}
    layer_edge_counts = {}
    for n in graph.get("nodes", []):
        layer = n.get("layer", "UNKNOWN")
        layer_node_counts[layer] = layer_node_counts.get(layer, 0) + 1
    for e in graph.get("edges", []):
        layer = e.get("layer", "UNKNOWN")
        layer_edge_counts[layer] = layer_edge_counts.get(layer, 0) + 1

    print(f"\n  Total nodes: {len(graph['nodes']):,}")
    print(f"  Total edges: {len(graph['edges']):,}")
    print(f"  New nodes added: {new_nodes:,}")
    print(f"  New edges added: {new_edges:,}")
    print(f"\n  Per-layer breakdown:")
    for layer in sorted(set(list(layer_node_counts.keys()) + list(layer_edge_counts.keys()))):
        nc = layer_node_counts.get(layer, 0)
        ec = layer_edge_counts.get(layer, 0)
        marker = " <-- NEW" if layer in ("STRATEGIC", "IMPEACHMENT", "AUTHORITY_CHAIN", "TIMELINE") else ""
        print(f"    {layer:20s}  nodes={nc:>6,}  edges={ec:>6,}{marker}")

    # Individual layer files
    print(f"\n  Layer data files:")
    for name in ["strategic", "impeachment", "authority", "timeline"]:
        fpath = os.path.join(LAYER_DIR, f"layer_{name}_data.json")
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"    OK layer_{name}_data.json ({size_kb:.1f} KB)")
        else:
            print(f"    MISSING layer_{name}_data.json")

    print(f"\n  Merged: {GRAPH_DATA_PATH}")
    merged_size = os.path.getsize(GRAPH_DATA_PATH) / (1024 * 1024)
    print(f"  Size: {merged_size:.2f} MB")
    print(f"\n{'='*70}")
    print("  PIPELINE COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
