from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket
import time
import json
import base64
import os
import tempfile
from PIL import Image
from password import hash_password, derive_des_key, get_password_hash_prefix, decrypt_des_cbc, encrypt_des_cbc
from steganography import encode_hash_in_image


class AllServicesListener(ServiceListener):
    """Service listener that collects all services of a given type without ID filtering."""
    
    def __init__(self):
        self.found_services = []
    
    def update_service(self, zc, type_, name):
        """Handle service update."""
        pass
    
    def remove_service(self, zc, type_, name):
        """Handle service removal."""
        # Remove from found_services if present
        self.found_services = [s for s in self.found_services if s['name'] != name]
    
    def add_service(self, zc, type_, name):
        """Handle new service discovery."""
        info = zc.get_service_info(type_, name)
        
        if info:
            addresses = ["%s" % socket.inet_ntoa(addr) 
                        for addr in info.addresses]
            
            info.server = str(info.server) if info.server else ""
            
            # Extract service name (first part before the dot)
            service_name = info.server.split('.')[0] if info.server else name.split('.')[0]
            
            service_info = {
                'name': service_name,
                'type': type_,
                'addresses': addresses,
                'port': info.port,
                'server': info.server
            }
            
            # Avoid duplicates
            if not any(s['name'] == service_name and s['addresses'][0] == addresses[0] 
                      for s in self.found_services):
                self.found_services.append(service_info)


class Client:
    """Client class for discovering and connecting to servers."""
    
    def __init__(self):
        """Initialize the client."""
        self.service_type = "_stgserver._tcp.local."
        self.zeromq_context = None
        self.zeromq_socket = None
        self.connected_server = None
        self.zeromq_port = 6162
        self.des_key = None  # Store DES key after login/registration
        self.current_username = None  # Store current logged-in username
    
    def discover_servers(self, timeout=5):
        """Discover all available stgserver services on the LAN.
        
        Args:
            timeout: Time to wait for service discovery in seconds (default: 5)
            
        Returns:
            list: List of server dictionaries with keys: 'name', 'address', 'port', 'server'
                  Returns empty list if no services found
        """
        zc = Zeroconf()
        listener = AllServicesListener()
        browser = ServiceBrowser(zc, self.service_type, listener)
        
        # Wait for discovery
        time.sleep(timeout)
        
        # Close zeroconf (this will stop the browser)
        zc.close()
        
        # Format servers for UI
        servers = []
        for service in listener.found_services:
            servers.append({
                'name': service['name'],
                'address': service['addresses'][0] if service['addresses'] else 'N/A',
                'port': service['port'],
                'server': service['server']
            })
        
        return servers
    
    def connect_to_server(self, address, port=6162):
        """Connect to a server using ZeroMQ REQ socket.
        
        Args:
            address: Server IP address
            port: ZeroMQ port (default: 6162)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            import zmq
            
            if self.zeromq_socket:
                self.disconnect()
            
            self.zeromq_context = zmq.Context()
            self.zeromq_socket = self.zeromq_context.socket(zmq.REQ)
            self.zeromq_socket.connect(f"tcp://{address}:{port}")
            self.connected_server = address
            return True
        except ImportError:
            print("Error: ZeroMQ (pyzmq) not installed. Please install it with: pip install pyzmq")
            return False
        except Exception as e:
            print(f"Error connecting to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the current server."""
        if self.zeromq_socket:
            try:
                self.zeromq_socket.close()
            except:
                pass
            self.zeromq_socket = None
        
        if self.zeromq_context:
            try:
                self.zeromq_context.term()
            except:
                pass
            self.zeromq_context = None
        
        self.connected_server = None
    
    def register(self, username, password, picture_path):
        """Register a new user with the server.
        
        Args:
            username: Username to register
            password: Password string
            picture_path: Path to profile picture file
            
        Returns:
            dict: Response dictionary with status and message
        """
        if not self.zeromq_socket:
            return {"status": "error", "message": "Not connected to server"}
        
        try:
            # 1. Hash password
            password_hash = hash_password(password)
            
            # 2. Derive DES key (store for future message encryption)
            self.des_key = derive_des_key(username, password_hash)
            self.current_username = username
            
            # 3. Normalize input image to PNG and encode hash in picture
            if not os.path.exists(picture_path):
                return {"status": "error", "message": "Picture file not found"}

            # Always convert source image to PNG (RGB) before steganography
            temp_dir = tempfile.gettempdir()
            source_png_path = os.path.join(temp_dir, f"{username}_source.png")
            encoded_picture_path = os.path.join(temp_dir, f"{username}_encoded.png")

            try:
                img = Image.open(picture_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(source_png_path, format="PNG")
            except Exception as e:
                return {"status": "error", "message": f"Failed to prepare PNG: {str(e)}"}

            try:
                encode_hash_in_image(source_png_path, password_hash, encoded_picture_path)
            except ValueError as e:
                # Clean temp source on error
                try:
                    os.remove(source_png_path)
                except:
                    pass
                return {"status": "error", "message": f"Steganography error: {str(e)}"}
            
            # 4. Read encoded picture
            with open(encoded_picture_path, "rb") as f:
                picture_data = f.read()
            
            picture_base64 = base64.b64encode(picture_data).decode('utf-8')
            
            # 5. Create request with password_hash (base64 encoded)
            request = {
                "action": "REQ::REGISTER",
                "username": username,
                "password_hash": base64.b64encode(password_hash).decode('utf-8'),
                "picture": picture_base64
            }
            
            # 6. Send request
            self.zeromq_socket.send_string(json.dumps(request))
            
            # 7. Wait for response
            response_str = self.zeromq_socket.recv_string()
            response = json.loads(response_str)
            
            # Clean up temporary files
            for p in (encoded_picture_path, source_png_path):
                try:
                    os.remove(p)
                except:
                    pass
            
            return response
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def login(self, username, password):
        """Login with username and password.
        
        Args:
            username: Username to login
            password: Password for authentication
            
        Returns:
            dict: Response dictionary with status and message
        """
        if not self.zeromq_socket:
            return {"status": "error", "message": "Not connected to server"}
        
        try:
            # 1. Hash password
            password_hash = hash_password(password)
            
            # 2. Get first 8 bytes for login verification
            hash_prefix = get_password_hash_prefix(password_hash)
            
            # 3. Create request with hash prefix
            request = {
                "action": "REQ::LOGIN",
                "username": username,
                "password_hash_prefix": base64.b64encode(hash_prefix).decode('utf-8')
            }
            
            # 4. Send request
            self.zeromq_socket.send_string(json.dumps(request))
            
            # 5. Wait for response
            response_str = self.zeromq_socket.recv_string()
            response = json.loads(response_str)
            
            # 6. On success, derive and store DES key
            if response.get("status") == "success":
                self.des_key = derive_des_key(username, password_hash)
                self.current_username = username
            
            return response
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_des_key(self):
        """Get the stored DES key for message encryption.
        
        Returns:
            bytes: DES key (8 bytes) or None if not available
        """
        return self.des_key

    def send_message(self, to_username, plaintext):
        """Send a message to recipient.
        
        Client encrypts the message with SENDER's key (self.des_key).
        Server will decrypt it with sender's key and re-encrypt with recipient's key.
        
        Args:
            to_username: Recipient username
            plaintext: Message body string
        Returns:
            dict: Response with status/message
        """
        if not self.zeromq_socket:
            return {"status": "error", "message": "Not connected to server"}
        if not self.current_username:
            return {"status": "error", "message": "Not logged in"}
        if not self.des_key:
            return {"status": "error", "message": "No encryption key available"}
            
        try:
            # Encrypt with SENDER's key
            iv_ct = encrypt_des_cbc(self.des_key, plaintext)
            import base64
            body_b64 = base64.b64encode(iv_ct).decode('utf-8')

            req = {
                "action": "REQ::SEND",
                "from": self.current_username,
                "to": to_username,
                "body": body_b64,
            }
            self.zeromq_socket.send_string(json.dumps(req))
            resp = json.loads(self.zeromq_socket.recv_string())
            return resp
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_users(self):
        """Get list of registered users from server.
        
        Returns:
            list: List of usernames on success, or empty list on error
        """
        if not self.zeromq_socket:
            return []
        
        try:
            req = {"action": "REQ::GET_USERS"}
            self.zeromq_socket.send_string(json.dumps(req))
            resp = json.loads(self.zeromq_socket.recv_string())
            
            if resp.get("status") == "success":
                return resp.get("users", [])
            return []
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    def fetch_messages(self):
        """Fetch messages for the logged-in user and decrypt using stored DES key.
        
        Returns:
            dict: {"status":"success","messages":[{"from":str,"body":str,"created_at":str}]} or error
        """
        if not self.zeromq_socket:
            return {"status": "error", "message": "Not connected to server"}
        if not self.current_username or not self.des_key:
            return {"status": "error", "message": "Not logged in"}
        try:
            req = {"action": "REQ::FETCH", "username": self.current_username}
            self.zeromq_socket.send_string(json.dumps(req))
            resp = json.loads(self.zeromq_socket.recv_string())
            if resp.get("status") != "success":
                return resp
            import base64
            decrypted = []
            for m in resp.get("messages", []):
                try:
                    raw = base64.b64decode(m.get("body", ""))
                    body = decrypt_des_cbc(self.des_key, raw)
                    decrypted.append({"from": m.get("from"), "body": body, "created_at": m.get("created_at")})
                except Exception as e:
                    decrypted.append({"from": m.get("from"), "body": f"<decrypt error: {e}>", "created_at": m.get("created_at")})
            return {"status": "success", "messages": decrypted}
        except Exception as e:
            return {"status": "error", "message": str(e)}

