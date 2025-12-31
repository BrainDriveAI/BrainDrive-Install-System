#!/usr/bin/env python3
"""
Script to create a simple BrainDrive logo image for the installer.
This creates a basic placeholder image that can be replaced with actual branding later.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_braindrive_logo():
    """Create a simple BrainDrive logo image."""
    
    # Create a 200x200 image with a gradient background
    size = (200, 200)
    image = Image.new('RGB', size, color='#1e3a8a')  # Dark blue background
    draw = ImageDraw.Draw(image)
    
    # Create a gradient effect
    for y in range(size[1]):
        # Gradient from dark blue to lighter blue
        color_value = int(30 + (y / size[1]) * 100)  # 30 to 130
        color = (color_value, color_value + 50, 255)  # Blue gradient
        draw.line([(0, y), (size[0], y)], fill=color)
    
    # Draw a circle in the center
    circle_center = (size[0] // 2, size[1] // 2)
    circle_radius = 60
    circle_bbox = [
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    ]
    draw.ellipse(circle_bbox, fill='#ffffff', outline='#fbbf24', width=4)
    
    # Draw "BD" text in the circle
    try:
        # Try to use a system font
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
    
    text = "BD"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = circle_center[0] - text_width // 2
    text_y = circle_center[1] - text_height // 2
    
    draw.text((text_x, text_y), text, fill='#1e3a8a', font=font)
    
    # Add "BrainDrive" text below the circle
    try:
        title_font = ImageFont.truetype("arial.ttf", 16)
    except:
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
    
    title_text = "BrainDrive"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = size[0] // 2 - title_width // 2
    title_y = circle_center[1] + circle_radius + 20
    
    draw.text((title_x, title_y), title_text, fill='#ffffff', font=title_font)
    
    return image

def main():
    """Create and save the BrainDrive logo."""
    print("Creating BrainDrive logo image...")
    
    # Create the logo
    logo = create_braindrive_logo()
    
    # Save as PNG
    logo.save('braindrive.png', 'PNG')
    print("✅ Created braindrive.png")
    
    # Also create a smaller version for the card
    small_logo = logo.resize((50, 50), Image.Resampling.LANCZOS)
    small_logo.save('braindrive_small.png', 'PNG')
    print("✅ Created braindrive_small.png")
    
    print("BrainDrive logo images created successfully!")

if __name__ == "__main__":
    main()