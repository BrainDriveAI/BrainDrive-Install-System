import os
import shutil
from pathlib import Path
from braindrive_installer.config.AppConfig import AppConfig

class DiskSpaceChecker:
    def __init__(self):
        """
        Initializes the DiskSpaceChecker class.
        Fetches the base path directory from the AppConfig singleton.
        """
        self.config = AppConfig()
        self.base_path = self.config.base_path

    def has_enough_space(self, required_space_gb):
        """
        Checks if the base path directory or its drive has enough free space.
        :param required_space_gb: The required space in GB as a string (e.g., "3.5").
        :return: True if there is enough space, False otherwise.
        """
        try:
            # Convert required space from string to float
            required_space_gb = float(required_space_gb)

            # Determine the path to check. If the configured base path does not
            # exist yet (common before first install), walk up its parents until
            # we find an existing directory. This avoids Windows-style drive
            # handling that does not apply on macOS/Linux.
            path_to_check = self.base_path or str(Path.home())
            candidate = Path(path_to_check)
            if not candidate.exists():
                for parent in candidate.parents:
                    if parent.exists():
                        path_to_check = str(parent)
                        break
                else:
                    path_to_check = str(Path.home())

            # Get the free space in bytes
            total, used, free = shutil.disk_usage(path_to_check)

            # Convert free space from bytes to GB
            free_space_gb = free / (1024 ** 3)

            return free_space_gb >= required_space_gb
        except ValueError:
            print("Invalid required_space_gb value. Must be a numeric string.")
            return False
        except Exception as e:
            print(f"Error checking disk space: {e}")
            return False
