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
    Export monitoring report to HTML
    
    Args:
        results (Dict): Report data
        filename (str): Output filename
        logz_api_token (str): Optional Logz.io API token
        cluster_name (str): Optional cluster name for Logz.io logs
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<title>OpenSearch Cluster Analysis Report</title>",
        '<style>body { font-family: Arial, sans-serif; margin: 20px; }h3 { color: #2c3e50; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 5px; }h4 { color: #34495e; margin-top: 20px; } .section { margin-bottom: 30px; } .group { margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; } .value { font-family: monospace; white-space: pre-wrap; } .list-item { margin: 5px 0; padding: 5px; background: #fff; border: 1px solid #eee; } .log-entry { margin: 5px 0; padding: 8px; border-radius: 4px; } .log-entry.error { background: #fee; border-left: 4px solid #c00; } .log-entry.warn { background: #fff3cd; border-left: 4px solid #ffc107; } .log-entry.info { background: #e3f2fd; border-left: 4px solid #2196f3; } .log-entry.debug { background: #f5f5f5; border-left: 4px solid #9e9e9e; } .source { color: #666; font-size: 0.9em; } table { border-collapse: collapse; width: 100%; margin: 10px 0; } th, td { border: 1px solid #ddd; padding: 8px; text-align: left; } th { background: #f5f5f5; } tr:nth-child(even) { background: #f9f9f9; } pre { margin: 0; white-space: pre-wrap; word-break: break-word; } /* Analysis section styles */ .analysis-summary { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; } .analysis-summary table { max-width: 600px; } .slow-queries, .parsing-exceptions { margin: 20px 0; } .slow-queries table td:nth-child(2), .parsing-exceptions table td:nth-child(2) { font-family: monospace; } .slow-queries pre, .parsing-exceptions pre { max-height: 200px; overflow-y: auto; background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 0.9em; }</style>',
        "</head>",
        "<body>",
        f"<h1>OpenSearch Monitoring Report</h1>",
        f"<p><b>Generated:</b> {now}</p>"
    ]
    
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