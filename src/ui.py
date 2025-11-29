import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path


class LoginScreen:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Encrypted Mail - Login")
        self.root.geometry("400x500")
        
        # Center the window
        self.center_window()
        
        # Variables
        self.username_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.register_mode = False
        self.selected_image_path = None
        
        self.setup_ui()
    
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the login/register UI"""
        # Main container with padding
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Encrypted Mail",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(0, 30))
        
        # Username field
        username_label = ctk.CTkLabel(
            main_frame,
            text="Username",
            font=ctk.CTkFont(size=12)
        )
        username_label.pack(anchor="w", pady=(0, 5))
        
        username_entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.username_var,
            width=320,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        username_entry.pack(pady=(0, 15))
        
        # Password field
        password_label = ctk.CTkLabel(
            main_frame,
            text="Password",
            font=ctk.CTkFont(size=12)
        )
        password_label.pack(anchor="w", pady=(0, 5))
        
        password_entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.password_var,
            width=320,
            height=40,
            show="*",
            font=ctk.CTkFont(size=14)
        )
        password_entry.pack(pady=(0, 20))
        
        # Login button
        self.login_button = ctk.CTkButton(
            main_frame,
            text="Login",
            width=320,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_login_click
        )
        self.login_button.pack(pady=(0, 10))
        
        # Register button
        self.register_button = ctk.CTkButton(
            main_frame,
            text="Register",
            width=320,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            command=self.on_register_click
        )
        self.register_button.pack(pady=(0, 10))
        
        # File dialog button (hidden initially)
        self.file_button = ctk.CTkButton(
            main_frame,
            text="Select Profile Picture",
            width=320,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            command=self.on_file_select,
            state="disabled"
        )
        self.file_button.pack(pady=(0, 10))
        self.file_button.pack_forget()  # Hide initially
        
        # Store references for later use
        self.username_entry = username_entry
        self.password_entry = password_entry
    
    def on_login_click(self):
        """Handle login button click"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        # TODO: Implement login functionality
        print(f"Login attempt: {username}")
    
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
        else:
            # Already in register mode, submit registration
            self.on_register_submit()
    
    def on_register_submit(self):
        """Handle register submission"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        # TODO: Implement registration functionality
        print(f"Register attempt: {username}, Image: {self.selected_image_path}")
    
    def on_register_cancel(self):
        """Cancel registration and return to login mode"""
        self.register_mode = False
        self.login_button.configure(text="Login", command=self.on_login_click)
        self.register_button.configure(text="Register", command=self.on_register_click)
        
        # Hide file dialog button
        self.file_button.pack_forget()
        self.selected_image_path = None
    
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
            print(f"Selected image: {file_path}")
    
    def run(self):
        """Start the GUI main loop"""
        self.root.mainloop()


def start_client_gui():
    """Start the client GUI application"""
    app = LoginScreen()
    app.run()

