def get_search_stats(client):
    stats = client.indices.stats(metric=["search"])
    return stats

# Note: Slow logs are typically stored in log files on the nodes, not accessible via API. This function is a placeholder.
def get_slow_logs():
    return "Slow logs are not accessible via OpenSearch API. Check node log files."


def get_latency_percentiles(client, index):
    # This function samples recent documents in the index and runs a percentiles aggregation on the 'took' value of queries.
    # Note: 'took' is not a field in documents, but a property of the search API response.
    # To get real percentiles, you must log query latencies as documents. Here, we use a workaround: sample recent documents and use a script if you have a latency field.
    # If you do not have such a field, this will return N/A.
    # If you have a latency field, set it here:
    latency_field = None  # e.g., 'latency_ms' if you log it
    if not latency_field:
        return None, None
    try:
        body = {
            "size": 0,
            "aggs": {
                "latency_percentiles": {
                    "percentiles": {
                        "field": latency_field,
                        "percents": [50, 90]
                    }
                }
            }
        }
        result = client.search(index=index, body=body)
        percentiles = result['aggregations']['latency_percentiles']['values']
        median = percentiles.get('50.0')
        p90 = percentiles.get('90.0')
        return median, p90
    except Exception:
        return None, None


def analyze_search_stats(stats, client=None, settings=None):
    # Define thresholds and reasons
    reasons = {
        "High average query latency": {},
        "Failed queries": {},
        "High query volume": {}
    }
    high_query_volume_list = []
    indices = stats.get('indices', {})
    for index, data in indices.items():
        search = data.get('total', {}).get('search', {})
        query_total = search.get('query_total', 0)
        query_time_in_millis = search.get('query_time_in_millis', 0)
        failed = search.get('failed', 0)
        # Get index creation date from settings if provided
        creation_date_ms = None
        if settings and index in settings:
            creation_date_ms = settings[index].get('settings', {}).get('index', {}).get('creation_date')
        avg_daily_queries = None
        creation_date_str = creation_date_ms
        if creation_date_ms:
            import time, datetime
            creation_date = int(creation_date_ms) / 1000
            days = max((time.time() - creation_date) / 86400, 1)
            avg_daily_queries = query_total / days
            creation_date_str = datetime.datetime.utcfromtimestamp(creation_date).strftime('%Y-%m-%d')
        # High latency (exclude search indices)
        if query_total > 0 and 'search' not in index.lower():
            avg_latency = query_time_in_millis / query_total
            if avg_latency > 100:
                median, p90 = None, None
                if client is not None:
                    median, p90 = get_latency_percentiles(client, index)
                details = f"avg: {avg_latency:.2f} ms"
                if median is not None:
                    details += f", median: {median:.2f} ms"
                else:
                    details += ", median: N/A"
                if p90 is not None:
                    details += f", 90th: {p90:.2f} ms"
                else:
                    details += ", 90th: N/A"
                reasons["High average query latency"][index] = details
        # Failed queries
        if failed > 0:
            reasons["Failed queries"][index] = f"{failed} failed"
        # High volume (use average daily queries if possible)
        if avg_daily_queries is not None and avg_daily_queries > 10000:
            high_query_volume_list.append((index, avg_daily_queries, creation_date_str))
        elif avg_daily_queries is None and query_total > 10000:
            reasons["High query volume"][index] = f"{query_total} queries (total, creation date unknown)"
    # Sort high query volume by avg_daily_queries descending
    if high_query_volume_list:
        high_query_volume_list.sort(key=lambda x: -x[1])
        reasons["High query volume"] = {i: f"{q:.0f} avg daily queries (created: {d})" for i, q, d in high_query_volume_list}
    # Only include reasons with issues
    grouped = {reason: idxs for reason, idxs in reasons.items() if idxs}
    if not grouped:
        grouped['all'] = ["No major search performance issues detected."]
    return grouped 