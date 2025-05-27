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
        self.api_token = api_token
        self.base_url = "https://api.logz.io/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-API-TOKEN': api_token
        }

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
        if not from_time:
            from_time = datetime.utcnow() - timedelta(minutes=int(time_range[:-1]))
        if not to_time:
            to_time = datetime.utcnow()

        # Construct the search payload
        must_conditions = [
            {
                "range": {
                    "@timestamp": {
                        "gte": from_time.isoformat(),
                        "lte": to_time.isoformat()
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
            "sort": [{"@timestamp": "desc"}],
            "_source": True,
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
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching logs: {str(e)}")
            return {"error": str(e)}

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
        query = f'cluster_name:"{cluster_name}"'
        return self.search_logs(query=query, time_range=time_range, size=size)

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
        # Get logs for the cluster
        logs = self.get_cluster_logs(cluster_name, time_range, size)
        
        # Initialize analysis results
        analysis = {
            "slow_queries": [],
            "parsing_exceptions": [],
            "summary": {
                "total_logs": logs.get("hits", {}).get("total", {}).get("value", 0),
                "slow_queries_count": 0,
                "parsing_exceptions_count": 0,
                "slowest_query_time": 0,
                "average_query_time": 0
            }
        }
        
        # Patterns for identifying issues
        slow_query_pattern = r"took\[(\d+)ms\]"
        parsing_exception_pattern = r"mapper_parsing_exception"
        
        total_query_time = 0
        query_count = 0
        
        # Analyze each log entry
        for hit in logs.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            message = source.get("message", "")
            timestamp = source.get("@timestamp")
            
            # Check for slow queries
            slow_query_match = re.search(slow_query_pattern, message)
            if slow_query_match:
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
        analysis["slow_queries"].sort(key=lambda x: x["query_time"], reverse=True)
        analysis["parsing_exceptions"].sort(key=lambda x: x["timestamp"], reverse=True)
        
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