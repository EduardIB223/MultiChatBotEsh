"""
Custom imghdr module to replace the missing standard library module in Python 3.13.
This is a simplified version that only implements the basic functionality needed by Telethon.
"""

def what(file, h=None):
    """
    Determine the type of image contained in a file or memory buffer.
    
    Args:
        file: A filename (string), a file object, or a bytes object.
        h: A bytes object containing the header of the file.
    
    Returns:
        A string describing the image type if recognized, else None.
    """
    if h is None:
        if isinstance(file, str):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
    
    if h.startswith(b'\xff\xd8'):
        return 'jpeg'
    elif h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
        return 'gif'
    elif h.startswith(b'BM'):
        return 'bmp'
    elif h.startswith(b'\x49\x49') or h.startswith(b'\x4d\x4d'):
        return 'tiff'
    elif h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'
    
    return None 