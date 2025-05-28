import time
from connectors import get_opensearch_client
from monitors.cluster_health import check_cluster_health, analyze_shard_allocation
from monitors.index_settings import get_index_settings, analyze_index_settings
from monitors.query_performance import get_search_stats, analyze_search_stats
from monitors.mapping_exceptions import get_mapping_exceptions, analyze_index_mappings
from monitors.aws_resources import get_domain_info, analyze_resource_alignment, get_cloudwatch_metrics
from reporter import export_html_report
from loguru import logger
from tqdm import tqdm
import sys
import logging

def configure_logging(log_level: str = "INFO"):
    """Configure logging level for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default logger
    logger.remove()
    
    # Add logger with specified level
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level.upper(),
        colorize=True
    )
    
    # Also log to file with more details
    logger.add(
        "opensearch_monitor.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level.upper(),
        rotation="1 day",
        retention="7 days"
    )

def run_monitors(host, port, region, access_key, secret_key, domain=None, username=None, password=None, use_ssl=True, logz_api_token=None):
    # Define monitoring stages
    stages = [
        "Connecting to OpenSearch cluster",
        "Checking cluster health",
        "Analyzing shard allocation",
        "Analyzing index settings",
        "Analyzing query performance",
        "Analyzing index mappings",
        "Analyzing AWS resources" if domain else None,
        "Analyzing Logz.io logs" if logz_api_token else None,
        "Generating report"
    ]
    # Filter out None stages
    stages = [stage for stage in stages if stage is not None]
    
    # Create progress bar with custom format
    pbar = tqdm(total=len(stages), desc="Monitoring Progress", 
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
    
    try:
        # Stage 1: Connect to cluster
        pbar.set_description(stages[0])
        client = get_opensearch_client(host, port, region, access_key, secret_key, username, password, use_ssl)
        pbar.update(1)
        print(f"\n✓ {stages[0]} - Completed")
        
        results = {}
        
        # Stage 2: Cluster Health
        pbar.set_description(stages[1])
        health_result = check_cluster_health(client)
        results["Cluster Health"] = health_result["health"]
        results["Cluster Health Analysis"] = health_result["analysis"]
        cluster_name = health_result["health"].get("cluster_name")
        if not cluster_name:
            logger.warning("Could not determine cluster name from health check")
        pbar.update(1)
        print(f"\n✓ {stages[1]} - Completed")
        
        # Stage 3: Shard Allocation
        pbar.set_description(stages[2])
        shard_issues = analyze_shard_allocation(client)
        results["Shard Allocation Analysis"] = shard_issues
        pbar.update(1)
        print(f"\n✓ {stages[2]} - Completed")
        
        # Stage 4: Index Settings
        pbar.set_description(stages[3])
        settings, _ = get_index_settings(client)
        index_issues = analyze_index_settings((settings, _))
        results["Index Settings Analysis"] = index_issues
        pbar.update(1)
        print(f"\n✓ {stages[3]} - Completed")
        
        # Stage 5: Query Performance
        pbar.set_description(stages[4])
        search_stats = get_search_stats(client)
        search_issues = analyze_search_stats(search_stats, client, settings)
        results["Search Stats Analysis"] = search_issues
        pbar.update(1)
        print(f"\n✓ {stages[4]} - Completed")
        
        # Stage 6: Mapping Analysis
        pbar.set_description(stages[5])
        mappings = get_mapping_exceptions(client)
        mapping_issues = analyze_index_mappings(mappings)
        results["Index Mapping Analysis"] = mapping_issues
        pbar.update(1)
        print(f"\n✓ {stages[5]} - Completed")
        
        # Stage 7: AWS Resources (if domain provided)
        if domain:
            pbar.set_description(stages[6])
            from monitors import aws_resources
            domain_info = get_domain_info(region, access_key, secret_key, domain)
            aws_analysis = analyze_resource_alignment(domain_info, health_result["health"], search_stats)
            results["AWS Resource Alignment Analysis"] = aws_analysis
            if region and access_key and secret_key:
                cw_metrics = get_cloudwatch_metrics(region, access_key, secret_key, domain)
                results["CloudWatch Infra Metrics"] = cw_metrics
            pbar.update(1)
            print(f"\n✓ {stages[6]} - Completed")
        
        # Stage 8: Logz.io Logs (if API token provided)
        if logz_api_token:
            pbar.set_description(stages[7])
            try:
                if not cluster_name:
                    logger.warning("Skipping Logz.io analysis: Cluster name not available")
                else:
                    from logz_client import LogzClient
                    logz_client = LogzClient(logz_api_token)
                    # Add default time range of 1 hour for analysis
                    time_range = "1h"  # Default to last hour
                    logz_analysis = logz_client.analyze_cluster_logs(
                        cluster_name=cluster_name,
                        time_range=time_range,
                        size=1000  # Increased size to get more logs
                    )
                    
                    if logz_analysis is None:
                        logger.warning("No Logz.io analysis data received")
                        results["Logz.io Analysis"] = {
                            "slow_queries": [],
                            "parsing_exceptions": [],
                            "summary": {
                                "total_logs": 0,
                                "slow_queries_count": 0,
                                "parsing_exceptions_count": 0
                            }
                        }
                    elif "error" in logz_analysis:
                        logger.error(f"Error in Logz.io analysis: {logz_analysis['error']}")
                        results["Logz.io Analysis"] = {
                            "slow_queries": [],
                            "parsing_exceptions": [],
                            "summary": {
                                "total_logs": 0,
                                "slow_queries_count": 0,
                                "parsing_exceptions_count": 0,
                                "error": logz_analysis["error"]
                            }
                        }
                    else:
                        results["Logz.io Analysis"] = {
                            "slow_queries": logz_analysis.get("slow_queries", []),
                            "parsing_exceptions": logz_analysis.get("parsing_exceptions", []),
                            "summary": logz_analysis.get("summary", {
                                "total_logs": 0,
                                "slow_queries_count": 0,
                                "parsing_exceptions_count": 0
                            })
                        }
            except Exception as e:
                logger.error(f"Error during Logz.io analysis: {str(e)}")
                results["Logz.io Analysis"] = {
                    "slow_queries": [],
                    "parsing_exceptions": [],
                    "summary": {
                        "total_logs": 0,
                        "slow_queries_count": 0,
                        "parsing_exceptions_count": 0,
                        "error": str(e)
                    }
                }
            finally:
                pbar.update(1)
                print(f"\n✓ {stages[7]} - Completed")
        
        # Stage 9: Generate Report
        pbar.set_description(stages[-1])
        export_html_report(results, logz_api_token=logz_api_token, cluster_name=cluster_name)
        pbar.update(1)
        print(f"\n✓ {stages[-1]} - Completed")
        
    except Exception as e:
        logger.error(f"Error during monitoring: {str(e)}")
        raise
    finally:
        pbar.close()
        print("\n")  # Add a newline after the progress bar


def main(host, port, region, access_key, secret_key, domain=None, username=None, password=None, use_ssl=True, logz_api_token=None, log_level="INFO"):
    print("OpenSearch Monitor started")
    try:
        # Configure logging first
        configure_logging(log_level)
        logger.info("Starting OpenSearch Monitor with log level: {}", log_level)
        
        run_monitors(host, port, region, access_key, secret_key, domain, username, password, use_ssl, logz_api_token)
        print("\nReport generated: opensearch_report.html")
    except Exception as e:
        logger.error(f"Error during monitoring: {str(e)}")
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenSearch Monitor Connectivity")
    parser.add_argument('--host', required=True, help='OpenSearch endpoint host')
    parser.add_argument('--port', type=int, default=443, help='OpenSearch endpoint port (default: 443)')
    parser.add_argument('--region', help='AWS region (optional)')
    parser.add_argument('--access_key', help='AWS access key ID (optional)')
    parser.add_argument('--secret_key', help='AWS secret access key (optional)')
    parser.add_argument('--domain', help='OpenSearch domain name (optional)')
    parser.add_argument('--username', help='OpenSearch username (optional)')
    parser.add_argument('--password', help='OpenSearch password (optional)')
    parser.add_argument('--no-ssl', dest='use_ssl', action='store_false', help='Disable SSL (default: enabled)')
    parser.add_argument('--logz-api-token', help='Logz.io API token (optional)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='INFO',
                       help='Set the logging level (default: INFO)')
    parser.set_defaults(use_ssl=True)
    args = parser.parse_args()
    main(args.host, args.port, args.region, args.access_key, args.secret_key, 
         args.domain, args.username, args.password, args.use_ssl, args.logz_api_token,
         args.log_level) 