import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from loguru import logger
import re

class LogzClient:
    def __init__(self, api_token: str, region: str = "us"):
        """Initialize Logz.io API client.
        
        Args:
            api_token: Logz.io API token
            region: Logz.io region (default: 'us')
        """
        if not api_token or not isinstance(api_token, str):
            raise ValueError("Valid API token is required")
            
        self.api_token = api_token
        self.base_url = "https://api.logz.io/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-API-TOKEN': api_token
        }
        logger.info(f"Initialized Logz.io client with base URL: {self.base_url}")

    def search_logs(self, 
                   query: Optional[str] = None,
                   time_range: str = "5m",
                   size: int = 100,
                   from_time: Optional[datetime] = None,
                   to_time: Optional[datetime] = None) -> Dict:
        """Search logs using Logz.io API.
        
        Args:
            query: Optional search query string
            time_range: Time range for search (e.g., "5m", "1h", "1d")
            size: Number of results to return (max 10000)
            from_time: Optional start time for search
            to_time: Optional end time for search
            
        Returns:
            Dict containing search results
        """
        if size > 10000:
            size = 10000
            logger.warning("Size parameter exceeds maximum of 10000, capping at 10000")

        # Parse time range
        if not from_time and not to_time:
            # Use relative time format that Logz.io expects
            time_range_value = time_range[:-1]  # Remove the 'm', 'h', or 'd'
            time_range_unit = time_range[-1]    # Get the unit
            gte = f"now-{time_range_value}{time_range_unit}"
            lte = "now"
        else:
            # Convert datetime objects to ISO format
            gte = from_time.isoformat() if from_time else "now-5m"
            lte = to_time.isoformat() if to_time else "now"

        logger.info(f"Searching logs with time range: {gte} to {lte}")

        # Construct the search payload
        must_conditions = [
            {
                "range": {
                    "@timestamp": {
                        "gte": gte,
                        "lte": lte
                    }
                }
            }
        ]

        # Add query if provided
        if query:
            must_conditions.append({
                "query_string": {
                    "query": query
                }
            })

        payload = {
            "query": {
                "bool": {
                    "must": must_conditions
                }
            },
            "from": 0,
            "size": size,
            "sort": [{}],  # Empty sort object as per API example
            "_source": True,  # Changed to True to get the full log message
            "post_filter": None,
            "docvalue_fields": ["@timestamp"],
            "version": True,
            "stored_fields": ["*"],
            "highlight": {},
            "aggregations": {
                "byType": {
                    "terms": {
                        "field": "type",
                        "size": 5
                    }
                }
            }
        }

        try:
            logger.debug(f"Sending request to {self.base_url}/search with payload: {json.dumps(payload)}")
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            # Log response status and headers
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response text: {response.text[:1000]}")  # Log first 1000 chars of response
            
            response.raise_for_status()
            result = response.json()
            
            # Log response summary
            total_hits = result.get("hits", {}).get("total", {}).get("value", 0)
            logger.info(f"Search returned {total_hits} hits")
            
            if total_hits == 0:
                logger.warning("No logs found for the given criteria")
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "Request to Logz.io API timed out"
            logger.error(error_msg)
            return {"error": error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error searching logs: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse: {e.response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during log search: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_cluster_logs(self, 
                        cluster_name: str,
                        time_range: str = "1h",
                        size: int = 100) -> Dict:
        """Get logs specific to an OpenSearch cluster.
        
        Args:
            cluster_name: Name of the OpenSearch cluster
            time_range: Time range for search (e.g., "5m", "1h", "1d")
            size: Number of results to return
            
        Returns:
            Dict containing cluster logs
        """
        if not cluster_name:
            error_msg = "Cluster name is required"
            logger.error(error_msg)
            return {"error": error_msg}
            
        logger.info(f"Fetching logs for cluster: {cluster_name}")
        # Updated query format to match Logz.io's expected format
        query = f'cluster_name: "{cluster_name}"'  # Added quotes around cluster name
        
        return self.search_logs(
            query=query,
            time_range=time_range,
            size=size
        )

    def analyze_cluster_logs(self, cluster_name: str, time_range: Optional[Dict[str, str]] = None, size: int = 1000) -> Dict[str, any]:
        """
        Analyze cluster logs for slow queries and parsing exceptions
        
        Args:
            cluster_name (str): Name of the cluster to analyze
            time_range (Dict): Optional time range for the search
            size (int): Maximum number of results to return
            
        Returns:
            Dict containing analysis results
        """
        logger.info(f"Starting log analysis for cluster: {cluster_name}")
        
        # Get logs for the cluster
        logs = self.get_cluster_logs(cluster_name, time_range, size)
        
        # Validate logs response
        if not isinstance(logs, dict):
            error_msg = f"Invalid response format from Logz.io: {type(logs)}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        if "error" in logs:
            logger.error(f"Failed to get cluster logs: {logs['error']}")
            return logs
            
        if "hits" not in logs:
            error_msg = "Response missing 'hits' field"
            logger.error(error_msg)
            logger.debug(f"Full response: {json.dumps(logs)}")
            return {"error": error_msg}
            
        hits = logs.get("hits", {})
        if not isinstance(hits, dict):
            error_msg = f"Invalid hits format: {type(hits)}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        total = hits.get("total", {})
        if not isinstance(total, dict):
            error_msg = f"Invalid total format: {type(total)}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        total_value = total.get("value", 0)
        if not isinstance(total_value, (int, float)):
            error_msg = f"Invalid total value format: {type(total_value)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Initialize analysis results with validated data
        analysis = {
            "slow_queries": [],
            "parsing_exceptions": [],
            "summary": {
                "total_logs": total_value,
                "slow_queries_count": 0,
                "parsing_exceptions_count": 0,
                "slowest_query_time": 0,
                "average_query_time": 0
            }
        }
        
        logger.info(f"Analyzing {analysis['summary']['total_logs']} log entries")
        
        # Get hits array with validation
        hits_array = hits.get("hits", [])
        if not isinstance(hits_array, list):
            error_msg = f"Invalid hits array format: {type(hits_array)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Patterns for identifying issues
        slow_query_pattern = r"took\[(\d+)ms\]"
        parsing_exception_pattern = r"mapper_parsing_exception"
        
        total_query_time = 0
        query_count = 0
        
        # Analyze each log entry with validation
        for hit in hits_array:
            if not isinstance(hit, dict):
                logger.warning(f"Skipping invalid hit format: {type(hit)}")
                continue
                
            source = hit.get("_source", {})
            if not isinstance(source, dict):
                logger.warning(f"Skipping hit with invalid _source format: {type(source)}")
                continue
                
            message = source.get("message", "")
            if not isinstance(message, str):
                logger.warning(f"Skipping hit with invalid message format: {type(message)}")
                continue
                
            timestamp = source.get("@timestamp")
            if not timestamp:
                logger.warning("Skipping hit without timestamp")
                continue
            
            # Check for slow queries
            slow_query_match = re.search(slow_query_pattern, message)
            if slow_query_match:
                try:
                    query_time = int(slow_query_match.group(1))
                    if query_time > 1000:  # Consider queries over 1 second as slow
                        analysis["slow_queries"].append({
                            "timestamp": timestamp,
                            "query_time": query_time,
                            "source": source.get("source", "N/A"),
                            "message": message
                        })
                        total_query_time += query_time
                        query_count += 1
                        if query_time > analysis["summary"]["slowest_query_time"]:
                            analysis["summary"]["slowest_query_time"] = query_time
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse query time from message: {message}. Error: {str(e)}")
            
            # Check for parsing exceptions
            if parsing_exception_pattern in message.lower():
                analysis["parsing_exceptions"].append({
                    "timestamp": timestamp,
                    "source": source.get("source", "N/A"),
                    "type": "Mapper Parsing Exception",
                    "message": message
                })
        
        # Update summary statistics
        analysis["summary"]["slow_queries_count"] = len(analysis["slow_queries"])
        analysis["summary"]["parsing_exceptions_count"] = len(analysis["parsing_exceptions"])
        if query_count > 0:
            analysis["summary"]["average_query_time"] = total_query_time / query_count
        
        # Sort results
        analysis["slow_queries"].sort(key=lambda x: x.get("query_time", 0), reverse=True)
        analysis["parsing_exceptions"].sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        logger.info(f"Analysis complete. Found {analysis['summary']['slow_queries_count']} slow queries and {analysis['summary']['parsing_exceptions_count']} parsing exceptions")
        return analysis

    def _extract_query_details(self, message: str) -> Dict[str, str]:
        """Extract query and index details from log message"""
        details = {"query": None, "index": None}
        
        # Try to extract index pattern
        index_match = re.search(r'index\[([^\]]+)\]', message)
        if index_match:
            details["index"] = index_match.group(1)
        
        # Try to extract query
        query_match = re.search(r'query\[([^\]]+)\]', message)
        if query_match:
            details["query"] = query_match.group(1)
        
        return details

    def _extract_parsing_exception_details(self, message: str) -> Dict[str, str]:
        """Extract details from parsing exception message"""
        details = {
            "reason": None,
            "field": None,
            "value": None
        }
        
        # Extract reason
        reason_match = re.search(r'reason\[([^\]]+)\]', message)
        if reason_match:
            details["reason"] = reason_match.group(1)
        
        # Extract field
        field_match = re.search(r'field\[([^\]]+)\]', message)
        if field_match:
            details["field"] = field_match.group(1)
        
        # Extract value
        value_match = re.search(r'value\[([^\]]+)\]', message)
        if value_match:
            details["value"] = value_match.group(1)
        
        return details 