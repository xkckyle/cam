###
try:
    import pyi_splash
except:
    print('test, no splash library import')
#
import sys,os
newd = r'c:\users\kelleyk\appdata\local\packages\pythonsoftwarefoundation.python.3.12_qbz5n2kfra8p0\localcache\local-packages\python312\site-packages'
sys.path.append(newd)
xoffset=4; mwidth=1280 ;mheight=720
def get_config_path(filename):
    if getattr(sys, 'frozen', False):
        # Compiled executable (PyInstaller)
        base_path = sys._MEIPASS  # Temporary folder where PyInstaller unpacks files
    else:
        # Running from source
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, filename)
config_file = get_config_path('config.txt')
#
if(os.path.exists('config.txt')):
    config_file='config.txt'
else:
    print('using default configs..')
#
print('config file = ',config_file)
import gxipy as gx

import cv2
import numpy as np
from gxipy import DeviceManager
import tkinter as tk
from tkinter import Menu
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import os

# Global variables
frozen_image = None
resized_frozen_image = None
numpy_image = None
drawing = False
start_point = None
lines = []
reference_length = None
last_saved_dir = None
measurement_mode = False

# Initialize device (camera)
device_manager = DeviceManager()
dev_num, dev_info_list = device_manager.update_device_list()
if dev_num == 0:
    print("Error: No camera detected.")
    quit()
device = device_manager.open_device_by_index(1)
try:
    device.import_config_file(config_file)
    print(f"Successfully loaded settings from {config_file}")
except gx.GxiApiError as e:
    print(f"Failed to load settings from {config_file}. Error: {e}")

stream = device.data_stream[0]
device.stream_on()
##stream.start()

# Resize the image based on height (maintain aspect ratio)
def resize_based_on_height(image, target_height):
    width, height = image.size
    aspect_ratio = width / height
    target_width = int(target_height * aspect_ratio)
    return image.resize((target_width, target_height), Image.LANCZOS)

# Function to swap red and blue channels
def swap_red_blue_channels(image):
    return image[..., [2, 1, 0]]  # Swap the R (0 index) and B (2 index) channels

# Save image function
def save_image(image):
    global last_saved_dir
    file_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG files", "*.jpg")])
    if file_path:
        cv2.imwrite(file_path, image)
        last_saved_dir = os.path.dirname(file_path)

# Function to rotate the image 180 degrees
def rotate_image_180(image):
    return cv2.rotate(image, cv2.ROTATE_180)

# Function to handle the save button or spacebar key
def save_photo_button():
    global frozen_image, resized_frozen_image, lines, numpy_image

    if frozen_image is not None and resized_frozen_image is not None:
        print("Saving with lines...")
        pil_image = Image.fromarray(frozen_image).convert("RGB")
        resized_image_with_lines = resize_based_on_height(pil_image, mheight)
        image_with_lines = draw_lines_on_image(np.array(resized_image_with_lines))
        original_size_image_with_lines = Image.fromarray(image_with_lines).resize(frozen_image.shape[1::-1])
        flipped_image = swap_red_blue_channels(np.array(original_size_image_with_lines))
##        flipped_image = rotate_image_180(flipped_image)  # Rotate the image before saving
        save_image(flipped_image)

    elif numpy_image is not None:
        print("Saving without lines...")
        pil_image = Image.fromarray(numpy_image).convert("RGB")
        flipped_image = swap_red_blue_channels(np.array(pil_image))
##        flipped_image = rotate_image_180(flipped_image)  # Rotate the image before saving
        save_image(flipped_image)
    else:
        print("No image available to save!")

# Function to handle the camera feed
def update_camera_feed():
    global numpy_image
    if not measurement_mode:
        raw_image = stream.get_image()
        numpy_image = raw_image.get_numpy_array()

        # Convert to RGB if it's in Bayer format and rotate 180 degrees
        if len(numpy_image.shape) == 2:  # If the image is in grayscale, convert to RGB
            numpy_image = cv2.cvtColor(numpy_image, cv2.COLOR_BAYER_BG2RGB)

        # Rotate the image 180 degrees
        numpy_image = rotate_image_180(numpy_image)

        pil_image = Image.fromarray(numpy_image)
        resized_image = resize_based_on_height(pil_image, mheight)
        imgtk = ImageTk.PhotoImage(resized_image)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)
    camera_label.after(10, update_camera_feed)

# Function to draw lines during measurement mode
def draw_lines_on_image(image):
    global lines, reference_length
    height, width = image.shape[:2]
    pil_image = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_image)

    for i, (p1, p2) in enumerate(lines):
        draw.line([p1, p2], fill="red", width=2)
        if i == 0:
            reference_length = calculate_distance(p1, p2)
            label = "100"
        else:
            line_length = calculate_distance(p1, p2)
            ratio = line_length / reference_length * 100
            label = f"{ratio:.2f}"
        mid_point = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        draw.text(mid_point, label, fill="yellow")

    return np.array(pil_image)

# Calculate the distance between two points
def calculate_distance(p1, p2):
    return np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

# Mouse event to start drawing lines
def on_mouse_down(event):
    global drawing, start_point
    drawing = True
    start_point = (event.x-xoffset, event.y)

# Mouse event to stop drawing and save the line
def on_mouse_up(event):
    global drawing, lines, start_point, resized_frozen_image
    drawing = False
    end_point = (event.x-xoffset, event.y)
    lines.append((start_point, end_point))

    if resized_frozen_image is not None:
        update_frozen_image(np.array(resized_frozen_image))

# Mouse drag event to show temporary line while drawing
def on_mouse_drag(event):
    global start_point, resized_frozen_image, drawing
    if resized_frozen_image is not None and drawing:
        temp_image = np.array(resized_frozen_image).copy()
        pil_image = Image.fromarray(temp_image)
        draw = ImageDraw.Draw(pil_image)
        draw.line([start_point, (event.x-xoffset, event.y)], fill="green", width=2)
        update_frozen_image(np.array(pil_image))

# Right-click to clear all lines
def on_right_click(event):
    global lines,resized_frozen_image
    lines.clear()
    print("Lines cleared.")
    if resized_frozen_image is not None:
        update_frozen_image(np.array(resized_frozen_image))

# Update frozen image during measurement mode
def update_frozen_image(image):
    global camera_label
    image_with_lines = draw_lines_on_image(image)
    pil_image = Image.fromarray(image_with_lines)
    resized_image = resize_based_on_height(pil_image, mheight)
    imgtk = ImageTk.PhotoImage(resized_image)
    camera_label.imgtk = imgtk
    camera_label.configure(image=imgtk)

# Enter measurement mode
def enter_measure_mode():
    global frozen_image, resized_frozen_image, numpy_image, measurement_mode, lines
    lines.clear()
    if numpy_image is not None:
        measurement_mode = True
        lines.clear()  # Clear lines when entering measurement mode
        frozen_image = numpy_image.copy() #swap_red_blue_channels(numpy_image.copy())
##        frozen_image = rotate_image_180(frozen_image)
        pil_image = Image.fromarray(numpy_image)#frozen_image)
        resized_frozen_image = resize_based_on_height(pil_image, mheight)
        print("Entered measure mode. Draw lines by clicking and dragging.")

# Exit measurement mode and return to live feed
def exit_measure_mode():
    global measurement_mode, lines
    measurement_mode = False
    lines.clear()
    print("Exited measure mode. Returning to live camera feed.")

# Initialize GUI window
root = tk.Tk()
root.title("Camera Feed")
root.geometry(f'{mwidth}x{mheight}')
root.resizable(False, False)

camera_label = tk.Label(root)
camera_label.pack()

# Add menu options
menu_bar = Menu(root)
root.config(menu=menu_bar)

# Add File menu
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Save Photo", command=save_photo_button)
file_menu.add_command(label="Exit", command=root.quit)
menu_bar.add_cascade(label="File", menu=file_menu)

# Add Measure menu
measure_menu = Menu(menu_bar, tearoff=0)
measure_menu.add_command(label="Enter Measurement Mode", command=enter_measure_mode)
measure_menu.add_command(label="Exit Measurement Mode", command=exit_measure_mode)
menu_bar.add_cascade(label="Measure", menu=measure_menu)

# Bind events for drawing lines in measurement mode
camera_label.bind("<Button-1>", on_mouse_down)
camera_label.bind("<ButtonRelease-1>", on_mouse_up)
camera_label.bind("<B1-Motion>", on_mouse_drag)
camera_label.bind("<Button-3>", on_right_click)  # Right-click to clear lines

# Bind spacebar to save photo
root.bind("<space>", lambda event: save_photo_button())

# Start the camera feed
update_camera_feed()
#
try:
    pyi_splash.close()
except:
    print('No splash to close')

root.mainloop()
