# Database Management for Token Storage

This directory contains scripts and modules for secure management of access tokens in the EveIntelExtension.

## Initial Setup

Before using the token storage system, you need to generate an encryption key:

1. Run the key generation script:
   ```
   python db/generate_key.py
   ```

2. This will create a FERNET_KEY in your .env file. IMPORTANT: Back up this key securely!
   If you lose this key, all stored tokens will be unrecoverable.

## Usage Scripts

### Listing Users

To see all users and their information: 