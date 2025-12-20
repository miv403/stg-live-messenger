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
import tempfile
from services import ServiceRegister
from logger import Logger
from constants import Const
from password import derive_des_key_from_hash, get_password_hash_prefix
from password import encrypt_des_cbc
from steganography import decode_hash_from_image


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
    
    def __init__(self, server_id="stgserver", port=6161, zeromq_port=6162):
        """Initialize the server.
        
        Args:
            server_id: Server ID for mDNS registration (default: "stgserver")
            port: Server port for mDNS service (default: 6161)
            zeromq_port: Port for ZeroMQ server (default: 6162)
        """
        self.server_id = server_id
        self.port = port
        self.logger = Logger()
        self.local_ip = None
        self.service_register = None
        self.service_thread = None
        self.zeromq_thread = None
        self.running = False
        self.zeromq_port = zeromq_port
        
        # Initialize databases and directories
        self._init_directories()
        self._init_user_database()
        self._init_mailbox_database()
        
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
        
        # Check if password_hash column exists (for migration)
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                picture_path TEXT NOT NULL
            )
        ''')
        
        # Migrate old schema if needed
        if 'key' in columns and 'password_hash' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
            # Copy key to password_hash for existing records
            cursor.execute('UPDATE users SET password_hash = key WHERE password_hash IS NULL')
            # Optionally drop key column (keep for now for compatibility)
        
        conn.commit()
        conn.close()

    def _init_mailbox_database(self):
        """Initialize mailbox database."""
        conn = sqlite3.connect(Const.MAILBOX_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mailbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_username TEXT NOT NULL,
                from_username TEXT NOT NULL,
                body BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mailbox_to ON mailbox(to_username)")
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
    
    # def handle_register(self, username):
    #     """Handle user registration request.
    #     
    #     Args:
    #         username: Username to register
    #         
    #     Returns:
    #         bool: True if registration successful, False otherwise
    #     """
    #     # TODO: Implement user registration functionality
    #     self.logger.log("REGISTER", f"{username} wants to be registered.")
    #     # Placeholder for registration logic
    #     self.logger.log("REGISTER", "Registering successful.")
    #     return True
    
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
            return self._handle_login(request)
        elif action == "REQ::SEND":
            return self._handle_send(request)
        elif action == "REQ::FETCH":
            return self._handle_fetch(request)
        elif action == "REQ::GET_USERS":
            return self._handle_get_users(request)
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
            password_hash_b64 = request.get("password_hash")
            picture_base64 = request.get("picture")
            
            # if not username or not password_hash_b64 or not picture_base64:
            if not username or not picture_base64:
                return {"status": "error", "message": "Missing required fields"}
            
            # Check if username already exists
            conn = sqlite3.connect(Const.USERS_DB)
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                self.logger.log("REGISTER", f"{username} registration failed: username already exists")
                return {"status": "error", "message": "Username already exists"}
            
            # Decode picture and save temporarily
            try:
                picture_data = base64.b64decode(picture_base64)
                picture_image = Image.open(io.BytesIO(picture_data))
                
                # Save to temporary file for steganography decoding
                temp_dir = tempfile.gettempdir()
                temp_picture_path = os.path.join(temp_dir, f"{username}_temp.png")
                picture_image.save(temp_picture_path, "PNG")
                
                # Decode password hash from picture using steganography
                try:
                    decoded_hash = decode_hash_from_image(temp_picture_path)
                except Exception as e:
                    os.remove(temp_picture_path)
                    conn.close()
                    self.logger.error(f"Steganography decode error for {username}: {e}")
                    return {"status": "error", "message": f"Failed to decode hash from picture: {str(e)}"}
                
                # Verify received hash matches decoded hash
                received_hash = base64.b64decode(password_hash_b64)
                # if decoded_hash != received_hash:
                #    os.remove(temp_picture_path)
                #    conn.close()
                #    self.logger.error(f"Hash verification failed for {username}")
                #    return {"status": "error", "message": "Hash verification failed"}
                
                # Save picture to final location
                picture_path = os.path.join(Const.IMG_DIR, f"{username}.png")
                picture_image.save(picture_path, "PNG")
                
                # Get relative path
                relative_path = os.path.relpath(picture_path, Const.CONFIG_DIR)
                
                # Clean up temporary file
                try:
                    os.remove(temp_picture_path)
                except:
                    pass
                    
            except Exception as e:
                conn.close()
                self.logger.error(f"Error processing picture for {username}: {e}")
                return {"status": "error", "message": f"Error processing picture: {str(e)}"}
            
            # Save user to database with password_hash
            cursor.execute(
                "INSERT INTO users (username, password_hash, picture_path) VALUES (?, ?, ?)",
                (username, password_hash_b64, relative_path)
                # (username, decoded_hash, relative_path)
            )
            
            conn.commit()
            conn.close()
            
            self.logger.log("REGISTER", f"{username} wants to be registered.")
            self.logger.log("REGISTER", "Registering successful.")
            
            # Insert welcome message encrypted with user's DES key
            try:
                des_key = self.get_user_des_key(username)
                if des_key:
                    welcome_text = "Welcome to STG Live Messenger!"
                    iv_ct = encrypt_des_cbc(des_key, welcome_text)
                    conn_mb = sqlite3.connect(Const.MAILBOX_DB)
                    cur_mb = conn_mb.cursor()
                    import datetime
                    cur_mb.execute(
                        "INSERT INTO mailbox (to_username, from_username, body, created_at) VALUES (?, ?, ?, ?)",
                        (username, "server", iv_ct, datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")
                    )
                    conn_mb.commit()
                    conn_mb.close()
            except Exception as e:
                self.logger.error(f"Failed to insert welcome message for {username}: {e}")

            return {"status": "success", "message": "Registration successful"}
            
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_login(self, request):
        """Handle login request.
        
        Args:
            request: Dictionary with username and password_hash_prefix
            
        Returns:
            dict: Response dictionary with status
        """
        try:
            username = request.get("username")
            hash_prefix_b64 = request.get("password_hash_prefix")
            
            if not username or not hash_prefix_b64:
                return {"status": "error", "message": "Missing username or password hash prefix"}
            
            # Query database for username and password_hash
            conn = sqlite3.connect(Const.USERS_DB)
            cursor = conn.cursor()
            
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                self.logger.log("LOGIN", f"Login failed for {username}: username not found")
                return {"status": "error", "message": "Invalid username or password"}
            
            stored_hash_b64 = result[0]
            stored_hash = base64.b64decode(stored_hash_b64)
            
            # Get first 8 bytes of stored hash
            stored_hash_prefix = get_password_hash_prefix(stored_hash)
            
            # Compare with received hash prefix
            received_hash_prefix = base64.b64decode(hash_prefix_b64)
            
            if stored_hash_prefix != received_hash_prefix:
                self.logger.log("LOGIN", f"Login failed for {username}: incorrect password")
                return {"status": "error", "message": "Invalid username or password"}
            
            # Login successful - DES key can be derived using get_user_des_key() when needed
            self.logger.log("LOGIN", f"{username} logged in successfully")
            return {"status": "success", "message": "Login successful"}
            
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_user_des_key(self, username):
        """Get DES key for a user by deriving it from stored password hash.
        
        Args:
            username: Username to get DES key for
            
        Returns:
            bytes: DES key (8 bytes) or None if user not found
        """
        try:
            conn = sqlite3.connect(Const.USERS_DB)
            cursor = conn.cursor()
            
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            stored_hash_b64 = result[0]
            stored_hash = base64.b64decode(stored_hash_b64)
            
            # Derive DES key using username as salt
            des_key = derive_des_key_from_hash(username, stored_hash)
            return des_key
            
        except Exception as e:
            self.logger.error(f"Error getting DES key for {username}: {e}")
            return None
    
    def handle_message(self):
        """Handle messaging functionality.
        
        TODO: Implement messaging functionality
        """
        pass

    def _handle_send(self, request):
        """Handle send message request.
        
        Expected request: {"action":"REQ::SEND","from":"<sender>","to":"<recipient>","body":"<encrypted_body_b64>"}
        body is encrypted with SENDER's key.
        """
        try:
            sender = request.get("from")
            recipient = request.get("to")
            body_b64 = request.get("body")
            if not sender or not recipient or body_b64 is None:
                return {"status": "error", "message": "Missing fields"}

            # Validate users exist and get keys
            conn = sqlite3.connect(Const.USERS_DB)
            cur = conn.cursor()
            
            # Check sender and get key
            # cur.execute("SELECT 1 FROM users WHERE username=?", (sender,))
            # if not cur.fetchone():
            #     conn.close()
            #     return {"status": "error", "message": "Sender not found"}
            sender_key = self.get_user_des_key(sender)
            if not sender_key:
                conn.close()
                return {"status": "error", "message": "Sender not found or key unavailable"}

            # Check recipient and get key
            # cur.execute("SELECT 1 FROM users WHERE username=?", (recipient,))
            # if not cur.fetchone():
            #     conn.close()
            #     return {"status": "error", "message": "Recipient not found"}
            recipient_key = self.get_user_des_key(recipient) # This function opens its own connection, optimized to minimal
            if not recipient_key:
                conn.close()
                return {"status": "error", "message": "Recipient not found or key unavailable"}
            
            conn.close()

            # Decrypt with SENDER key
            from password import decrypt_des_cbc
            import base64
            try:
                encrypted_body = base64.b64decode(body_b64)
                plaintext_body = decrypt_des_cbc(sender_key, encrypted_body)
            except Exception as e:
                self.logger.error(f"Decryption failed for message from {sender}: {e}")
                return {"status": "error", "message": "Server could not decrypt message with sender key"}

            # Encrypt with RECIPIENT key
            # iv_ct = encrypt_des_cbc(des_key, body)
            iv_ct = encrypt_des_cbc(recipient_key, plaintext_body)

            # Store in mailbox
            import datetime
            conn_mb = sqlite3.connect(Const.MAILBOX_DB)
            cur_mb = conn_mb.cursor()
            cur_mb.execute(
                "INSERT INTO mailbox (to_username, from_username, body, created_at) VALUES (?, ?, ?, ?)",
                (recipient, sender, iv_ct, datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")
            )
            conn_mb.commit()
            conn_mb.close()
            return {"status": "success", "message": "Message stored"}
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_get_users(self, request):
        """Handle request to get list of registered users.
        
        Expected request: {"action":"REQ::GET_USERS"}
        Returns: {"status":"success", "users":["user1", "user2", ...]}
        """
        try:
            conn = sqlite3.connect(Const.USERS_DB)
            cur = conn.cursor()
            cur.execute("SELECT username FROM users")
            users = [row[0] for row in cur.fetchall()]
            conn.close()
            return {"status": "success", "users": users}
        except Exception as e:
            self.logger.error(f"Get users error: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_fetch(self, request):
        """Handle fetch messages for a username.
        
        Expected request: {"action":"REQ::FETCH","username":"<user>"}
        Returns base64 iv|ciphertext bodies for client to decrypt.
        """
        try:
            username = request.get("username")
            if not username:
                return {"status": "error", "message": "Missing username"}

            # Validate user exists
            conn = sqlite3.connect(Const.USERS_DB)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
            if not cur.fetchone():
                conn.close()
                return {"status": "error", "message": "User not found"}
            conn.close()

            # Fetch messages
            conn_mb = sqlite3.connect(Const.MAILBOX_DB)
            cur_mb = conn_mb.cursor()
            cur_mb.execute(
                "SELECT from_username, body, created_at FROM mailbox WHERE to_username=? ORDER BY id ASC",
                (username,)
            )
            rows = cur_mb.fetchall()
            conn_mb.close()
            import base64
            messages = [
                {"from": r[0], "body": base64.b64encode(r[1]).decode("ascii"), "created_at": r[2]}
                for r in rows
            ]
            return {"status": "success", "messages": messages}
        except Exception as e:
            self.logger.error(f"Fetch error: {e}")
            return {"status": "error", "message": str(e)}
