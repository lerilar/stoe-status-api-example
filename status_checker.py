#!/usr/bin/env python3
import os
import logging
import requests
import json
from datetime import datetime
import argparse
import copy
import time
import yaml
from dotenv import load_dotenv
from notification_providers import get_notification_provider

# Default message templates
DEFAULT_DEGRADATION_TITLE = "🔴 Issue with {name}"
DEFAULT_DEGRADATION_MESSAGE = """
Status Degradation Detected:
Component: {name}
Previous Status: {prev_status}
Current Status: {status}
"""

DEFAULT_RECOVERY_TITLE = "🟢 Recovery for {name}"
DEFAULT_RECOVERY_MESSAGE = """
Status Recovery Detected:
Component: {name}
Previous Status: {prev_status}
Current Status: {status}
"""

DEFAULT_NEW_ISSUE_TITLE = "🔴 Issue with {name}"
DEFAULT_NEW_ISSUE_MESSAGE = """
Status Issue Detected:
Component: {name}
Current Status: {status}
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('status_checker.log')
    ]
)
logger = logging.getLogger('status_checker')

def load_environment():
    """Load environment variables from .env file"""
    try:
        load_dotenv()
        token = os.getenv('GOTIFY_TOKEN')
        if not token:
            raise ValueError("GOTIFY_TOKEN not found in .env file")
        return token
    except Exception as e:
        logger.error(f"Failed to load environment variables: {e}")
        raise

def get_status():
    """Fetch status information from the API"""
    try:
        response = requests.get('https://status.stoe.no/api/v1/status', timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch status data: {e}")
        raise

def load_config():
    """Load configuration from config.yaml file"""
    try:
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
                logger.info("Configuration loaded successfully")
                return config
        else:
            logger.warning("config.yaml not found, using default settings")
            return {"components": []}
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {"components": []}

def load_state():
    """Load previous state from state.json file"""
    try:
        if os.path.exists("state.json"):
            with open("state.json", "r") as f:
                return json.load(f)
        else:
            logger.info("No previous state found, creating new state file")
            return {}
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return {}

def save_state(status_data):
    """Save current state with timestamps for issues"""
    try:
        current_state = load_state()
        new_state = {}
        
        for component in status_data:
            component_id = component.get('id', 'unknown')
            name = component.get('name', 'Unknown Component')
            current_status = component.get('status', 'unknown').lower()
            
            # Update state with basic information
            new_state[component_id] = {
                "name": name,
                "status": current_status,
                "last_updated": datetime.now().isoformat()
            }
            
            if component_id in current_state:
                # If status changed from operational to non-operational, record start time
                if (current_state[component_id].get('status') == 'operational' 
                    and current_status != 'operational'):
                    new_state[component_id]['issue_start'] = datetime.now().isoformat()
                # If status is still non-operational, keep the start time
                elif current_status != 'operational' and 'issue_start' in current_state[component_id]:
                    new_state[component_id]['issue_start'] = current_state[component_id]['issue_start']
            else:
                # New component with issue
                if current_status != 'operational':
                    new_state[component_id]['issue_start'] = datetime.now().isoformat()
        
        with open("state.json", "w") as f:
            json.dump(new_state, f, indent=4)
        logger.info("State saved successfully")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def format_duration(start_time_str):
    """Format the duration since the start time"""
    try:
        start_time = datetime.fromisoformat(start_time_str)
        duration = datetime.now() - start_time
        
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "less than 1m"
    except Exception as e:
        logger.error(f"Failed to format duration: {e}")
        return "unknown duration"

def get_message(component_id, component_name, current_status, prev_status=None, message_type="degradation", config_map=None, state=None):
    """
    Get the appropriate message for a status change notification.
    Uses custom message from config if available, otherwise falls back to default.
    
    Args:
        component_id: The ID of the component
        component_name: The display name of the component
        current_status: Current status of the component
        prev_status: Previous status of the component (optional)
        message_type: Type of message ("degradation" or "recovery")
        config_map: Mapping of component IDs to their configuration
    
    Returns:
        tuple: (title, message) formatted with component information
    """
    # Format parameters for string substitution
    format_params = {
        "name": component_name,
        "status": current_status,
        "prev_status": prev_status if prev_status else "unknown",
        "duration": ""
    }
    
    # Add duration for recovery messages
    if message_type == "recovery" and state and component_id in state:
        if 'issue_start' in state[component_id]:
            duration = format_duration(state[component_id]['issue_start'])
            format_params["duration"] = f" (duration: {duration})"
    
    # Get emoji for the title based on message type
    emoji = "🔴" if message_type == "degradation" else "🟢"
    title = f"{emoji} {component_name}"
    
    # Default message template
    if message_type == "degradation":
        message = DEFAULT_DEGRADATION_MESSAGE if prev_status else DEFAULT_NEW_ISSUE_MESSAGE
    else:  # recovery
        message = DEFAULT_RECOVERY_MESSAGE
    
    # Try to get custom message from config
    if config_map and component_id in config_map:
        component_config = config_map[component_id]
        if 'messages' in component_config and message_type in component_config['messages']:
            custom_message = component_config['messages'][message_type]
            if custom_message:
                logger.info(f"Using custom {message_type} message for {component_name}")
                message = custom_message
                return title, custom_message.format(**format_params)
    
    return title, message.format(**format_params)

def check_components(status_data, notification_provider):
    """Check each component's status and send notifications for issues"""
    try:
        # Load previous state and configuration
        previous_state = load_state()
        config = load_config()
        issues_found = False
        
        # Create a mapping of component IDs to their configuration
        config_map = {}
        for component_config in config.get('components', []):
            config_map[component_config.get('id')] = component_config
        
        for component in status_data:
            component_id = component.get('id', 'unknown')
            name = component.get('name', 'Unknown Component')
            status = component.get('status', 'unknown').lower()
            logger.info(f"Component: {name}, Status: {status}")
            
            # Check if component is in config, if not use default settings
            component_config = config_map.get(component_id, {
                "enabled": True,
                "notify_on": ["degradation", "recovery"]
            })
            
            # Skip if notifications are disabled for this component
            if not component_config.get('enabled', True):
                logger.info(f"Skipping notifications for {name} (disabled in config)")
                continue
                
            # Get notification preferences
            notify_on = component_config.get('notify_on', ["degradation", "recovery"])
            
            # Check if status has changed
            if component_id in previous_state:
                prev_status = previous_state[component_id]["status"]
                
                # Check for degradation (was operational, now it's not)
                if prev_status == "operational" and status != "operational" and "degradation" in notify_on:
                    issues_found = True
                    title, message = get_message(
                        component_id, 
                        name, 
                        status, 
                        prev_status, 
                        "degradation", 
                        config_map,
                        previous_state
                    )
                    notification_provider.send_notification(title, message)
                
                # Check for recovery (was not operational, now it is)
                elif prev_status != "operational" and status == "operational" and "recovery" in notify_on:
                    title, message = get_message(
                        component_id, 
                        name, 
                        status, 
                        prev_status, 
                        "recovery", 
                        config_map,
                        previous_state
                    )
                    notification_provider.send_notification(title, message)
            
            # For new components or first run, notify if not operational
            elif status != "operational" and "degradation" in notify_on:
                issues_found = True
                title, message = get_message(
                    component_id, 
                    name, 
                    status, 
                    None,  # No previous status for new components 
                    "degradation", 
                    config_map,
                    previous_state
                )
                notification_provider.send_notification(title, message)
        
        if not issues_found:
            logger.info("All components are operational")
        
        # Save the updated state
        save_state(status_data)
            
    except Exception as e:
        logger.error(f"Error checking components: {e}")
        raise

def test_status_changes(original_data):
    """
    Create a modified copy of the status data with one component's status changed.
    Used for testing status change notifications.
    """
    # Create a deep copy of the original data
    modified_data = copy.deepcopy(original_data)
    
    # Change the status of the first component if available
    if modified_data and len(modified_data) > 0:
        # Find first operational component to modify
        for component in modified_data:
            if component.get('status', '').lower() == 'operational':
                logger.info(f"Simulating status change for component: {component.get('name')}")
                # Modify the status to simulate an issue
                component['status'] = 'major_outage'
                break
    
    return modified_data
def main():
    """Main function to execute the status check"""
    try:
        # Parse command-line arguments
        parser = argparse.ArgumentParser(description="Status checker for stoe.no")
        parser.add_argument("--test", action="store_true", help="Run test sequence to simulate status changes")
        args = parser.parse_args()
        
        # Load configuration
        config = load_config()
        
        # Initialize notification provider
        notification_provider = get_notification_provider(config)
        if args.test:
            logger.info("Running in test mode - simulating status changes")
            
            # Test 1: Initial check
            logger.info("Test 1: Checking current status (baseline)")
            status_data = get_status()
            check_components(status_data, notification_provider)
            
            # Test 2: Simulate BankID failure
            logger.info("Test 2: Simulating BankID failure")
            time.sleep(2)
            logger.info("Simulating status change for component: BankID")
            check_components([
                {"id": "bankid", "name": "BankID", "status": "major_outage"},
                {"id": "digital-id-card", "name": "Digital ID-card", "status": "operational"},
                {"id": "id-check", "name": "ID check", "status": "operational"}
            ], notification_provider)
            
            # Test 3: Simulate Digital ID-card failure
            logger.info("Test 3: Simulating Digital ID-card failure")
            time.sleep(2)
            logger.info("Simulating status change for component: Digital ID-card")
            check_components([
                {"id": "bankid", "name": "BankID", "status": "major_outage"},
                {"id": "digital-id-card", "name": "Digital ID-card", "status": "major_outage"},
                {"id": "id-check", "name": "ID check", "status": "operational"}
            ], notification_provider)
            
            # Test 4: Recovery for both
            logger.info("Test 4: Simulating recovery for all components")
            time.sleep(2)
            check_components([
                {"id": "bankid", "name": "BankID", "status": "operational"},
                {"id": "digital-id-card", "name": "Digital ID-card", "status": "operational"},
                {"id": "id-check", "name": "ID check", "status": "operational"}
            ], notification_provider)
            
            logger.info("Test sequence completed")
        else:
            # Normal operation - Get status data
            status_data = get_status()
            
            # Check components and send notifications
            check_components(status_data, notification_provider)
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        # Optionally, send a notification about the script failure
        try:
            error_config = load_config()
            error_notification_provider = get_notification_provider(error_config)
            error_notification_provider.send_notification(
                "Status Checker Error",
                f"The status checker script encountered an error: {str(e)}"
            )
        except Exception:
            logger.error("Failed to send error notification")

if __name__ == "__main__":
    main()
