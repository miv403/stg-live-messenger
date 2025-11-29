import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from PIL import Image
import os
import threading
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
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left container - Login/Register
        self.setup_login_container(main_frame)
        
        # Right container - Server Status and Logs
        self.setup_right_containers(main_frame)
    
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
        
        # Title
        status_title = ctk.CTkLabel(
            status_frame,
            text="Server Status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        status_title.pack(pady=(15, 10), padx=15, anchor="w")
        
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
            else:
                self.root.after(0, lambda: self.add_log("No servers found on LAN"))
        
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
                return
            
            self.root.after(0, lambda: self.add_log(f"Logging in as {username}..."))
            
            # Send login request
            response = self.client.login(username, password)
            
            # Disconnect
            self.client.disconnect()
            
            # Handle response
            if response.get("status") == "success":
                self.root.after(0, lambda: self.add_log(f"Login successful for {username}"))
                # Show green success message
                self.root.after(0, lambda: self.login_success_label.pack(pady=(10, 0)))
            else:
                error_msg = response.get("message", "Unknown error")
                self.root.after(0, lambda: self.add_log(f"Login failed: {error_msg}"))
                # Hide success message if visible
                if self.login_success_label.winfo_viewable():
                    self.root.after(0, lambda: self.login_success_label.pack_forget())
        
        # Start login in background thread
        thread = threading.Thread(target=login, daemon=True)
        thread.start()
    
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
                return
            
            self.root.after(0, lambda: self.add_log(f"Registering user {username}..."))
            
            # Send registration request
            response = self.client.register(username, password, self.selected_image_path)
            
            # Disconnect
            self.client.disconnect()
            
            # Handle response
            if response.get("status") == "success":
                self.root.after(0, lambda: self.add_log(f"Registration successful for {username}"))
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
        self.add_log("Registration cancelled")
    
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
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def start_client_gui():
    """Start the client GUI application"""
    app = LoginScreen()
    app.run()

