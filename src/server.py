import socket
import threading
import signal
import sys
import json
import sqlite3
import os
import base64
from PIL import Image
import io
from services import ServiceRegister
from logger import Logger
from constants import Const


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
        self.zeromq_thread = None
        self.running = False
        self.zeromq_port = 6162
        
        # Initialize databases and directories
        self._init_directories()
        self._init_user_database()
        
        # Get local IP address
        self.local_ip = get_local_ip()
        if not self.local_ip:
            self.logger.error("Could not determine local IP address")
            raise RuntimeError("Could not determine local IP address")
        
        self.logger.log("SERVER", f"Server initialized with IP: {self.local_ip}, Port: {self.port}")
    
    def _init_directories(self):
        """Initialize required directories."""
        os.makedirs(Const.DB_DIR, exist_ok=True)
        os.makedirs(Const.IMG_DIR, exist_ok=True)
    
    def _init_user_database(self):
        """Initialize user database."""
        conn = sqlite3.connect(Const.USERS_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                picture_path TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
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
        
        # Start ZeroMQ server in a separate thread
        self.zeromq_thread = threading.Thread(target=self._start_zeromq_server, daemon=True)
        self.zeromq_thread.start()
        
        self.logger.log("SERVER", f"ZeroMQ server started on port {self.zeromq_port}")
        
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
        
        if self.zeromq_thread and self.zeromq_thread.is_alive():
            # ZeroMQ thread will stop when running is False
            self.zeromq_thread.join(timeout=2)
        
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
    
    def _start_zeromq_server(self):
        """Start ZeroMQ REP socket server."""
        try:
            import zmq
            
            context = zmq.Context()
            socket = context.socket(zmq.REP)
            socket.bind(f"tcp://*:{self.zeromq_port}")
            
            self.logger.log("ZEROMQ", f"ZeroMQ server listening on port {self.zeromq_port}")
            
            while self.running:
                try:
                    # Wait for request with timeout
                    if socket.poll(1000, zmq.POLLIN):
                        message = socket.recv_string()
                        request = json.loads(message)
                        
                        # Route request based on action
                        response = self._handle_request(request)
                        
                        # Send response
                        socket.send_string(json.dumps(response))
                except zmq.Again:
                    # Timeout, continue loop
                    continue
                except Exception as e:
                    self.logger.error(f"ZeroMQ error: {e}")
                    error_response = {"status": "error", "message": str(e)}
                    try:
                        socket.send_string(json.dumps(error_response))
                    except:
                        pass
            
            socket.close()
            context.term()
        except ImportError:
            self.logger.error("ZeroMQ (pyzmq) not installed. Please install it with: pip install pyzmq")
        except Exception as e:
            self.logger.error(f"ZeroMQ server error: {e}")
    
    def _handle_request(self, request):
        """Handle incoming request and route to appropriate handler.
        
        Args:
            request: Dictionary containing request data
            
        Returns:
            dict: Response dictionary
        """
        action = request.get("action", "")
        
        if action == "REQ::REGISTER":
            return self._handle_register(request)
        elif action == "REQ::LOGIN":
            return {"status": "error", "message": "Not implemented yet"}
        elif action == "REQ::SEND":
            return {"status": "error", "message": "Not implemented yet"}
        elif action == "REQ::FETCH":
            return {"status": "error", "message": "Not implemented yet"}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def _handle_register(self, request):
        """Handle registration request.
        
        Args:
            request: Dictionary with username, password_hash, and picture (base64)
            
        Returns:
            dict: Response dictionary with status
        """
        try:
            username = request.get("username")
            password_hash = request.get("password_hash")
            picture_base64 = request.get("picture")
            
            if not username or not password_hash or not picture_base64:
                return {"status": "error", "message": "Missing required fields"}
            
            # Check if username already exists
            conn = sqlite3.connect(Const.USERS_DB)
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                self.logger.log("REGISTER", f"{username} registration failed: username already exists")
                return {"status": "error", "message": "Username already exists"}
            
            # Decode and save picture
            try:
                picture_data = base64.b64decode(picture_base64)
                picture_image = Image.open(io.BytesIO(picture_data))
                
                # Convert to PNG if needed and save
                picture_path = os.path.join(Const.IMG_DIR, f"{username}.png")
                picture_image.save(picture_path, "PNG")
                
                # Get relative path
                relative_path = os.path.relpath(picture_path, Const.CONFIG_DIR)
            except Exception as e:
                conn.close()
                self.logger.error(f"Error saving picture for {username}: {e}")
                return {"status": "error", "message": f"Error saving picture: {str(e)}"}
            
            # Save user to database (using password as key for now)
            cursor.execute(
                "INSERT INTO users (username, key, picture_path) VALUES (?, ?, ?)",
                (username, password_hash, relative_path)
            )
            
            conn.commit()
            conn.close()
            
            self.logger.log("REGISTER", f"{username} wants to be registered.")
            self.logger.log("REGISTER", "Registering successful.")
            
            return {"status": "success", "message": "Registration successful"}
            
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return {"status": "error", "message": str(e)}
    
    def handle_message(self):
        """Handle messaging functionality.
        
        TODO: Implement messaging functionality
        """
        pass

