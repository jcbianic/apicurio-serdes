# Core Types API

Core data model classes for representing HTTP requests, responses, headers, and other fundamental httpx objects.

## Overview

These classes represent the fundamental data structures used throughout httpx. They provide rich APIs for inspecting and manipulating HTTP messages.

## Capabilities

### Response Class

```python { .api }
class Response:
    """
    HTTP response object containing status, headers, and content.
    
    Attributes:
        status_code (int): HTTP status code (e.g., 200, 404)
        headers (Headers): Response headers
        content (bytes): Raw response body content
        text (str): Response body as decoded text
        url (URL): Final URL after any redirects
        request (Request): Associated request object
        history (list[Response]): List of redirect responses
        cookies (Cookies): Response cookies
        is_closed (bool): Whether response has been closed
        is_stream_consumed (bool): Whether streaming content has been consumed
        http_version (str): HTTP version used ("HTTP/1.1" or "HTTP/2")
        reason_phrase (str): HTTP reason phrase
        elapsed (timedelta): Request/response duration
        encoding (str): Character encoding for text content
    """
    
    def json(self, **kwargs):
        """
        Parse response content as JSON.
        
        Args:
            **kwargs: Arguments passed to json.loads()
        
        Returns:
            any: Parsed JSON content
        
        Raises:
            JSONDecodeError: If content is not valid JSON
        """
    
    def raise_for_status(self):
        """
        Raise HTTPStatusError for 4xx/5xx status codes.
        
        Raises:
            HTTPStatusError: If status_code is 400 or higher
        
        Returns:
            Response: Self (for method chaining)
        """
    
    def read(self):
        """
        Read and return the response content as bytes.
        
        Returns:
            bytes: Response content
        """
    
    async def aread(self):
        """
        Read and return the response content as bytes (async).
        
        Returns:
            bytes: Response content
        """
    
    def iter_bytes(self, chunk_size=1024):
        """
        Iterate over response content as bytes chunks.
        
        Args:
            chunk_size (int): Size of each chunk (default: 1024)
        
        Yields:
            bytes: Chunks of response content
        """
    
    async def aiter_bytes(self, chunk_size=1024):
        """
        Iterate over response content as bytes chunks (async).
        
        Args:
            chunk_size (int): Size of each chunk (default: 1024)
        
        Yields:
            bytes: Chunks of response content
        """
    
    def iter_text(self, chunk_size=1024):
        """
        Iterate over response content as text chunks.
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            str: Text chunks of response content
        """
    
    async def aiter_text(self, chunk_size=1024):
        """
        Iterate over response content as text chunks (async).
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            str: Text chunks of response content
        """
    
    def iter_lines(self):
        """
        Iterate over response content as text lines.
        
        Yields:
            str: Lines of response content
        """
    
    async def aiter_lines(self):
        """
        Iterate over response content as text lines (async).
        
        Yields:
            str: Lines of response content
        """
    
    def iter_raw(self, chunk_size=1024):
        """
        Iterate over raw response content without decoding.
        
        Args:
            chunk_size (int): Size of each chunk (default: 1024)
        
        Yields:
            bytes: Raw chunks of response content
        """
    
    async def aiter_raw(self, chunk_size=1024):
        """
        Iterate over raw response content without decoding (async).
        
        Args:
            chunk_size (int): Size of each chunk (default: 1024)
        
        Yields:
            bytes: Raw chunks of response content
        """
    
    def close(self):
        """Close the response and release connection."""
    
    async def aclose(self):
        """Close the response and release connection (async)."""
    
    # Status code properties
    @property
    def is_informational(self):
        """True for 1xx status codes."""
        return 100 <= self.status_code < 200
    
    @property
    def is_success(self):
        """True for 2xx status codes."""
        return 200 <= self.status_code < 300
    
    @property
    def is_redirect(self):
        """True for 3xx status codes."""
        return 300 <= self.status_code < 400
    
    @property
    def is_client_error(self):
        """True for 4xx status codes."""
        return 400 <= self.status_code < 500
    
    @property
    def is_server_error(self):
        """True for 5xx status codes."""
        return 500 <= self.status_code < 600
    
    @property
    def is_error(self):
        """True for 4xx and 5xx status codes."""
        return 400 <= self.status_code < 600
```

### Request Class

```python { .api }
class Request:
    """
    HTTP request object containing method, URL, headers, and content.
    
    Attributes:
        method (str): HTTP method (GET, POST, etc.)
        url (URL): Request URL
        headers (Headers): Request headers
        content (bytes): Request body content (after reading)
        extensions (dict): Request extensions/metadata
    """
    
    def read(self):
        """
        Read and return the request content as bytes.
        
        Returns:
            bytes: Request content
        """
    
    async def aread(self):
        """
        Read and return the request content as bytes (async).
        
        Returns:
            bytes: Request content
        """
```

### Headers Class

```python { .api }
class Headers:
    """
    Case-insensitive HTTP headers collection.
    
    Implements MutableMapping[str, str] interface.
    
    Attributes:
        encoding (str): Header encoding (ascii, utf-8, or iso-8859-1)
        raw (list[tuple[bytes, bytes]]): Raw header items as bytes
    """
    
    def __init__(self, headers=None, encoding=None):
        """
        Initialize headers collection.
        
        Args:
            headers (dict | list | Headers, optional): Initial headers
            encoding (str, optional): Header encoding
        """
    
    def get(self, key, default=None):
        """
        Get header value with default.
        
        Args:
            key (str): Header name (case-insensitive)
            default (str, optional): Default value if header not found
        
        Returns:
            str: Header value or default
        """
    
    def get_list(self, key, split_commas=False):
        """
        Get all values for a header as a list.
        
        Args:
            key (str): Header name (case-insensitive)
            split_commas (bool): Whether to split comma-separated values
        
        Returns:
            list[str]: List of header values
        """
    
    def update(self, headers):
        """
        Update headers with new values.
        
        Args:
            headers (dict | list | Headers): Headers to add/update
        """
    
    def copy(self):
        """
        Create a copy of the headers.
        
        Returns:
            Headers: New headers instance
        """
    
    def keys(self):
        """Return header names."""
    
    def values(self):
        """Return header values."""
    
    def items(self):
        """Return header name-value pairs."""
    
    def multi_items(self):
        """
        Return all header pairs including duplicates.
        
        Returns:
            list[tuple[str, str]]: All header name-value pairs
        """
```

### Cookies Class

```python { .api }
class Cookies:
    """
    HTTP cookies as mutable mapping.
    
    Implements MutableMapping[str, str] interface.
    
    Attributes:
        jar (CookieJar): Underlying cookie jar
    """
    
    def __init__(self, cookies=None):
        """
        Initialize cookies collection.
        
        Args:
            cookies (dict | list | Cookies, optional): Initial cookies
        """
    
    def set(self, name, value, domain="", path="/"):
        """
        Set a cookie.
        
        Args:
            name (str): Cookie name
            value (str): Cookie value
            domain (str): Cookie domain (default: "")
            path (str): Cookie path (default: "/")
        """
    
    def get(self, name, default=None, domain=None, path=None):
        """
        Get cookie value.
        
        Args:
            name (str): Cookie name
            default (str, optional): Default value if cookie not found
            domain (str, optional): Cookie domain
            path (str, optional): Cookie path
        
        Returns:
            str: Cookie value or default
        """
    
    def delete(self, name, domain=None, path=None):
        """
        Delete a cookie.
        
        Args:
            name (str): Cookie name
            domain (str, optional): Cookie domain
            path (str, optional): Cookie path
        """
    
    def clear(self, domain=None, path=None):
        """
        Clear cookies.
        
        Args:
            domain (str, optional): Only clear cookies for this domain
            path (str, optional): Only clear cookies for this path
        """
    
    def update(self, cookies):
        """
        Update cookies with new values.
        
        Args:
            cookies (dict | Cookies): Cookies to add/update
        """
    
    def extract_cookies(self, response):
        """
        Extract cookies from response Set-Cookie headers.
        
        Args:
            response (Response): Response to extract cookies from
        """
    
    def set_cookie_header(self, request):
        """
        Set Cookie header on request.
        
        Args:
            request (Request): Request to set Cookie header on
        """
```

### URL Class

```python { .api }
class URL:
    """
    URL parsing and manipulation.
    
    Attributes:
        scheme (str): URL scheme (normalized lowercase)
        userinfo (bytes): Raw userinfo as bytes
        username (str): URL-decoded username
        password (str): URL-decoded password
        host (str): Host (normalized, IDNA decoded)
        port (int | None): Port number (None for default ports)
        path (str): URL-decoded path
        query (bytes): Raw query string as bytes
        params (QueryParams): Parsed query parameters
        fragment (str): URL fragment (without #)
        is_absolute_url (bool): True if absolute URL
        is_relative_url (bool): True if relative URL
    """
    
    def __init__(self, url=""):
        """
        Initialize URL.
        
        Args:
            url (str): URL string to parse
        """
    
    def copy_with(self, **kwargs):
        """
        Create modified copy of URL.
        
        Args:
            **kwargs: URL components to modify (scheme, host, port, path, etc.)
        
        Returns:
            URL: New URL instance with modifications
        """
    
    def copy_set_param(self, key, value):
        """
        Create copy with query parameter set.
        
        Args:
            key (str): Parameter name
            value (str): Parameter value
        
        Returns:
            URL: New URL with parameter set
        """
    
    def copy_add_param(self, key, value):
        """
        Create copy with query parameter added.
        
        Args:
            key (str): Parameter name
            value (str): Parameter value
        
        Returns:
            URL: New URL with parameter added
        """
    
    def copy_remove_param(self, key):
        """
        Create copy with query parameter removed.
        
        Args:
            key (str): Parameter name to remove
        
        Returns:
            URL: New URL with parameter removed
        """
    
    def copy_merge_params(self, params):
        """
        Create copy with query parameters merged.
        
        Args:
            params (dict | QueryParams): Parameters to merge
        
        Returns:
            URL: New URL with parameters merged
        """
    
    def join(self, url):
        """
        Join with relative URL.
        
        Args:
            url (str | URL): Relative URL to join
        
        Returns:
            URL: Joined URL
        """
```

### QueryParams Class

```python { .api }
class QueryParams:
    """
    URL query parameters as immutable multi-dict.
    
    Implements Mapping[str, str] interface.
    """
    
    def __init__(self, params=None):
        """
        Initialize query parameters.
        
        Args:
            params (str | dict | list | QueryParams, optional): Initial parameters
        """
    
    def get(self, key, default=None):
        """
        Get first value for parameter.
        
        Args:
            key (str): Parameter name
            default (str, optional): Default if parameter not found
        
        Returns:
            str: Parameter value or default
        """
    
    def get_list(self, key):
        """
        Get all values for parameter.
        
        Args:
            key (str): Parameter name
        
        Returns:
            list[str]: All values for parameter
        """
    
    def set(self, key, value):
        """
        Return new instance with parameter set.
        
        Args:
            key (str): Parameter name
            value (str): Parameter value
        
        Returns:
            QueryParams: New instance with parameter set
        """
    
    def add(self, key, value):
        """
        Return new instance with parameter added.
        
        Args:
            key (str): Parameter name
            value (str): Parameter value
        
        Returns:
            QueryParams: New instance with parameter added
        """
    
    def remove(self, key):
        """
        Return new instance with parameter removed.
        
        Args:
            key (str): Parameter name to remove
        
        Returns:
            QueryParams: New instance with parameter removed
        """
    
    def merge(self, params):
        """
        Return merged instance.
        
        Args:
            params (dict | QueryParams): Parameters to merge
        
        Returns:
            QueryParams: New merged instance
        """
    
    def keys(self):
        """Return parameter names."""
    
    def values(self):
        """Return parameter values."""
    
    def items(self):
        """Return parameter name-value pairs."""
    
    def multi_items(self):
        """
        Return all parameter pairs including duplicates.
        
        Returns:
            list[tuple[str, str]]: All parameter name-value pairs
        """
```

## Usage Examples

### Working with Response

```python
import httpx

response = httpx.get('https://httpbin.org/json')

# Status and headers
print(response.status_code)  # 200
print(response.headers['content-type'])  # 'application/json'

# Content access
print(response.text)         # Response as text
print(response.content)      # Response as bytes
print(response.json())       # Parse JSON

# Status checks
if response.is_success:
    print("Request succeeded")

# Raise exception for error status
response.raise_for_status()
```

### Headers Manipulation

```python
import httpx

headers = httpx.Headers({
    'User-Agent': 'MyApp/1.0',
    'Accept': 'application/json'
})

# Case-insensitive access
print(headers['user-agent'])  # 'MyApp/1.0'
print(headers.get('accept'))  # 'application/json'

# Multiple values
headers.update({'Accept': 'text/html'})
all_accepts = headers.get_list('accept')
```

### URL Construction

```python
import httpx

url = httpx.URL('https://example.com/path')
print(url.host)   # 'example.com'
print(url.path)   # '/path'

# URL manipulation
new_url = url.copy_with(path='/new-path')
with_params = url.copy_set_param('page', '1')

# Join URLs
base = httpx.URL('https://api.example.com/')
endpoint = base.join('users/123')
```

### Query Parameters

```python
import httpx

params = httpx.QueryParams({'page': '1', 'limit': '10'})
print(params.get('page'))  # '1'

# Immutable operations
new_params = params.set('page', '2')
more_params = params.add('filter', 'active')
```

### Response Streaming

```python
import httpx

with httpx.stream('GET', 'https://example.com/large-file') as response:
    for chunk in response.iter_bytes():
        process_chunk(chunk)
    
    # Or iterate text
    for line in response.iter_lines():
        process_line(line)
```

## Type Aliases

These type aliases define the parameter types accepted by httpx functions and classes.

```python { .api }
# URL types
URL = URL  # URL class
URLTypes = Union[URL, str]

# Query parameter types  
QueryParamTypes = Union[
    QueryParams,
    Mapping[str, Union[str, int, float, bool, None, Sequence[Union[str, int, float, bool, None]]]],
    List[Tuple[str, Union[str, int, float, bool, None]]],
    Tuple[Tuple[str, Union[str, int, float, bool, None]], ...],
    str,
    bytes,
]

# Header types
HeaderTypes = Union[
    Headers,
    Mapping[str, str],
    Mapping[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]

# Cookie types
CookieTypes = Union[Cookies, CookieJar, Dict[str, str], List[Tuple[str, str]]]

# Timeout types
TimeoutTypes = Union[
    Optional[float],
    Tuple[Optional[float], Optional[float], Optional[float], Optional[float]],
    Timeout,
]

# Proxy types
ProxyTypes = Union[URL, str, Proxy]

# SSL certificate types
CertTypes = Union[str, Tuple[str, str], Tuple[str, str, str]]

# Authentication types
AuthTypes = Union[
    Tuple[Union[str, bytes], Union[str, bytes]],
    Callable[[Request], Request],
    Auth,
]

# Request content types
RequestContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]
ResponseContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]

# Request data types  
RequestData = Mapping[str, Any]

# File upload types
FileContent = Union[IO[bytes], bytes, str]
FileTypes = Union[
    FileContent,
    Tuple[Optional[str], FileContent],
    Tuple[Optional[str], FileContent, Optional[str]],
    Tuple[Optional[str], FileContent, Optional[str], Mapping[str, str]],
]
RequestFiles = Union[Mapping[str, FileTypes], Sequence[Tuple[str, FileTypes]]]

# Request extension types
RequestExtensions = Mapping[str, Any]
ResponseExtensions = Mapping[str, Any]

# Event hook types
EventHook = Callable[..., Any]

# Stream types
SyncByteStream = Iterator[bytes]
AsyncByteStream = AsyncIterator[bytes]
```

## Constants

```python { .api }
# Default timeout configuration
DEFAULT_TIMEOUT_CONFIG: Timeout

# Default connection limits
DEFAULT_LIMITS: Limits  

# Default maximum redirects
DEFAULT_MAX_REDIRECTS: int

# Client default sentinel value
USE_CLIENT_DEFAULT: UseClientDefault

class UseClientDefault:
    """Sentinel value indicating client default should be used."""
```