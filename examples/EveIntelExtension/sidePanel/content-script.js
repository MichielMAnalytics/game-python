// Content script that runs on web pages to detect text selection
(function() {
  // Prevent multiple injections
  if (window.eveIntelActivated) {
    console.log('🔍 EveIntel content script already activated, skipping');
    return;
  }
  window.eveIntelActivated = true;
  
  console.log('🔍 EveIntel text selection content script activated');
  
  let lastSelection = '';
  let debounceTimer;
  let connectionAttempts = 0;
  const MAX_CONNECTION_ATTEMPTS = 5;

  // Try to establish connection with service worker
  function ensureServiceWorkerConnection() {
    if (connectionAttempts >= MAX_CONNECTION_ATTEMPTS) {
      console.log('🔍 EveIntel reached maximum connection attempts');
      return;
    }
    
    connectionAttempts++;
    
    // Let the extension know this content script is active
    chrome.runtime.sendMessage({ 
      action: 'contentScriptReady',
      source: 'content-script.js',
      timestamp: Date.now()
    }, response => {
      if (response && response.success) {
        console.log('🔍 EveIntel content script confirmed connection with service worker');
      } else {
        console.log('🔍 EveIntel content script connection attempt failed, will retry');
        // Retry after delay
        setTimeout(ensureServiceWorkerConnection, 1000);
      }
    });
  }

  // Function to handle text selection
  function handleSelection() {
    const selection = window.getSelection().toString().trim();
    
    // Only proceed if selection is not empty and different from last one
    if (selection && selection !== lastSelection) {
      console.log('🔍 EveIntel detected text selection:', selection.substring(0, 50) + (selection.length > 50 ? '...' : ''));
      lastSelection = selection;
      
      // Debounce to avoid sending too many messages
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        // Send selected text to the extension with page URL
        chrome.runtime.sendMessage({
          action: 'textSelected',
          text: selection,
          pageUrl: window.location.href,
          pageTitle: document.title,
          timestamp: Date.now()
        }, response => {
          if (response && response.success) {
            console.log('🔍 EveIntel successfully sent selected text to extension');
            addSelectionIndicator(true);
          } else {
            console.error('🔍 EveIntel failed to send selected text', response);
            addSelectionIndicator(false);
          }
        });
      }, 300);
    }
  }
  
  // Add a visual indicator when text is selected
  function addSelectionIndicator(success = true) {
    // Remove any existing indicator
    removeSelectionIndicator();
    
    const selection = window.getSelection();
    if (!selection.toString().trim()) return;
    
    // Create indicator element
    const indicator = document.createElement('div');
    indicator.id = 'eveintel-selection-indicator';
    
    // Message content
    const message = success ? 'TEXT SELECTED FOR EVE' : 'FAILED TO CAPTURE SELECTION';
    
    // Create layout elements
    const iconElement = document.createElement('img');
    iconElement.src = chrome.runtime.getURL('images/icon-hq-white.png');
    iconElement.style.width = '20px';
    iconElement.style.height = '20px';
    iconElement.style.marginRight = '10px';
    iconElement.style.display = 'block';
    
    // Add error indicator if failed
    if (!success) {
      const errorOverlay = document.createElement('div');
      errorOverlay.style.position = 'absolute';
      errorOverlay.style.top = '0';
      errorOverlay.style.left = '0';
      errorOverlay.style.right = '10px';
      errorOverlay.style.bottom = '0';
      errorOverlay.style.display = 'flex';
      errorOverlay.style.alignItems = 'center';
      errorOverlay.style.justifyContent = 'center';
      errorOverlay.style.fontSize = '16px';
      errorOverlay.textContent = '⚠️';
      
      const iconContainer = document.createElement('div');
      iconContainer.style.position = 'relative';
      iconContainer.appendChild(iconElement);
      iconContainer.appendChild(errorOverlay);
      indicator.appendChild(iconContainer);
    } else {
      indicator.appendChild(iconElement);
    }
    
    const textElement = document.createElement('span');
    textElement.textContent = message;
    textElement.style.fontFamily = '"JetBrains Mono", monospace';
    textElement.style.textTransform = 'uppercase';
    textElement.style.letterSpacing = '0.05em';
    textElement.style.fontSize = '12px';
    
    indicator.appendChild(textElement);
    
    // Apply styles
    indicator.style.position = 'fixed';
    indicator.style.bottom = '20px';
    indicator.style.right = '20px';
    indicator.style.backgroundColor = '#1a1a1a';
    indicator.style.color = '#ffeb3b';
    indicator.style.padding = '10px 16px';
    indicator.style.borderRadius = '4px';
    indicator.style.fontWeight = '500';
    indicator.style.zIndex = '9999999';
    indicator.style.boxShadow = '0 2px 10px rgba(0,0,0,0.3)';
    indicator.style.border = '1px solid rgba(255, 235, 59, 0.3)';
    indicator.style.opacity = '0';
    indicator.style.transition = 'opacity 0.3s';
    indicator.style.display = 'flex';
    indicator.style.alignItems = 'center';
    
    // Add font import for JetBrains Mono
    const fontLink = document.createElement('link');
    fontLink.rel = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap';
    fontLink.id = 'eveintel-font';
    
    // Add the font link if it doesn't exist yet
    if (!document.getElementById('eveintel-font')) {
      document.head.appendChild(fontLink);
    }
    
    document.body.appendChild(indicator);
    
    // Fade in
    setTimeout(() => {
      indicator.style.opacity = '1';
    }, 10);
    
    // Fade out after 2 seconds
    setTimeout(() => {
      if (indicator) {
        indicator.style.opacity = '0';
        setTimeout(() => removeSelectionIndicator(), 300);
      }
    }, 2000);
  }
  
  function removeSelectionIndicator() {
    const indicator = document.getElementById('eveintel-selection-indicator');
    if (indicator) {
      indicator.remove();
    }
  }
  
  // Listen for selection changes
  document.addEventListener('mouseup', function(e) {
    handleSelection();
  });
  
  document.addEventListener('keyup', (e) => {
    // Only check selection on arrow keys, shift, ctrl combinations
    const keysToCheck = [
      'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
      'Shift', 'Control', 'Meta', 'Alt', 'End', 'Home'
    ];
    if (keysToCheck.includes(e.key) || e.ctrlKey || e.shiftKey) {
      handleSelection();
    }
  });
  
  // Set initial connection attempt
  ensureServiceWorkerConnection();
  
  // Also check for initial selection when script loads
  setTimeout(handleSelection, 1000);
  
  // Set up a periodic check to make sure selection is still working
  // This helps if the connection gets dropped
  setInterval(() => {
    ensureServiceWorkerConnection();
  }, 60000); // Check every minute
})(); 