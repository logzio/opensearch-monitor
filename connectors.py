from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

def get_opensearch_client(host, port, region=None, aws_access_key=None, aws_secret_key=None, username=None, password=None, use_ssl=True):
    if username and password:
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            use_ssl=use_ssl,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
    else:
        if region and aws_access_key and aws_secret_key:
            awsauth = AWS4Auth(
                aws_access_key,
                aws_secret_key,
                region,
                'es'
            )
            client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=awsauth,
                use_ssl=use_ssl,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
        else:
            client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                use_ssl=use_ssl,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
    return client 