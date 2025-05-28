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

        # Simplified payload - only what we need for log analysis
        payload = {
            "query": {
                "bool": {
                    "must": must_conditions
                }
            },
            "from": 0,
            "size": size,
            "sort": [{"@timestamp": "desc"}],  # Sort by timestamp descending
            "_source": True,  # Get the full log message
            "stored_fields": ["*"]
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
            logger.debug(f"Response text: {response.text[:10000]}")  # Log first 1000 chars of response
            
            response.raise_for_status()
            result = response.json()
            
            # Handle different total hits formats
            total_hits = 0
            hits = result.get("hits", {})
            if isinstance(hits, dict):
                total = hits.get("total", {})
                if isinstance(total, dict):
                    # New format: {"total": {"value": 123, "relation": "eq"}}
                    total_hits = total.get("value", 0)
                elif isinstance(total, (int, float)):
                    # Old format: {"total": 123}
                    total_hits = total
                else:
                    logger.warning(f"Unexpected total hits format: {type(total)}")
            
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
            logger.debug(f"Full response: {response.text if 'response' in locals() else 'No response'}")
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
        
        # Updated query to search for patterns in messages
        query = f'''
        (
            cluster_name:"{cluster_name}" AND (
                type:elasticsearch_slow_search OR
                message:*"took_millis["* OR
                message:*"mapper_parsing_exception"* OR
                message:*"MapperParsingException"*
            )
        )
        '''
        
        return self.search_logs(
            query=query,
            time_range=time_range,
            size=size
        )

    def analyze_cluster_logs(self, cluster_name: str, time_range: str = "1h", size: int = 1000) -> Dict[str, any]:
        """
        Analyze cluster logs for slow queries, slow indexing, and parsing exceptions
        
        Args:
            cluster_name (str): Name of the cluster to analyze
            time_range (str): Time range for the search (e.g., "5m", "1h", "1d")
            size (int): Maximum number of results to return
            
        Returns:
            Dict containing analysis results
        """
        logger.info(f"Starting log analysis for cluster: {cluster_name} with time range: {time_range}")
        
        # Get logs for the cluster
        logs = self.get_cluster_logs(
            cluster_name=cluster_name,
            time_range=time_range,
            size=size
        )
        
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
            
        # Handle different total hits formats
        total_value = 0
        total = hits.get("total", {})
        if isinstance(total, dict):
            # New format: {"total": {"value": 123, "relation": "eq"}}
            total_value = total.get("value", 0)
        elif isinstance(total, (int, float)):
            # Old format: {"total": 123}
            total_value = total
        else:
            error_msg = f"Unexpected total hits format: {type(total)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Initialize analysis results with validated data
        analysis = {
            "slow_queries": [],
            "slow_indexing": [],
            "parsing_exceptions": [],
            "summary": {
                "total_logs": total_value,
                "slow_queries_count": 0,
                "slow_indexing_count": 0,
                "parsing_exceptions_count": 0,
                "slowest_query_time": 0,
                "slowest_indexing_time": 0,
                "average_query_time": 0,
                "average_indexing_time": 0
            }
        }
        
        logger.info(f"Analyzing {analysis['summary']['total_logs']} log entries")
        
        # Get hits array with validation
        hits_array = hits.get("hits", [])
        if not isinstance(hits_array, list):
            error_msg = f"Invalid hits array format: {type(hits_array)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        total_query_time = 0
        total_indexing_time = 0
        query_count = 0
        indexing_count = 0
        
        # Patterns for identifying issues
        slow_indexing_pattern = r'took_millis\[(\d+)\]'
        query_pattern = r'query\[(.*?)\]'  # Pattern to extract query
        index_pattern = r'index\[(.*?)\]'  # Pattern to extract index
        
        # Log a sample message for debugging
        if hits_array:
            sample_message = hits_array[0].get("_source", {})
            logger.debug(f"Sample log entry format: {json.dumps(sample_message, indent=2)}")
        
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
            
            # Check log type for slow search
            log_type = source.get("type", "")
            
            # Handle slow search logs
            if log_type == "elasticsearch_slow_search":
                try:
                    # Get took_millis directly from the source
                    query_time = source.get("took_millis")
                    if isinstance(query_time, (int, float)):
                        # Get query from originalSearchRequest.query
                        original_request = source.get("originalSearchRequest", {})
                        actual_query = original_request.get("query", "N/A")
                        
                        # Clean up the query if it's a JSON string
                        try:
                            if isinstance(actual_query, str) and actual_query.startswith('{') and actual_query.endswith('}'):
                                query_json = json.loads(actual_query)
                                actual_query = json.dumps(query_json, indent=2)
                            elif isinstance(actual_query, dict):
                                actual_query = json.dumps(actual_query, indent=2)
                        except json.JSONDecodeError:
                            pass  # Keep the original query if it's not valid JSON
                        
                        # Get index from the source
                        actual_index = source.get("index", "N/A")
                        
                        logger.debug(f"Found slow query with took_millis: {query_time}, query: {actual_query}")
                        analysis["slow_queries"].append({
                            "timestamp": timestamp,
                            "query_time": query_time,
                            "source": source.get("source", "N/A"),
                            "message": message,
                            "index": actual_index,
                            "query": actual_query,
                            "query_type": source.get("query_type", "N/A"),
                            "shard": source.get("shard", "N/A")
                        })
                        total_query_time += query_time
                        query_count += 1
                        if query_time > analysis["summary"]["slowest_query_time"]:
                            analysis["summary"]["slowest_query_time"] = query_time
                except Exception as e:
                    logger.warning(f"Failed to process slow search log: {message}. Error: {str(e)}")
                    logger.debug(f"Full message content: {message}")
                    logger.debug(f"Full source content: {json.dumps(source, indent=2)}")
            
            # Handle slow indexing logs by searching in message
            slow_indexing_match = re.search(slow_indexing_pattern, message)
            if slow_indexing_match:
                try:
                    indexing_time = int(slow_indexing_match.group(1))
                    logger.debug(f"Found slow indexing with took_millis: {indexing_time}")
                    analysis["slow_indexing"].append({
                        "timestamp": timestamp,
                        "indexing_time": indexing_time,
                        "source": source.get("source", "N/A"),
                        "message": message,
                        "index": source.get("index", "N/A")
                    })
                    total_indexing_time += indexing_time
                    indexing_count += 1
                    if indexing_time > analysis["summary"]["slowest_indexing_time"]:
                        analysis["summary"]["slowest_indexing_time"] = indexing_time
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse indexing time from message: {message}. Error: {str(e)}")
            
            # Handle parsing exceptions
            elif "mapper_parsing_exception" in message.lower() or "MapperParsingException" in message:
                logger.debug(f"Found parsing exception: {message}")
                analysis["parsing_exceptions"].append({
                    "timestamp": timestamp,
                    "source": source.get("source", "N/A"),
                    "type": "Mapper Parsing Exception",
                    "message": message,
                    "index": source.get("index", "N/A")
                })
        
        # Update summary statistics
        analysis["summary"]["slow_queries_count"] = len(analysis["slow_queries"])
        analysis["summary"]["slow_indexing_count"] = len(analysis["slow_indexing"])
        analysis["summary"]["parsing_exceptions_count"] = len(analysis["parsing_exceptions"])
        
        if query_count > 0:
            analysis["summary"]["average_query_time"] = total_query_time / query_count
        if indexing_count > 0:
            analysis["summary"]["average_indexing_time"] = total_indexing_time / indexing_count
        
        # Sort results
        analysis["slow_queries"].sort(key=lambda x: x.get("query_time", 0), reverse=True)
        analysis["slow_indexing"].sort(key=lambda x: x.get("indexing_time", 0), reverse=True)
        analysis["parsing_exceptions"].sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        logger.info(f"Analysis complete. Found {analysis['summary']['slow_queries_count']} slow queries, "
                   f"{analysis['summary']['slow_indexing_count']} slow indexing operations, and "
                   f"{analysis['summary']['parsing_exceptions_count']} parsing exceptions")
        
        if (analysis['summary']['slow_queries_count'] == 0 and 
            analysis['summary']['slow_indexing_count'] == 0 and 
            analysis['summary']['parsing_exceptions_count'] == 0):
            logger.debug("No issues found. Sample of analyzed messages:")
            for hit in hits_array[:5]:  # Log first 5 messages for debugging
                source = hit.get("_source", {})
                logger.debug(f"Log entry: {json.dumps(source, indent=2)}")
        
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