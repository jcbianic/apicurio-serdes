# Synchronous HTTP Client

The `Client` class provides a synchronous HTTP client with connection pooling, cookie persistence, and configuration reuse across multiple requests. It's more efficient than top-level functions when making multiple requests.

## Overview

The client maintains connection pools, persistent cookies, and default configuration that applies to all requests. It's thread-safe and can be shared between threads.

## Capabilities

### Client Class

#### Constructor

```python { .api }
class Client:
    def __init__(self, *, auth=None, params=None, headers=None, cookies=None, verify=True, cert=None, trust_env=True, http1=True, http2=False, proxy=None, mounts=None, timeout=DEFAULT_TIMEOUT_CONFIG, follow_redirects=False, limits=DEFAULT_LIMITS, max_redirects=DEFAULT_MAX_REDIRECTS, event_hooks=None, base_url="", transport=None, default_encoding="utf-8"):
        """
        Initialize a synchronous HTTP client.
        
        Args:
            auth (Auth, optional): Default authentication for all requests
            params (dict, optional): Default query parameters for all requests
            headers (dict, optional): Default headers for all requests
            cookies (dict, optional): Default cookies for all requests
            verify (bool | str | SSLContext): SSL certificate verification (default: True)
            cert (str | tuple, optional): Client certificate file path or (cert, key) tuple
            http1 (bool): Enable HTTP/1.1 (default: True)
            http2 (bool): Enable HTTP/2 (default: False)
            proxy (str | Proxy, optional): Proxy URL or configuration
            mounts (dict, optional): Mapping of URL prefixes to custom transports
            timeout (Timeout): Default timeout configuration (default: 5.0s)
            follow_redirects (bool): Default redirect behavior (default: False)
            limits (Limits): Connection pool limits (default: max_connections=100, max_keepalive_connections=20)
            max_redirects (int): Maximum number of redirect hops (default: 20)
            event_hooks (dict, optional): Request/response event hooks
            base_url (str): Base URL to prepend to relative URLs
            transport (BaseTransport, optional): Custom transport implementation
            trust_env (bool): Use environment variables for proxy/SSL config (default: True)
            default_encoding (str | callable): Default text encoding for responses (default: "utf-8")
        """
```

#### Request Methods

```python { .api }
def get(
    self,
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    extensions: RequestExtensions | None = None,
) -> Response:
    """
    Send a GET request.
    
    Args:
        url (str): URL for the request (can be relative to base_url)
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers (merged with client defaults)
        cookies (dict, optional): Cookies (merged with client defaults)
        auth (Auth | USE_CLIENT_DEFAULT): Authentication (overrides client default)
        follow_redirects (bool | USE_CLIENT_DEFAULT): Redirect behavior (overrides client default)
        timeout (Timeout | USE_CLIENT_DEFAULT): Timeout configuration (overrides client default)
        extensions (dict, optional): Protocol extensions
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """

def post(
    self,
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    extensions: RequestExtensions | None = None,
) -> Response:
    """
    Send a POST request.
    
    Args:
        url (str): URL for the request (can be relative to base_url)
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers (merged with client defaults)
        cookies (dict, optional): Cookies (merged with client defaults)
        auth (Auth | USE_CLIENT_DEFAULT): Authentication (overrides client default)
        follow_redirects (bool | USE_CLIENT_DEFAULT): Redirect behavior (overrides client default)
        timeout (Timeout | USE_CLIENT_DEFAULT): Timeout configuration (overrides client default)
        extensions (dict, optional): Protocol extensions
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """

def put(self, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a PUT request. Same arguments as post()."""

def patch(self, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a PATCH request. Same arguments as post()."""

def delete(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a DELETE request. Same arguments as get()."""

def head(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a HEAD request. Same arguments as get()."""

def options(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send an OPTIONS request. Same arguments as get()."""

def request(
    self,
    method: str,
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    extensions: RequestExtensions | None = None,
) -> Response:
    """
    Send an HTTP request with specified method.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
        url (str): URL for the request (can be relative to base_url)
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers (merged with client defaults)
        cookies (dict, optional): Cookies (merged with client defaults)
        auth (Auth | USE_CLIENT_DEFAULT): Authentication (overrides client default)
        follow_redirects (bool | USE_CLIENT_DEFAULT): Redirect behavior (overrides client default)
        timeout (Timeout | USE_CLIENT_DEFAULT): Timeout configuration (overrides client default)
        extensions (dict, optional): Protocol extensions
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### Advanced Methods

```python { .api }
def send(
    self,
    request: Request,
    *,
    stream: bool = False,
    auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
    timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
) -> Response:
    """
    Send a pre-built Request object.
    
    Args:
        request (Request): Request object to send
        stream (bool): Whether to return a streaming response (default: False)
        auth (Auth | USE_CLIENT_DEFAULT): Authentication (overrides client default)
        follow_redirects (bool | USE_CLIENT_DEFAULT): Redirect behavior (overrides client default)
        timeout (Timeout | USE_CLIENT_DEFAULT): Timeout configuration (overrides client default)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """

def build_request(self, method, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None):
    """
    Build a Request object without sending it.
    
    Args:
        method (str): HTTP method
        url (str): URL for the request
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers (merged with client defaults)
        cookies (dict, optional): Cookies (merged with client defaults)
    
    Returns:
        Request: Prepared request object
    """

def stream(self, method, url, **kwargs):
    """
    Stream a request response.
    
    Args:
        method (str): HTTP method
        url (str): URL for the request
        **kwargs: Same arguments as request() method
    
    Returns:
        Generator yielding Response: Context manager for streaming response
    
    Usage:
        with client.stream('GET', '/large-file') as response:
            for chunk in response.iter_bytes():
                process(chunk)
    """

def close(self):
    """
    Close the client and release all connections.
    
    Should be called when done with the client to ensure connections
    are properly closed and resources are released.
    """
```

#### Context Manager Support

```python { .api }
def __enter__(self):
    """Enter context manager."""
    return self

def __exit__(self, exc_type=None, exc_value=None, traceback=None):
    """Exit context manager and close client."""
    self.close()
```

## Usage Examples

### Basic Client Usage

```python
import httpx

# Create and use client
client = httpx.Client()
try:
    response = client.get('https://httpbin.org/get')
    print(response.json())
finally:
    client.close()
```

### Context Manager (Recommended)

```python
import httpx

with httpx.Client() as client:
    response = client.get('https://httpbin.org/get')
    print(response.json())
# Client automatically closed
```

### Client with Default Configuration

```python
import httpx

# Client with base URL and default headers
with httpx.Client(
    base_url='https://api.example.com',
    headers={'User-Agent': 'MyApp/1.0'},
    timeout=10.0
) as client:
    # Relative URLs are resolved against base_url
    users = client.get('/users').json()
    user = client.get('/users/123').json()
```

### Authentication and Cookies

```python
import httpx

auth = httpx.BasicAuth('username', 'password')

with httpx.Client(auth=auth) as client:
    # All requests use authentication
    response = client.get('https://example.com/protected')
    
    # Cookies are automatically persisted
    client.post('https://example.com/login', data={'user': 'me'})
    profile = client.get('https://example.com/profile')  # Uses login cookies
```

### HTTP/2 Support

```python
import httpx

with httpx.Client(http2=True) as client:
    response = client.get('https://http2.example.com')
    print(response.http_version)  # "HTTP/2"
```

### Custom Timeouts and Limits

```python
import httpx

timeout = httpx.Timeout(10.0, connect=5.0)
limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)

with httpx.Client(timeout=timeout, limits=limits) as client:
    response = client.get('https://example.com')
```

### Proxy Support

```python
import httpx

# HTTP proxy
with httpx.Client(proxy='http://proxy.example.com:8080') as client:
    response = client.get('https://example.com')

# SOCKS proxy
with httpx.Client(proxy='socks5://proxy.example.com:1080') as client:
    response = client.get('https://example.com')
```

### Stream Large Responses

```python
import httpx

with httpx.Client() as client:
    with client.stream('GET', 'https://example.com/large-file') as response:
        for chunk in response.iter_bytes(chunk_size=1024):
            # Process chunk without loading entire response into memory
            process_chunk(chunk)
```

### Build and Send Requests

```python
import httpx

with httpx.Client() as client:
    # Build request
    request = client.build_request('POST', '/api/data', json={'key': 'value'})
    
    # Inspect or modify request
    print(request.headers)
    
    # Send the request
    response = client.send(request)
```

### Event Hooks

```python
import httpx

def log_request(request):
    print(f"Request: {request.method} {request.url}")

def log_response(response):
    print(f"Response: {response.status_code}")

with httpx.Client(event_hooks={'request': [log_request], 'response': [log_response]}) as client:
    response = client.get('https://example.com')
```