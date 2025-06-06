# EveIntel Twitter Assistant Chrome Extension

This Chrome Extension provides a side panel interface for the EveIntel Twitter Assistant, allowing users to post tweets and create Twitter threads directly from their browser.

## Features

- Post tweets directly from your browser
- Create Twitter threads with proper formatting
- Chat with an AI assistant about Twitter-related tasks
- Persistent chat history
- Responsive side panel UI

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top-right corner
3. Click "Load unpacked" and select the `sidePanel` folder from this repository
4. The extension should now appear in your extensions list

## Usage

1. Click the EveIntel extension icon in your browser toolbar
2. The side panel will open with the chat interface
3. Type a message to interact with the assistant
4. To post a tweet, simply ask the assistant to do so
5. To create a thread, ask the assistant to create a thread on a topic

## Development

Make sure the backend server is running at `http://localhost:5001` before using the extension.

To modify the extension:
- Edit `sidepanel.html` for the HTML structure
- Edit `styles.css` for styling
- Edit `sidepanel.js` for the application logic
