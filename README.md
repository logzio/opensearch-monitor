# OpenSearch Monitor

A comprehensive monitoring tool for OpenSearch clusters that provides detailed analysis of cluster health, performance, and configuration. The tool generates an HTML report with insights about your OpenSearch cluster, including Logz.io integration for log analysis.

## Features

- Cluster Health Analysis
- Shard Allocation Analysis
- Index Settings Analysis
- Query Performance Analysis
- Index Mapping Analysis
- AWS Resource Alignment Analysis (for AWS OpenSearch domains)
- Logz.io Integration for Log Analysis
- HTML Report Generation with Progress Tracking

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Access to an OpenSearch cluster
- (Optional) AWS credentials for AWS OpenSearch domains
- (Optional) Logz.io API token for log analysis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/opensearch_monitor.git
cd opensearch_monitor
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

To run the monitor with basic OpenSearch connection:

```bash
python main.py --host your-opensearch-host --port 9200
```

### With Authentication

If your OpenSearch cluster requires authentication:

```bash
python main.py --host your-opensearch-host --port 9200 --username your-username --password your-password
```

### With AWS OpenSearch

For AWS OpenSearch domains, include AWS credentials and domain name:

```bash
python main.py --host your-opensearch-host --port 9200 \
    --region us-east-1 \
    --access_key your-aws-access-key \
    --secret_key your-aws-secret-key \
    --domain your-opensearch-domain
```

### With Logz.io Integration

To include Logz.io log analysis in the report:

```bash
python main.py --host your-opensearch-host --port 9200 \
    --logz-api-token your-logz-api-token
```

### Complete Example

A complete example with all options:

```bash
python main.py \
    --host your-opensearch-host \
    --port 9200 \
    --region us-east-1 \
    --access_key your-aws-access-key \
    --secret_key your-aws-secret-key \
    --domain your-opensearch-domain \
    --username your-username \
    --password your-password \
    --logz-api-token your-logz-api-token \
    --no-ssl
```

## Command Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--host` | OpenSearch endpoint host | Yes | - |
| `--port` | OpenSearch endpoint port | No | 443 |
| `--region` | AWS region (for AWS OpenSearch) | No | - |
| `--access_key` | AWS access key ID | No | - |
| `--secret_key` | AWS secret access key | No | - |
| `--domain` | OpenSearch domain name | No | - |
| `--username` | OpenSearch username | No | - |
| `--password` | OpenSearch password | No | - |
| `--logz-api-token` | Logz.io API token | No | - |
| `--no-ssl` | Disable SSL | No | SSL enabled |

## Output

The tool generates an HTML report (`opensearch_report.html`) that includes:

- Cluster Health Status
- Shard Allocation Analysis
- Index Settings Analysis
- Query Performance Metrics
- Index Mapping Analysis
- AWS Resource Alignment (if applicable)
- Logz.io Log Analysis (if API token provided)

The report includes a progress bar showing the current stage of the monitoring process.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For support, please open an issue in the GitHub repository. 