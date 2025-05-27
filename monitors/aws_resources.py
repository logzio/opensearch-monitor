import boto3
import datetime

def get_domain_info(region, aws_access_key, aws_secret_key, domain_name):
    client = boto3.client('opensearch', region_name=region,
                         aws_access_key_id=aws_access_key,
                         aws_secret_access_key=aws_secret_key)
    if not domain_name:
        return {'error': 'OPENSEARCH_DOMAIN not set'}
    try:
        response = client.describe_domain(DomainName=domain_name)
        return response['DomainStatus']
    except Exception as e:
        return {'error': str(e)}


def get_cloudwatch_metrics(region, aws_access_key, aws_secret_key, domain_name, period=300, duration_minutes=60):
    cw = boto3.client('cloudwatch', region_name=region,
                      aws_access_key_id=aws_access_key,
                      aws_secret_access_key=aws_secret_key)
    metrics = [
        'CPUUtilization',
        'JVMMemoryPressure',
        'FreeStorageSpace',
        'ClusterIndexWritesBlocked',
        'ClusterStatus.red',
        'ClusterStatus.yellow',
        'Nodes',
        'AutomatedSnapshotFailure'
    ]
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(minutes=duration_minutes)
    results = {}
    for metric in metrics:
        response = cw.get_metric_statistics(
            Namespace='AWS/ES',
            MetricName=metric,
            Dimensions=[{'Name': 'DomainName', 'Value': domain_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=['Average', 'Maximum']
        )
        datapoints = response.get('Datapoints', [])
        if datapoints:
            # Sort by Timestamp descending
            datapoints = sorted(datapoints, key=lambda x: x['Timestamp'], reverse=True)
            results[metric] = {
                'Average': datapoints[0].get('Average'),
                'Maximum': datapoints[0].get('Maximum'),
                'Timestamp': datapoints[0].get('Timestamp').isoformat()
            }
        else:
            results[metric] = 'No data'
    return results


def analyze_resource_alignment(domain_info, cluster_health, search_stats):
    issues = []
    if 'error' in domain_info:
        return [domain_info['error']]
    instance_type = domain_info['ClusterConfig']['InstanceType']
    instance_count = domain_info['ClusterConfig']['InstanceCount']
    storage_gb = int(domain_info['EBSOptions']['VolumeSize']) if domain_info['EBSOptions']['EBSEnabled'] else 0
    # Example checks (expand as needed):
    if instance_count < 3:
        issues.append(f"Only {instance_count} data nodes. Consider at least 3 for HA.")
    if 'number_of_nodes' in cluster_health and cluster_health['number_of_nodes'] > instance_count:
        issues.append("Cluster reports more nodes than provisioned. Check for node failures or split-brain.")
    # Storage check (if available)
    if storage_gb > 0:
        # Try to estimate usage from search_stats (not exact, but illustrative)
        total_docs = 0
        for idx in search_stats.get('indices', {}).values():
            total_docs += idx.get('total', {}).get('docs', {}).get('count', 0)
        if total_docs > 1_000_000 and storage_gb < 100:
            issues.append(f"High doc count ({total_docs}) but low storage ({storage_gb}GB). Monitor disk usage.")
    # Instance type check
    if instance_type.startswith('t3.'):
        issues.append(f"Instance type {instance_type} is burstable and not recommended for production.")
    if not issues:
        issues.append("AWS resources appear aligned with current cluster load.")
    return issues 