def get_mapping_exceptions(client, index_pattern="*"):
    # OpenSearch does not provide a direct API for mapping exceptions, but we can check index mappings
    try:
        mappings = client.indices.get_mapping(index=index_pattern)
        return mappings
    except Exception as e:
        return {"error": str(e)}

# Parsing exceptions are typically found in logs, not via API. This is a placeholder.
def get_parsing_exceptions():
    return "Parsing exceptions are not accessible via OpenSearch API. Check node log files."


def analyze_index_mappings(mappings):
    issues = {}
    for index, data in mappings.items():
        index_issues = []
        properties = data.get('mappings', {}).get('properties', {})
        field_count = len(properties)
        if field_count > 1000:
            index_issues.append(f"High number of fields: {field_count}")
        for field, field_info in properties.items():
            # Check for fields with both text and keyword
            if isinstance(field_info, dict):
                if field_info.get('type') == 'text' and 'fields' in field_info and 'keyword' in field_info['fields']:
                    index_issues.append(f"Field '{field}' uses both text and keyword mapping (may increase index size)")
        if index_issues:
            issues[index] = index_issues
    if not issues:
        issues['all'] = ["No major mapping optimization issues detected."]
    return issues 