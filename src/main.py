import customtkinter as ctk
import sys
import threading
import time
import os
from datetime import datetime
from PIL import Image, ImageTk
import send2trash


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("GalleryCleaner")
        self.geometry("920x595")
        
        # Set minimum window size to accommodate the 800x500 green section
        # 800 (green) + 50 (left sidebar) + 50 (right sidebar) + 20 (padding) = 920px width
        # 500 (green) + 75 (bottom section) + 20 (padding) = 595px height
        self.minsize(920, 595)
        
        # Set maximum window width to 1200 pixels
        self.maxsize(1200, 10000)  # 10000 for height allows unlimited vertical expansion
        
        # Set theme and color
        ctk.set_appearance_mode("system")  # Default system theme
        ctk.set_default_color_theme("blue")  # Blue color theme
        
        # Configure window close behavior
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind ESC key to cancel focus
        self.bind("<Escape>", self.cancel_focus)
        
        # Bind keyboard shortcuts for navigation and deletion
        self.bind("<Key-d>", self.on_key_right_arrow)
        self.bind("<Key-D>", self.on_key_right_arrow)
        self.bind("<Right>", self.on_key_right_arrow)
        
        self.bind("<Key-a>", self.on_key_left_arrow)
        self.bind("<Key-A>", self.on_key_left_arrow)
        self.bind("<Left>", self.on_key_left_arrow)
        
        self.bind("<Key-s>", self.on_key_delete)
        self.bind("<Key-S>", self.on_key_delete)
        self.bind("<Down>", self.on_key_delete)
        
        # Bind Ctrl+R for refresh
        self.bind("<Control-r>", self.on_key_refresh)
        self.bind("<Control-R>", self.on_key_refresh)
        
        # Bind Ctrl+Q for rotate left and Ctrl+E for rotate right
        self.bind("<Control-q>", self.on_key_rotate_left)
        self.bind("<Control-Q>", self.on_key_rotate_left)
        self.bind("<Control-e>", self.on_key_rotate_right)
        self.bind("<Control-E>", self.on_key_rotate_right)
        
        # Bind Escape or Ctrl+B for back functionality
        self.bind("<Escape>", self.on_key_back)
        self.bind("<Control-b>", self.on_key_back)
        self.bind("<Control-B>", self.on_key_back)
        
        # Make sure the window can receive focus for key events
        self.focus_set()
        
        # Configure grid layout (optional, for future use)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create display layers
        self.create_layers()
        
        # Initialize current image index
        self.current_image_index = 0
        
        # Initialize image cache for preloading
        self.image_cache = {}
        
        # Initialize rotation tracking
        self.current_rotation = 0  # 0, 90, 180, 270 degrees
        
        # Show the initial layer
        self.show_layer1()

    # UI Setup Methods
    def create_layers(self):
        """Create the two display layers as frames."""
        # Layer 1: Initial layer with input box and button
        self.layer1 = ctk.CTkFrame(self)
        self.layer1.grid(row=0, column=0, sticky="nsew")
        self.layer1.grid_columnconfigure(0, weight=1)
        self.layer1.grid_rowconfigure(0, weight=1)
        self.layer1.grid_rowconfigure(1, weight=0)
        self.layer1.grid_rowconfigure(2, weight=0)
        self.layer1.grid_rowconfigure(3, weight=0)
        self.layer1.grid_rowconfigure(4, weight=0)
        self.layer1.grid_rowconfigure(5, weight=1)
        
        # Input box in the middle
        self.input_box = ctk.CTkEntry(
            self.layer1,
            placeholder_text="Enter directory path...",
            width=300,
            height=40
        )
        self.input_box.grid(row=1, column=0, pady=(10, 10), sticky="")
        
        # Bind Enter key to the input box to trigger submit
        self.input_box.bind("<Return>", lambda event: self.handle_submit())
        
        # Checkbox and label frame
        self.checkbox_frame = ctk.CTkFrame(self.layer1, fg_color="transparent")
        self.checkbox_frame.grid(row=2, column=0, pady=(10, 10), sticky="")
        self.checkbox_frame.configure(width=300)
        
        # Recursive checkbox
        self.recursive_checkbox = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Operate Recursively  ",
            height=20,
            text_color=("gray10", "gray90"),
            checkbox_width=18,
            checkbox_height=18,
            border_width=2,
            text_color_disabled=("gray40", "gray60")
        )
        self.recursive_checkbox.pack(anchor="center")
        
        # Error message label below the checkbox
        self.error_label = ctk.CTkLabel(
            self.layer1,
            text="",
            text_color="red",
            width=300,
            height=20
        )
        self.error_label.grid(row=3, column=0, pady=(10, 10), sticky="")
        
        # Button below the error label
        self.main_button = self.create_button(
            self.layer1,
            text="Submit",
            command=self.handle_submit,
            width=300,
            height=40
        )
        self.main_button.grid(row=4, column=0, pady=(10, 10), sticky="")
        
        # Layer 2: Second layer with 4 sections
        self.layer2 = ctk.CTkFrame(self)
        self.layer2.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid layout for 3 columns and 2 rows
        self.layer2.grid_columnconfigure(0, weight=0, minsize=50)  # Left sidebar - fixed 50px
        self.layer2.grid_columnconfigure(1, weight=1)  # Middle section (expandable)
        self.layer2.grid_columnconfigure(2, weight=0, minsize=50)  # Right sidebar - fixed 50px
        self.layer2.grid_rowconfigure(0, weight=1)  # Top row (expandable)
        self.layer2.grid_rowconfigure(1, weight=0, minsize=75)  # Bottom row - fixed 75px
        
        # Left sidebar (spans both rows) - fixed 50px width
        self.left_sidebar = ctk.CTkFrame(self.layer2, width=50)
        self.left_sidebar.grid(row=0, column=0, rowspan=2, sticky="ns", padx=5, pady=5)
        self.left_sidebar.grid_propagate(False)  # Prevent resizing
        
        # Configure left sidebar grid for centering
        self.left_sidebar.grid_columnconfigure(0, weight=1)
        self.left_sidebar.grid_rowconfigure(0, weight=1)
        
        # Load left arrow icon
        try:
            left_arrow_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/arrow-92-64.ico"),
                dark_image=Image.open("resources/images/arrow-92-64.ico"),
                size=(24, 24)
            )
        except Exception:
            left_arrow_icon = None
        
        # Left sidebar button (centered)
        self.left_button = self.create_button(
            self.left_sidebar,
            text="◀" if left_arrow_icon is None else "",
            image=left_arrow_icon,
            command=self.on_left_arrow_click,
            width=40,
            height=40
        )
        self.left_button.grid(row=0, column=0, sticky="")
        
        # Right sidebar (spans both rows) - fixed 50px width
        self.right_sidebar = ctk.CTkFrame(self.layer2, width=50)
        self.right_sidebar.grid(row=0, column=2, rowspan=2, sticky="ns", padx=5, pady=5)
        self.right_sidebar.grid_propagate(False)  # Prevent resizing
        
        # Configure right sidebar grid for centering
        self.right_sidebar.grid_columnconfigure(0, weight=1)
        self.right_sidebar.grid_rowconfigure(0, weight=1)
        
        # Load right arrow icon
        try:
            right_arrow_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/arrow-28-64.ico"),
                dark_image=Image.open("resources/images/arrow-28-64.ico"),
                size=(24, 24)
            )
        except Exception:
            right_arrow_icon = None
        
        # Right sidebar button (centered)
        self.right_button = self.create_button(
            self.right_sidebar,
            text="▶" if right_arrow_icon is None else "",
            image=right_arrow_icon,
            command=self.on_right_arrow_click,
            width=40,
            height=40
        )
        self.right_button.grid(row=0, column=0, sticky="")
        
        # Top middle section - green display area with minimum size
        self.green_section = ctk.CTkFrame(self.layer2, width=800, height=500)
        self.green_section.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.green_section.grid_propagate(False)  # Prevent resizing
        
        # Configure green section grid for centering image and labels
        self.green_section.grid_columnconfigure(0, weight=1)
        self.green_section.grid_rowconfigure(0, weight=1)  # Image display area
        self.green_section.grid_rowconfigure(1, weight=0)  # Combined index and progress bar area
        self.green_section.grid_rowconfigure(2, weight=0)  # Combined name and details area
        
        # Add image display label in the green section
        self.image_label = ctk.CTkLabel(
            self.green_section,
            text="No image selected",
            font=("Arial", 16),
            text_color="white"
        )
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        
        # Add combined frame for image index and progress bar
        self.index_progress_frame = ctk.CTkFrame(self.green_section, fg_color="transparent")
        self.index_progress_frame.grid(row=1, column=0, sticky="", padx=10, pady=(0, 8))
        self.index_progress_frame.grid_columnconfigure(0, weight=0)  # Image index label
        self.index_progress_frame.grid_columnconfigure(1, weight=0)  # Spacer
        self.index_progress_frame.grid_columnconfigure(2, weight=1)  # Progress bar
        self.index_progress_frame.grid_columnconfigure(3, weight=0)  # Percentage label
        
        # Add image index label
        self.image_index_label = ctk.CTkLabel(
            self.index_progress_frame,
            text="",
            font=("Arial", 12, "bold"),
            text_color="lightgray",
            anchor="center"
        )
        self.image_index_label.grid(row=0, column=0, sticky="", padx=(0, 15))
        
        # Add progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.index_progress_frame,
            width=200,
            height=10,
            progress_color=("#3B8ED0", "#1F6AA5")
        )
        self.progress_bar.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.progress_bar.set(0)  # Initial value
        
        # Add percentage label
        self.progress_label = ctk.CTkLabel(
            self.index_progress_frame,
            text="0%",
            font=("Arial", 10, "bold"),
            text_color="lightgray",
            width=35
        )
        self.progress_label.grid(row=0, column=3, sticky="e")
        
        # Add combined frame for file information (name and details)
        self.info_frame = ctk.CTkFrame(self.green_section, fg_color="transparent")
        self.info_frame.grid(row=2, column=0, sticky="", padx=20, pady=(5, 10))
        self.info_frame.grid_columnconfigure(0, weight=1)  # Center the content
        
        # Add combined file information label (name and details together)
        self.image_details_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=("Arial", 11),
            text_color="lightgray",
            anchor="center"
        )
        self.image_details_label.grid(row=0, column=0, sticky="ew")
        
        # Bottom middle section - fixed 75px height
        self.bottom_middle = ctk.CTkFrame(self.layer2, height=75)
        self.bottom_middle.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.bottom_middle.grid_propagate(False)  # Prevent resizing
        
        # Configure bottom middle grid for centering 5 buttons horizontally
        self.bottom_middle.grid_columnconfigure(0, weight=1)
        self.bottom_middle.grid_columnconfigure(1, weight=0)  # Back button
        self.bottom_middle.grid_columnconfigure(2, weight=0)  # Delete button
        self.bottom_middle.grid_columnconfigure(3, weight=0)  # Rotate left button
        self.bottom_middle.grid_columnconfigure(4, weight=0)  # Rotate right button
        self.bottom_middle.grid_columnconfigure(5, weight=0)  # Refresh button
        self.bottom_middle.grid_columnconfigure(6, weight=1)
        self.bottom_middle.grid_rowconfigure(0, weight=1)
        
        # Add back button
        try:
            back_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/stop-64.ico"),
                dark_image=Image.open("resources/images/stop-64.ico"),
                size=(20, 20)
            )
        except Exception:
            back_icon = None
        
        self.back_button = self.create_button(
            self.bottom_middle,
            text="BACK" if back_icon is None else "",
            image=back_icon,
            command=self.on_back_click,
            width=80,
            height=30
        )
        self.back_button.grid(row=0, column=1, padx=5, sticky="")

        # Add delete button centered in the bottom section
        # Load icon images
        try:
            trash_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/trash-10-64.ico"),
                dark_image=Image.open("resources/images/trash-10-64.ico"),
                size=(20, 20)
            )
        except Exception:
            trash_icon = None
        
        try:
            rotate_left_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/rotate-64.ico"),
                dark_image=Image.open("resources/images/rotate-64.ico"),
                size=(20, 20)
            )
        except Exception:
            rotate_left_icon = None
        
        try:
            # Mirror the rotate icon for right rotation
            rotate_icon_image = Image.open("resources/images/rotate-64.ico")
            rotate_right_icon = ctk.CTkImage(
                light_image=rotate_icon_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                dark_image=rotate_icon_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                size=(20, 20)
            )
        except Exception:
            rotate_right_icon = None
        
        try:
            refresh_icon = ctk.CTkImage(
                light_image=Image.open("resources/images/sinchronize-64.ico"),
                dark_image=Image.open("resources/images/sinchronize-64.ico"),
                size=(20, 20)
            )
        except Exception:
            refresh_icon = None
        
        self.bottom_button1 = self.create_button(
            self.bottom_middle,
            text="🗑️" if trash_icon is None else "",
            image=trash_icon,
            command=self.on_delete_click,
            fg_color="red",
            hover_color="darkred",
            width=80,
            height=30
        )
        self.bottom_button1.grid(row=0, column=2, padx=5, sticky="")
        
        # Add rotate left button
        self.rotate_left_button = self.create_button(
            self.bottom_middle,
            text="↶" if rotate_left_icon is None else "",
            image=rotate_left_icon,
            command=self.on_rotate_left_click,
            width=80,
            height=30
        )
        self.rotate_left_button.grid(row=0, column=3, padx=5, sticky="")
        
        # Add rotate right button
        self.rotate_right_button = self.create_button(
            self.bottom_middle,
            text="↷" if rotate_right_icon is None else "",
            image=rotate_right_icon,
            command=self.on_rotate_right_click,
            width=80,
            height=30
        )
        self.rotate_right_button.grid(row=0, column=4, padx=5, sticky="")
        
        # Add refresh button
        self.bottom_button2 = self.create_button(
            self.bottom_middle,
            text="🔄" if refresh_icon is None else "",
            image=refresh_icon,
            command=self.on_refresh_click,
            width=80,
            height=30
        )
        self.bottom_button2.grid(row=0, column=5, padx=5, sticky="")
        
        # Hide layer 2 initially
        self.layer2.grid_remove()
    
    def create_button(self, parent, text, command=None, **kwargs):
        """Method for creating buttons with consistent styling"""
        return ctk.CTkButton(parent, text=text, command=command, **kwargs)
    
    def show_layer1(self):
        """Show layer 1 and hide layer 2"""
        self.layer2.grid_remove()
        self.layer1.grid(row=0, column=0, sticky="nsew")
    
    def show_layer2(self):
        """Show layer 2 and hide layer 1"""
        self.layer1.grid_remove()
        self.layer2.grid(row=0, column=0, sticky="nsew")

    # Event Handlers
    def handle_submit(self):
        """Handle the submit button click - validate directory and switch layers"""
        # Get the directory path from the input box
        directory_path = self.input_box.get().strip()
        
        # Check if input is empty
        if not directory_path:
            self.display_error(self.error_label, "Please enter a directory path")
            return
        
        # Check if directory exists
        if not os.path.exists(directory_path):
            self.display_error(self.error_label, "Directory does not exist")
            return
        
        # Check if path is actually a directory
        if not os.path.isdir(directory_path):
            self.display_error(self.error_label, "Path is not a directory")
            return
        
        # Check read, write, and execute permissions
        if not os.access(directory_path, os.R_OK):
            self.display_error(self.error_label, "Cannot read from directory")
            return
        
        if not os.access(directory_path, os.W_OK):
            self.display_error(self.error_label, "Cannot write to directory")
            return
        
        if not os.access(directory_path, os.X_OK):
            self.display_error(self.error_label, "Cannot execute in directory")
            return
        
        # Try to list files in the directory
        try:
            # Check if recursive operation is enabled
            is_recursive = self.recursive_checkbox.get()
            
            # Get files using the dedicated function
            images = self.list_images(directory_path, is_recursive)
            
            # Check if the files list is empty
            if not images:
                self.display_error(self.error_label, "The directory has no images. Activate the Recursive Option if the images are in sub-directories")
                return
            
            self.directory_images = images
            self.current_directory = directory_path
            self.current_image_index = 0
            self.current_image_path = images[0] if images else None
            
            # Clear the image cache when loading a new directory
            self.clear_container_completely()
            self.image_cache.clear()
            
            # If all checks pass, switch to second layer
            self.show_layer2()
            
            # Load and display the first image file
            self.load_first_image_file()
            
        except PermissionError:
            self.display_error(self.error_label, "Permission denied accessing directory")
        except Exception as e:
            self.display_error(self.error_label, f"Error accessing directory: {str(e)}")

    def on_left_arrow_click(self):
        """Handle left arrow button click - navigate to previous image"""
        if hasattr(self, 'directory_images') and self.directory_images and hasattr(self, 'current_image_path'):
            if self.current_image_index > 0:
                # Clear container before switching
                self.clear_container_completely()
                self.current_image_index -= 1
                previous_image_path = self.directory_images[self.current_image_index]
                self.display_file(previous_image_path)

    def on_right_arrow_click(self):
        """Handle right arrow button click - navigate to next image"""
        if hasattr(self, 'directory_images') and self.directory_images and hasattr(self, 'current_image_path'):
            if self.current_image_index < len(self.directory_images) - 1:
                # Clear container before switching
                self.clear_container_completely()
                self.current_image_index += 1
                next_image_path = self.directory_images[self.current_image_index]
                self.display_file(next_image_path)

    def on_delete_click(self):
        """Handle delete button click - move current image to trash and navigate to next"""
        if hasattr(self, 'directory_images') and self.directory_images and hasattr(self, 'current_image_path'):
            try:
                # Clear container before deleting
                self.clear_container_completely()
                
                send2trash.send2trash(self.current_image_path)
                self.directory_images.remove(self.current_image_path)
                
                if self.current_image_path in self.image_cache:
                    del self.image_cache[self.current_image_path]
                
                if not self.directory_images:
                    self.input_box.delete(0, 'end')
                    self.display_error(self.error_label, "All images were cleared")
                    self.show_layer1()
                    return
                
                if self.current_image_index >= len(self.directory_images):
                    self.current_image_index = len(self.directory_images) - 1
                
                next_image_path = self.directory_images[self.current_image_index]
                self.display_file(next_image_path)
            except Exception:
                pass

    def on_refresh_click(self):
        """Handle refresh button click - reconstruct the files list and reload the second layer"""
        if hasattr(self, 'current_directory') and self.current_directory:
            try:
                # Clear container before refreshing
                self.clear_container_completely()
                
                self.image_cache.clear()
                is_recursive = self.recursive_checkbox.get()
                images = self.list_images(self.current_directory, is_recursive)
                
                if not images:
                    self.input_box.delete(0, 'end')
                    self.display_error(self.error_label, "No images found after refresh")
                    self.show_layer1()
                    return
                
                current_image_path = getattr(self, 'current_image_path', None)
                self.directory_images = images
                
                new_index = 0
                if current_image_path and current_image_path in images:
                    new_index = images.index(current_image_path)
                
                self.current_image_index = new_index
                self.current_image_path = images[new_index]
                self.display_file(self.current_image_path)
            except Exception:
                pass
    
    def on_rotate_left_click(self):
        """Handle rotate left button click - rotate image 90 degrees counter-clockwise"""
        if hasattr(self, 'current_image_path') and self.current_image_path and self.is_image_file(self.current_image_path):
            self.current_rotation = (self.current_rotation - 90) % 360
            self.display_image(self.current_image_path)

    def on_rotate_right_click(self):
        """Handle rotate right button click - rotate image 90 degrees clockwise"""
        if hasattr(self, 'current_image_path') and self.current_image_path and self.is_image_file(self.current_image_path):
            self.current_rotation = (self.current_rotation + 90) % 360
            self.display_image(self.current_image_path)

    def on_closing(self):
        """Handle window close event - shuts down the entire application"""
        # Clean up all resources before closing
        self.clear_container_completely()
        self.quit()
        self.destroy()
        sys.exit()

    def on_back_click(self):
        """Handle back button click - return to layer 1 and clear input box"""
        # Clear container before going back
        self.clear_container_completely()
        
        self.input_box.delete(0, 'end')
        self.error_label.configure(text="")
        self.show_layer1()
        self.input_box.focus_set()



    # Keyboard Event Handlers
    def cancel_focus(self, event=None):
        """Cancel focus on any focused widget when ESC is pressed"""
        # Only cancel focus if we're on layer 1, otherwise handle back functionality
        if hasattr(self, 'layer1') and self.layer1.winfo_viewable():
            self.focus_set()
        else:
            self.on_key_back(event)
    
    def on_key_right_arrow(self, event=None):
        """Handle D key, right arrow key presses - navigate to next image"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_right_arrow_click()
    
    def on_key_left_arrow(self, event=None):
        """Handle A key, left arrow key presses - navigate to previous image"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_left_arrow_click()
    
    def on_key_delete(self, event=None):
        """Handle S key press - delete current image"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_delete_click()
    
    def on_key_refresh(self, event=None):
        """Handle Ctrl+R key press - refresh current directory"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_refresh_click()

    def on_key_rotate_left(self, event=None):
        """Handle Ctrl+Q key press - rotate left"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_rotate_left_click()

    def on_key_rotate_right(self, event=None):
        """Handle Ctrl+E key press - rotate right"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_rotate_right_click()

    def on_key_back(self, event=None):
        """Handle Escape or Ctrl+B key press - return to layer 1"""
        if hasattr(self, 'layer2') and self.layer2.winfo_viewable():
            self.on_back_click()

    # Display Methods
    def display_file(self, file_path):
        """Display file"""
        # Clear previous content before displaying new file - Enhanced container cleaning
        self.clear_container_completely()
        
        if file_path:
            self.current_image_path = file_path
            
            # Reset rotation when switching to a new file
            self.current_rotation = 0
            
            if hasattr(self, 'directory_images') and self.directory_images:
                try:
                    current_index = self.directory_images.index(file_path)
                    self.current_image_index = current_index
                    total_count = len(self.directory_images)
                    self.image_index_label.configure(text=f"{current_index + 1} of {total_count}")
                    
                    if total_count > 1:
                        progress_percentage = current_index / (total_count - 1)
                        percentage_text = f"{int(progress_percentage * 100)}%"
                    else:
                        progress_percentage = 0
                        percentage_text = "0%"
                    
                    self.progress_bar.set(progress_percentage)
                    self.progress_label.configure(text=percentage_text)
                except ValueError:
                    self.image_index_label.configure(text="")
                    self.progress_bar.set(0)
                    self.progress_label.configure(text="0%")
            else:
                self.image_index_label.configure(text="")
                self.progress_bar.set(0)
                self.progress_label.configure(text="0%")
            
            file_details = self.get_file_details(file_path)
            self.image_details_label.configure(text=file_details)
            
            self.display_image(file_path)
            self.update_navigation_buttons(file_path)
            
            if hasattr(self, 'directory_images') and self.directory_images:
                self.preload_images(self.current_image_index)
        else:
            self.reset_ui_state()
        
    def display_image(self, image_path):
        """Display an image in the section, resized to fit"""
        try:
            # Clear previous content first
            self.clear_container_completely()
            
            # Create cache key that includes rotation
            cache_key = f"{image_path}_rot_{self.current_rotation}"
            
            if cache_key in self.image_cache:
                photo = self.image_cache[cache_key]
                self.image_label.configure(image=photo, text="")
                self.image_label.image = photo
                return
            
            # Handle image files
            photo = self.load_and_resize_image(image_path)
            if photo:
                self.image_label.configure(image=photo, text="")
                self.image_label.image = photo
                self.image_cache[cache_key] = photo
            else:
                self.image_label.configure(image=None, text="Error loading image")
                self.image_label.image = None
                    
        except Exception as e:
            self.image_label.configure(image=None, text=f"Error loading image: {str(e)}")
            self.image_label.image = None

    def clear_image(self):
        """Clear the image display"""
        self.clear_container_completely()
        self.image_label.configure(image=None, text="No image selected")
        self.image_label.image = None
    
    def clear_container_completely(self):
        """Clear all resources and reset display state"""
        # Clear image display
        if hasattr(self, 'image_label'):
            self.image_label.configure(image="", text="")
            if hasattr(self.image_label, 'image'):
                self.image_label.image = None
        
        # Force garbage collection of image resources
        try:
            import gc
            gc.collect()
        except:
            pass
    
    def reset_ui_state(self):
        """Reset the UI state when no image is available."""
        self.clear_container_completely()
        self.image_index_label.configure(text="")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.image_details_label.configure(text="")
        self.current_image_path = None
        self.current_rotation = 0
        
        if hasattr(self, 'left_button') and hasattr(self, 'right_button'):
            self.left_button.configure(fg_color="gray", hover_color="gray")
            self.right_button.configure(fg_color="gray", hover_color="gray")
        
        if hasattr(self, 'rotate_left_button') and hasattr(self, 'rotate_right_button'):
            self.rotate_left_button.configure(fg_color="gray", hover_color="gray")
            self.rotate_right_button.configure(fg_color="gray", hover_color="gray")

    def update_navigation_buttons(self, current_item_path):
        """Update the state of navigation buttons based on current item position"""
        if not hasattr(self, 'directory_images') or not self.directory_images:
            self.left_button.configure(fg_color="gray", hover_color="gray")
            self.right_button.configure(fg_color="gray", hover_color="gray")
            return
        
        try:
            current_index = self.directory_images.index(current_item_path)
            self.current_image_index = current_index
            
            if current_index <= 0:
                self.left_button.configure(fg_color="gray", hover_color="gray")
            else:
                self.left_button.configure(
                    fg_color=("#3B8ED0", "#1F6AA5"),
                    hover_color=("#36719F", "#144870")
                )
            
            if current_index >= len(self.directory_images) - 1:
                self.right_button.configure(fg_color="gray", hover_color="gray")
            else:
                self.right_button.configure(
                    fg_color=("#3B8ED0", "#1F6AA5"),
                    hover_color=("#36719F", "#144870")
                )
        except ValueError:
            self.left_button.configure(fg_color="gray", hover_color="gray")
            self.right_button.configure(fg_color="gray", hover_color="gray")

    def display_error(self, label, message, duration=3):
        """Display an error message in the specified label for a given duration.
        
        Args:
            label (ctk.CTkLabel): The label widget to display the error in
            message (str): The error message to display
            duration (int): Time in seconds to display the error (default: 3)
        """
        def clear_error():
            time.sleep(duration)
            label.configure(text="")
        
        # Display the error message immediately
        label.configure(text=message)
        
        # Start a thread to clear the error after the specified duration
        threading.Thread(target=clear_error, daemon=True).start()

    def load_and_resize_image(self, image_path):
        """Load and resize an image to fit the green section"""
        try:
            image = Image.open(image_path)
            
            # Apply rotation if it's an image file
            if self.is_image_file(image_path) and self.current_rotation != 0:
                image = image.rotate(-self.current_rotation, expand=True)
            
            self.green_section.update_idletasks()
            green_width = self.green_section.winfo_width()
            green_height = self.green_section.winfo_height()
            
            max_width = max(green_width - 40, 300)
            max_height = max(green_height - 130, 200)
            
            aspect_ratio = image.width / image.height
            
            if aspect_ratio > max_width / max_height:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            
            new_width = max(new_width, 100)
            new_height = max(new_height, 100)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def preload_images(self, center_index):
        """Preload images around the center index to cache"""
        if not hasattr(self, 'directory_images') or not self.directory_images:
            return
        
        start_index = max(0, center_index - 19)
        end_index = min(len(self.directory_images), center_index + 31)
        
        images_to_keep = set()
        for i in range(start_index, end_index):
            if i < len(self.directory_images):
                image_path = self.directory_images[i]
                images_to_keep.add(image_path)
                # Also keep rotated versions for images
                if self.is_image_file(image_path):
                    for rot in [0, 90, 180, 270]:
                        images_to_keep.add(f"{image_path}_rot_{rot}")
        
        keys_to_remove = [key for key in self.image_cache.keys() if key not in images_to_keep]
        for key in keys_to_remove:
            del self.image_cache[key]
        
        def preload_worker():
            for i in range(start_index, end_index):
                if i < len(self.directory_images):
                    image_path = self.directory_images[i]
                    # Only preload original orientation to avoid excessive memory usage
                    cache_key = image_path
                    if cache_key not in self.image_cache:
                        try:
                            # Temporarily set rotation to 0 for preloading
                            original_rotation = self.current_rotation
                            self.current_rotation = 0
                            photo = self.load_and_resize_image(image_path)
                            self.current_rotation = original_rotation
                            if photo:
                                self.image_cache[cache_key] = photo
                        except Exception:
                            pass
        
        threading.Thread(target=preload_worker, daemon=True).start()

    # Utility Methods (No UI Interaction)
    def list_images(self, directory_path, recursive=False):
        """List viewable image files in the specified directory.
        
        Args:
            directory_path (str): Path to the directory to list files from
            recursive (bool): Whether to list files recursively in subdirectories
            
        Returns:
            list: List of viewable image file paths (absolute paths)
        """
        try:
            # Get all items in the directory
            all_items = os.listdir(directory_path)
            
            # Separate files and folders with absolute paths
            files = []
            folders = []
            
            for item in all_items:
                item_path = os.path.join(directory_path, item)
                if os.path.isfile(item_path):
                    # Skip files that contain "desktop.ini" in their name
                    if "desktop.ini" not in item.lower():
                        files.append(item_path)  # Add absolute path
                elif os.path.isdir(item_path):
                    folders.append(item_path)  # Add absolute path
            
            if not recursive:
                # If not recursive, filter to only viewable images
                images = [f for f in files if self.is_image_file(f)]
                return images
            else:
                # If recursive, process folders and add their contents
                for folder in folders:
                    # Recursively get files from each folder
                    folder_files = self.list_images(folder, recursive=True)
                    # Add all files from the folder to the original list
                    files.extend(folder_files)
                
                # Filter to only viewable images
                images = [f for f in files if self.is_image_file(f)]
                return images
                
        except PermissionError:
            raise PermissionError("Permission denied accessing directory")
        except Exception as e:
            raise Exception(f"Error accessing directory: {str(e)}")
    def load_first_image_file(self):
        """Load and display the first image file in the directory images list"""
        if hasattr(self, 'directory_images') and self.directory_images:
            self.current_image_index = 0
            first_image_path = self.directory_images[0]
            self.display_file(first_image_path)
        else:
            self.reset_ui_state()

    def get_file_details(self, file_path):
        """Get file details including format, size, resolution, creation and modification dates"""
        try:
            file_stats = os.stat(file_path)
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            
            _, ext = os.path.splitext(file_path)
            format_type = ext.upper().lstrip('.')
            
            size_bytes = file_stats.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
            resolution_str = "N/A"
            if self.is_image_file(file_path):
                try:
                    with Image.open(file_path) as img:
                        resolution_str = f"{img.width}×{img.height}"
                except Exception:
                    resolution_str = "N/A"
            
            creation_time = datetime.fromtimestamp(file_stats.st_ctime)
            modification_time = datetime.fromtimestamp(file_stats.st_mtime)
            
            creation_str = creation_time.strftime("%Y-%m-%d %H:%M")
            modification_str = modification_time.strftime("%Y-%m-%d %H:%M")
            
            details = f"{name_without_ext} • {format_type} • {size_str} • {resolution_str} • Created: {creation_str} • Modified: {modification_str}"
            return details
        except Exception:
            return "Error retrieving file details"


    def is_image_file(self, file_path):
        """Check if a file is an image based on its extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico', '.tga', '.psd'}
        _, ext = os.path.splitext(file_path.lower())
        return ext in image_extensions


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()