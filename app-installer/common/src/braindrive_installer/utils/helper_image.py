import os
import shutil
import sys
import threading
from pathlib import Path

from braindrive_installer.config.AppConfig import AppConfig

class HelperImage:
    """
    Helper class to manage image files for both script and PyInstaller executable environments,
    and to integrate with AppConfig for base path checking.
    """

    @staticmethod
    def get_image_path(image_name, callback=None):
        """
        Get the path of the image file. If it doesn't exist, extract it from the PyInstaller directory (_MEIPASS)
        or check the AppConfig base path.
        
        :param image_name: Name of the image file to check and extract if necessary.
        :param callback: Optional callback function to call after the image is extracted.
        :return: Full path to the image file.
        """
        app_config = AppConfig()  # Initialize AppConfig to get the base path

        # Check the current working directory first
        target_path = Path.cwd() / image_name
        if target_path.exists():
            if callback:
                callback(str(target_path))
            return str(target_path)

        # Check the AppConfig base path
        app_config_path = Path(app_config.base_path) / image_name
        if app_config_path.exists():
            if callback:
                callback(str(app_config_path))
            return str(app_config_path)

        # Determine additional search locations (PyInstaller _MEIPASS, package assets, etc.)
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        package_assets_dir = Path(__file__).resolve().parents[4] / "assets"

        candidate_sources = [
            base_dir / image_name,
            base_dir / "assets" / image_name,
            package_assets_dir / image_name,
        ]

        # Extract the file from the first matching source path
        for source_path in candidate_sources:
            if source_path.exists():
                try:
                    app_config_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(source_path), str(app_config_path))
                    print(f"Extracted '{image_name}' to '{app_config_path}'.")
                    if callback:
                        callback(str(app_config_path))
                    return str(app_config_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to extract '{image_name}': {e}")

        raise FileNotFoundError(
            f"Image '{image_name}' not found in '{target_path}', '{app_config_path}', or any asset search paths."
        )

    @staticmethod
    def extract_images_in_background(image_list, callback=None):
        """
        Extract multiple images in a background thread.
        
        :param image_list: List of image filenames to extract.
        :param callback: Optional callback function to call after all images are processed.
        """
        def extract_task():
            app_config = AppConfig()  # Initialize AppConfig to get the base path
            extracted_images = []

            for image_name in image_list:
                try:
                    # Check or extract each image
                    target_path = HelperImage.get_image_path(image_name)
                    extracted_images.append(target_path)
                except Exception as e:
                    print(f"Error processing '{image_name}': {e}")

            # Invoke the callback with the list of extracted images
            if callback:
                callback(extracted_images)

        # Run the extraction task in a background thread
        threading.Thread(target=extract_task, daemon=True).start()
