# Streaming API

Stream request and response content to handle large files efficiently without loading everything into memory.

## Overview

httpx provides comprehensive streaming capabilities for both requests and responses. This is essential for handling large files, real-time data, or when memory usage is a concern.

## Capabilities

### Response Streaming

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
    """
    Stream a request response without loading content into memory.
    
    Args:
        method (str): HTTP method
        url (URL | str): URL for the request
        params (QueryParamTypes, optional): Query parameters
        content (RequestContent, optional): Raw bytes content
        data (RequestData, optional): Form data
        files (RequestFiles, optional): Files to upload
        json (Any, optional): JSON-serializable object
        headers (HeaderTypes, optional): HTTP headers
        cookies (CookieTypes, optional): Cookies
        auth (AuthTypes, optional): Authentication
        proxy (ProxyTypes, optional): Proxy URL
        timeout (TimeoutTypes): Timeout configuration
        follow_redirects (bool): Whether to follow redirects
        verify (ssl.SSLContext | str | bool): SSL verification
        trust_env (bool): Use environment variables
    
    Returns:
        Iterator[Response]: Context manager yielding streaming response
    
    Usage:
        with httpx.stream('GET', url) as response:
            for chunk in response.iter_bytes():
                process_chunk(chunk)
    """
```

### Response Streaming Methods

```python { .api }
class Response:
    def iter_bytes(self, chunk_size: int = 1024) -> Iterator[bytes]:
        """
        Iterate over response content as bytes chunks.
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            bytes: Chunks of response content
        
        Note:
            Content is decoded (decompressed) if Content-Encoding is present.
        """
    
    async def aiter_bytes(self, chunk_size: int = 1024) -> AsyncIterator[bytes]:
        """
        Iterate over response content as bytes chunks (async).
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            bytes: Chunks of response content
        """
    
    def iter_text(self, chunk_size: int = 1024) -> Iterator[str]:
        """
        Iterate over response content as text chunks.
        
        Args:
            chunk_size (int): Size of each chunk in bytes before decoding (default: 1024)
        
        Yields:
            str: Text chunks of response content
        
        Note:
            Content is decoded using the response's character encoding.
        """
    
    async def aiter_text(self, chunk_size: int = 1024) -> AsyncIterator[str]:
        """
        Iterate over response content as text chunks (async).
        
        Args:
            chunk_size (int): Size of each chunk in bytes before decoding (default: 1024)
        
        Yields:
            str: Text chunks of response content
        """
    
    def iter_lines(self) -> Iterator[str]:
        """
        Iterate over response content as text lines.
        
        Yields:
            str: Lines of response content (without line endings)
        
        Note:
            Handles different line ending styles (\\n, \\r\\n, \\r).
        """
    
    async def aiter_lines(self) -> AsyncIterator[str]:
        """
        Iterate over response content as text lines (async).
        
        Yields:
            str: Lines of response content (without line endings)
        """
    
    def iter_raw(self, chunk_size=1024):
        """
        Iterate over raw response content without any decoding.
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            bytes: Raw chunks exactly as received from server
        
        Note:
            No decompression or decoding is performed.
        """
    
    async def aiter_raw(self, chunk_size=1024):
        """
        Iterate over raw response content without any decoding (async).
        
        Args:
            chunk_size (int): Size of each chunk in bytes (default: 1024)
        
        Yields:
            bytes: Raw chunks exactly as received from server
        """
```

### Client Streaming Methods

```python { .api }
class Client:
    def stream(self, method, url, **kwargs):
        """
        Stream a request response using the client.
        
        Args:
            method (str): HTTP method
            url (str): URL for the request
            **kwargs: Same arguments as client.request()
        
        Returns:
            Generator[Response]: Context manager yielding streaming response
        """

class AsyncClient:
    def stream(self, method, url, **kwargs):
        """
        Stream a request response using the async client.
        
        Args:
            method (str): HTTP method
            url (str): URL for the request
            **kwargs: Same arguments as client.request()
        
        Returns:
            AsyncGenerator[Response]: Async context manager yielding streaming response
        """
```

## Usage Examples

### Basic Response Streaming

```python
import httpx

# Stream large file download
with httpx.stream('GET', 'https://example.com/large-file.zip') as response:
    with open('large-file.zip', 'wb') as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
```

### Streaming with Client

```python
import httpx

with httpx.Client() as client:
    with client.stream('GET', 'https://example.com/large-file.zip') as response:
        print(f"Content-Length: {response.headers.get('content-length')}")
        
        total_size = 0
        with open('large-file.zip', 'wb') as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                total_size += len(chunk)
                print(f"Downloaded: {total_size} bytes")
```

### Text Streaming

```python
import httpx

# Stream text content line by line
with httpx.stream('GET', 'https://example.com/large-text-file.txt') as response:
    for line in response.iter_lines():
        process_line(line)

def process_line(line):
    # Process each line without loading entire file
    print(f"Line: {line}")
```

### JSON Streaming

```python
import httpx
import json

# Stream and parse JSON objects line by line (JSONL format)
with httpx.stream('GET', 'https://api.example.com/data.jsonl') as response:
    for line in response.iter_lines():
        if line.strip():  # Skip empty lines
            data = json.loads(line)
            process_json_object(data)

def process_json_object(obj):
    print(f"Processing: {obj}")
```

### Async Response Streaming

```python
import httpx
import asyncio

async def download_file():
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', 'https://example.com/large-file.zip') as response:
            with open('large-file.zip', 'wb') as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)

asyncio.run(download_file())
```

### Streaming with Progress

```python
import httpx

def download_with_progress(url, filename):
    with httpx.stream('GET', url) as response:
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)")

download_with_progress('https://example.com/file.zip', 'file.zip')
```

### Raw Content Streaming

```python
import httpx

# Stream raw content without decompression
with httpx.stream('GET', 'https://example.com/compressed-data.gz') as response:
    with open('compressed-data.gz', 'wb') as f:
        # iter_raw() preserves original compression
        for chunk in response.iter_raw():
            f.write(chunk)
```

### Conditional Streaming

```python
import httpx

def smart_download(url, filename):
    with httpx.stream('GET', url) as response:
        content_length = response.headers.get('content-length')
        
        if content_length and int(content_length) > 10_000_000:  # 10MB
            # Stream large files
            print("Large file detected, streaming...")
            with open(filename, 'wb') as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        else:
            # Load small files normally
            print("Small file, loading into memory...")
            content = response.read()
            with open(filename, 'wb') as f:
                f.write(content)

smart_download('https://example.com/unknown-size-file', 'file.dat')
```

### Streaming API Responses

```python
import httpx
import json

def stream_api_data(api_url):
    """Stream paginated API data."""
    page = 1
    
    with httpx.Client() as client:
        while True:
            with client.stream('GET', f"{api_url}?page={page}") as response:
                # Check if we have data
                if response.status_code != 200:
                    break
                
                # Parse JSON response
                data = json.loads(response.read())
                
                if not data.get('items'):
                    break
                
                # Process each item
                for item in data['items']:
                    yield item
                
                page += 1

# Usage
for item in stream_api_data('https://api.example.com/data'):
    process_item(item)
```

### Server-Sent Events (SSE) Simulation

```python
import httpx

def stream_events(url):
    """Stream server-sent events."""
    with httpx.stream('GET', url, headers={'Accept': 'text/event-stream'}) as response:
        for line in response.iter_lines():
            if line.startswith('data: '):
                event_data = line[6:]  # Remove 'data: ' prefix
                yield event_data

# Usage
for event in stream_events('https://api.example.com/events'):
    print(f"Event: {event}")
```

### Error Handling in Streaming

```python
import httpx

def safe_stream_download(url, filename):
    try:
        with httpx.stream('GET', url) as response:
            response.raise_for_status()  # Check status before streaming
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    
            print(f"Successfully downloaded {filename}")
            
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        print(f"Request error: {exc}")
    except IOError as exc:
        print(f"File error: {exc}")

safe_stream_download('https://example.com/file.zip', 'file.zip')
```

### Memory-Efficient JSON Processing

```python
import httpx
import json

def process_large_json_array(url):
    """Process large JSON array without loading entire response."""
    with httpx.stream('GET', url) as response:
        # Assume response is JSON array with objects on separate lines
        buffer = ""
        
        for chunk in response.iter_text():
            buffer += chunk
            
            # Process complete JSON objects
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    try:
                        obj = json.loads(line)
                        yield obj
                    except json.JSONDecodeError:
                        continue
        
        # Process remaining buffer
        if buffer.strip():
            try:
                obj = json.loads(buffer)
                yield obj
            except json.JSONDecodeError:
                pass

# Usage
for item in process_large_json_array('https://api.example.com/large-dataset'):
    process_item(item)
```

### Resumable Downloads

```python
import httpx
import os

def resumable_download(url, filename):
    """Download file with resume capability."""
    # Check if partial file exists
    resume_pos = 0
    if os.path.exists(filename):
        resume_pos = os.path.getsize(filename)
        print(f"Resuming download from byte {resume_pos}")
    
    headers = {}
    if resume_pos > 0:
        headers['Range'] = f'bytes={resume_pos}-'
    
    mode = 'ab' if resume_pos > 0 else 'wb'
    
    with httpx.stream('GET', url, headers=headers) as response:
        if response.status_code in (200, 206):  # OK or Partial Content
            with open(filename, mode) as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            print(f"Download completed: {filename}")
        else:
            print(f"Download failed: {response.status_code}")

resumable_download('https://example.com/large-file.zip', 'large-file.zip')
```