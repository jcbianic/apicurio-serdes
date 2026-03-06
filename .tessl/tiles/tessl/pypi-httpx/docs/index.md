# httpx

A fully featured HTTP client library for Python 3 with both synchronous and asynchronous APIs, HTTP/2 support, and modern capabilities.

## Package Information

- **Package Name**: httpx
- **Language**: Python
- **Installation**: `pip install httpx`

## Core Imports

```python
import httpx

# For direct access to key classes
from httpx import Client, AsyncClient, Response, Request

# For authentication
from httpx import BasicAuth, DigestAuth

# For configuration  
from httpx import Timeout, Limits, Proxy

# For data structures
from httpx import Headers, Cookies, URL, QueryParams

# For exceptions
from httpx import HTTPError, HTTPStatusError, RequestError

# Constants
from httpx import USE_CLIENT_DEFAULT
```

## Basic Usage

```python
import httpx

# Simple GET request
response = httpx.get('https://httpbin.org/get')
print(response.status_code)
print(response.json())

# POST with data
response = httpx.post('https://httpbin.org/post', json={'key': 'value'})

# Using a client for multiple requests
with httpx.Client() as client:
    response = client.get('https://httpbin.org/get')
    print(response.text)
```

## Architecture

httpx provides two main approaches for making HTTP requests:

1. **Top-level functions** - Convenient for single requests (`httpx.get()`, `httpx.post()`, etc.)
2. **Client classes** - Efficient for multiple requests with connection pooling (`httpx.Client`, `httpx.AsyncClient`)

The library supports both synchronous and asynchronous programming patterns with equivalent APIs.

## Capabilities

### Request Functions

Top-level convenience functions for making HTTP requests without managing a client instance.

```python { .api }
def get(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send a GET request."""

def post(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send a POST request."""

def put(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send a PUT request."""

def patch(
    url: URL | str,
    *,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send a PATCH request."""

def delete(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> Response:
    """Send a DELETE request."""

def head(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send a HEAD request."""

def options(
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> Response:
    """Send an OPTIONS request."""

def request(
    method: str,
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> Response:
    """Send an HTTP request with specified method."""
```

[Request Functions API](./requests-api.md)

### Synchronous HTTP Client

The `Client` class provides a synchronous HTTP client with connection pooling, cookie persistence, and configuration reuse across multiple requests.

```python { .api }
class Client:
    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        proxy: ProxyTypes | None = None,
        mounts: None | Mapping[str, BaseTransport | None] = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: None | Mapping[str, list[EventHook]] = None,
        base_url: URL | str = "",
        transport: BaseTransport | None = None,
        default_encoding: str | Callable[[bytes], str] = "utf-8",
    ) -> None:
        """Initialize a synchronous HTTP client."""
    
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
        """Send a GET request."""
    
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
        """Send a POST request."""
    
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
        """Send an HTTP request."""
    
    def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        auth: AuthTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
    ) -> Response:
        """Send a pre-built Request object."""
    
    def close(self) -> None:
        """Close the client and release connections."""
```

[Synchronous Client API](./sync-client.md)

### Asynchronous HTTP Client  

The `AsyncClient` class provides an asynchronous HTTP client with the same features as the synchronous client but using async/await syntax.

```python { .api }
class AsyncClient:
    def __init__(
        self,
        *,
        auth: AuthTypes | None = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        proxy: ProxyTypes | None = None,
        mounts: None | Mapping[str, AsyncBaseTransport | None] = None,
        timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
        event_hooks: None | Mapping[str, list[EventHook]] = None,
        base_url: URL | str = "",
        transport: AsyncBaseTransport | None = None,
        default_encoding: str | Callable[[bytes], str] = "utf-8",
    ) -> None:
        """Initialize an asynchronous HTTP client."""
    
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
        """Send a GET request."""
    
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
        """Send a POST request."""
    
    async def request(
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
        """Send an HTTP request."""
    
    async def aclose(self) -> None:
        """Close the client and release connections."""
```

[Asynchronous Client API](./async-client.md)

### Response and Request Objects

Core data model classes for representing HTTP requests and responses.

```python { .api }
class Response:
    status_code: int
    headers: Headers
    content: bytes
    text: str
    url: URL
    request: Request
    
    def json(self, **kwargs: Any) -> Any:
        """Parse response content as JSON."""
    
    def raise_for_status(self) -> None:
        """Raise HTTPStatusError for 4xx/5xx status codes."""

class Request:
    method: str
    url: URL
    headers: Headers
    content: bytes
    
    def read(self):
        """Read the request content."""

class Headers:
    """Case-insensitive HTTP headers."""
    
    def get(self, key, default=None):
        """Get header value."""
```

[Core Types API](./types.md)

### Authentication

Authentication mechanisms for HTTP requests including Basic, Digest, and custom authentication.

```python { .api }
class BasicAuth:
    def __init__(self, username, password):
        """HTTP Basic authentication."""

class DigestAuth:
    def __init__(self, username, password):
        """HTTP Digest authentication."""

class Auth:
    """Base class for custom authentication."""
    
    def auth_flow(self, request):
        """Authentication flow generator."""
```

[Authentication API](./authentication.md)

### Configuration

Timeout, connection limits, proxy, and SSL configuration options.

```python { .api }
class Timeout:
    def __init__(self, timeout=5.0, *, connect=None, read=None, write=None, pool=None):
        """Configure request timeouts."""

class Limits:
    def __init__(self, *, max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0):
        """Configure connection pool limits."""

class Proxy:
    def __init__(self, url, *, auth=None, headers=None):
        """Configure HTTP/HTTPS/SOCKS proxy."""
```

[Configuration API](./configuration.md)

### Exception Handling

Comprehensive exception hierarchy for handling different types of HTTP errors and request failures.

```python { .api }
class HTTPError(Exception):
    """Base class for all HTTP-related exceptions."""
    
    @property
    def request(self) -> Request:
        """The request that caused this exception."""

class RequestError(HTTPError):
    """Exception occurred during request processing."""

class HTTPStatusError(HTTPError):
    """Response returned an HTTP error status code (4xx or 5xx)."""
    
    @property
    def response(self) -> Response:
        """The response that caused this exception."""

# Transport layer exceptions
class TransportError(RequestError):
    """Exception occurred at the transport layer."""

class TimeoutException(TransportError):
    """Request timed out."""

class ConnectTimeout(TimeoutException):
    """Connection timed out."""

class ReadTimeout(TimeoutException):
    """Reading response timed out."""

class WriteTimeout(TimeoutException):
    """Writing request timed out."""

class PoolTimeout(TimeoutException):
    """Connection pool timeout."""

class NetworkError(TransportError):
    """Network-related error."""

class ConnectError(NetworkError):
    """Failed to establish connection."""

class ReadError(NetworkError):
    """Error reading response."""

class WriteError(NetworkError):
    """Error writing request."""

class CloseError(NetworkError):
    """Error closing connection."""

class ProtocolError(TransportError):
    """HTTP protocol error."""

class LocalProtocolError(ProtocolError):
    """Local protocol error."""

class RemoteProtocolError(ProtocolError):
    """Remote protocol error."""

class ProxyError(TransportError):
    """Proxy-related error."""

class UnsupportedProtocol(TransportError):
    """Unsupported protocol."""

class DecodingError(RequestError):
    """Response content decoding error."""

class TooManyRedirects(RequestError):
    """Too many redirect responses."""

# URL and data validation exceptions
class InvalidURL(Exception):
    """Invalid URL format."""

class CookieConflict(Exception):
    """Cookie conflict error."""

# Streaming exceptions
class StreamError(Exception):
    """Stream-related error."""

class StreamConsumed(StreamError):
    """Stream content already consumed."""

class StreamClosed(StreamError):
    """Stream is closed."""

class ResponseNotRead(StreamError):
    """Response content not read."""

class RequestNotRead(StreamError):
    """Request content not read."""
```

### Streaming

Stream request and response content to handle large files efficiently.

```python { .api }
def stream(
    method: str,
    url: URL | str,
    *,
    params: QueryParamTypes | None = None,
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    headers: HeaderTypes | None = None,
    cookies: CookieTypes | None = None,
    auth: AuthTypes | None = None,
    proxy: ProxyTypes | None = None,
    timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
    follow_redirects: bool = False,
    verify: ssl.SSLContext | str | bool = True,
    trust_env: bool = True,
) -> Iterator[Response]:
    """Stream a request response."""

class Response:
    def iter_bytes(self, chunk_size: int = 1024) -> Iterator[bytes]:
        """Iterate over response content as bytes."""
    
    def iter_text(self, chunk_size: int = 1024) -> Iterator[str]:
        """Iterate over response content as text."""
```

[Streaming API](./streaming.md)