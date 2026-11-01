// ThunderX Popup Script

document.addEventListener('DOMContentLoaded', () => {
  const enabledToggle = document.getElementById('enabled');
  const tasksContainer = document.getElementById('tasks');

  // Load enabled state
  chrome.storage.local.get(['enabled'], (result) => {
    enabledToggle.checked = result.enabled !== false;
  });

  // Save enabled state
  enabledToggle.addEventListener('change', () => {
    chrome.storage.local.set({ enabled: enabledToggle.checked });
  });

  // Load tasks
  loadTasks();

  // Refresh tasks periodically
  setInterval(loadTasks, 2000);
});

function loadTasks() {
  chrome.runtime.sendMessage({ action: 'getTasks' }, (response) => {
    if (response && response.tasks) {
      displayTasks(response.tasks);
    }
  });
}

function displayTasks(tasks) {
  const container = document.getElementById('tasks');
  
  if (!tasks || tasks.length === 0) {
    container.innerHTML = '<div class="empty">No active downloads</div>';
    return;
  }

  container.innerHTML = tasks.map(task => `
    <div class="task" data-id="${task.task_id}">
      <div class="task-name">${escapeHtml(task.filename)}</div>
      <div class="task-progress">
        <div class="task-progress-bar" style="width: ${task.progress || 0}%"></div>
      </div>
      <div class="task-info">
        <span>${formatSize(task.downloaded_size)} / ${formatSize(task.total_size)}</span>
        <span>${task.status}</span>
        <button class="btn" onclick="toggleTask('${task.task_id}', '${task.status}')">
          ${task.status === 'downloading' ? 'Pause' : 'Resume'}
        </button>
      </div>
    </div>
  `).join('');
}

function toggleTask(taskId, status) {
  if (status === 'downloading') {
    chrome.runtime.sendMessage({ action: 'pauseTask', taskId });
  } else {
    chrome.runtime.sendMessage({ action: 'resumeTask', taskId });
  }
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
