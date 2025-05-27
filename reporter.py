from loguru import logger
import datetime
from typing import Optional, Dict, Any
from logz_client import LogzClient


def report(title, data):
    logger.info(f"{title}: {data}")
    print(f"{title}: {data}")


def get_logz_logs(api_token: Optional[str], cluster_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch and analyze logs from Logz.io if API token is provided
    
    Args:
        api_token (str): Optional Logz.io API token
        cluster_name (str): Name of the cluster to search for
        
    Returns:
        Dict containing logs and analysis or None if no API token provided
    """
    if not api_token:
        return None
        
    try:
        client = LogzClient(api_token)
        # Get both raw logs and analysis
        logs = client.get_cluster_logs(cluster_name)
        analysis = client.analyze_cluster_logs(cluster_name)
        
        return {
            "raw_logs": {
                "total_hits": logs.get("hits", {}).get("total", {}).get("value", 0),
                "logs": [
                    {
                        "timestamp": hit.get("_source", {}).get("@timestamp"),
                        "message": hit.get("_source", {}).get("message"),
                        "level": hit.get("_source", {}).get("level"),
                        "source": hit.get("_source", {}).get("source")
                    }
                    for hit in logs.get("hits", {}).get("hits", [])
                ]
            },
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to fetch Logz.io logs: {str(e)}")
        return None


def export_html_report(results: Dict[str, Any], filename: str = "opensearch_report.html", 
                      logz_api_token: Optional[str] = None, cluster_name: Optional[str] = None):
    """
    Export monitoring report to HTML with optimization recommendations
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Define optimization recommendations for each section with severity and complexity levels
    optimization_recommendations = {
        "Cluster Health": {
            "title": "Cluster Health Optimization Steps",
            "steps": [
                {
                    "description": "Ensure all nodes are healthy and responsive",
                    "severity": "Critical",
                    "complexity": "Basic",
                    "impact": "High impact on cluster stability and performance"
                },
                {
                    "description": "Check for any pending tasks that might be blocking operations",
                    "severity": "High",
                    "complexity": "Basic",
                    "impact": "Affects cluster operations and response time"
                },
                {
                    "description": "Monitor cluster status and address any red/yellow status indicators",
                    "severity": "Critical",
                    "complexity": "Basic",
                    "impact": "Critical for cluster health and data availability"
                },
                {
                    "description": "Review and adjust cluster settings (e.g., discovery, network settings)",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Improves cluster stability and performance"
                },
                {
                    "description": "Verify that all nodes have sufficient resources (CPU, memory, disk)",
                    "severity": "High",
                    "complexity": "Basic",
                    "impact": "Essential for preventing node failures"
                }
            ]
        },
        "Shard Allocation Analysis": {
            "title": "Shard Allocation Optimization Steps",
            "steps": [
                {
                    "description": "Balance shards across nodes to prevent hot spots",
                    "severity": "High",
                    "complexity": "Intermediate",
                    "impact": "Improves cluster performance and resource utilization"
                },
                {
                    "description": "Consider reducing the number of shards if they are too small",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Reduces overhead and improves resource efficiency"
                },
                {
                    "description": "Review and adjust shard allocation awareness settings",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Optimizes data distribution across availability zones"
                },
                {
                    "description": "Check for any unassigned shards and resolve allocation issues",
                    "severity": "Critical",
                    "complexity": "Basic",
                    "impact": "Critical for data availability and cluster health"
                },
                {
                    "description": "Monitor shard sizes and consider reindexing if needed",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Improves search performance and resource utilization"
                }
            ]
        },
        "Index Settings Analysis": {
            "title": "Index Settings Optimization Steps",
            "steps": [
                {
                    "description": "Review and optimize refresh intervals based on your use case",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Balances indexing performance and search latency"
                },
                {
                    "description": "Adjust number of replicas based on availability requirements",
                    "severity": "High",
                    "complexity": "Basic",
                    "impact": "Critical for data availability and read performance"
                },
                {
                    "description": "Implement index lifecycle management (ILM) for better resource utilization",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Automates index management and optimizes resource usage"
                },
                {
                    "description": "Optimize merge settings to reduce resource contention",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Improves indexing performance and reduces resource spikes"
                },
                {
                    "description": "Review and adjust translog settings for better durability and performance",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Balances durability and performance requirements"
                }
            ]
        },
        "Search Stats Analysis": {
            "title": "Search Performance Optimization Steps",
            "steps": [
                {
                    "description": "Optimize query patterns to reduce search latency",
                    "severity": "High",
                    "complexity": "Intermediate",
                    "impact": "Significantly improves search response times"
                },
                {
                    "description": "Review and adjust search thread pool settings",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Optimizes resource utilization for search operations"
                },
                {
                    "description": "Use filter context instead of query context where possible",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Improves query performance and caching efficiency"
                },
                {
                    "description": "Implement caching strategies for frequently used queries",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Reduces search latency for common queries"
                },
                {
                    "description": "Monitor and optimize field data usage",
                    "severity": "High",
                    "complexity": "Advanced",
                    "impact": "Reduces memory usage and improves stability"
                }
            ]
        },
        "Index Mapping Analysis": {
            "title": "Mapping Optimization Steps",
            "steps": [
                {
                    "description": "Review and optimize field mappings to reduce memory usage",
                    "severity": "High",
                    "complexity": "Intermediate",
                    "impact": "Significantly reduces memory footprint"
                },
                {
                    "description": "Use keyword fields instead of text fields where exact matching is needed",
                    "severity": "Medium",
                    "complexity": "Basic",
                    "impact": "Improves search performance and reduces resource usage"
                },
                {
                    "description": "Implement dynamic templates for better field type management",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Prevents mapping explosions and improves consistency"
                },
                {
                    "description": "Remove unused fields to reduce index size",
                    "severity": "Low",
                    "complexity": "Basic",
                    "impact": "Reduces storage requirements and improves performance"
                },
                {
                    "description": "Use appropriate date formats and numeric types",
                    "severity": "Medium",
                    "complexity": "Basic",
                    "impact": "Improves search performance and reduces storage"
                }
            ]
        },
        "AWS Resource Alignment Analysis": {
            "title": "AWS Resource Optimization Steps",
            "steps": [
                {
                    "description": "Review instance types and consider upgrading if resource constrained",
                    "severity": "High",
                    "complexity": "Basic",
                    "impact": "Critical for cluster performance and stability"
                },
                {
                    "description": "Optimize EBS volume types and sizes based on workload",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Improves I/O performance and reduces costs"
                },
                {
                    "description": "Consider using reserved instances for cost optimization",
                    "severity": "Low",
                    "complexity": "Basic",
                    "impact": "Reduces operational costs"
                },
                {
                    "description": "Implement auto-scaling policies based on metrics",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Optimizes resource utilization and costs"
                },
                {
                    "description": "Review and adjust network settings for better performance",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Improves cluster communication and stability"
                }
            ]
        },
        "Logz.io Analysis": {
            "title": "Log Analysis Optimization Steps",
            "steps": [
                {
                    "description": "Address any mapper parsing exceptions by fixing data types or mappings",
                    "severity": "Critical",
                    "complexity": "Intermediate",
                    "impact": "Prevents data ingestion failures and improves data quality"
                },
                {
                    "description": "Optimize slow queries by reviewing and improving query patterns",
                    "severity": "High",
                    "complexity": "Intermediate",
                    "impact": "Significantly improves search performance"
                },
                {
                    "description": "Implement query caching where appropriate",
                    "severity": "Medium",
                    "complexity": "Intermediate",
                    "impact": "Reduces search latency for repeated queries"
                },
                {
                    "description": "Use search templates for complex queries",
                    "severity": "Medium",
                    "complexity": "Advanced",
                    "impact": "Improves query consistency and performance"
                },
                {
                    "description": "Monitor and adjust thread pool settings based on query patterns",
                    "severity": "High",
                    "complexity": "Advanced",
                    "impact": "Optimizes resource utilization for search operations"
                }
            ]
        }
    }
    
    # Add CSS for severity and complexity levels
    severity_colors = {
        "Critical": "#d32f2f",  # Red
        "High": "#f57c00",      # Orange
        "Medium": "#fbc02d",    # Yellow
        "Low": "#388e3c"        # Green
    }
    
    complexity_colors = {
        "Basic": "#2196f3",     # Blue
        "Intermediate": "#7b1fa2",  # Purple
        "Advanced": "#5d4037"   # Brown
    }
    
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<title>OpenSearch Cluster Analysis Report</title>",
        '<style>',
        'body { font-family: Arial, sans-serif; margin: 20px; }',
        'h3 { color: #2c3e50; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }',
        'h4 { color: #34495e; margin-top: 20px; }',
        '.section { margin-bottom: 30px; }',
        '.group { margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; }',
        '.value { font-family: monospace; white-space: pre-wrap; }',
        '.list-item { margin: 5px 0; padding: 5px; background: #fff; border: 1px solid #eee; }',
        '.log-entry { margin: 5px 0; padding: 8px; border-radius: 4px; }',
        '.log-entry.error { background: #fee; border-left: 4px solid #c00; }',
        '.log-entry.warn { background: #fff3cd; border-left: 4px solid #ffc107; }',
        '.log-entry.info { background: #e3f2fd; border-left: 4px solid #2196f3; }',
        '.log-entry.debug { background: #f5f5f5; border-left: 4px solid #9e9e9e; }',
        '.source { color: #666; font-size: 0.9em; }',
        'table { border-collapse: collapse; width: 100%; margin: 10px 0; }',
        'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
        'th { background: #f5f5f5; }',
        'tr:nth-child(even) { background: #f9f9f9; }',
        'pre { margin: 0; white-space: pre-wrap; word-break: break-word; }',
        '.analysis-summary { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; }',
        '.analysis-summary table { max-width: 600px; }',
        '.slow-queries, .parsing-exceptions { margin: 20px 0; }',
        '.slow-queries table td:nth-child(2), .parsing-exceptions table td:nth-child(2) { font-family: monospace; }',
        '.slow-queries pre, .parsing-exceptions pre { max-height: 200px; overflow-y: auto; background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 0.9em; }',
        '.optimization-steps { background: #e8f5e9; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #4caf50; }',
        '.optimization-steps h4 { color: #2e7d32; margin-top: 0; }',
        '.optimization-steps ol { margin: 10px 0; padding-left: 20px; }',
        '.optimization-steps li { margin: 12px 0; }',
        '.optimization-step { margin-bottom: 8px; }',
        '.step-description { font-weight: 500; }',
        '.step-metadata { margin-top: 4px; font-size: 0.9em; }',
        '.severity-badge, .complexity-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; color: white; margin-right: 8px; font-size: 0.85em; }',
        '.impact-text { color: #666; font-style: italic; }',
        '</style>',
        "</head>",
        "<body>",
        f"<h1>OpenSearch Monitoring Report</h1>",
        f"<p><b>Generated:</b> {now}</p>"
    ]
    
    # Add legend for severity and complexity levels
    html.append('<div class="optimization-steps" style="margin-bottom: 30px;">')
    html.append('<h4>Optimization Levels Legend</h4>')
    html.append('<div style="margin-bottom: 10px;"><strong>Severity Levels:</strong>')
    for severity, color in severity_colors.items():
        html.append(f'<span class="severity-badge" style="background-color: {color};">{severity}</span>')
    html.append('</div>')
    html.append('<div><strong>Complexity Levels:</strong>')
    for complexity, color in complexity_colors.items():
        html.append(f'<span class="complexity-badge" style="background-color: {color};">{complexity}</span>')
    html.append('</div>')
    html.append('</div>')
    
    # Table of Contents
    html.append('<div class="toc"><h2>Table of Contents</h2><ul>')
    for section in results.keys():
        anchor = section.lower().replace(' ', '-').replace('.', '').replace(':', '').replace('/', '-')
        html.append(f'<li><a href="#{anchor}">{section}</a></li>')
    html.append('</ul></div>')
    
    # Report Sections
    for section, data in results.items():
        anchor = section.lower().replace(' ', '-').replace('.', '').replace(':', '').replace('/', '-')
        html.append(f"<div><h3 id='{anchor}'>{section}</h3>")
        
        # Add optimization recommendations if available
        if section in optimization_recommendations:
            rec = optimization_recommendations[section]
            html.append("<div class='optimization-steps'>")
            html.append(f"<h4>{rec['title']}</h4>")
            html.append("<ol>")
            for step in rec['steps']:
                html.append("<li>")
                html.append(f"<div class='optimization-step'>")
                html.append(f"<div class='step-description'>{step['description']}</div>")
                html.append("<div class='step-metadata'>")
                html.append(f"<span class='severity-badge' style='background-color: {severity_colors[step['severity']]};'>{step['severity']}</span>")
                html.append(f"<span class='complexity-badge' style='background-color: {complexity_colors[step['complexity']]};'>{step['complexity']}</span>")
                html.append(f"<span class='impact-text'>Impact: {step['impact']}</span>")
                html.append("</div>")
                html.append("</div>")
                html.append("</li>")
            html.append("</ol>")
            html.append("</div>")
        
        if section == "Logz.io Analysis" and isinstance(data, dict):
            # Display analysis summary
            summary = data.get("summary", {})
            
            html.append("<div class='analysis-summary'>")
            html.append("<h4>Analysis Summary</h4>")
            html.append("<table>")
            html.append("<tr><th>Metric</th><th>Value</th></tr>")
            html.append(f"<tr><td>Total Logs Analyzed</td><td>{summary.get('total_logs', 0)}</td></tr>")
            html.append(f"<tr><td>Slow Queries Found</td><td>{summary.get('slow_queries_count', 0)}</td></tr>")
            html.append(f"<tr><td>Parsing Exceptions Found</td><td>{summary.get('parsing_exceptions_count', 0)}</td></tr>")
            if summary.get('slowest_query_time', 0) > 0:
                html.append(f"<tr><td>Slowest Query Time</td><td>{summary.get('slowest_query_time', 0)} ms</td></tr>")
                html.append(f"<tr><td>Average Query Time</td><td>{summary.get('average_query_time', 0):.2f} ms</td></tr>")
            html.append("</table>")
            html.append("</div>")

            # Display slow queries
            slow_queries = data.get("slow_queries", [])
            if slow_queries:
                html.append("<div class='slow-queries'>")
                html.append("<h4>Slow Queries</h4>")
                html.append("<table>")
                html.append("<tr><th>Timestamp</th><th>Duration (ms)</th><th>Source</th><th>Message</th></tr>")
                for query in slow_queries:
                    html.append("<tr>")
                    html.append(f"<td>{query.get('timestamp', 'N/A')}</td>")
                    html.append(f"<td>{query.get('query_time', 0)}</td>")
                    html.append(f"<td>{query.get('source', 'N/A')}</td>")
                    html.append(f"<td><pre>{query.get('message', 'N/A')}</pre></td>")
                    html.append("</tr>")
                html.append("</table>")
                html.append("</div>")

            # Display parsing exceptions
            parsing_exceptions = data.get("parsing_exceptions", [])
            if parsing_exceptions:
                html.append("<div class='parsing-exceptions'>")
                html.append("<h4>Parsing Exceptions</h4>")
                html.append("<table>")
                html.append("<tr><th>Timestamp</th><th>Source</th><th>Type</th><th>Message</th></tr>")
                for exc in parsing_exceptions:
                    html.append("<tr>")
                    html.append(f"<td>{exc.get('timestamp', 'N/A')}</td>")
                    html.append(f"<td>{exc.get('source', 'N/A')}</td>")
                    html.append(f"<td>{exc.get('type', 'N/A')}</td>")
                    html.append(f"<td><pre>{exc.get('message', 'N/A')}</pre></td>")
                    html.append("</tr>")
                html.append("</table>")
                html.append("</div>")
        elif isinstance(data, dict):
            # Rest of the existing code for other sections remains unchanged
            if all(isinstance(v, dict) for v in data.values()):
                for group, group_data in data.items():
                    html.append(f"<div><h4>{group}</h4>")
                    html.append("<table>")
                    html.append("<tr><th>Index</th><th>Details</th></tr>")
                    for idx, details in group_data.items():
                        html.append(f"<tr><td>{idx}</td><td>{details}</td></tr>")
                    html.append("</table>")
                    html.append("</div>")
            elif all(isinstance(v, list) for v in data.values()):
                for group, group_data in data.items():
                    html.append(f"<div><h4>{group}</h4>")
                    html.append("<ul>")
                    for idx in group_data:
                        html.append(f"<li>{idx}</li>")
                    html.append("</ul>")
                    html.append("</div>")
            else:
                html.append("<table>")
                html.append("<tr><th>Key</th><th>Value</th></tr>")
                for k, v in data.items():
                    if isinstance(v, dict):
                        html.append(f"<tr><td>{k}</td><td><table><tr>{''.join(f'<th>{subk}</th>' for subk in v.keys())}</tr><tr>{''.join(f'<td>{subv}</td>' for subv in v.values())}</tr></table></td></tr>")
                    else:
                        html.append(f"<tr><td>{k}</td><td><pre>{v}</pre></td></tr>")
                html.append("</table>")
        elif isinstance(data, list):
            html.append("<ul>")
            for item in data:
                html.append(f"<li>{item}</li>")
            html.append("</ul>")
        else:
            html.append(f"<pre>{data}</pre>")
        html.append("</div>")
    
    html.append("</body></html>")
    with open(filename, "w") as f:
        f.write("\n".join(html)) 