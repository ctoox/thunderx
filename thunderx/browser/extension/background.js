// ThunderX Browser Extension Background Script

const THUNDERX_API = 'http://127.0.0.1:9527/api';

// Intercept downloads and send to ThunderX
chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  // Check if ThunderX should handle this download
  chrome.storage.local.get(['enabled'], (result) => {
    if (result.enabled !== false) {
      // Send to ThunderX
      sendToThunderX(downloadItem.url, downloadItem.filename);
      
      // Cancel browser download
      chrome.downloads.cancel(downloadItem.id);
      chrome.downloads.erase({ id: downloadItem.id });
    }
  });
});

// Context menu for right-click download
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'thunderx-download',
    title: 'Download with ThunderX',
    contexts: ['link']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'thunderx-download') {
    sendToThunderX(info.linkUrl, null);
  }
});

async function sendToThunderX(url, filename) {
  try {
    const response = await fetch(`${THUNDERX_API}/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: url,
        filename: filename,
        headers: {}
      })
    });
    
    const data = await response.json();
    console.log('ThunderX download started:', data);
    
    // Show notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'ThunderX',
      message: `Download started: ${filename || url}`
    });
    
  } catch (error) {
    console.error('ThunderX error:', error);
    
    // Show error notification
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: 'ThunderX Error',
      message: 'Could not connect to ThunderX. Is it running?'
    });
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getTasks') {
    fetch(`${THUNDERX_API}/tasks`)
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }
  
  if (request.action === 'pauseTask') {
    fetch(`${THUNDERX_API}/tasks/${request.taskId}/pause`, { method: 'POST' })
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }
  
  if (request.action === 'resumeTask') {
    fetch(`${THUNDERX_API}/tasks/${request.taskId}/resume`, { method: 'POST' })
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }
});
