# Configuration API

Timeout, connection limits, proxy, and SSL configuration options for customizing httpx client behavior.

## Overview

httpx provides comprehensive configuration options for timeouts, connection pooling, proxy settings, and SSL/TLS handling. These can be set as defaults for clients or overridden per request.

## Capabilities

### Timeout Configuration

```python { .api }
class Timeout:
    """
    Timeout configuration for HTTP requests.
    
    Supports granular timeout control for different phases of the request.
    """
    
    def __init__(self, timeout=5.0, *, connect=None, read=None, write=None, pool=None):
        """
        Initialize timeout configuration.
        
        Args:
            timeout (float | None): Default timeout for all operations (default: 5.0)
            connect (float | None): Connection timeout (default: uses timeout)
            read (float | None): Read timeout (default: uses timeout)
            write (float | None): Write timeout (default: uses timeout)
            pool (float | None): Pool acquisition timeout (default: uses timeout)
        
        Special values:
            - None: No timeout (wait indefinitely)
            - 0.0: No timeout (same as None)
            - Positive float: Timeout in seconds
        """
    
    def as_dict(self):
        """
        Convert timeout to dictionary format.
        
        Returns:
            dict[str, float | None]: Timeout configuration as dict
        """
```

### Connection Limits

```python { .api }
class Limits:
    """
    Connection pool limits configuration.
    
    Controls the number of concurrent connections and keep-alive behavior.
    """
    
    def __init__(self, *, max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0):
        """
        Initialize connection limits.
        
        Args:
            max_connections (int | None): Maximum concurrent connections (default: 100)
            max_keepalive_connections (int | None): Maximum keep-alive connections (default: 20)
            keepalive_expiry (float | None): Keep-alive connection timeout in seconds (default: 5.0)
        
        Notes:
            - max_connections includes both active and keep-alive connections
            - Keep-alive connections are reused for better performance
            - None means no limit (use with caution)
        """
```

### Proxy Configuration

```python { .api }
class Proxy:
    """
    Proxy configuration for HTTP requests.
    
    Supports HTTP, HTTPS, and SOCKS5 proxies with authentication.
    """
    
    def __init__(self, url, *, auth=None, headers=None):
        """
        Initialize proxy configuration.
        
        Args:
            url (str | URL): Proxy URL (e.g., 'http://proxy.example.com:8080')
            auth (tuple[str, str], optional): Proxy authentication (username, password)
            headers (dict, optional): Additional headers to send to proxy
        
        Supported schemes:
            - http://: HTTP proxy
            - https://: HTTPS proxy (proxy connection is encrypted)
            - socks5://: SOCKS5 proxy
            - socks5h://: SOCKS5 proxy with hostname resolution through proxy
        """
    
    @property
    def url(self):
        """Proxy URL."""
        return self._url
    
    @property
    def auth(self):
        """Proxy authentication credentials."""
        return self._auth
    
    @property
    def headers(self):
        """Proxy headers."""
        return self._headers
```

## Usage Examples

### Basic Timeout Configuration

```python
import httpx

# Simple timeout (applies to all operations)
response = httpx.get('https://example.com', timeout=10.0)

# No timeout
response = httpx.get('https://example.com', timeout=None)

# Client with default timeout
with httpx.Client(timeout=30.0) as client:
    response = client.get('https://example.com')
```

### Granular Timeout Control

```python
import httpx

# Different timeouts for different phases
timeout = httpx.Timeout(
    timeout=30.0,    # Default for all operations
    connect=5.0,     # Connection timeout
    read=10.0,       # Read timeout
    write=5.0,       # Write timeout
    pool=2.0         # Pool acquisition timeout
)

with httpx.Client(timeout=timeout) as client:
    response = client.get('https://example.com')
```

### Connection Limits

```python
import httpx

# Custom connection limits
limits = httpx.Limits(
    max_connections=50,              # Total connections
    max_keepalive_connections=10,    # Keep-alive connections
    keepalive_expiry=30.0           # Keep-alive timeout
)

with httpx.Client(limits=limits) as client:
    # Client will maintain at most 50 concurrent connections
    # with up to 10 keep-alive connections reused for 30 seconds
    response = client.get('https://example.com')
```

### HTTP Proxy

```python
import httpx

# Simple HTTP proxy
with httpx.Client(proxy='http://proxy.example.com:8080') as client:
    response = client.get('https://example.com')

# Proxy with authentication
proxy = httpx.Proxy(
    'http://proxy.example.com:8080',
    auth=('username', 'password')
)

with httpx.Client(proxy=proxy) as client:
    response = client.get('https://example.com')
```

### SOCKS Proxy

```python
import httpx

# SOCKS5 proxy
with httpx.Client(proxy='socks5://proxy.example.com:1080') as client:
    response = client.get('https://example.com')

# SOCKS5 with hostname resolution through proxy
with httpx.Client(proxy='socks5h://proxy.example.com:1080') as client:
    response = client.get('https://example.com')
```

### Multiple Proxies

```python
import httpx

# Different proxies for different protocols
proxies = {
    'http://': 'http://proxy.example.com:8080',
    'https://': 'https://secure-proxy.example.com:8443'
}

with httpx.Client(proxies=proxies) as client:
    # HTTP requests use first proxy, HTTPS use second
    http_response = client.get('http://example.com')
    https_response = client.get('https://example.com')
```

### SSL/TLS Configuration

```python
import httpx
import ssl

# Disable SSL verification (not recommended for production)
with httpx.Client(verify=False) as client:
    response = client.get('https://self-signed.example.com')

# Custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

with httpx.Client(verify=ssl_context) as client:
    response = client.get('https://example.com')

# Custom CA bundle
with httpx.Client(verify='/path/to/ca-bundle.crt') as client:
    response = client.get('https://example.com')
```

### Client Certificates

```python
import httpx

# Client certificate for mutual TLS
with httpx.Client(cert='/path/to/client.pem') as client:
    response = client.get('https://api.example.com')

# Separate cert and key files
with httpx.Client(cert=('/path/to/client.crt', '/path/to/client.key')) as client:
    response = client.get('https://api.example.com')
```

### HTTP/2 Configuration

```python
import httpx

# Enable HTTP/2
with httpx.Client(http2=True) as client:
    response = client.get('https://http2.example.com')
    print(response.http_version)  # "HTTP/2"

# HTTP/1.1 only
with httpx.Client(http1=True, http2=False) as client:
    response = client.get('https://example.com')
    print(response.http_version)  # "HTTP/1.1"
```

### Combined Configuration

```python
import httpx

# Comprehensive client configuration
timeout = httpx.Timeout(
    timeout=30.0,
    connect=5.0,
    read=10.0
)

limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20
)

proxy = httpx.Proxy(
    'http://proxy.example.com:8080',
    auth=('user', 'pass')
)

with httpx.Client(
    timeout=timeout,
    limits=limits,
    proxy=proxy,
    http2=True,
    verify=True,
    headers={'User-Agent': 'MyApp/1.0'}
) as client:
    response = client.get('https://api.example.com/data')
```

### Environment Variable Support

```python
import httpx

# httpx automatically uses these environment variables when trust_env=True:
# - HTTP_PROXY, HTTPS_PROXY: Proxy URLs
# - NO_PROXY: Comma-separated list of hosts to bypass proxy
# - SSL_CERT_FILE, SSL_CERT_DIR: SSL certificate locations
# - REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE: CA bundle file

with httpx.Client(trust_env=True) as client:
    # Uses proxy from HTTP_PROXY/HTTPS_PROXY if set
    response = client.get('https://example.com')

# Disable environment variable usage
with httpx.Client(trust_env=False) as client:
    # Ignores proxy environment variables
    response = client.get('https://example.com')
```

### Per-Request Overrides

```python
import httpx

# Client with default 5-second timeout
with httpx.Client(timeout=5.0) as client:
    # Use default timeout
    response1 = client.get('https://fast.example.com')
    
    # Override timeout for slow endpoint
    response2 = client.get('https://slow.example.com', timeout=30.0)
    
    # No timeout for this request
    response3 = client.get('https://example.com', timeout=None)
```

### Async Configuration

```python
import httpx
import asyncio

async def main():
    timeout = httpx.Timeout(10.0)
    limits = httpx.Limits(max_connections=50)
    
    async with httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        http2=True
    ) as client:
        response = await client.get('https://example.com')
        print(response.status_code)

asyncio.run(main())
```

### Default Configurations

```python
import httpx

# httpx provides these defaults:
DEFAULT_TIMEOUT_CONFIG = httpx.Timeout(timeout=5.0)
DEFAULT_LIMITS = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=5.0
)
DEFAULT_MAX_REDIRECTS = 20

# These are used when not explicitly specified
with httpx.Client() as client:
    # Uses default timeout of 5 seconds
    # Uses default connection limits
    # Follows up to 20 redirects
    response = client.get('https://example.com')
```