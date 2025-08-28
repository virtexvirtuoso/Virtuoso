#!/bin/bash
# Permanent InfluxDB environment setup script
# Usage: source set_influxdb_env.sh

# Set InfluxDB environment variables
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ==
export INFLUXDB_ORG=coinmaestro
export INFLUXDB_BUCKET=VirtuosoDB

# Add these variables to .zshrc or .bash_profile for permanent setup
if [ -z "$INFLUXDB_ENV_ADDED" ]; then
    # Determine shell type
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bash_profile"
    else
        echo "Unknown shell. Please manually add the variables to your shell profile."
        return 1
    fi
    
    # Ask for confirmation
    echo "This will add InfluxDB environment variables to $SHELL_RC for permanent use."
    echo "Do you want to proceed? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        # Add variables to shell profile
        cat << 'EOF' >> "$SHELL_RC"

# Virtuoso Trading System - InfluxDB Environment Variables
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ==
export INFLUXDB_ORG=coinmaestro
export INFLUXDB_BUCKET=VirtuosoDB
export INFLUXDB_ENV_ADDED=true
EOF
        
        echo "Environment variables added to $SHELL_RC"
        echo "Please run 'source $SHELL_RC' or restart your terminal for changes to take effect."
        export INFLUXDB_ENV_ADDED=true
    else
        echo "Operation cancelled. Environment variables will only be set for the current session."
    fi
else
    echo "InfluxDB environment variables are already set permanently."
fi

# Verify variables are set correctly for current session
echo "InfluxDB environment variables for current session:"
echo "INFLUXDB_URL: $INFLUXDB_URL"
echo "INFLUXDB_ORG: $INFLUXDB_ORG"
echo "INFLUXDB_BUCKET: $INFLUXDB_BUCKET"
echo "INFLUXDB_TOKEN: ${INFLUXDB_TOKEN:0:10}...${INFLUXDB_TOKEN: -10}" 