#!/usr/bin/env python3
"""
Script to generate a secure Fernet encryption key for token storage.
This script should be run once to create a key that will be used for
encrypting and decrypting access tokens in the database.
"""

import os
import sys
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv, find_dotenv, set_key

def generate_encryption_key():
    """Generate a new Fernet encryption key and save it to .env file"""
    # Find the .env file
    dotenv_path = find_dotenv()
    if not dotenv_path:
        # If no .env file exists, create one in the parent directory
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if not os.path.exists(dotenv_path):
            open(dotenv_path, 'w').close()
    
    # Load existing environment variables
    load_dotenv(dotenv_path)
    
    # Check if a key already exists
    existing_key = os.getenv('FERNET_KEY')
    if existing_key:
        print(f"Warning: An encryption key already exists in {dotenv_path}")
        response = input("Do you want to generate a new key? This will invalidate all existing tokens. (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled. Existing key preserved.")
            return
    
    # Generate a new key
    key = Fernet.generate_key()
    key_str = key.decode()
    
    # Save the key to the .env file without quotes
    # Method 1: Directly write to the file to avoid quotes
    with open(dotenv_path, 'r') as file:
        lines = file.readlines()
    
    # Remove any existing FERNET_KEY line
    lines = [line for line in lines if not line.startswith('FERNET_KEY=')]
    
    # Add the new key line without quotes
    lines.append(f"FERNET_KEY={key_str}\n")
    
    with open(dotenv_path, 'w') as file:
        file.writelines(lines)
    
    print(f"New encryption key generated and saved to {dotenv_path}")
    print("IMPORTANT: Keep this key secure and backed up. Losing it will make existing tokens unrecoverable.")
    print(f"Key: {key_str}")
    
    # Set the key in the current environment
    os.environ['FERNET_KEY'] = key_str
    
    return key

# If an existing key has quotes, this function will fix it
def fix_existing_key():
    """Fix an existing FERNET_KEY by removing any quotes around it"""
    dotenv_path = find_dotenv()
    if not dotenv_path:
        print("No .env file found.")
        return
    
    # Load the key
    load_dotenv(dotenv_path)
    key = os.getenv('FERNET_KEY')
    
    if not key:
        print("No FERNET_KEY found in .env file.")
        return
    
    # Check if the key has quotes
    if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
        # Remove quotes
        fixed_key = key[1:-1]
        
        # Update the file
        with open(dotenv_path, 'r') as file:
            lines = file.readlines()
        
        for i, line in enumerate(lines):
            if line.startswith('FERNET_KEY='):
                lines[i] = f"FERNET_KEY={fixed_key}\n"
        
        with open(dotenv_path, 'w') as file:
            file.writelines(lines)
        
        # Update environment
        os.environ['FERNET_KEY'] = fixed_key
        
        print(f"Fixed FERNET_KEY in {dotenv_path} by removing quotes.")
        print(f"New key value: {fixed_key}")
    else:
        print("FERNET_KEY looks good (no surrounding quotes).")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate or fix a Fernet encryption key")
    parser.add_argument("--fix", action="store_true", 
                        help="Fix an existing key by removing quotes (if present)")
    args = parser.parse_args()
    
    if args.fix:
        fix_existing_key()
    else:
        generate_encryption_key() 