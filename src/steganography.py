from PIL import Image
import os


def validate_image_size(image_path, required_bits):
    """Validate if image has enough pixels for encoding.
    
    Args:
        image_path: Path to image file
        required_bits: Number of bits needed for encoding
        
    Returns:
        bool: True if image is large enough, False otherwise
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        available_bits = width * height * 3  # RGB = 3 bits per pixel
        return available_bits >= required_bits
    except Exception:
        return False


def encode_hash_in_image(image_path, password_hash, output_path):
    """Encode password hash into image using LSB steganography.
    
    Args:
        image_path: Path to original image
        password_hash: Password hash as bytes (32 bytes)
        output_path: Path to save encoded image
        
    Returns:
        str: Path to encoded image
        
    Raises:
        ValueError: If image is too small or other encoding error
    """
    if not os.path.exists(image_path):
        raise ValueError(f"Image file not found: {image_path}")
    
    # Validate image size (32 bytes = 256 bits + 16 bits length = 272 bits)
    required_bits = 272
    if not validate_image_size(image_path, required_bits):
        raise ValueError(f"Image too small. Need at least {required_bits // 3} pixels for encoding.")
    
    img = Image.open(image_path)
    # Normalize to PNG and RGB to preserve LSBs
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    pixels = img.load()
    width, height = img.size
    
    # Convert hash to binary string
    hash_binary = ''.join(format(byte, '08b') for byte in password_hash)
    hash_length = len(hash_binary)  # Should be 256 bits
    
    # Encode length first (16 bits to support values up to 65535)
    length_bits = format(hash_length, '016b')
    
    bit_index = 0
    
    # Encode length (16 bits)
    for i in range(16):
        x = (bit_index // 3) % width
        y = (bit_index // 3) // width
        channel = bit_index % 3
        
        pixel = list(pixels[x, y])
        # Set LSB to length bit
        pixel[channel] = (pixel[channel] & 0xFE) | int(length_bits[i])
        pixels[x, y] = tuple(pixel)
        bit_index += 1
    
    # Encode hash bits (256 bits)
    for bit in hash_binary:
        x = (bit_index // 3) % width
        y = (bit_index // 3) // width
        channel = bit_index % 3
        
        pixel = list(pixels[x, y])
        # Set LSB to hash bit
        pixel[channel] = (pixel[channel] & 0xFE) | int(bit)
        pixels[x, y] = tuple(pixel)
        bit_index += 1
    
    # Save encoded image explicitly as PNG (lossless)
    img.save(output_path, format="PNG")
    return output_path


def decode_hash_from_image(image_path):
    """Decode password hash from image using LSB steganography.
    
    Args:
        image_path: Path to encoded image
        
    Returns:
        bytes: Password hash (32 bytes)
        
    Raises:
        ValueError: If decoding fails
    """
    if not os.path.exists(image_path):
        raise ValueError(f"Image file not found: {image_path}")
    
    img = Image.open(image_path)
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    pixels = img.load()
    width, height = img.size
    
    bit_index = 0
    
    # Read length first (16 bits)
    length_bits = ''
    for i in range(16):
        x = (bit_index // 3) % width
        y = (bit_index // 3) // width
        channel = bit_index % 3
        
        pixel = pixels[x, y]
        # Extract LSB
        length_bits += str(pixel[channel] & 0x01)
        bit_index += 1
    
    hash_length = int(length_bits, 2)
    
    # Validate length (should be 256 bits)
    if hash_length != 256:
        raise ValueError(f"Invalid hash length: {hash_length}, expected 256")
    
    # Read hash bits
    hash_bits = ''
    for i in range(hash_length):
        x = (bit_index // 3) % width
        y = (bit_index // 3) // width
        channel = bit_index % 3
        
        pixel = pixels[x, y]
        # Extract LSB
        hash_bits += str(pixel[channel] & 0x01)
        bit_index += 1
    
    # Convert binary string back to bytes
    hash_bytes = bytes(int(hash_bits[i:i+8], 2) for i in range(0, len(hash_bits), 8))
    
    # Validate hash length (should be 32 bytes)
    if len(hash_bytes) != 32:
        raise ValueError(f"Invalid hash size: {len(hash_bytes)} bytes, expected 32")
    
    return hash_bytes

