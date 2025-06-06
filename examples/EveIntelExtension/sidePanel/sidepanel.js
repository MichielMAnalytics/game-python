console.log('sidepanel.js');

// Configuration
const API_URL = 'http://localhost:5001/api';

// Get the user ID from storage
async function getUserId() {
  const result = await chrome.storage.local.get(['persistentUserId']);
  if (result.persistentUserId) {
    return result.persistentUserId;
  }
  
  // If no ID exists, create one and store it
  const newUserId = 'chrome-extension-user-' + Date.now();
  await chrome.storage.local.set({ persistentUserId: newUserId });
  return newUserId;
}

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const selectedTextContainer = document.getElementById('selected-text-container');
const selectedTextContent = document.getElementById('selected-text-content');
const clearSelectionButton = document.getElementById('clear-selection-button');
const menuButton = document.getElementById('menu-button');
const menuDropdown = document.getElementById('menu-dropdown');
const resetChatButton = document.getElementById('reset-chat');
const logoutButton = document.getElementById('logout');

// State
let isWaitingForResponse = false;
let messageHistory = [];
let USER_ID = null; // We'll set this properly after getting from storage

// Add these variables and functions near the top of your sidepanel.js
let port = null;
let messageInputPlaceholder = "Type your message...";

// Add a global variable to store the hidden full text and URLs
let hiddenTextData = {
  fullText: null,
  sourceUrl: null
};

// Add a tab tracking variable at the top of the file with other state variables
let activeTabId = null;

// At the beginning of sidepanel.js, add this authentication check
document.addEventListener('DOMContentLoaded', function() {
  // Get persistent user ID first
  getUserId().then(userId => {
    USER_ID = userId;
    
    // Then check if authenticated
    chrome.storage.local.get(['isAuthenticated'], function(result) {
      if (!result.isAuthenticated) {
        // If not authenticated, redirect to auth page
        window.location.href = 'auth.html';
        return;
      }
      
      // Continue with normal initialization if authenticated
      loadChatHistory();
      setupHeaderActions();
      
      // Connect to service worker
      connectToServiceWorker();
      
      // Set up textarea auto-resize
      messageInput.addEventListener('input', adjustTextareaHeight);
    });
  });
});

// Load chat history from storage
function loadChatHistory() {
  chrome.storage.local.get(['chatHistory'], function(result) {
    if (result.chatHistory && result.chatHistory.length) {
      // Just set the message history, don't display yet
      messageHistory = result.chatHistory;
      
      // Clear UI first to prevent duplications
      chatMessages.innerHTML = '';
      
      // Now display the messages
      displaySavedMessages();
    } else {
      // Only add welcome message if this is the first time the extension is opened
      // or if the chat was intentionally reset
      chrome.storage.local.get(['welcomeMessageShown'], function(welcomeResult) {
        if (!welcomeResult.welcomeMessageShown) {
          // Add welcome message with updated text and formatting
          addMessage('assistant', 'Hi! I\'m <span class="eve-brand">EVE</span>, your Digital Presence Agent. Select text on any webpage and I\'ll help turn it into engaging tweets to enhance your digital presence. How can I help you today?');
          
          // Mark that we've shown the welcome message
          chrome.storage.local.set({ welcomeMessageShown: true });
        }
      });
    }
  });
}

// Event Listeners
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', function(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

// Add this to the initialization section where other event listeners are set up
messageInput.addEventListener('input', function() {
  // If the input is empty, we should clear any hidden data
  if (messageInput.value.trim() === '') {
    hiddenTextData = {
      fullText: null,
      sourceUrl: null
    };
    console.log('Input cleared, hidden data reset');
  }
  
  // Keep the auto-resize functionality
  adjustTextareaHeight();
});

// Add event listener for the clear button after DOM content loaded
clearSelectionButton.addEventListener('click', clearSelectedText);

// Functions
function sendMessage() {
  const message = messageInput.value.trim();
  if (!message || isWaitingForResponse) return;
  
  // Ensure we have a user ID
  if (!USER_ID) {
    getUserId().then(userId => {
      USER_ID = userId;
      sendMessageWithUserId(message);
    });
  } else {
    sendMessageWithUserId(message);
  }
}

function sendMessageWithUserId(message) {
  // Prepare the message to send to API, including hidden full text if available
  let messageToSend = message;
  let hasEnhancedData = false;
  
  // If we have hidden data, append it in a format the AI can understand
  // but that won't be displayed to the user
  if (hiddenTextData.fullText || hiddenTextData.sourceUrl) {
    // Create a separate message object with hidden data
    const enhancedMessage = {
      visibleText: message,
      fullQuotedText: hiddenTextData.fullText,
      sourceUrl: hiddenTextData.sourceUrl
    };
    
    // Log to see what's being sent
    console.log('Sending enhanced message with source URL:', hiddenTextData.sourceUrl);
    
    // Convert to JSON string for sending
    messageToSend = JSON.stringify(enhancedMessage);
    hasEnhancedData = true;
    
    // Reset hidden data after sending
    hiddenTextData = {
      fullText: null,
      sourceUrl: null
    };
  }
  
  // Add user message to UI
  addMessage('user', message);
  messageInput.value = '';
  
  // Disable input while waiting
  isWaitingForResponse = true;
  sendButton.disabled = true;
  
  // Show typing indicator
  showTypingIndicator();
  
  // Send to API
  fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: USER_ID,
      message: messageToSend,
      has_enhanced_data: hasEnhancedData
    })
  })
  .then(response => {
    // Check specifically for 429 status code (too many requests)
    if (response.status === 429) {
      throw new Error('RATE_LIMIT_EXCEEDED');
    }
    
    // Handle server errors (500) specially
    if (response.status === 500) {
      throw new Error('SERVER_ERROR');
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    // Debug the full response
    console.log('Full API response:', data);
    
    // Check if authentication is required
    if (data.authentication_required) {
        // Redirect to auth page
        chrome.storage.local.set({ isAuthenticated: false });
        window.location.href = 'auth.html';
        return;
    }
    
    // Hide typing indicator
    hideTypingIndicator();
    
    // Handle response
    if (data.response) {
      addMessage('assistant', data.response);
    }
    
    // Handle function calls
    if (data.functionCall) {
      const functionName = data.functionCall.name;
      
      // Debug the function call response structure
      console.log('Function call data:', data.functionCall);
      
      if (functionName === 'post_to_twitter') {
        // Debug: Log everything we can about this response
        console.log("==== TWEET DEBUGGING ====");
        console.log("Full response object:", data);
        console.log("Full response JSON:", JSON.stringify(data));
        console.log("Full response text:", data.response);
        console.log("Function call object:", data.functionCall);
        console.log("Function call args:", data.functionCall.args);
        
        // First try to get tweet content and ID from args if available
        let tweetContent = 'undefined';
        let tweetId = null;
        let tweetUrl = null;
        
        // Check different possible structures
        if (data.functionCall.args) {
          console.log('Function args found:', JSON.stringify(data.functionCall.args));
          
          if (data.functionCall.args.tweet_content) {
            tweetContent = data.functionCall.args.tweet_content;
            console.log('Found tweet_content:', tweetContent);
          }
          
          // Check for tweet ID directly in args - THIS IS THE IMPROVED PART
          if (data.functionCall.args.tweet_id) {
            tweetId = data.functionCall.args.tweet_id;
            console.log('Found tweet_id in args:', tweetId);
          }
        }
        
        // If ID is still null, check the response text for the ID pattern as fallback
        if (!tweetId && data.response) {
          console.log('Checking response for tweet ID...');
          
          // Look for ID in the success message format we defined above
          const idInMessagePattern = /with ID: (\d+)/;
          const idInMessageMatch = data.response.match(idInMessagePattern);
          if (idInMessageMatch && idInMessageMatch[1]) {
            tweetId = idInMessageMatch[1];
            console.log('Found tweet ID embedded in success message:', tweetId);
          }
          
          // Try to parse the full JSON from the response if available
          try {
            const responseJson = JSON.parse(data.response);
            if (responseJson && responseJson.data && responseJson.data.id) {
              tweetId = responseJson.data.id;
              console.log('Found tweet ID in parsed JSON response:', tweetId);
            }
          } catch (e) {
            console.log("Response is not valid JSON");
          }
        }
        
        // Log the final values before creating the message
        console.log('Final values - Content:', tweetContent);
        console.log('Final values - ID:', tweetId);
        console.log('Final values - URL:', tweetUrl);
        
        // Create message content with link if available and change styling
        let messageContent = `Tweet posted: <span class="tweet-content">${tweetContent}</span>`;
        
        // Always add a link, using the provided URL, the constructed one, or a generic one
        if (tweetUrl) {
          console.log('Using provided tweet URL:', tweetUrl);
          messageContent += `<br><a href="${tweetUrl}" target="_blank" class="tweet-link">View on X</a>`;
        } else if (tweetId) {
          // Construct URL from ID if direct URL not provided
          const constructedUrl = `https://twitter.com/i/status/${tweetId}`;
          console.log('Constructed URL from tweet ID:', constructedUrl);
          messageContent += `<br><a href="${constructedUrl}" target="_blank" class="tweet-link">View on X</a>`;
        } else {
          // If no URL or ID is available, still add a link to X
          console.log('No tweet URL or ID available, using X home');
          messageContent += `<br><a href="https://twitter.com/home" target="_blank" class="tweet-link">Go to X</a>`;
        }
        
        // Make sure to add the twitter-success class to ensure action buttons appear
        addMessage('system', messageContent, 'twitter-success');
      } else if (functionName === 'post_twitter_thread') {
        // Handle thread posting similarly
        let threadLength = 'multiple';
        let firstTweetId = null;
        let threadUrl = null;
        
        console.log('Thread function call data:', JSON.stringify(data.functionCall));
        
        if (data.functionCall.args) {
          console.log('Thread args:', JSON.stringify(data.functionCall.args));
          
          if (data.functionCall.args.thread_content) {
            threadLength = data.functionCall.args.thread_content.length;
            console.log('Thread length:', threadLength);
          }
          
          // Check for tweet ID in the function args
          if (data.functionCall.args.first_tweet_id) {
            firstTweetId = data.functionCall.args.first_tweet_id;
            console.log('First tweet ID in args:', firstTweetId);
          } else {
            console.log('No first_tweet_id in args');
          }
          
          if (data.functionCall.args.thread_url) {
            threadUrl = data.functionCall.args.thread_url;
            console.log('Thread URL in args:', threadUrl);
          } else {
            console.log('No thread_url in args');
          }
          
          // Check if we have a results array with ids
          if (data.functionCall.args.result_ids && Array.isArray(data.functionCall.args.result_ids)) {
            console.log('Found result_ids array:', data.functionCall.args.result_ids);
            
            // Get the first tweet ID if available
            if (data.functionCall.args.result_ids.length > 0) {
              const firstId = data.functionCall.args.result_ids[0];
              if (firstId && !firstTweetId) {
                firstTweetId = firstId;
                console.log('Found first tweet ID in result_ids array:', firstTweetId);
              }
            }
          }
          
          // Check if tweet_ids exists instead
          if (data.functionCall.args.tweet_ids && Array.isArray(data.functionCall.args.tweet_ids)) {
            console.log('Found tweet_ids array:', data.functionCall.args.tweet_ids);
            
            // Get the first tweet ID if available
            if (data.functionCall.args.tweet_ids.length > 0) {
              const firstId = data.functionCall.args.tweet_ids[0];
              if (firstId && !firstTweetId) {
                firstTweetId = firstId;
                console.log('Found first tweet ID in tweet_ids array:', firstTweetId);
              }
            }
          }
        }
        
        // If we still haven't found a tweet ID, check the response text for patterns
        if (!firstTweetId && data.response) {
          console.log('Checking response text for first tweet ID...');
          
          // Look for ID in the success message format we defined
          const idInMessagePattern = /with first ID: (\d+)/;
          const idInMessageMatch = data.response.match(idInMessagePattern);
          if (idInMessageMatch && idInMessageMatch[1]) {
            firstTweetId = idInMessageMatch[1];
            console.log('Found first tweet ID embedded in success message:', firstTweetId);
          }
          
          // New pattern specifically for the format shown in logs: "The first tweet's ID is 1911509224993268178"
          const firstTweetIdPattern = /first tweet'?s ID is (\d+)/;
          const firstTweetIdMatch = data.response.match(firstTweetIdPattern);
          if (firstTweetIdMatch && firstTweetIdMatch[1]) {
            firstTweetId = firstTweetIdMatch[1];
            console.log('Found first tweet ID in response message:', firstTweetId);
          }
          
          // Try other patterns similar to the single tweet case
          const idJsonPattern = /"id"\s*:\s*"(\d+)"/;
          const idJsonMatch = data.response.match(idJsonPattern);
          if (idJsonMatch && idJsonMatch[1]) {
            firstTweetId = idJsonMatch[1];
            console.log('Found first tweet ID in response using JSON pattern:', firstTweetId);
          }
          
          const idColonPattern = /id\s*:\s*(\d+)/;
          const idColonMatch = data.response.match(idColonPattern);
          if (idColonMatch && idColonMatch[1]) {
            firstTweetId = idColonMatch[1];
            console.log('Found first tweet ID in response using colon pattern:', firstTweetId);
          }
          
          // Pattern for any digits that might be the ID
          if (!firstTweetId) {
            const numericIdPattern = /\b(\d{18,19})\b/; // Twitter IDs are typically 18-19 digits
            const numericMatch = data.response.match(numericIdPattern);
            if (numericMatch && numericMatch[1]) {
              firstTweetId = numericMatch[1];
              console.log('Found first tweet ID using numeric pattern:', firstTweetId);
            }
          }
          
          // Pattern 3: Look for data.id structure in JSON string  
          if (!firstTweetId) {
            const dataIdPattern = /"data".*?"id".*?:.*?"(\d+)"/;
            const dataIdMatch = data.response.match(dataIdPattern);
            if (dataIdMatch && dataIdMatch[1]) {
              firstTweetId = dataIdMatch[1];
              console.log('Found first tweet ID in nested data structure:', firstTweetId);
            }
          }
          
          // Look for edit_history_tweet_ids
          if (!firstTweetId) {
            const editHistoryPattern = /"edit_history_tweet_ids".*?:.*?\["(\d+)"\]/;
            const editHistoryMatch = data.response.match(editHistoryPattern);
            if (editHistoryMatch && editHistoryMatch[1]) {
              firstTweetId = editHistoryMatch[1];
              console.log('Found first tweet ID in edit_history_tweet_ids:', firstTweetId);
            }
          }
        }
        
        // Log final values before creating message
        console.log('Final thread values - Length:', threadLength);
        console.log('Final thread values - First ID:', firstTweetId);
        console.log('Final thread values - URL:', threadUrl);
        
        // Create message content with link if available
        let messageContent = `X thread with ${threadLength} tweets posted successfully.`;
        
        // Always add a link, using the provided URL, the constructed one, or a generic one
        if (threadUrl) {
          console.log('Using provided thread URL:', threadUrl);
          messageContent += `<br><a href="${threadUrl}" target="_blank" class="tweet-link">View thread on X</a>`;
        } else if (firstTweetId) {
          // Construct URL from ID if direct URL not provided
          const constructedUrl = `https://twitter.com/i/status/${firstTweetId}`;
          console.log('Constructed thread URL from first tweet ID:', constructedUrl);
          messageContent += `<br><a href="${constructedUrl}" target="_blank" class="tweet-link">View thread on X</a>`;
        } else {
          // If no URL or ID is available, still add a link to X
          console.log('No thread URL or ID available, using X home');
          messageContent += `<br><a href="https://twitter.com/home" target="_blank" class="tweet-link">Go to X</a>`;
        }
        
        addMessage('system', messageContent, 'twitter-success');
      }
    }
  })
  .catch(error => {
    console.error('Error:', error);
    hideTypingIndicator();
    
    // Check specifically for different error types
    if (error.message === 'RATE_LIMIT_EXCEEDED') {
      addMessage('system', 'You\'ve sent too many messages in a short period of time. Please wait a moment before trying again.', 'error-message');
    } else if (error.message === 'SERVER_ERROR') {
      addMessage('system', 'The server encountered an internal error. This might be due to high demand or a temporary issue. Please try again in a few minutes.', 'error-message');
    } else {
      addMessage('system', 'Sorry, there was an error connecting to the server. Please try again later.', 'error-message');
    }
  })
  .finally(() => {
    isWaitingForResponse = false;
    sendButton.disabled = false;
  });
}

function addMessage(role, content, additionalClass = '') {
  // Create message element
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `${role}-message`);
  if (additionalClass) {
    messageElement.classList.add(additionalClass);
  }
  
  // Handle markdown-like formatting for code
  if (content.includes('```')) {
    content = formatCodeBlocks(content);
  }
  
  // For twitter-success messages, extract the URL and strip the link part
  let tweetUrl = null;
  if (additionalClass === 'twitter-success') {
    // Extract the URL if present in the content
    const urlMatch = content.match(/href="([^"]+)"/);
    if (urlMatch && urlMatch[1]) {
      tweetUrl = urlMatch[1];
      // Remove the <br><a>...</a> part from the content
      content = content.replace(/<br><a[^>]*>.*?<\/a>/g, '');
    }
  }
  
  // Create content container
  const contentElement = document.createElement('div');
  contentElement.classList.add('message-content');
  contentElement.innerHTML = content;
  messageElement.appendChild(contentElement);
  
  // Add action buttons for assistant messages and system messages with twitter-success class
  if (role === 'assistant' || (role === 'system' && additionalClass === 'twitter-success')) {
    const actionsElement = document.createElement('div');
    actionsElement.classList.add('message-actions');
    
    // Add special X button for twitter-success messages first
    if (additionalClass === 'twitter-success' && tweetUrl) {
      const xBtn = document.createElement('button');
      xBtn.classList.add('message-action-btn', 'x-btn');
      xBtn.title = 'View on X';
      xBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      `;
      xBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.open(tweetUrl, '_blank');
      });
      actionsElement.appendChild(xBtn);
    }
    
    // Copy button - Keep the same
    const copyBtn = document.createElement('button');
    copyBtn.classList.add('message-action-btn', 'copy-btn');
    copyBtn.title = 'Copy to clipboard';
    copyBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
    `;
    copyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(contentElement.textContent).then(() => {
        // Show a brief confirmation
        const originalTitle = copyBtn.title;
        copyBtn.title = 'Copied!';
        setTimeout(() => {
          copyBtn.title = originalTitle;
        }, 2000);
      });
    });
    
    // Upvote button - Change to thumbs up
    const upvoteBtn = document.createElement('button');
    upvoteBtn.classList.add('message-action-btn', 'upvote-btn');
    upvoteBtn.title = 'Upvote this response';
    upvoteBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
      </svg>
    `;
    upvoteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Toggle active class for visual feedback
      upvoteBtn.classList.toggle('active');
      if (upvoteBtn.classList.contains('active')) {
        downvoteBtn.classList.remove('active');
      }
      // Future functionality will be added later
    });
    
    // Downvote button - Change to thumbs down
    const downvoteBtn = document.createElement('button');
    downvoteBtn.classList.add('message-action-btn', 'downvote-btn');
    downvoteBtn.title = 'Downvote this response';
    downvoteBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
      </svg>
    `;
    downvoteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      // Toggle active class for visual feedback
      downvoteBtn.classList.toggle('active');
      if (downvoteBtn.classList.contains('active')) {
        upvoteBtn.classList.remove('active');
      }
      // Future functionality will be added later
    });
    
    // Add buttons to action container
    actionsElement.appendChild(copyBtn);
    actionsElement.appendChild(upvoteBtn);
    actionsElement.appendChild(downvoteBtn);
    
    // Add actions to message
    messageElement.appendChild(actionsElement);
  }
  
  chatMessages.appendChild(messageElement);
  
  // Save to history - preserve the original content with link for history
  if (additionalClass === 'twitter-success' && tweetUrl) {
    // Add back the link for storage so it can be recreated if needed
    const fullContent = content + `<br><a href="${tweetUrl}" target="_blank" class="tweet-link">View on X</a>`;
    messageHistory.push({ role, content: fullContent, additionalClass, tweetUrl });
  } else {
    messageHistory.push({ role, content, additionalClass });
  }
  
  saveMessageHistory();
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatCodeBlocks(content) {
  // Simple markdown code block formatter
  let formatted = content;
  const codeBlockRegex = /```([\s\S]*?)```/g;
  
  formatted = formatted.replace(codeBlockRegex, function(match, code) {
    return `<pre><code>${code}</code></pre>`;
  });
  
  return formatted;
}

function showTypingIndicator() {
  const typingIndicator = document.createElement('div');
  typingIndicator.classList.add('typing-indicator');
  typingIndicator.id = 'typing-indicator';
  
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    typingIndicator.appendChild(dot);
  }
  
  chatMessages.appendChild(typingIndicator);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
  const typingIndicator = document.getElementById('typing-indicator');
  if (typingIndicator) {
    typingIndicator.remove();
  }
}

function saveMessageHistory() {
  // Keep only the last 50 messages to avoid storage issues
  if (messageHistory.length > 50) {
    messageHistory = messageHistory.slice(messageHistory.length - 50);
  }
  
  chrome.storage.local.set({ chatHistory: messageHistory });
}

function displaySavedMessages() {
  // Clear any existing messages in the UI to prevent duplicates
  chatMessages.innerHTML = '';
  
  // Display each message in the UI without adding to messageHistory again
  messageHistory.forEach(msg => {
    // Create message element
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', `${msg.role}-message`);
    if (msg.additionalClass) {
      messageElement.classList.add(msg.additionalClass);
    }
    
    // For twitter-success messages, extract the URL and strip the link part
    let tweetUrl = msg.tweetUrl || null;
    let displayContent = msg.content;
    
    if (msg.additionalClass === 'twitter-success' && !tweetUrl) {
      // Extract the URL if present in the content
      const urlMatch = msg.content.match(/href="([^"]+)"/);
      if (urlMatch && urlMatch[1]) {
        tweetUrl = urlMatch[1];
        // Remove the <br><a>...</a> part from the content
        displayContent = msg.content.replace(/<br><a[^>]*>.*?<\/a>/g, '');
      }
    }
    
    // Create content container
    const contentElement = document.createElement('div');
    contentElement.classList.add('message-content');
    contentElement.innerHTML = displayContent;
    messageElement.appendChild(contentElement);
    
    // Add action buttons for assistant messages and system messages with twitter-success class
    if (msg.role === 'assistant' || (msg.role === 'system' && msg.additionalClass === 'twitter-success')) {
      // Create and add action buttons as in the original addMessage function
      const actionsElement = document.createElement('div');
      actionsElement.classList.add('message-actions');
      
      // Add special X button for twitter-success messages first
      if (msg.additionalClass === 'twitter-success' && tweetUrl) {
        const xBtn = document.createElement('button');
        xBtn.classList.add('message-action-btn', 'x-btn');
        xBtn.title = 'View on X';
        xBtn.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
          </svg>
        `;
        xBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          window.open(tweetUrl, '_blank');
        });
        actionsElement.appendChild(xBtn);
      }
      
      // Copy button
      const copyBtn = document.createElement('button');
      copyBtn.classList.add('message-action-btn', 'copy-btn');
      copyBtn.title = 'Copy to clipboard';
      copyBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      `;
      copyBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(contentElement.textContent).then(() => {
          // Show a brief confirmation
          const originalTitle = copyBtn.title;
          copyBtn.title = 'Copied!';
          setTimeout(() => {
            copyBtn.title = originalTitle;
          }, 2000);
        });
      });
      
      // Upvote button
      const upvoteBtn = document.createElement('button');
      upvoteBtn.classList.add('message-action-btn', 'upvote-btn');
      upvoteBtn.title = 'Upvote this response';
      upvoteBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>
      `;
      upvoteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        upvoteBtn.classList.toggle('active');
        if (upvoteBtn.classList.contains('active')) {
          downvoteBtn.classList.remove('active');
        }
      });
      
      // Downvote button
      const downvoteBtn = document.createElement('button');
      downvoteBtn.classList.add('message-action-btn', 'downvote-btn');
      downvoteBtn.title = 'Downvote this response';
      downvoteBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
        </svg>
      `;
      downvoteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        downvoteBtn.classList.toggle('active');
        if (downvoteBtn.classList.contains('active')) {
          upvoteBtn.classList.remove('active');
        }
      });
      
      // Add buttons to action container
      actionsElement.appendChild(copyBtn);
      actionsElement.appendChild(upvoteBtn);
      actionsElement.appendChild(downvoteBtn);
      
      // Add actions to message
      messageElement.appendChild(actionsElement);
    }
    
    chatMessages.appendChild(messageElement);
  });
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update setupHeaderActions to use the new menu elements
function setupHeaderActions() {
  // Set up menu toggle
  menuButton.addEventListener('click', toggleMenu);
  
  // Close menu when clicking outside
  document.addEventListener('click', function(event) {
    if (!menuButton.contains(event.target) && !menuDropdown.contains(event.target)) {
      closeMenu();
    }
  });
  
  // Set up reset chat button
  resetChatButton.addEventListener('click', function() {
    resetChat();
    closeMenu();
  });
  
  // Set up logout button
  logoutButton.addEventListener('click', function() {
    logout();
    closeMenu();
  });
}

function resetChat() {
  // Clear UI
  chatMessages.innerHTML = '';
  
  // Clear history
  messageHistory = [];
  saveMessageHistory();
  
  // Reset welcome message flag so it shows again after reset
  chrome.storage.local.set({ welcomeMessageShown: false });
  
  // Reset server-side conversation
  fetch(`${API_URL}/reset`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: USER_ID
    })
  }).catch(error => {
    console.error('Error resetting chat:', error);
  });
  
  // Add welcome message with updated formatting
  addMessage('assistant', 'What can I help with?');
}

function logout() {
  if (confirm('Are you sure you want to logout?')) {
    // Get user ID
    chrome.storage.local.get(['userId'], function(result) {
      const userId = result.userId;
      
      // Call logout API
      fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId
        })
      })
      .then(() => {
        // Clear all authentication state
        chrome.storage.local.clear();
        
        // Make sure isAuthenticated is definitely set to false
        chrome.storage.local.set({ isAuthenticated: false });
        
        // Notify service worker
        chrome.runtime.sendMessage({ action: 'logout' });
        
        // Redirect to auth page
        window.location.href = 'auth.html';
      })
      .catch(error => {
        console.error('Error logging out:', error);
        alert('Error logging out. Please try again.');
      });
    });
  }
}

// Function to toggle menu visibility
function toggleMenu() {
  if (menuDropdown.classList.contains('active')) {
    closeMenu();
  } else {
    openMenu();
  }
}

// Function to open the menu
function openMenu() {
  menuDropdown.classList.add('active');
  menuButton.setAttribute('aria-expanded', 'true');
}

// Function to close the menu
function closeMenu() {
  menuDropdown.classList.remove('active');
  menuButton.setAttribute('aria-expanded', 'false');
}

// Function to establish connection with service worker
function connectToServiceWorker() {
  console.log('Side panel connecting to service worker...');
  
  try {
    port = chrome.runtime.connect({ name: 'sidePanel' });
    
    port.onMessage.addListener(message => {
      console.log('Side panel received message:', message);
      
      if (message.action === 'updateSelectedText') {
        console.log('Inserting selected text into input:', 
                   message.text.substring(0, 50) + (message.text.length > 50 ? '...' : ''));
        
        // Always replace existing content with new selection, don't append
        // Make sure to pass the pageUrl here
        insertSelectedTextIntoInput(message.text, message.pageUrl, true);
      }
    });
    
    // Check for any existing selected text
    chrome.runtime.sendMessage({ action: 'getSelectedText' }, response => {
      console.log('Checked for existing selected text, response:', response);
      
      if (response && response.text) {
        console.log('Found existing selected text, inserting into input');
        // Make sure to pass the pageUrl from the response
        insertSelectedTextIntoInput(response.text, response.pageUrl, true);
      }
    });
    
    // Actively ensure content script is loaded in the active tab
    ensureContentScriptLoaded();
    
    // Set up listener for tab changes
    setupTabChangeListener();
    
    console.log('Side panel successfully connected to service worker');
  } catch (error) {
    console.error('Error connecting side panel to service worker:', error);
  }
}

// Add a new function to ensure content script is loaded
function ensureContentScriptLoaded() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    if (tabs.length === 0) return;
    
    const activeTab = tabs[0];
    console.log(`Ensuring content script is loaded in active tab ${activeTab.id}`);
    
    // Ask service worker to inject content script
    chrome.runtime.sendMessage({ 
      action: 'ensureContentScriptLoaded',
      tabId: activeTab.id
    });
  });
}

// Add a function to track tab changes
function setupTabChangeListener() {
  // Track active tab changes
  chrome.tabs.onActivated.addListener(activeInfo => {
    // Clear input when switching tabs
    if (activeTabId && activeTabId !== activeInfo.tabId) {
      // Either clear the input entirely or just clear the selection
      clearSelectedText();
    }
    
    // Update active tab ID
    activeTabId = activeInfo.tabId;
    
    // Ensure content script is loaded in the newly activated tab
    chrome.tabs.get(activeTabId, tab => {
      if (tab && tab.url) {
        console.log(`Tab changed, ensuring content script is loaded in tab ${activeTabId}`);
        chrome.runtime.sendMessage({ 
          action: 'ensureContentScriptLoaded',
          tabId: activeTabId
        });
      }
    });
  });
  
  // Also track URL changes within the same tab
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (tabId === activeTabId && changeInfo.url) {
      // URL changed in the active tab, clear the selection
      clearSelectedText();
    }
  });
  
  // Get initial active tab
  chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
    if (tabs.length > 0) {
      activeTabId = tabs[0].id;
    }
  });
}

// Update the insertSelectedTextIntoInput function to properly store the source URL
function insertSelectedTextIntoInput(text, pageUrl = null, forceReplace = false) {
  if (!text) return;
  
  // Store hidden data
  hiddenTextData.fullText = text;
  hiddenTextData.sourceUrl = pageUrl; // Make sure pageUrl is being stored
  
  console.log('Source URL stored:', pageUrl); // Add this debug log
  
  // Enhance and truncate the text for display
  const displayText = enhanceSelectedText(text, pageUrl);
  
  // Show the text in the selection container
  selectedTextContent.textContent = `"${displayText}"`;
  selectedTextContainer.classList.add('has-content');
  
  // Focus the input for immediate typing
  messageInput.focus();
}

// Update clear selected text function
function clearSelectedText() {
  // Clear the selection container
  selectedTextContent.textContent = '';
  selectedTextContainer.classList.remove('has-content');
  
  // Reset hidden data - this is critical
  hiddenTextData = {
    fullText: null,
    sourceUrl: null
  };
  
  console.log('Text selection cleared, hidden data reset');
  
  // Focus the input
  messageInput.focus();
}

// Update enhanceSelectedText to be simpler since we're using it differently now
function enhanceSelectedText(text, pageUrl = null) {
  if (!text) return text;
  
  // Format the text to show only about 8 words
  let displayText = text;
  const words = text.split(/\s+/);
  
  if (words.length > 8) {
    // Take first 4 words and last 4 words with ellipsis in between
    displayText = words.slice(0, 4).join(' ') + ' [...] ' + words.slice(-4).join(' ');
  }
  
  return displayText;
}

// Helper function to adjust textarea height based on content
function adjustTextareaHeight() {
  messageInput.style.height = 'auto';
  // Set a minimum height
  const minHeight = 48;
  // Get the scroll height
  const scrollHeight = messageInput.scrollHeight;
  // Use the greater of min height or scroll height
  messageInput.style.height = Math.max(minHeight, scrollHeight) + 'px';
}
