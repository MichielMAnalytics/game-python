// Configuration
const API_URL = 'http://localhost:5001/api';

// DOM Elements
const loginTab = document.getElementById('login-tab');
const registerTab = document.getElementById('register-tab');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const apiKeyForm = document.getElementById('api-key-form');

const loginEmail = document.getElementById('login-email');
const loginPassword = document.getElementById('login-password');
const loginButton = document.getElementById('login-button');

const registerEmail = document.getElementById('register-email');
const registerPassword = document.getElementById('register-password');
const registerConfirm = document.getElementById('register-confirm');
const registerButton = document.getElementById('register-button');

const apiKeyInput = document.getElementById('api-key');
const authButton = document.getElementById('auth-button');
const authStatus = document.getElementById('auth-status');
const loadingElement = document.getElementById('loading');

// App State
let currentUserId = null;

// Event Listeners
loginTab.addEventListener('click', () => switchTab('login'));
registerTab.addEventListener('click', () => switchTab('register'));
loginButton.addEventListener('click', handleLogin);
registerButton.addEventListener('click', handleRegister);
authButton.addEventListener('click', startAuthProcess);
document.addEventListener('DOMContentLoaded', checkExistingAuth);

// Add these event listeners after the DOM content loaded event
document.addEventListener('DOMContentLoaded', function() {
  // Existing initialization code...
  
  // Add keyboard event listeners for Enter key in forms
  
  // Login form Enter key support
  loginForm.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleLogin();
    }
  });
  
  // Register form Enter key support
  registerForm.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleRegister();
    }
  });
  
  // API Key form Enter key support
  apiKeyForm.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      startAuthProcess();
    }
  });
});

// Functions to switch between tabs
function switchTab(tab) {
  if (tab === 'login') {
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
    loginForm.classList.add('active');
    registerForm.classList.remove('active');
    apiKeyForm.classList.remove('active');
  } else if (tab === 'register') {
    loginTab.classList.remove('active');
    registerTab.classList.add('active');
    loginForm.classList.remove('active');
    registerForm.classList.add('active');
    apiKeyForm.classList.remove('active');
  } else if (tab === 'api-key') {
    loginTab.classList.remove('active');
    registerTab.classList.remove('active');
    loginForm.classList.remove('active');
    registerForm.classList.remove('active');
    apiKeyForm.classList.add('active');
  }
}

// Check if already authenticated
function checkExistingAuth() {
  // First check if we have a user ID in storage
  chrome.storage.local.get(['userId', 'isAuthenticated'], function(result) {
    const userId = result.userId;
    const isAuthenticated = result.isAuthenticated;
    
    // If explicitly logged out, always show login form
    if (isAuthenticated === false) {
      switchTab('login');
      return;
    }
    
    if (!userId) {
      // No user ID, show login form
      switchTab('login');
      return;
    }
    
    // We have a user ID, check auth status
    fetch(`${API_URL}/auth/status?user_id=${userId}`)
      .then(response => response.json())
      .then(data => {
        console.log('Auth status check response:', data); // Debug log
        
        if (data.authenticated) {
          // Create and show the logo loader without text parameter
          showLogoLoader();
          
          // Save auth status locally
          chrome.storage.local.set({ 
            isAuthenticated: true,
            userInfo: data.user_info || null,
            userId: userId
          });
          
          setTimeout(() => {
            window.location.href = 'sidepanel.html';
          }, 2000);
        } else if (data.api_key_stored) {
          // User exists and has API key but needs Twitter auth
          currentUserId = userId;
          
          // Show a proper message without mentioning the user's email
          showInfo('Twitter authentication needed. Starting authorization...');
          
          // Start Twitter auth directly
          setTimeout(() => {
            startTwitterAuthOnly();
          }, 1000);
        } else if (data.user_exists) {
          // User exists but needs API key
          currentUserId = userId;
          showInfo('API key needed to continue');
          switchTab('api-key');
        } else {
          // User ID not recognized, show login
          //showInfo('Please log in to continue');
          switchTab('login');
        }
      })
      .catch(error => {
        console.error('Error checking auth status:', error);
        showError('Error checking authentication status. Please log in again.');
        switchTab('login');
      });
  });
}

// Add a new function to show the logo loader
function showLogoLoader() {
  // Hide any existing status messages
  authStatus.style.display = 'none';
  loadingElement.style.display = 'none';
  
  // Create the logo loader container if it doesn't exist
  let loaderContainer = document.getElementById('logo-loader-container');
  if (!loaderContainer) {
    loaderContainer = document.createElement('div');
    loaderContainer.id = 'logo-loader-container';
    loaderContainer.className = 'logo-loader-container';
    
    // Create the logo element
    const logoImg = document.createElement('img');
    logoImg.src = 'images/icon-hq-white.png';
    logoImg.alt = 'EVE Logo';
    logoImg.className = 'logo-loader';
    
    // Add the logo to the container (no text element)
    loaderContainer.appendChild(logoImg);
    
    // Add the container to the body
    document.body.appendChild(loaderContainer);
  }
  
  // Make sure it's visible
  loaderContainer.style.display = 'flex';
}

// Handle login form submission
function handleLogin() {
  const email = loginEmail.value.trim();
  const password = loginPassword.value.trim();
  
  if (!email || !password) {
    showError('Please enter both email and password');
    return;
  }
  
  // Validate email format
  if (!validateEmail(email)) {
    showError('Please enter a valid email address');
    return;
  }
  
  // Show loading state
  loginButton.disabled = true;
  loadingElement.style.display = 'block';
  authStatus.style.display = 'none';
  
  // Send login request
  fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.success) {
      // Save user ID
      currentUserId = data.user_id;
      chrome.storage.local.set({ userId: data.user_id });
      
      console.log('Login response:', data); // Debug log
      
      // If user info exists, it likely means we have Twitter auth, 
      // regardless of what has_twitter_auth says
      const hasTwitterInfo = data.user_info && 
                             (data.user_info.id || data.user_info.name);
      
      if (data.has_twitter_auth || hasTwitterInfo) {
        // Already fully authenticated with Twitter
        // Instead of showing success message, show the logo loader
        showLogoLoader();
        
        // Save auth status
        chrome.storage.local.set({ 
          isAuthenticated: true,
          userInfo: data.user_info || null
        });
        
        setTimeout(() => {
          window.location.href = 'sidepanel.html';
        }, 2000);
      } 
      else if (data.has_api_key) {
        // Has API key but needs Twitter auth
        // Brief success message before Twitter auth
        showSuccess('Login successful! Starting Twitter authorization...');
        
        // Give a brief delay to show the success message
        setTimeout(() => {
          // Initiate Twitter auth directly without asking for API key
          startTwitterAuthOnly();
        }, 1500);
      } 
      else {
        // Needs API key
        showSuccess('Login successful! Please enter your GAME API key.');
        setTimeout(() => {
          switchTab('api-key');
        }, 1000);
      }
    } else {
      showError(data.error || 'Login failed');
    }
  })
  .catch(error => {
    showError('Login failed: ' + error.message);
  })
  .finally(() => {
    loginButton.disabled = false;
    loadingElement.style.display = 'none';
  });
}

// Add this new function to handle Twitter auth directly without API key input
function startTwitterAuthOnly() {
  if (!currentUserId) {
    showError('User session not found. Please login again.');
    setTimeout(() => {
      switchTab('login');
    }, 2000);
    return;
  }
  
  // Show loading state
  loadingElement.style.display = 'block';
  authStatus.style.display = 'none';
  
  // Clear any previous messages
  showInfo('Initiating Twitter authorization...');
  
  // Send message to background script to handle auth without requiring API key
  chrome.runtime.sendMessage({
    action: 'initiate_auth',
    requiresApiKey: false,  // Flag indicating we don't need to provide the API key
    userId: currentUserId
  }, function(response) {
    if (response && response.success) {
      // Auth initiated in background script
      showInfo('Twitter authorization page has been opened in a new tab. Please complete the authorization there.');
      
      // Start polling for auth completion
      startPolling(currentUserId);
    } else {
      const errorMsg = response ? (response.error || 'Failed to initiate authentication') : 
                                 'No response from background script';
      showError(errorMsg);
      loadingElement.style.display = 'none';
    }
  });
}

// Handle registration form submission
function handleRegister() {
  const email = registerEmail.value.trim();
  const password = registerPassword.value.trim();
  const confirm = registerConfirm.value.trim();
  
  // Basic validation
  if (!email || !password || !confirm) {
    showError('Please fill in all fields');
    return;
  }
  
  if (password !== confirm) {
    showError('Passwords do not match');
    return;
  }
  
  if (password.length < 8) {
    showError('Password must be at least 8 characters long');
    return;
  }
  
  if (!validateEmail(email)) {
    showError('Please enter a valid email address');
    return;
  }
  
  // Show loading state
  registerButton.disabled = true;
  loadingElement.style.display = 'block';
  authStatus.style.display = 'none';
  
  // Send registration request
  fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.success) {
      // Save user ID
      currentUserId = data.user_id;
      chrome.storage.local.set({ userId: data.user_id });
      
      showSuccess('Registration successful! Please enter your GAME API key.');
      setTimeout(() => {
        switchTab('api-key');
      }, 1000);
    } else {
      showError(data.error || 'Registration failed');
    }
  })
  .catch(error => {
    showError('Registration failed: ' + error.message);
  })
  .finally(() => {
    registerButton.disabled = false;
    loadingElement.style.display = 'none';
  });
}

// Email validation function
function validateEmail(email) {
  const re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
  return re.test(String(email).toLowerCase());
}

// Start the Twitter authentication process
function startAuthProcess() {
  const apiKey = apiKeyInput.value.trim();
  
  if (!apiKey) {
    showError('Please enter your GAME API key');
    return;
  }
  
  if (!currentUserId) {
    showError('User session not found. Please login again.');
    setTimeout(() => {
      switchTab('login');
    }, 2000);
    return;
  }
  
  // Show loading state
  authButton.disabled = true;
  loadingElement.style.display = 'block';
  authStatus.style.display = 'none';
  
  // Send message to background script to handle auth
  chrome.runtime.sendMessage({
    action: 'initiate_auth',
    apiKey: apiKey,
    userId: currentUserId
  }, function(response) {
    if (response && response.success) {
      // Auth initiated in background script
      showInfo('Twitter authorization page has been opened in a new tab. Please complete the authorization there.');
      
      // Start polling for auth completion
      startPolling(currentUserId);
    } else {
      showError(response.error || 'Failed to initiate authentication');
      authButton.disabled = false;
      loadingElement.style.display = 'none';
    }
  });
}

// Poll the server to check if auth is complete
function startPolling(userId) {
  // Show the logo loader during polling (removing message parameter)
  showLogoLoader();
  
  const pollInterval = setInterval(() => {
    fetch(`${API_URL}/auth/status?user_id=${userId}`)
      .then(response => response.json())
      .then(data => {
        if (data.authenticated) {
          clearInterval(pollInterval);
          
          // No need to update text element anymore
          
          // Save auth status and user info locally
          chrome.storage.local.set({ 
            isAuthenticated: true,
            userInfo: data.user_info || null,
            userId: userId
          });
          
          // Redirect to main chat interface
          setTimeout(() => {
            window.location.href = 'sidepanel.html';
          }, 2000);
        }
      })
      .catch(error => {
        console.error('Error polling auth status:', error);
      });
  }, 3000); // Check every 3 seconds
  
  // Stop polling after 5 minutes (300000 ms)
  setTimeout(() => {
    clearInterval(pollInterval);
    // Remove the logo loader
    const loaderContainer = document.getElementById('logo-loader-container');
    if (loaderContainer) {
      loaderContainer.remove();
    }
    showError('Authentication timed out. Please try again.');
    authButton.disabled = false;
    loadingElement.style.display = 'none';
  }, 300000);
}

// Helper functions for UI updates
function showError(message) {
  authStatus.className = 'auth-status error';
  authStatus.textContent = message;
  authStatus.style.display = 'block';
  loadingElement.style.display = 'none';
}

function showSuccess(message) {
  authStatus.className = 'auth-status success';
  authStatus.textContent = message;
  authStatus.style.display = 'block';
  loadingElement.style.display = 'none';
}

function showInfo(message) {
  authStatus.className = 'auth-status';
  authStatus.style.display = 'block';
  authStatus.textContent = message;
  loadingElement.style.display = 'none';
} 