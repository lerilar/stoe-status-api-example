# Status Checker

A Python script for checking status and sending notifications.

## Prerequisites

* Python 3.x
* pip (Python package installer)
* Either Gotify server access or Slack workspace access

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - requests: For API communication with status endpoints and notification services
   - PyYAML: For reading the configuration file
   - python-dotenv: For managing environment variables and tokens

## Configuration

1. Create or modify `config.yaml` with the following structure:
   ```yaml
   # Notification configuration
   notifications:
     provider: gotify  # or 'slack'
     gotify:
       url: 'https://your-gotify-server.com'
       # Add your Gotify token to the .env file
     slack:
       channel: '#your-channel'
       # Add your Slack token to the .env file

   # Components to monitor
   components:
     - id: component-id
       name: "Component Name"
       enabled: true
       notify_on:
         - degradation
         - recovery
       messages:
         degradation: "Custom degradation message: {status}"
         recovery: "Custom recovery message{duration}"
   ```

2. Create a `.env` file in the installation directory with your tokens:
   ```
   GOTIFY_TOKEN=your-gotify-token
   SLACK_TOKEN=your-slack-token
   ```
   
   Note: Make sure to never commit the `.env` file to version control.

3. Update the configuration values with your specific settings:
   - Choose your notification provider (gotify or slack)
   - Configure the provider-specific settings (URL for Gotify or channel for Slack)
   - Ensure your tokens are correctly set in the .env file
   - Add or modify components to monitor with:
     - Unique ID and display name
     - Enable/disable monitoring
     - Customize notification triggers
     - Set custom messages for different states
       - Use {status} placeholder for status information
       - Use {duration} placeholder for downtime duration

## Setting up the Cron Job

1. Ensure the check_status.sh script is executable:

   ```bash
   chmod +x check_status.sh
   ```

2. Open your crontab file:

   ```bash
   crontab -e
   ```

3. Add a line to run the script at your desired interval:
   ```bash
   # Run every 5 minutes
   */5 * * * * [path-to-installation]/check_status.sh
   ```

The check_status.sh script will:

- Navigate to the correct project directory
- Activate the Python virtual environment
- Run the status checker
- Deactivate the virtual environment

Make sure to adjust the path in the crontab entry to match your actual installation directory

## Usage

### Normal Operation
The script will run automatically via cron job to monitor status changes.

### Manual Testing
To test the system's functionality, you can use the test flag:
```bash
python status_checker.py --test
```

This will simulate a sequence of status changes:
1. Initial check of current status (baseline)
2. Simulates a BankID failure
3. Simulates a Digital ID-card failure
4. Simulates recovery for all components

This is useful for verifying that your notification setup is working correctly.

## Troubleshooting

- Ensure the virtual environment is activated when installing dependencies
- Verify all paths in the cron job are absolute paths
- Check the configuration file for correct formatting and valid credentials
- Make sure the script has necessary permissions to execute
