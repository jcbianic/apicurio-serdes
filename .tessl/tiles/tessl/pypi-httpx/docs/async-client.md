# Asynchronous HTTP Client

The `AsyncClient` class provides an asynchronous HTTP client with the same features as the synchronous `Client` but using async/await syntax. It's designed for high-concurrency applications and integrates seamlessly with async frameworks.

## Overview

The async client uses the same API as the synchronous client but all methods are coroutines that must be awaited. It maintains async connection pools and supports concurrent requests efficiently.

## Capabilities

### AsyncClient Class

#### Constructor

```python { .api }
class AsyncClient:
    def __init__(self, *, auth=None, params=None, headers=None, cookies=None, verify=True, cert=None, http1=True, http2=False, proxy=None, mounts=None, timeout=DEFAULT_TIMEOUT_CONFIG, follow_redirects=False, limits=DEFAULT_LIMITS, max_redirects=DEFAULT_MAX_REDIRECTS, event_hooks=None, base_url="", transport=None, trust_env=True, default_encoding="utf-8"):
        """
        Initialize an asynchronous HTTP client.
        
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
            transport (AsyncBaseTransport, optional): Custom async transport implementation
            trust_env (bool): Use environment variables for proxy/SSL config (default: True)
            default_encoding (str | callable): Default text encoding for responses (default: "utf-8")
        """
```

#### Request Methods

```python { .api }
async def get(
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
    Send a GET request asynchronously.
    
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

async def post(
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
    Send a POST request asynchronously.
    
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

async def put(self, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a PUT request asynchronously. Same arguments as post()."""

async def patch(self, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a PATCH request asynchronously. Same arguments as post()."""

async def delete(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a DELETE request asynchronously. Same arguments as get()."""

async def head(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send a HEAD request asynchronously. Same arguments as get()."""

async def options(self, url, *, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """Send an OPTIONS request asynchronously. Same arguments as get()."""

async def request(self, method, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT, extensions=None):
    """
    Send an HTTP request with specified method asynchronously.
    
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
async def send(self, request, *, stream=False, auth=USE_CLIENT_DEFAULT, follow_redirects=USE_CLIENT_DEFAULT, timeout=USE_CLIENT_DEFAULT):
    """
    Send a pre-built Request object asynchronously.
    
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
    Build a Request object without sending it (synchronous).
    
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
    Stream a request response asynchronously.
    
    Args:
        method (str): HTTP method
        url (str): URL for the request
        **kwargs: Same arguments as request() method
    
    Returns:
        AsyncGenerator yielding Response: Async context manager for streaming response
    
    Usage:
        async with client.stream('GET', '/large-file') as response:
            async for chunk in response.aiter_bytes():
                await process_chunk(chunk)
    """

async def aclose(self):
    """
    Close the client and release all connections asynchronously.
    
    Should be called when done with the client to ensure connections
    are properly closed and resources are released.
    """
```

#### Context Manager Support

```python { .api }
async def __aenter__(self):
    """Enter async context manager."""
    return self

async def __aexit__(self, exc_type=None, exc_value=None, traceback=None):
    """Exit async context manager and close client."""
    await self.aclose()
```

## Usage Examples

### Basic Async Client Usage

```python
import httpx
import asyncio

async def main():
    client = httpx.AsyncClient()
    try:
        response = await client.get('https://httpbin.org/get')
        print(response.json())
    finally:
        await client.aclose()

asyncio.run(main())
```

### Async Context Manager (Recommended)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://httpbin.org/get')
        print(response.json())
    # Client automatically closed

asyncio.run(main())
```

### Concurrent Requests

```python
import httpx
import asyncio

async def fetch_url(client, url):
    response = await client.get(url)
    return response.json()

async def main():
    urls = [
        'https://httpbin.org/delay/1',
        'https://httpbin.org/delay/2',
        'https://httpbin.org/delay/3'
    ]
    
    async with httpx.AsyncClient() as client:
        # Make concurrent requests
        tasks = [fetch_url(client, url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            print(result)

asyncio.run(main())
```

### Async Client with Configuration

```python
import httpx
import asyncio

async def main():
    timeout = httpx.Timeout(10.0, connect=5.0)
    limits = httpx.Limits(max_connections=50)
    
    async with httpx.AsyncClient(
        base_url='https://api.example.com',
        headers={'User-Agent': 'AsyncApp/1.0'},
        timeout=timeout,
        limits=limits
    ) as client:
        response = await client.get('/users')
        users = response.json()

asyncio.run(main())
```

### Async Streaming

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', 'https://example.com/large-file') as response:
            async for chunk in response.aiter_bytes(chunk_size=1024):
                # Process chunk asynchronously
                await process_chunk(chunk)

async def process_chunk(chunk):
    # Simulate async processing
    await asyncio.sleep(0.01)
    print(f"Processed {len(chunk)} bytes")

asyncio.run(main())
```

### FastAPI Integration

```python
import httpx
from fastapi import FastAPI

app = FastAPI()

# Create a shared client for the application
client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()

@app.get("/proxy/{path:path}")
async def proxy_request(path: str):
    response = await client.get(f"https://api.example.com/{path}")
    return response.json()
```

### Async Authentication

```python
import httpx
import asyncio

async def main():
    auth = httpx.BasicAuth('username', 'password')
    
    async with httpx.AsyncClient(auth=auth) as client:
        # All requests use authentication
        response = await client.get('https://example.com/protected')
        data = response.json()

asyncio.run(main())
```

### Error Handling

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get('https://httpbin.org/status/404')
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"Error response {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            print(f"Request error: {exc}")

asyncio.run(main())
```

### ASGI Application Testing

```python
import httpx
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "Hello World"}

async def test_app():
    # Test ASGI app directly without network calls
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/hello")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}

asyncio.run(test_app())
```