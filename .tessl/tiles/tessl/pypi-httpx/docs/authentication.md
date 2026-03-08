# Authentication API

Authentication mechanisms for HTTP requests including Basic, Digest, custom authentication, and .netrc file support.

## Overview

httpx provides several built-in authentication classes and a base class for implementing custom authentication schemes. Authentication can be configured per request or as a default for a client.

## Capabilities

### Base Auth Class

```python { .api }
class Auth:
    """
    Base class for authentication schemes.
    
    Attributes:
        requires_request_body (bool): Whether auth needs request body
        requires_response_body (bool): Whether auth needs response body
    """
    
    def auth_flow(self, request):
        """
        Main authentication flow generator.
        
        Args:
            request (Request): Request to authenticate
        
        Yields:
            Request: Modified request with authentication
        
        Returns:
            Response: Final response after authentication
        """
    
    def sync_auth_flow(self, request):
        """
        Synchronous authentication flow generator.
        
        Args:
            request (Request): Request to authenticate
        
        Yields:
            Request: Modified request with authentication
        
        Returns:
            Response: Final response after authentication
        """
    
    async def async_auth_flow(self, request):
        """
        Asynchronous authentication flow generator.
        
        Args:
            request (Request): Request to authenticate
        
        Yields:
            Request: Modified request with authentication
        
        Returns:
            Response: Final response after authentication
        """
```

### Basic Authentication

```python { .api }
class BasicAuth(Auth):
    """
    HTTP Basic authentication scheme.
    
    Encodes credentials as base64 and adds Authorization header.
    """
    
    def __init__(self, username, password):
        """
        Initialize Basic authentication.
        
        Args:
            username (str | bytes): Username for authentication
            password (str | bytes): Password for authentication
        """
```

### Digest Authentication

```python { .api }
class DigestAuth(Auth):
    """
    HTTP Digest authentication scheme.
    
    Implements RFC 7616 HTTP Digest Access Authentication.
    Supports MD5, SHA-256, SHA-512 algorithms and session variants.
    """
    
    def __init__(self, username, password):
        """
        Initialize Digest authentication.
        
        Args:
            username (str | bytes): Username for authentication
            password (str | bytes): Password for authentication
        
        Supported algorithms:
            - MD5, MD5-SESS
            - SHA, SHA-SESS  
            - SHA-256, SHA-256-SESS
            - SHA-512, SHA-512-SESS
        """
```

### NetRC Authentication

```python { .api }
class NetRCAuth(Auth):
    """
    Authentication using .netrc file credentials.
    
    Reads credentials from .netrc file based on hostname.
    Falls back to Basic authentication if credentials found.
    """
    
    def __init__(self, file=None):
        """
        Initialize .netrc authentication.
        
        Args:
            file (str, optional): Path to .netrc file (default: ~/.netrc)
        """
```

## Usage Examples

### Basic Authentication

```python
import httpx

# With top-level functions
auth = httpx.BasicAuth('username', 'password')
response = httpx.get('https://httpbin.org/basic-auth/username/password', auth=auth)

# With client
with httpx.Client(auth=auth) as client:
    response = client.get('https://example.com/protected')
    print(response.status_code)
```

### Digest Authentication

```python
import httpx

# Digest auth automatically handles the challenge-response flow
auth = httpx.DigestAuth('username', 'password')
response = httpx.get('https://httpbin.org/digest-auth/auth/username/password', auth=auth)

print(response.status_code)  # 200 after successful authentication
```

### NetRC Authentication

```python
import httpx

# Uses credentials from ~/.netrc file
# Format: machine example.com login username password secret
auth = httpx.NetRCAuth()
response = httpx.get('https://example.com/protected', auth=auth)

# Custom .netrc file location
auth = httpx.NetRCAuth(file='/path/to/custom/.netrc')
response = httpx.get('https://example.com/protected', auth=auth)
```

### Client with Default Authentication

```python
import httpx

# All requests from this client will use authentication
auth = httpx.BasicAuth('api_key', '')
with httpx.Client(auth=auth, base_url='https://api.example.com') as client:
    users = client.get('/users').json()
    user = client.get('/users/123').json()
    
    # Override auth for specific request
    public_data = client.get('/public', auth=None).json()
```

### Async Authentication

```python
import httpx
import asyncio

async def main():
    auth = httpx.BasicAuth('username', 'password')
    
    async with httpx.AsyncClient(auth=auth) as client:
        response = await client.get('https://example.com/protected')
        print(response.json())

asyncio.run(main())
```

### Custom Authentication

```python
import httpx

class BearerAuth(httpx.Auth):
    """Custom Bearer token authentication."""
    
    def __init__(self, token):
        self.token = token
    
    def auth_flow(self, request):
        # Add Authorization header
        request.headers['Authorization'] = f'Bearer {self.token}'
        yield request

# Usage
auth = BearerAuth('your-token-here')
response = httpx.get('https://api.example.com/data', auth=auth)
```

### API Key Authentication

```python
import httpx

class APIKeyAuth(httpx.Auth):
    """Custom API key authentication via header."""
    
    def __init__(self, api_key, header_name='X-API-Key'):
        self.api_key = api_key
        self.header_name = header_name
    
    def auth_flow(self, request):
        request.headers[self.header_name] = self.api_key
        yield request

# Usage
auth = APIKeyAuth('your-api-key', 'X-API-Key')
with httpx.Client(auth=auth) as client:
    response = client.get('https://api.example.com/data')
```

### OAuth 2.0 Bearer Token

```python
import httpx

class OAuth2Auth(httpx.Auth):
    """OAuth 2.0 Bearer token authentication."""
    
    def __init__(self, access_token):
        self.access_token = access_token
    
    def auth_flow(self, request):
        request.headers['Authorization'] = f'Bearer {self.access_token}'
        yield request

# Usage
auth = OAuth2Auth('your-access-token')
response = httpx.get('https://api.example.com/user', auth=auth)
```

### Authentication with Retry Logic

```python
import httpx
import time

class TokenAuth(httpx.Auth):
    """Token authentication with automatic refresh."""
    
    def __init__(self, get_token_func):
        self.get_token_func = get_token_func
        self.token = None
        self.token_expires = 0
    
    def auth_flow(self, request):
        # Refresh token if expired
        if time.time() >= self.token_expires:
            self.token, expires_in = self.get_token_func()
            self.token_expires = time.time() + expires_in - 60  # Refresh 60s early
        
        request.headers['Authorization'] = f'Bearer {self.token}'
        response = yield request
        
        # If unauthorized, try refreshing token once
        if response.status_code == 401:
            self.token, expires_in = self.get_token_func()
            self.token_expires = time.time() + expires_in - 60
            request.headers['Authorization'] = f'Bearer {self.token}'
            yield request

def get_access_token():
    """Function to obtain access token."""
    # Implement token acquisition logic
    return 'new-token', 3600  # token, expires_in_seconds

auth = TokenAuth(get_access_token)
with httpx.Client(auth=auth) as client:
    response = client.get('https://api.example.com/data')
```

### Multiple Authentication Schemes

```python
import httpx

# Different authentication for different endpoints
basic_auth = httpx.BasicAuth('user', 'pass')
digest_auth = httpx.DigestAuth('user', 'pass')

with httpx.Client() as client:
    # Basic auth for one endpoint
    response1 = client.get('https://example.com/basic', auth=basic_auth)
    
    # Digest auth for another endpoint
    response2 = client.get('https://example.com/digest', auth=digest_auth)
    
    # No auth for public endpoint
    response3 = client.get('https://example.com/public')
```

### Error Handling

```python
import httpx

auth = httpx.BasicAuth('wrong-user', 'wrong-pass')

try:
    response = httpx.get('https://httpbin.org/basic-auth/user/pass', auth=auth)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 401:
        print("Authentication failed")
    else:
        print(f"HTTP error: {exc.response.status_code}")
except httpx.RequestError as exc:
    print(f"Request error: {exc}")
```