#!/bin/bash

# Function to process files recursively
process_files() {
    for file in "$1"/*; do
        if [ -d "$file" ]; then
            # If it's a directory, recursively process it
            process_files "$file"
        elif [[ "$file" == *.py ]]; then
            # If it's a Python file, print the file path and its contents
            echo "File: $file"
            echo "====================="
            cat "$file"
            echo
            echo "====================="
            echo
        fi
    done
}

# Start processing from the current directory
process_files "$(pwd)"
