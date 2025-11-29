from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket
import time
import json
import base64
import os
import tempfile
from password import hash_password, derive_des_key, get_password_hash_prefix
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
            
            # 3. Encode hash in picture
            if not os.path.exists(picture_path):
                return {"status": "error", "message": "Picture file not found"}
            
            # Create temporary file for encoded picture
            temp_dir = tempfile.gettempdir()
            encoded_picture_path = os.path.join(temp_dir, f"{username}_encoded.png")
            
            try:
                encode_hash_in_image(picture_path, password_hash, encoded_picture_path)
            except ValueError as e:
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
            
            # Clean up temporary file
            try:
                os.remove(encoded_picture_path)
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

