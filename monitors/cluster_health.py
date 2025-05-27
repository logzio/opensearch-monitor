def check_cluster_health(client):
    health = client.cluster.health()
    # Try to get number of search nodes from health, else from nodes info
    number_of_search_nodes = health.get("number_of_search_nodes")
    if number_of_search_nodes is None:
        try:
            nodes_info = client.nodes.info()
            number_of_search_nodes = sum(
                1 for node in nodes_info['nodes'].values()
                if 'search' in node.get('roles', [])
            )
        except Exception:
            number_of_search_nodes = None
    analysis = analyze_cluster_health(health, number_of_search_nodes)
    return {"health": health, "analysis": analysis}


def analyze_cluster_health(health, number_of_search_nodes=None):
    status = health.get("status")
    number_of_nodes = health.get("number_of_nodes")
    number_of_data_nodes = health.get("number_of_data_nodes")
    unassigned_shards = health.get("unassigned_shards")
    active_shards_percent = health.get("active_shards_percent_as_number")
    analysis = []
    if status != "green":
        analysis.append(f"Cluster status is {status}. Immediate attention may be required.")
    if number_of_nodes is not None:
        analysis.append(f"Number of nodes: {number_of_nodes}")
    if number_of_data_nodes is not None:
        analysis.append(f"Number of data nodes: {number_of_data_nodes}")
    if number_of_search_nodes is not None:
        analysis.append(f"Number of search nodes: {number_of_search_nodes}")
    if unassigned_shards > 0:
        analysis.append(f"There are {unassigned_shards} unassigned shards.")
    if active_shards_percent < 100:
        analysis.append(f"Only {active_shards_percent}% of shards are active.")
    if not analysis:
        analysis.append("Cluster health is optimal.")
    return analysis


def analyze_shard_allocation(client, index_pattern="*"):
    cat_shards = client.cat.shards(index=index_pattern, format="json")
    issues = []
    node_shard_count = {}
    for shard in cat_shards:
        if shard["state"] != "STARTED":
            issues.append(f"Shard {shard['shard']} of index {shard['index']} is in state {shard['state']} on node {shard['node']}.")
        node = shard["node"]
        node_shard_count[node] = node_shard_count.get(node, 0) + 1
    # Get node disk usage
    node_stats = client.nodes.stats(metric=["fs"])
    node_disk_info = {}
    for node_id, node in node_stats["nodes"].items():
        name = node.get("name")
        fs = node.get("fs", {})
        total = fs.get("total", {})
        disk_total = total.get("total_in_bytes")
        disk_available = total.get("available_in_bytes")
        disk_used = total.get("used_in_bytes")
        node_disk_info[name] = {
            "allocated": disk_total,
            "used": disk_used,
            "available": disk_available
        }
    # Report nodes with too many shards (e.g., >1000) and their disk usage
    for node, count in node_shard_count.items():
        if count > 1000:
            disk = node_disk_info.get(node, {})
            allocated_gb = int(disk.get("allocated", 0) / (1024 ** 3)) if disk.get("allocated") else 'N/A'
            used_gb = int(disk.get("used", 0) / (1024 ** 3)) if disk.get("used") else 'N/A'
            issues.append(f"Node {node} has a high shard count: {count} shards (allocated: {allocated_gb} GB, used: {used_gb} GB) (consider rebalancing or reducing shard count)")
    if not issues:
        issues.append("All shards are properly allocated and started.")
    return issues 