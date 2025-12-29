import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from PIL import Image
import os
import threading
import hashlib
from client import Client


class LoginScreen:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("STG Live Messenger")
        self.root.geometry("900x600")
        
        # Center the window
        self.center_window()
        
        # Variables
        self.username_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.register_mode = False
        self.selected_image_path = None
        self.discovered_servers = []
        self.connected_to_server = False
        
        # Initialize client for service discovery
        self.client = Client()
        
        self.setup_ui()
        
        # Start server discovery in background thread
        self.discover_servers()
    
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the main UI with three containers"""
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left container - Login/Register
        self.setup_login_container(self.main_frame)
        
        # Right container - Server Status and Logs
        self.setup_right_containers(self.main_frame)
    
    def setup_login_container(self, parent):
        """Setup the left container for login/register"""
        login_frame = ctk.CTkFrame(parent, width=350)
        login_frame.pack(side="left", fill="both", padx=(0, 10), pady=0)
        login_frame.pack_propagate(False)
        
        # Inner frame with padding
        inner_frame = ctk.CTkFrame(login_frame, fg_color="transparent")
        inner_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib", "logo.png")
        if os.path.exists(logo_path):
            logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(120, 120)
            )
            logo_label = ctk.CTkLabel(
                inner_frame,
                image=logo_image,
                text=""
            )
            logo_label.pack(pady=(0, 15))
        
        # Title
        # title_label = ctk.CTkLabel(
        #     inner_frame,
        #     text="STG Live Messenger",
        #     font=ctk.CTkFont(size=24, weight="bold")
        # )
        # title_label.pack(pady=(0, 30))
        
        # Username field
        username_label = ctk.CTkLabel(
            inner_frame,
            text="Username",
            font=ctk.CTkFont(size=12)
        )
        username_label.pack(anchor="w", pady=(0, 5))
        
        username_entry = ctk.CTkEntry(
            inner_frame,
            textvariable=self.username_var,
            width=290,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        username_entry.pack(pady=(0, 15))
        
        # Password field
        password_label = ctk.CTkLabel(
            inner_frame,
            text="Password",
            font=ctk.CTkFont(size=12)
        )
        password_label.pack(anchor="w", pady=(0, 5))
        
        password_entry = ctk.CTkEntry(
            inner_frame,
            textvariable=self.password_var,
            width=290,
            height=40,
            show="*",
            font=ctk.CTkFont(size=14)
        )
        password_entry.pack(pady=(0, 20))
        
        # Login button
        self.login_button = ctk.CTkButton(
            inner_frame,
            text="Login",
            width=290,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_login_click
        )
        self.login_button.pack(pady=(0, 10))
        
        # Register button
        self.register_button = ctk.CTkButton(
            inner_frame,
            text="Register",
            width=290,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            command=self.on_register_click
        )
        self.register_button.pack(pady=(0, 10))
        
        # File dialog button (hidden initially)
        self.file_button = ctk.CTkButton(
            inner_frame,
            text="Select Profile Picture",
            width=290,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            command=self.on_file_select,
            state="disabled"
        )
        self.file_button.pack(pady=(0, 10))
        self.file_button.pack_forget()  # Hide initially
        
        # Login success message (initially hidden)
        self.login_success_label = ctk.CTkLabel(
            inner_frame,
            text="Login successful",
            font=ctk.CTkFont(size=12),
            text_color="#00ff00"  # Green color
        )
        # Don't pack initially, will be shown on successful login
        
        # Store references for later use
        self.username_entry = username_entry
        self.password_entry = password_entry
    
    def setup_right_containers(self, parent):
        """Setup the right containers for server status and logs"""
        right_frame = ctk.CTkFrame(parent, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=0)
        
        # Server Status container (top)
        self.setup_server_status_container(right_frame)
        
        # Logs container (bottom)
        self.setup_logs_container(right_frame)
    
    def setup_server_status_container(self, parent):
        """Setup the server status container with a list"""
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Header frame with title, refresh button, and connection status
        header_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Title
        status_title = ctk.CTkLabel(
            header_frame,
            text="Server Status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        status_title.pack(side="left", anchor="w")
        
        # Connection status indicator (green tick)
        self.connection_status_label = ctk.CTkLabel(
            header_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray"  # Gray when not connected
        )
        self.connection_status_label.pack(side="right", padx=(10, 0))
        
        # Refresh button
        refresh_button = ctk.CTkButton(
            header_frame,
            text="Refresh",
            width=80,
            height=30,
            font=ctk.CTkFont(size=12),
            command=self.discover_servers
        )
        refresh_button.pack(side="right", padx=(10, 0))
        
        # Scrollable frame for server list
        scrollable_frame = ctk.CTkScrollableFrame(
            status_frame,
            fg_color="transparent"
        )
        scrollable_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Store reference for updating server list later
        self.server_list_frame = scrollable_frame
        
        # Placeholder text
        placeholder_label = ctk.CTkLabel(
            scrollable_frame,
            text="No servers found on LAN",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        placeholder_label.pack(pady=10)
        self.server_placeholder = placeholder_label
    
    def setup_logs_container(self, parent):
        """Setup the logs container"""
        logs_frame = ctk.CTkFrame(parent)
        logs_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Title
        logs_title = ctk.CTkLabel(
            logs_frame,
            text="Logs",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        logs_title.pack(pady=(15, 10), padx=15, anchor="w")
        
        # Text widget for logs (read-only)
        self.logs_text = ctk.CTkTextbox(
            logs_frame,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.logs_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Add initial log message
        self.add_log("Client started. Ready to connect.")
    
    def discover_servers(self):
        """Discover servers in a background thread to avoid blocking UI."""
        def discover():
            self.add_log("Discovering servers on LAN...")
            servers = self.client.discover_servers(timeout=5)
            # Store discovered servers
            self.discovered_servers = servers
            # Update UI from main thread
            self.root.after(0, lambda: self.update_server_list(servers))
            if servers:
                self.root.after(0, lambda: self.add_log(f"Found {len(servers)} server(s)"))
                self.root.after(0, lambda: self.update_connection_status(True))
            else:
                self.root.after(0, lambda: self.add_log("No servers found on LAN"))
                self.root.after(0, lambda: self.update_connection_status(False))
        
        # Start discovery in background thread
        thread = threading.Thread(target=discover, daemon=True)
        thread.start()
    
    def add_log(self, message):
        """Add a log message to the logs container"""
        self.logs_text.configure(state="normal")
        self.logs_text.insert("end", f"{message}\n")
        self.logs_text.see("end")
        self.logs_text.configure(state="disabled")
    
    def update_server_list(self, servers):
        """Update the server list in the server status container
        
        Args:
            servers: List of server dictionaries with keys like 'name', 'address', 'port', etc.
        """
        # Clear existing items
        for widget in self.server_list_frame.winfo_children():
            widget.destroy()
        
        if not servers:
            # Show placeholder if no servers
            placeholder_label = ctk.CTkLabel(
                self.server_list_frame,
                text="No servers found on LAN",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            placeholder_label.pack(pady=10)
            self.server_placeholder = placeholder_label
        else:
            # Display each server
            for server in servers:
                server_item = ctk.CTkFrame(self.server_list_frame, fg_color="transparent")
                server_item.pack(fill="x", pady=5, padx=5)
                
                # Server name/ID
                name_label = ctk.CTkLabel(
                    server_item,
                    text=server.get('name', 'Unknown'),
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w"
                )
                name_label.pack(anchor="w", pady=(0, 2))
                
                # Server address and port
                address_text = f"{server.get('address', 'N/A')}:{server.get('port', 'N/A')}"
                address_label = ctk.CTkLabel(
                    server_item,
                    text=address_text,
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                    anchor="w"
                )
                address_label.pack(anchor="w")
            self.update_connection_status(True)
    
    def update_connection_status(self, connected):
        """Update the connection status indicator.
        
        Args:
            connected: Boolean indicating if connected to server
        """
        self.connected_to_server = connected
        if connected:
            self.connection_status_label.configure(text="✓", text_color="#00ff00")  # Green tick
        else:
            self.connection_status_label.configure(text="●", text_color="gray")  # Gray dot
    
    def on_login_click(self):
        """Handle login button click"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        # Validate inputs
        if not username:
            self.add_log("Error: Username cannot be empty")
            return
        
        if not password:
            self.add_log("Error: Password cannot be empty")
            return
        
        # Check if server is available
        if not self.discovered_servers:
            self.add_log("Error: No servers found. Please wait for server discovery.")
            return
        
        # Hide success message if visible
        if self.login_success_label.winfo_viewable():
            self.login_success_label.pack_forget()
        
        # Use first server for now
        server = self.discovered_servers[0]
        server_address = server.get('address')
        
        if not server_address:
            self.add_log("Error: Invalid server address")
            return
        
        # Login in background thread to avoid blocking UI
        def login():
            self.root.after(0, lambda: self.add_log(f"Connecting to server {server_address}..."))
            
            # Connect to server
            if not self.client.connect_to_server(server_address):
                self.root.after(0, lambda: self.add_log("Error: Failed to connect to server"))
                self.root.after(0, lambda: self.update_connection_status(False))
                return
            
            self.root.after(0, lambda: self.update_connection_status(True))
            self.root.after(0, lambda: self.add_log(f"Logging in as {username}..."))
            
            # Send login request
            response = self.client.login(username, password)
            
            # Handle response
            if response.get("status") == "success":
                self.root.after(0, lambda: self.add_log(f"Login successful for {username}"))
                # Show green success message
                self.root.after(0, lambda: self.login_success_label.pack(pady=(10, 0)))
                # After short delay, show mailbox UI and auto-fetch once
                def _show_mailbox_and_fetch():
                    self.show_mailbox_ui()
                    # connect, fetch, disconnect
                    if self.client.connect_to_server(server_address):
                        self.update_connection_status(True)
                        resp = self.client.fetch_messages()
                        self.update_connection_status(False)
                        self.client.disconnect()
                        if resp.get("status") == "success":
                            self.update_messages_table(resp.get("messages", []))
                        else:
                            self.add_log(f"Fetch error: {resp.get('message')}")
                self.root.after(1200, _show_mailbox_and_fetch)
            else:
                error_msg = response.get("message", "Unknown error")
                self.root.after(0, lambda: self.add_log(f"Login failed: {error_msg}"))
                # Hide success message if visible
                if self.login_success_label.winfo_viewable():
                    self.root.after(0, lambda: self.login_success_label.pack_forget())
        
        # Start login in background thread
        thread = threading.Thread(target=login, daemon=True)
        thread.start()

    def show_mailbox_ui(self):
        """Replace left container with mailbox view."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        container = ctk.CTkFrame(self.main_frame)
        container.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=0)
        container.pack_propagate(False)

        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=30, pady=30)

        header = ctk.CTkLabel(inner, text="Mailbox", font=ctk.CTkFont(size=18, weight="bold"))
        header.pack(anchor="w", pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))

        refresh_btn = ctk.CTkButton(btn_frame, text="Refresh", width=100, command=self.on_refresh_click)
        refresh_btn.pack(side="left")

        send_btn = ctk.CTkButton(btn_frame, text="Send", width=100, command=self.on_send_click)
        send_btn.pack(side="left", padx=(10, 0))

        # Messages table-like view (two columns)
        self.messages_list = ctk.CTkTextbox(inner, height=360)
        self.messages_list.pack(fill="both", expand=True)

        # Keep right containers (server status + logs)
        self.setup_right_containers(self.main_frame)

    def update_messages_table(self, messages):
        """Render messages in the textbox with from, title, and body."""
        self.messages_list.configure(state="normal")
        self.messages_list.delete("1.0", "end")
        for m in messages:
            frm = m.get("from", "?")
            title = m.get("title", "")
            body = m.get("body", "")
            
            # Display with title if present
            if title:
                self.messages_list.insert("end", f"From: {frm}\nTitle: {title}\n{body}\n\n")
            else:
                self.messages_list.insert("end", f"From: {frm}\n{body}\n\n")
        self.messages_list.configure(state="disabled")

    def on_refresh_click(self):
        # Use first discovered server
        if not self.discovered_servers:
            self.add_log("No servers to refresh from")
            return
        server_address = self.discovered_servers[0].get('address')
        def do_refresh():
            if self.client.connect_to_server(server_address):
                self.root.after(0, lambda: self.update_connection_status(True))
                resp = self.client.fetch_messages()
                self.client.disconnect()
                self.root.after(0, lambda: self.update_connection_status(False))
                if resp.get("status") == "success":
                    self.root.after(0, lambda: self.update_messages_table(resp.get("messages", [])))
                else:
                    self.root.after(0, lambda: self.add_log(f"Refresh error: {resp.get('message')}"))
        threading.Thread(target=do_refresh, daemon=True).start()

    def on_send_click(self):
        if not self.discovered_servers:
            self.add_log("No servers available")
            return
            
        server_address = self.discovered_servers[0].get('address')
        self.add_log("Fetching user list...")
        
        def fetch_users():
            users = []
            if self.client.connect_to_server(server_address):
                users = self.client.get_users()
                self.client.disconnect()
            
            # Filter current user
            current = self.username_var.get()
            users = [u for u in users if u != current]
            
            self.root.after(0, lambda: self._show_send_dialog(users))
            
        threading.Thread(target=fetch_users, daemon=True).start()

    def _show_send_dialog(self, users):
        if not users:
            self.add_log("No other users found to message")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Send Message")
        dialog.geometry("400x350")
        
        # Lift window and set focus
        dialog.lift()
        dialog.focus_force()
        
        # Wait for window to be visible before grabbing
        dialog.after(100, dialog.grab_set)
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="To:").pack(anchor="w")
        
        to_var = ctk.StringVar(value=users[0] if users else "")
        to_menu = ctk.CTkOptionMenu(frame, variable=to_var, values=users)
        to_menu.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(frame, text="Title:").pack(anchor="w")
        title_entry = ctk.CTkEntry(frame)
        title_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(frame, text="Message:").pack(anchor="w")
        body_text = ctk.CTkTextbox(frame, height=80)
        body_text.pack(fill="both")

        def do_send():
            to_user = to_var.get()
            title = title_entry.get().strip()
            body = body_text.get("1.0", "end").strip()
            if not to_user or not body:
                self.add_log("Provide recipient and message body")
                return
            
            if not self.discovered_servers:
                self.add_log("No server available")
                return
                
            server_address = self.discovered_servers[0].get('address')
            
            def send_bg():
                if self.client.connect_to_server(server_address):
                    self.root.after(0, lambda: self.update_connection_status(True))
                    resp = self.client.send_message(to_user, body, title)
                    self.client.disconnect()
                    self.root.after(0, lambda: self.update_connection_status(False))
                    
                    if resp.get("status") == "success":
                        self.root.after(0, lambda: self.add_log("Message sent"))
                        self.root.after(0, dialog.destroy)
                    else:
                        self.root.after(0, lambda: self.add_log(f"Send error: {resp.get('message')}"))
            
            threading.Thread(target=send_bg, daemon=True).start()

        send_btn = ctk.CTkButton(frame, text="Send", command=do_send)
        send_btn.pack(pady=(10,0))
    
    def on_register_click(self):
        """Handle register button click"""
        if not self.register_mode:
            # Switch to register mode
            self.register_mode = True
            self.login_button.configure(text="Register", command=self.on_register_submit)
            self.register_button.configure(text="Cancel", command=self.on_register_cancel)
            
            # Show file dialog button
            self.file_button.pack(pady=(0, 10))
            self.file_button.configure(state="normal")
            self.add_log("Registration mode activated")
        else:
            # Already in register mode, submit registration
            self.on_register_submit()
    
    def on_register_submit(self):
        """Handle register submission"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        # Validate inputs
        if not username:
            self.add_log("Error: Username cannot be empty")
            return
        
        if not password:
            self.add_log("Error: Password cannot be empty")
            return
        
        if not self.selected_image_path:
            self.add_log("Error: Please select a profile picture")
            return
        
        # Check if server is available
        if not self.discovered_servers:
            self.add_log("Error: No servers found. Please wait for server discovery.")
            return
        
        # Use first server for now
        server = self.discovered_servers[0]
        server_address = server.get('address')
        
        if not server_address:
            self.add_log("Error: Invalid server address")
            return
        
        # Register in background thread to avoid blocking UI
        def register():
            self.root.after(0, lambda: self.add_log(f"Connecting to server {server_address}..."))
            
            # Connect to server
            if not self.client.connect_to_server(server_address):
                self.root.after(0, lambda: self.add_log("Error: Failed to connect to server"))
                self.root.after(0, lambda: self.update_connection_status(False))
                return
            
            self.root.after(0, lambda: self.update_connection_status(True))
            self.root.after(0, lambda: self.add_log(f"Registering user {username}..."))
            
            # Send registration request
            response = self.client.register(username, password, self.selected_image_path)
            
            # Disconnect
            self.client.disconnect()
            self.root.after(0, lambda: self.update_connection_status(False))
            
            # Handle response
            if response.get("status") == "success":
                self.root.after(0, lambda: self.add_log(f"Registration successful for {username}"))
                
                # Show comparison window if paths are returned
                source_path = response.get("source_path")
                encoded_path = response.get("encoded_path")
                if source_path and encoded_path:
                     self.root.after(0, lambda: self.show_comparison_window(source_path, encoded_path))
                
                # Reset form
                self.root.after(0, self.on_register_cancel)
            else:
                error_msg = response.get("message", "Unknown error")
                self.root.after(0, lambda: self.add_log(f"Registration failed: {error_msg}"))
        
        # Start registration in background thread
        thread = threading.Thread(target=register, daemon=True)
        thread.start()
    
    def on_register_cancel(self):
        """Cancel registration and return to login mode"""
        self.register_mode = False
        self.login_button.configure(text="Login", command=self.on_login_click)
        self.register_button.configure(text="Register", command=self.on_register_click)
        
        # Hide file dialog button
        self.file_button.pack_forget()
        self.selected_image_path = None
        # self.add_log("Registration cancelled")
    
    def on_file_select(self):
        """Open file dialog for image selection"""
        file_path = filedialog.askopenfilename(
            title="Select Profile Picture",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_image_path = file_path
            # Update button text to show selected file
            file_name = Path(file_path).name
            if len(file_name) > 25:
                file_name = file_name[:22] + "..."
            self.file_button.configure(text=f"Selected: {file_name}")
            self.add_log(f"Profile picture selected: {file_name}")
            print(f"Selected image: {file_path}")
    
    def show_comparison_window(self, source_path, encoded_path):
        """Show window comparing original and encoded images with their hashes."""
        window = ctk.CTkToplevel(self.root)
        window.title("Steganography Result")
        window.geometry("800x600")
        
        # Make modal
        window.transient(self.root)
        window.lift()
        
        # Calculate hashes
        def get_file_hash(path):
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    sha256.update(data)
            return sha256.hexdigest()

        source_hash = get_file_hash(source_path)
        encoded_hash = get_file_hash(encoded_path)
        
        # Container
        container = ctk.CTkFrame(window)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Helper to create image frame
        def create_image_panel(parent, path, hash_val, title):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(side="left", fill="both", expand=True, padx=10)
            
            ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))
            
            # Load and resize image
            pil_img = Image.open(path)
            # Calculate resize keeping aspect ratio
            max_size = (350, 350)
            pil_img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            
            img_label = ctk.CTkLabel(frame, image=ctk_img, text="")
            img_label.pack(pady=10)
            
            # Hash label
            ctk.CTkLabel(frame, text="SHA-256 Hash:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
            
            # Textbox for hash (easier to copy/read)
            hash_box = ctk.CTkTextbox(frame, height=60, width=300)
            hash_box.pack(pady=5)
            hash_box.insert("1.0", hash_val)
            hash_box.configure(state="disabled")

        create_image_panel(container, source_path, source_hash, "Original Image")
        create_image_panel(container, encoded_path, encoded_hash, "Encoded Image")

        # Cleanup files when window closes
        def on_close():
            try:
                if os.path.exists(source_path): os.remove(source_path)
                if os.path.exists(encoded_path): os.remove(encoded_path)
            except:
                pass
            window.destroy()
            
        window.protocol("WM_DELETE_WINDOW", on_close)

    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def start_client_gui():
    """Start the client GUI application"""
    app = LoginScreen()
    app.run()

