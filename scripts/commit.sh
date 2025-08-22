#!/bin/bash

# Script to create commits with virtuoso_dev attribution
# Usage: ./scripts/commit.sh "Commit message"

if [ -z "$1" ]; then
    echo "Usage: $0 \"Commit message\""
    exit 1
fi

git commit -m "$1

Developed by virtuoso_dev"