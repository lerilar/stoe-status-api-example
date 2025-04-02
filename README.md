# BankID Status Checker

A Python script for monitoring BankID's status page and sending notifications on status changes.

## Disclaimer

This script is provided by BankID BankAxept AS and developed as an open-source example of how to use the BankID status API. It is provided "as-is" without any warranty or support.

Users are free to:
- Use and modify the code
- Make improvements and adaptations
- Share and distribute modifications

The primary purpose of this script is to demonstrate a practical implementation of the Stø status API integration. While we welcome community contributions and improvements, please note that no official support is provided.

[!NOTE] Please note that the status api may change over time, components may be added, changed or removed. An occasional manual check towards the api is encouraged to catch these changes.

A more detailed information about the endpoints is provided at [Api doc](https://status.stoe.no/api/v1). This page will be maintained with the api.

To add more ways to alert, you update the `notification_providers.py` file and add the required config


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

## Slack Configuration

To use Slack for notifications, you'll need:

1. A Slack Bot Token (starts with `xoxb-`)
2. A Slack channel where notifications will be sent

### Setup Steps:

1. Create a Slack App and Bot:
   - Go to https://api.slack.com/apps
   - Create a new app or use an existing one
   - Under "OAuth & Permissions", add these bot token scopes:
     - chat:write
     - channels:read (for public channels)
     - groups:read (for private channels)
   - Install the app to your workspace
   - Copy the Bot User OAuth Token (starts with `xoxb-`)

2. Configure the environment:
   - Add your Slack token to `.env`:
     ```
     SLACK_TOKEN=xoxb-your-bot-token
     ```

3. Update config.yaml:
   ```yaml
   notifications:
     provider: slack
     slack:
       channel: '#your-channel'  # Use '#' for public, '@' for DMs
   ```

4. Invite the bot to your channel:
   - In Slack, type `/invite @your-bot-name` in the channel you specified

### Notes:
- No Slack client installation is needed on the server
- The script uses Slack's Web API via HTTPS
- The only requirements are:
  - Internet connection to reach slack.com
  - Valid Slack Bot Token
  - The 'requests' library (included in requirements.txt)

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
   # Run every 5 minutes - the api does not update 
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
