"""
Plugin Builder for BrainDrive Installer
Handles plugin discovery and building automation for BrainDrive plugins.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from braindrive_installer.core.node_manager import NodeManager
from braindrive_installer.core.installer_logger import get_installer_logger


class PluginBuilder:
    """Manages plugin building automation for BrainDrive installation."""
    
    def __init__(self, plugins_path: str, status_updater=None):
        """
        Initialize Plugin Builder.
        
        Args:
            plugins_path: Path to the plugins directory
            status_updater: Optional status updater for progress tracking
        """
        self.plugins_path = plugins_path
        self.status_updater = status_updater
        self.logger = get_installer_logger()
        self.node_manager = NodeManager(status_updater)
        
    def _update_status(self, message: str, progress: Optional[int] = None):
        """Update status if status_updater is available."""
        if self.status_updater:
            self.status_updater.update_status(message, "", progress or 0)
        self.logger.info(message)
    
    def discover_plugins(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Find all plugin directories with package.json files.
        
        Returns:
            Tuple of (success, list_of_plugin_info)
        """
        self._update_status("Discovering plugins...")
        
        if not os.path.exists(self.plugins_path):
            error_msg = f"Plugins directory does not exist: {self.plugins_path}"
            self._update_status(error_msg)
            return False, []
        
        if not os.path.isdir(self.plugins_path):
            error_msg = f"Plugins path is not a directory: {self.plugins_path}"
            self._update_status(error_msg)
            return False, []
        
        plugins = []
        
        try:
            # Scan for plugin directories
            for item in os.listdir(self.plugins_path):
                item_path = os.path.join(self.plugins_path, item)
                
                # Skip files, only process directories
                if not os.path.isdir(item_path):
                    continue
                
                # Check if directory has package.json
                exists, package_info = self.node_manager.check_package_json_exists(item_path)
                if exists:
                    plugin_info = {
                        "name": package_info.get("name", item),
                        "version": package_info.get("version", "unknown"),
                        "path": item_path,
                        "directory_name": item,
                        "scripts": package_info.get("scripts", {}),
                        "dependencies": package_info.get("dependencies", {}),
                        "devDependencies": package_info.get("devDependencies", {}),
                        "has_build_script": "build" in package_info.get("scripts", {}),
                        "has_dev_script": "dev" in package_info.get("scripts", {}),
                        "package_json_path": package_info.get("path")
                    }
                    plugins.append(plugin_info)
                    self.logger.debug(f"Found plugin: {plugin_info['name']} at {item_path}")
            
            self._update_status(f"Discovered {len(plugins)} plugins")
            return True, plugins
            
        except Exception as e:
            error_msg = f"Error discovering plugins: {str(e)}"
            self._update_status(error_msg)
            return False, []
    
    def check_plugin_built(self, plugin_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a plugin is properly built by looking for build artifacts.
        
        Args:
            plugin_path: Path to the plugin directory
            
        Returns:
            Tuple of (is_built, build_info)
        """
        build_info = {
            "has_node_modules": False,
            "has_dist": False,
            "has_build": False,
            "build_artifacts": []
        }
        
        # Check for node_modules
        if self.node_manager.check_node_modules_exists(plugin_path):
            build_info["has_node_modules"] = True
        
        # Check for common build output directories
        common_build_dirs = ["dist", "build", "lib", "out"]
        for build_dir in common_build_dirs:
            build_dir_path = os.path.join(plugin_path, build_dir)
            if os.path.exists(build_dir_path) and os.path.isdir(build_dir_path):
                if os.listdir(build_dir_path):  # Directory is not empty
                    build_info["build_artifacts"].append(build_dir)
                    if build_dir == "dist":
                        build_info["has_dist"] = True
                    elif build_dir == "build":
                        build_info["has_build"] = True
        
        # A plugin is considered built if it has node_modules and at least one build artifact
        is_built = build_info["has_node_modules"] and len(build_info["build_artifacts"]) > 0
        
        return is_built, build_info
    
    def build_plugin(self, plugin_path: str, force_clean: bool = False) -> Tuple[bool, str]:
        """
        Build an individual plugin.
        
        Args:
            plugin_path: Path to the plugin directory
            force_clean: Whether to clean node_modules before building
            
        Returns:
            Tuple of (success, error_message_if_failed)
        """
        # Get plugin name for logging
        exists, package_info = self.node_manager.check_package_json_exists(plugin_path)
        if not exists:
            error_msg = f"Cannot build plugin: {package_info.get('error', 'Unknown error')}"
            self._update_status(error_msg)
            return False, error_msg
        
        plugin_name = package_info.get("name", os.path.basename(plugin_path))
        self._update_status(f"Building plugin: {plugin_name}")
        
        # Clean node_modules if requested
        if force_clean:
            success, error_msg = self.node_manager.clean_node_modules(plugin_path)
            if not success:
                self._update_status(f"Warning: Failed to clean node_modules for {plugin_name}: {error_msg}")
        
        # Install dependencies
        self._update_status(f"Installing dependencies for {plugin_name}...")
        success, error_msg = self.node_manager.install_dependencies(plugin_path)
        if not success:
            error_msg = f"Failed to install dependencies for {plugin_name}: {error_msg}"
            self._update_status(error_msg)
            return False, error_msg
        
        # Check if plugin has a build script
        scripts = package_info.get("scripts", {})
        if "build" in scripts:
            self._update_status(f"Running build script for {plugin_name}...")
            success, error_msg = self.node_manager.run_build_script(plugin_path, "build")
            if not success:
                error_msg = f"Failed to build {plugin_name}: {error_msg}"
                self._update_status(error_msg)
                return False, error_msg
        else:
            self._update_status(f"No build script found for {plugin_name}, skipping build step")
        
        # Verify the plugin was built successfully
        is_built, build_info = self.check_plugin_built(plugin_path)
        if is_built:
            artifacts = ", ".join(build_info["build_artifacts"])
            self._update_status(f"Plugin {plugin_name} built successfully (artifacts: {artifacts})")
            return True, ""
        else:
            error_msg = f"Plugin {plugin_name} build verification failed"
            self._update_status(error_msg)
            return False, error_msg
    
    def build_all_plugins(self, force_clean: bool = False, 
                         skip_built: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Build all discovered plugins.
        
        Args:
            force_clean: Whether to clean node_modules before building
            skip_built: Whether to skip plugins that are already built
            
        Returns:
            Tuple of (overall_success, build_results)
        """
        self._update_status("Starting batch plugin build...")
        
        # Discover plugins
        success, plugins = self.discover_plugins()
        if not success:
            return False, {"error": "Failed to discover plugins"}
        
        if not plugins:
            self._update_status("No plugins found to build")
            return True, {"plugins_built": 0, "plugins_skipped": 0, "plugins_failed": 0}
        
        build_results = {
            "total_plugins": len(plugins),
            "plugins_built": 0,
            "plugins_skipped": 0,
            "plugins_failed": 0,
            "build_details": {},
            "failed_plugins": []
        }
        
        for i, plugin in enumerate(plugins):
            plugin_name = plugin["name"]
            plugin_path = plugin["path"]
            
            progress = int((i / len(plugins)) * 100)
            self._update_status(f"Processing plugin {i+1}/{len(plugins)}: {plugin_name}", progress)
            
            # Check if plugin is already built and skip if requested
            if skip_built:
                is_built, build_info = self.check_plugin_built(plugin_path)
                if is_built:
                    self._update_status(f"Plugin {plugin_name} is already built, skipping")
                    build_results["plugins_skipped"] += 1
                    build_results["build_details"][plugin_name] = {
                        "status": "skipped",
                        "reason": "already_built",
                        "build_info": build_info
                    }
                    continue
            
            # Build the plugin
            success, error_msg = self.build_plugin(plugin_path, force_clean)
            
            if success:
                build_results["plugins_built"] += 1
                build_results["build_details"][plugin_name] = {
                    "status": "success",
                    "path": plugin_path
                }
            else:
                build_results["plugins_failed"] += 1
                build_results["failed_plugins"].append(plugin_name)
                build_results["build_details"][plugin_name] = {
                    "status": "failed",
                    "error": error_msg,
                    "path": plugin_path
                }
        
        # Final status update
        total_processed = build_results["plugins_built"] + build_results["plugins_failed"]
        self._update_status(
            f"Plugin build complete: {build_results['plugins_built']} built, "
            f"{build_results['plugins_skipped']} skipped, "
            f"{build_results['plugins_failed']} failed"
        )
        
        # Overall success if no plugins failed
        overall_success = build_results["plugins_failed"] == 0
        
        return overall_success, build_results
    
    def get_plugin_status(self, plugin_path: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a plugin.
        
        Args:
            plugin_path: Path to the plugin directory
            
        Returns:
            Dictionary with plugin status information
        """
        status = {
            "path": plugin_path,
            "exists": os.path.exists(plugin_path),
            "is_directory": os.path.isdir(plugin_path) if os.path.exists(plugin_path) else False
        }
        
        if not status["exists"] or not status["is_directory"]:
            return status
        
        # Check package.json
        exists, package_info = self.node_manager.check_package_json_exists(plugin_path)
        status["has_package_json"] = exists
        if exists:
            status["package_info"] = package_info
        
        # Check build status
        is_built, build_info = self.check_plugin_built(plugin_path)
        status["is_built"] = is_built
        status["build_info"] = build_info
        
        # Check available scripts
        if exists:
            success, scripts = self.node_manager.get_available_scripts(plugin_path)
            status["available_scripts"] = scripts if success else []
        
        return status
    
    def clean_all_plugins(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Clean node_modules from all plugins.
        
        Returns:
            Tuple of (success, clean_results)
        """
        self._update_status("Cleaning all plugins...")
        
        # Discover plugins
        success, plugins = self.discover_plugins()
        if not success:
            return False, {"error": "Failed to discover plugins"}
        
        clean_results = {
            "total_plugins": len(plugins),
            "plugins_cleaned": 0,
            "plugins_failed": 0,
            "clean_details": {}
        }
        
        for plugin in plugins:
            plugin_name = plugin["name"]
            plugin_path = plugin["path"]
            
            success, error_msg = self.node_manager.clean_node_modules(plugin_path)
            
            if success:
                clean_results["plugins_cleaned"] += 1
                clean_results["clean_details"][plugin_name] = {"status": "cleaned"}
            else:
                clean_results["plugins_failed"] += 1
                clean_results["clean_details"][plugin_name] = {
                    "status": "failed",
                    "error": error_msg
                }
        
        self._update_status(
            f"Plugin cleaning complete: {clean_results['plugins_cleaned']} cleaned, "
            f"{clean_results['plugins_failed']} failed"
        )
        
        overall_success = clean_results["plugins_failed"] == 0
        return overall_success, clean_results
    
    def validate_plugins_directory(self) -> Tuple[bool, str]:
        """
        Validate that the plugins directory exists and is accessible.
        
        Returns:
            Tuple of (is_valid, error_message_if_invalid)
        """
        if not os.path.exists(self.plugins_path):
            return False, f"Plugins directory does not exist: {self.plugins_path}"
        
        if not os.path.isdir(self.plugins_path):
            return False, f"Plugins path is not a directory: {self.plugins_path}"
        
        try:
            # Test read access
            os.listdir(self.plugins_path)
            return True, ""
        except PermissionError:
            return False, f"No read permission for plugins directory: {self.plugins_path}"
        except Exception as e:
            return False, f"Error accessing plugins directory: {str(e)}"