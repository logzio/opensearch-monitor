def get_index_settings(client, index_pattern="*"):
    settings = client.indices.get_settings(index=index_pattern)
    stats = client.indices.stats(index=index_pattern, metric=["store"])
    return settings, stats


def analyze_index_settings(settings_and_stats):
    settings, stats = settings_and_stats
    issues = {}
    for index, data in settings.items():
        index_issues = []
        s = data.get('settings', {}).get('index', {})
        # Get index size in bytes
        size_in_bytes = stats.get('indices', {}).get(index, {}).get('total', {}).get('store', {}).get('size_in_bytes', 0)
        size_in_gb = size_in_bytes / (1024 ** 3)
        # Check for high number of shards only if index is small (<50GB)
        num_shards = int(s.get('number_of_shards', 1))
        if num_shards > 5 and size_in_gb < 50:
            index_issues.append(f"High number of primary shards for small index (<50GB): {num_shards} shards, {size_in_gb:.2f} GB")
        # Check for low number of replicas, skip for search or test indices
        num_replicas = int(s.get('number_of_replicas', 1))
        if num_replicas < 1 and 'search' not in index.lower() and 'test' not in index.lower():
            index_issues.append("No replicas configured")
        # Check for refresh interval < 1s, skip for Kibana indices
        refresh_interval = s.get('refresh_interval', '1s')
        if not index.startswith('.kibana'):
            try:
                refresh_sec = float(refresh_interval.rstrip('s'))
                if refresh_sec < 1:
                    index_issues.append("Default refresh_interval (<1s) may impact indexing throughput")
            except Exception:
                pass
        # Add more checks as needed
        if index_issues:
            issues[index] = index_issues
    if not issues:
        return {'all': ["No major issues detected in index settings."]}
    return group_and_sort_index_issues(issues)


def group_and_sort_index_issues(issues):
    # Define impact levels (higher is more important)
    impact_map = {
        "High number of primary shards for small index (<50GB)": 3,
        "No replicas configured": 2,
        "Default refresh_interval (1s) may impact indexing throughput": 1,
        "Default refresh_interval (<1s) may impact indexing throughput": 1
    }
    grouped = {}
    for index, problems in issues.items():
        for problem in problems:
            # For high shard count, group by prefix for sorting
            if problem.startswith("High number of primary shards for small index"):
                grouped.setdefault("High number of primary shards for small index (<50GB)", []).append(f"{index}: {problem.split(':',1)[1].strip()}")
            else:
                grouped.setdefault(problem, []).append(index)
    # Sort by impact
    sorted_grouped = dict(sorted(grouped.items(), key=lambda x: -impact_map.get(x[0], 0)))
    return sorted_grouped 