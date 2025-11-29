from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket
import time
import json
import base64
import os


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
            password: Password (will be used as key for now)
            picture_path: Path to profile picture file
            
        Returns:
            dict: Response dictionary with status and message
        """
        if not self.zeromq_socket:
            return {"status": "error", "message": "Not connected to server"}
        
        try:
            # Read and encode picture
            if not os.path.exists(picture_path):
                return {"status": "error", "message": "Picture file not found"}
            
            with open(picture_path, "rb") as f:
                picture_data = f.read()
            
            picture_base64 = base64.b64encode(picture_data).decode('utf-8')
            
            # Create request
            request = {
                "action": "REQ::REGISTER",
                "username": username,
                "password_hash": password,  # Using password as key for now
                "picture": picture_base64
            }
            
            # Send request
            self.zeromq_socket.send_string(json.dumps(request))
            
            # Wait for response
            response_str = self.zeromq_socket.recv_string()
            response = json.loads(response_str)
            
            return response
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

