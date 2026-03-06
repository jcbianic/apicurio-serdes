# Request Functions API

Top-level convenience functions for making HTTP requests without explicitly managing a client instance. These functions are ideal for single requests or simple scripts.

## Overview

Each function creates a temporary client, makes the request, and automatically closes the connection. For multiple requests, consider using `httpx.Client` for better performance through connection reuse.

## Capabilities

### HTTP Method Functions

#### GET Request

```python { .api }
def get(url, *, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a GET request.
    
    Args:
        url (str): URL for the request
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        proxy (Proxy | str, optional): Proxy configuration
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
        HTTPStatusError: If response has 4xx/5xx status and raise_for_status() called
    """
```

#### POST Request

```python { .api }
def post(url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a POST request.
    
    Args:
        url (str): URL for the request
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        proxy (Proxy | str, optional): Proxy configuration
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### PUT Request

```python { .api }
def put(url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a PUT request.
    
    Args:
        url (str): URL for the request
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### PATCH Request

```python { .api }
def patch(url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a PATCH request.
    
    Args:
        url (str): URL for the request
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### DELETE Request

```python { .api }
def delete(url, *, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a DELETE request.
    
    Args:
        url (str): URL for the request
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### HEAD Request

```python { .api }
def head(url, *, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send a HEAD request.
    
    Args:
        url (str): URL for the request
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object (with empty body)
    
    Raises:
        RequestError: If the request fails
    """
```

#### OPTIONS Request

```python { .api }
def options(url, *, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send an OPTIONS request.
    
    Args:
        url (str): URL for the request
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

#### Generic REQUEST Function

```python { .api }
def request(method, url, *, content=None, data=None, files=None, json=None, params=None, headers=None, cookies=None, auth=None, proxy=None, follow_redirects=False, timeout=DEFAULT_TIMEOUT_CONFIG, verify=True, trust_env=True):
    """
    Send an HTTP request with specified method.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
        url (str): URL for the request
        content (bytes, optional): Raw bytes content for request body
        data (dict, optional): Form data to send in request body
        files (dict, optional): Files to upload
        json (any, optional): JSON-serializable object for request body
        params (dict, optional): Query parameters to append to URL
        headers (dict, optional): HTTP headers to send
        cookies (dict, optional): Cookies to send with request
        auth (Auth, optional): Authentication handler
        follow_redirects (bool): Whether to follow HTTP redirects (default: False)
        timeout (Timeout): Request timeout configuration (default: 5.0s)
        proxy (Proxy | str, optional): Proxy configuration
        verify (bool | str | SSLContext): SSL certificate verification (default: True)
        trust_env (bool): Use environment variables for proxy/SSL config (default: True)
    
    Returns:
        Response: HTTP response object
    
    Raises:
        RequestError: If the request fails
    """
```

### Streaming Function

```python { .api }
def stream(method, url, **kwargs):
    """
    Stream a request response instead of loading it into memory.
    
    Args:
        method (str): HTTP method
        url (str): URL for the request
        **kwargs: Same arguments as request() function
    
    Returns:
        Generator yielding Response: Context manager that yields response for streaming
    
    Usage:
        with httpx.stream('GET', 'https://example.com/large-file') as response:
            for chunk in response.iter_bytes():
                process(chunk)
    """
```

## Usage Examples

### Simple GET Request

```python
import httpx

response = httpx.get('https://httpbin.org/get')
print(response.status_code)  # 200
print(response.json())       # Response data as dict
```

### POST with JSON Data

```python
import httpx

data = {'name': 'John', 'age': 30}
response = httpx.post('https://httpbin.org/post', json=data)
print(response.json()['json'])  # Echo of sent data
```

### POST with Form Data

```python
import httpx

data = {'username': 'user', 'password': 'pass'}
response = httpx.post('https://example.com/login', data=data)
```

### File Upload

```python
import httpx

files = {'file': ('report.csv', open('report.csv', 'rb'), 'text/csv')}
response = httpx.post('https://example.com/upload', files=files)
```

### Custom Headers and Parameters

```python
import httpx

headers = {'User-Agent': 'My-App/1.0'}
params = {'page': 1, 'limit': 10}

response = httpx.get(
    'https://api.example.com/data',
    headers=headers,
    params=params
)
```

### Authentication

```python
import httpx

auth = httpx.BasicAuth('username', 'password')
response = httpx.get('https://example.com/protected', auth=auth)
```

### Timeout Configuration

```python
import httpx

# Simple timeout
response = httpx.get('https://example.com', timeout=10.0)

# Detailed timeout
timeout = httpx.Timeout(10.0, connect=5.0)
response = httpx.get('https://example.com', timeout=timeout)
```