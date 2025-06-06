// Configuration
const API_URL = 'http://localhost:5001/api';

// Instead of generating a new user ID every time, we'll create a function to get or create one
async function getUserId() {
  const result = await chrome.storage.local.get(['persistentUserId']);
  if (result.persistentUserId) {
    return result.persistentUserId;
  }
  
  // If no persistent ID exists, create one and store it
  const newUserId = 'chrome-extension-user-' + Date.now();
  await chrome.storage.local.set({ persistentUserId: newUserId });
  return newUserId;
}

// Token for preventing multiple auth requests
let authInProgress = false;

// Add these variables at the top of your service worker
let lastSelectedText = '';
let lastSelectedPageUrl = null;
let sidePanelPort = null;

// Function to inject content script into a tab
function injectContentScript(tabId, url) {
  if (!url || !url.startsWith('http') || url.includes('chrome-extension://')) {
    return; // Skip non-http or extension pages
  }
  
  console.log(`Injecting content script into tab ${tabId} (${url.substring(0, 50)}...)`);
  
  chrome.scripting.executeScript({
    target: { tabId: tabId },
    files: ['content-script.js']
  }).then(() => {
    console.log(`Successfully injected content script into tab ${tabId}`);
  }).catch(err => {
    console.error(`Error injecting content script into tab ${tabId}:`, err);
    
    // Try alternative injection method if the first one fails
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: createInlineContentScript
    }).catch(fallbackErr => {
      console.error(`Fallback injection also failed for tab ${tabId}:`, fallbackErr);
    });
  });
}

// Listen for when the extension is installed or updated
chrome.runtime.onInstalled.addListener(async () => {
  // Set the side panel behavior
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
  
  // Get or create a persistent user ID
  const userId = await getUserId();
  
  // Initialize auth state
  chrome.storage.local.get(['isAuthenticated'], function(result) {
    let updates = {};
    
    if (!result.hasOwnProperty('isAuthenticated')) {
      updates.isAuthenticated = false;
    }
    
    // Ensure userId is set
    updates.userId = userId;
    
    if (Object.keys(updates).length > 0) {
      chrome.storage.local.set(updates);
    }
  });

  // Add this code right after the chrome.runtime.onInstalled event handler
  // This ensures we inject the content script into all existing tabs when the extension is first loaded

  // Create a function that gets injected directly if the file method fails
  function createInlineContentScript() {
    console.log('🔍 EveIntel injected via inline function');
    
    // Prevent duplicate injection
    if (window.eveIntelInjected) return;
    window.eveIntelInjected = true;
    
    let lastSelection = '';
    
    // Function to handle text selection
    function handleSelection() {
      const selection = window.getSelection().toString().trim();
      if (selection && selection !== lastSelection) {
        console.log('🔍 EveIntel detected text selection (inline):', selection.substring(0, 50) + '...');
        lastSelection = selection;
        
        // Send to extension
        chrome.runtime.sendMessage({
          action: 'textSelected',
          text: selection
        });
        
        // Show visual indicator
        showSelectionIndicator(selection);
      }
    }
    
    function showSelectionIndicator(selectedText) {
      // Remove existing indicator if any
      const existingIndicator = document.getElementById('eveintel-selection-indicator');
      if (existingIndicator) existingIndicator.remove();
      
      // Create indicator
      const indicator = document.createElement('div');
      indicator.id = 'eveintel-selection-indicator';
      indicator.textContent = '✓ Selected for EveIntel';
      indicator.style.position = 'fixed';
      indicator.style.bottom = '20px';
      indicator.style.right = '20px';
      indicator.style.backgroundColor = '#1DA1F2';
      indicator.style.color = 'white';
      indicator.style.padding = '8px 12px';
      indicator.style.borderRadius = '4px';
      indicator.style.fontSize = '14px';
      indicator.style.zIndex = '9999';
      indicator.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
      
      document.body.appendChild(indicator);
      
      // Remove after 2 seconds
      setTimeout(() => {
        if (indicator && document.body.contains(indicator)) {
          indicator.remove();
        }
      }, 2000);
    }
    
    // Listen for selection changes
    document.addEventListener('mouseup', handleSelection);
    document.addEventListener('keyup', handleSelection);
    
    // Check initial selection
    setTimeout(handleSelection, 500);
    
    // Notify that we're ready
    chrome.runtime.sendMessage({ action: 'contentScriptReady' });
  }

  // Inject content script into all existing tabs when extension is loaded
  chrome.tabs.query({}, tabs => {
    for (const tab of tabs) {
      if (tab.id && tab.url) {
        injectContentScript(tab.id, tab.url);
      }
    }
  });

  // Also inject when user switches to a tab
  chrome.tabs.onActivated.addListener(activeInfo => {
    chrome.tabs.get(activeInfo.tabId, tab => {
      if (tab.id && tab.url) {
        injectContentScript(tab.id, tab.url);
      }
    });
  });

  // Update the existing tabs.onUpdated listener to use our new function
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.id && tab.url) {
      injectContentScript(tab.id, tab.url);
    }
  });
});

// Open the side panel when the extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

// Listen for messages from the content scripts or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'initiate_auth') {
    // Prevent multiple auth requests
    if (authInProgress) {
      sendResponse({ success: false, error: 'Authentication already in progress' });
      return true;
    }
    
    authInProgress = true;
    
    // Use the userId from the message if provided, otherwise get from storage
    const processAuth = async (userId) => {
      try {
        // Handle auth initialization in background script
        let data;
        
        if (message.requiresApiKey === false) {
          // Use existing API key stored for the user
          data = await initiateAuthWithStoredKey(userId);
        } else {
          // Regular flow with provided API key
          data = await initiateAuthProcess(message.apiKey, userId);
        }
        
        // Only open a tab if the server hasn't already opened one
        if (data.auth_url && !data.browser_opened) {
          chrome.tabs.create({ url: data.auth_url });
        }
        sendResponse({ success: true });
      } catch (error) {
        console.error('Auth error:', error);
        sendResponse({ success: false, error: error.message || 'Authentication failed' });
      } finally {
        authInProgress = false;
      }
    };
    
    if (message.userId) {
      // Use the provided userId
      processAuth(message.userId);
    } else {
      // Get userId from storage
      getUserId().then(userId => {
        processAuth(userId);
      });
    }
    
    return true; // Keep the message channel open for async response
  } 
  else if (message.action === 'auth_completed') {
    // Update authentication status
    chrome.storage.local.set({ isAuthenticated: true });
    sendResponse({ success: true });
  } 
  else if (message.action === 'logout') {
    // Clear authentication status
    chrome.storage.local.set({ isAuthenticated: false });
    sendResponse({ success: true });
  }
  else if (message.action === 'textSelected') {
    console.log('Text selection received from content script:', 
                message.text.substring(0, 50) + (message.text.length > 50 ? '...' : ''));
    
    // Store the selected text AND the page URL
    lastSelectedText = message.text;
    lastSelectedPageUrl = message.pageUrl;
    
    // If side panel is connected, send the text to it
    if (sidePanelPort) {
      console.log('Forwarding selected text to side panel');
      sidePanelPort.postMessage({ 
        action: 'updateSelectedText', 
        text: message.text,
        pageUrl: message.pageUrl
      });
    } else {
      console.log('Side panel not connected, storing text for later');
    }
    
    sendResponse({ success: true });
    return true;
  }
  else if (message.action === 'getSelectedText') {
    // Side panel is requesting the latest selected text
    sendResponse({ 
      text: lastSelectedText,
      pageUrl: lastSelectedPageUrl
    });
    // Clear the text after sending to avoid duplicates
    lastSelectedText = '';
    lastSelectedPageUrl = null;
  }
  else if (message.action === 'contentScriptReady') {
    // Content script has loaded
    sendResponse({ success: true });
  }
  else if (message.action === 'ensureContentScriptLoaded') {
    // If sidepanel requests content script loading
    const tabId = message.tabId;
    if (tabId) {
      chrome.tabs.get(tabId, tab => {
        if (tab && tab.url) {
          console.log(`Sidepanel requested content script for tab ${tabId}`);
          injectContentScript(tabId, tab.url);
          sendResponse({ success: true });
        } else {
          sendResponse({ success: false, error: 'Invalid tab' });
        }
      });
      return true; // Keep channel open for async response
    }
  }
  else if (message.action === 'getOrCreateUserId') {
    getUserId().then(userId => {
      sendResponse({ userId: userId });
    });
    return true; // Keep the message channel open for async response
  }
  
  return true; // Keep the message channel open for async response
});

// Add this to handle communication with the side panel
chrome.runtime.onConnect.addListener(port => {
  if (port.name === 'sidePanel') {
    sidePanelPort = port;
    
    // Send any existing selected text when the panel connects
    if (lastSelectedText) {
      port.postMessage({ 
        action: 'updateSelectedText', 
        text: lastSelectedText,
        pageUrl: lastSelectedPageUrl
      });
      lastSelectedText = '';
      lastSelectedPageUrl = null;
    }
    
    // Listen for disconnect
    port.onDisconnect.addListener(() => {
      sidePanelPort = null;
    });
  }
});

// Helper function to initiate auth process via API
async function initiateAuthProcess(apiKey, providedUserId = null) {
  // We must have a userId provided now, no fallbacks
  if (!providedUserId) {
    throw new Error("User ID is required for authentication");
  }
  
  const userId = providedUserId;
  
  // Store this userId in storage
  await chrome.storage.local.set({ userId: userId });
  
  const response = await fetch(`${API_URL}/auth/initiate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      api_key: apiKey,
      user_id: userId
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  
  // If already authenticated, no need for further steps
  if (data.already_authenticated) {
    chrome.storage.local.set({ isAuthenticated: true, userId: userId });
  }
  
  return data;
}

// New helper function for initiating auth with stored API key
async function initiateAuthWithStoredKey(userId) {
  // Store this userId in storage
  await chrome.storage.local.set({ userId: userId });
  
  try {
    const response = await fetch(`${API_URL}/auth/initiate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        user_id: userId,
        use_stored_key: true  // Tell the server to use the stored key
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from API:', errorText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    // If already authenticated, no need for further steps
    if (data.already_authenticated) {
      chrome.storage.local.set({ isAuthenticated: true, userId: userId });
    }
    
    return data;
  } catch (error) {
    console.error('Error in initiateAuthWithStoredKey:', error);
    throw error;
  }
}

// Optional: Listen for auth callback to handle redirect
chrome.webNavigation.onCompleted.addListener((details) => {
  // Check if this is a callback URL from the oauth process
  if (details.url.includes('localhost:8714/callback') && 
      details.url.includes('state=') && 
      details.url.includes('code=')) {
    
    // Wait for the auth process to complete before closing the tab
    setTimeout(() => {
      chrome.tabs.remove(details.tabId);
    }, 3000); // Give user 3 seconds to see the success message
  }
}, { url: [{ urlContains: 'localhost:8714/callback' }] });
