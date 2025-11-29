import socket
import threading
import signal
import sys
from services import ServiceRegister
from logger import Logger


def get_local_ip():
    """Get the local IP address (first non-loopback IPv4 address).
    
    Returns:
        str: Local IP address, or None if not found
    """
    try:
        # Connect to a remote address to determine local IP
        # This doesn't actually send data, just determines the route
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback: try to get IP from hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            # If it's loopback, try to find another interface
            if local_ip.startswith("127."):
                # Try to get IP from network interfaces
                try:
                    import ifaddr
                    adapters = ifaddr.get_adapters()
                    for adapter in adapters:
                        for ip in adapter.ips:
                            if ip.is_IPv4 and not ip.ip.startswith("127."):
                                return ip.ip
                except ImportError:
                    # ifaddr not available, return loopback as fallback
                    pass
            return local_ip
        except Exception:
            return None


class Server:
    """Server class for encrypted mail program with mDNS service registration."""
    
    def __init__(self, server_id="stgserver", port=6161):
        """Initialize the server.
        
        Args:
            server_id: Server ID for mDNS registration (default: "stgserver")
            port: Server port (default: 6161)
        """
        self.server_id = server_id
        self.port = port
        self.logger = Logger()
        self.local_ip = None
        self.service_register = None
        self.service_thread = None
        self.running = False
        
        # Get local IP address
        self.local_ip = get_local_ip()
        if not self.local_ip:
            self.logger.error("Could not determine local IP address")
            raise RuntimeError("Could not determine local IP address")
        
        self.logger.log("SERVER", f"Server initialized with IP: {self.local_ip}, Port: {self.port}")
    
    def start(self):
        """Start the server and register mDNS service."""
        if self.running:
            self.logger.log("SERVER", "Server is already running")
            return
        
        self.running = True
        self.logger.log("SERVER", "Server starting.")
        
        # Initialize service registration
        self.service_register = ServiceRegister(self.server_id, self.port, self.local_ip)
        
        # Register service in a separate thread
        self.service_thread = threading.Thread(target=self._register_service, daemon=True)
        self.service_thread.start()
        
        self.logger.log("SERVICE", f"Service registered as {self.server_id}.")
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Keep server running
            while self.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _register_service(self):
        """Register mDNS service in a separate thread."""
        try:
            self.service_register.register()
        except Exception as e:
            self.logger.error(f"Service registration error: {e}")
    
    def stop(self):
        """Stop the server and unregister mDNS service."""
        if not self.running:
            return
        
        self.logger.log("SERVER", "Server stopping.")
        self.running = False
        
        if self.service_register:
            self.service_register.stop = True
        
        if self.service_thread and self.service_thread.is_alive():
            self.service_thread.join(timeout=2)
        
        self.logger.log("SERVER", "Server stopped.")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.log("SERVER", f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def handle_register(self, username):
        """Handle user registration request.
        
        Args:
            username: Username to register
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        # TODO: Implement user registration functionality
        self.logger.log("REGISTER", f"{username} wants to be registered.")
        # Placeholder for registration logic
        self.logger.log("REGISTER", "Registering successful.")
        return True
    
    def handle_message(self):
        """Handle messaging functionality.
        
        TODO: Implement messaging functionality
        """
        pass

