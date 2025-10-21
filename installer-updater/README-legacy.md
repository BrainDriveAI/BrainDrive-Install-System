> ⚠️ **Archived Project**  
> This project is no longer actively maintained by the original authors.  
> The repository remains available for reference and community use.

# Installer Auto Updater

This Python script automates the process of checking for and updating the OpenWebUI installer to the latest version. It fetches release data from the GitHub repository, compares the installed version with the latest version, and downloads the latest installer if necessary.

## Features
- **Version Checking**: Compares the installed version of the installer with the latest version available on GitHub.
- **Automatic Download**: Downloads the latest version of the installer if an update is available.
- **Error Handling**: Includes error handling for network issues, file permission errors, and other unexpected failures.
- **Configuration File**: Stores the installation directory and the current version in a configuration file to keep track of updates.

## Requirements
- Python 3.8 or higher
- `requests` library
- `dulwich` library (for GitHub interaction)





## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/BrainDriveAI/InstallerAutoUpdater.git
   ```
2. Navigate to the project directory:
   ```bash
   cd InstallerAutoUpdater
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
## Usage
   ```bash
   python InstallerAutoUpdater.py
   ```


### How It Works
1. **Configuration File**: When first run, the script will create a `config.json` file to store the installation directory and version.
2. **Check for Updates**: The script checks for the latest release from the [OpenWebUI_CondaInstaller GitHub repository](https://github.com/BrainDriveAI/OpenWebUI_CondaInstaller).
3. **Download New Version**: If an update is available, the latest installer is downloaded.
4. **Run Installer**: After downloading the new installer, it will be executed.

### Configuration File
The script uses a configuration file (`config.json`) located in the installation directory (`OpenWebUI`). The file stores:
- `install_dir`: The directory where the installer is located.
- `current_version`: The current installed version.
- `last_checked`: The last time an update check was performed.

The configuration file is automatically created when the script is run for the first time.

## Error Handling
The script includes basic error handling for:
- **Network Issues**: If there is no internet connection, it will notify the user.
- **Timeouts**: In case of network delays or timeouts, the script will ask the user to try again.
- **File Permission Errors**: If there is an issue running the installer or accessing files, it will provide helpful messages.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing
Feel free to fork the repository, open issues, and submit pull requests for improvements or bug fixes.

## Acknowledgements
- This script interacts with the [OpenWebUI_CondaInstaller](https://github.com/BrainDriveAI/OpenWebUI_CondaInstaller) GitHub repository for release updates.
