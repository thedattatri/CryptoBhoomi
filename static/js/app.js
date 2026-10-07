/**
 * CryptoBhoomi — Core Application JavaScript
 * Handles MetaMask connection, contract loading, UI utilities
 */

// ============ CONTRACT LOADING ============

async function loadContractDetails() {
  try {
    const response = await fetch('/api/contract-details');
    const data = await response.json();

    if (data.error) {
      console.error('Contract loading error:', data.error);
      return false;
    }

    // Users Contract
    if (data.Users && data.Users.address) {
      localStorage.setItem('Users_ContractAddress', data.Users.address);
      localStorage.setItem('Users_ContractABI', JSON.stringify(data.Users.abi));
    }

    // LandRegistry Contract
    if (data.LandRegistry && data.LandRegistry.address) {
      localStorage.setItem('LandRegistry_ContractAddress', data.LandRegistry.address);
      localStorage.setItem('LandRegistry_ContractABI', JSON.stringify(data.LandRegistry.abi));
    }

    // TransferOwnership Contract
    if (data.TransferOwnership && data.TransferOwnership.address) {
      localStorage.setItem('TransferOwnership_ContractAddress', data.TransferOwnership.address);
      localStorage.setItem('TransferOwnership_ContractABI', JSON.stringify(data.TransferOwnership.abi));
    }

    return true;
  } catch (error) {
    console.error('Failed to load contract details:', error);
    return false;
  }
}


// ============ WALLET ============

function disconnectWallet() {
  localStorage.removeItem('userAddress');
  localStorage.removeItem('Users_ContractABI');
  localStorage.removeItem('Users_ContractAddress');
  localStorage.removeItem('LandRegistry_ContractABI');
  localStorage.removeItem('LandRegistry_ContractAddress');
  localStorage.removeItem('TransferOwnership_ContractABI');
  localStorage.removeItem('TransferOwnership_ContractAddress');
  localStorage.removeItem('empName');
  localStorage.removeItem('revenueDeptId');
}


// ============ ERROR HANDLING ============

function parseError(error) {
  if (error.code === 4001) return 'Transaction rejected by user';

  try {
    const msgStr = error.message || '';
    const jsonStart = msgStr.indexOf('{');
    if (jsonStart !== -1) {
      const jsonStr = msgStr.slice(jsonStart);
      const parsed = JSON.parse(jsonStr);

      // Try different error formats
      if (parsed.value && parsed.value.data && parsed.value.data.data) {
        const dataObj = parsed.value.data.data;
        const txHash = Object.keys(dataObj)[0];
        if (txHash && dataObj[txHash].reason) {
          return dataObj[txHash].reason;
        }
      }
      if (parsed.message) return parsed.message;
    }
  } catch (e) { /* ignore parse errors */ }

  return error.message || 'Transaction failed';
}


// ============ TOAST NOTIFICATIONS ============

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = { success: 'bi-check-circle', error: 'bi-x-circle', warning: 'bi-exclamation-triangle', info: 'bi-info-circle' };
  toast.innerHTML = `
    <i class="bi ${icons[type] || icons.info}"></i>
    <span class="toast-msg">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;

  container.appendChild(toast);
  setTimeout(() => { if (toast.parentElement) toast.remove(); }, 5000);
}


// ============ LOADING OVERLAY ============

function showLoading(text = 'Processing transaction...') {
  const overlay = document.getElementById('loadingOverlay');
  const textEl = document.getElementById('loadingText');
  if (overlay) { overlay.classList.remove('hidden'); }
  if (textEl) { textEl.textContent = text; }
}

function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) { overlay.classList.add('hidden'); }
}


// ============ PDF POPUP ============

function closePdfPopup() {
  const popup = document.getElementById('pdfPopup');
  if (popup) {
    popup.classList.remove('active');
    document.getElementById('pdfFrame').src = '';
  }
}


// ============ PROMPT MODAL ============

let _promptResolve = null;

function showPrompt(label) {
  return new Promise((resolve) => {
    _promptResolve = resolve;
    const overlay = document.getElementById('promptOverlay');
    const labelEl = document.getElementById('promptLabel');
    const input = document.getElementById('promptInput');

    if (labelEl) labelEl.textContent = label;
    if (input) input.value = '';
    if (overlay) overlay.classList.add('active');
    if (input) input.focus();
  });
}

function resolvePrompt() {
  const input = document.getElementById('promptInput');
  const overlay = document.getElementById('promptOverlay');
  const value = input ? input.value : null;
  if (overlay) overlay.classList.remove('active');
  if (_promptResolve) { _promptResolve(value); _promptResolve = null; }
}

function cancelPrompt() {
  const overlay = document.getElementById('promptOverlay');
  if (overlay) overlay.classList.remove('active');
  if (_promptResolve) { _promptResolve(null); _promptResolve = null; }
}


// ============ NOTIFICATIONS ============

function toggleNotifications() {
  const dropdown = document.getElementById('notifDropdown');
  if (dropdown) dropdown.classList.toggle('active');
}

async function loadNotifications() {
  const addr = localStorage.getItem('userAddress');
  if (!addr) return;

  try {
    const res = await fetch(`/api/notifications/${addr}`);
    const data = await res.json();

    if (data.status === 1 && data.notifications.length > 0) {
      const badge = document.getElementById('notifBadge');
      const list = document.getElementById('notifList');
      const unread = data.notifications.filter(n => !n.read).length;

      if (badge) {
        badge.textContent = unread;
        badge.classList.toggle('hidden', unread === 0);
      }

      if (list) {
        list.innerHTML = data.notifications.map(n =>
          `<div class="notif-item">
            <strong>${n.title}</strong><br>
            <span>${n.message}</span>
            <div class="notif-time">${new Date(n.timestamp).toLocaleString()}</div>
          </div>`
        ).join('');
      }
    }
  } catch (e) { /* silent fail */ }
}

// Poll notifications every 30 seconds
setInterval(loadNotifications, 30000);

// Close notification dropdown on outside click
document.addEventListener('click', function (e) {
  const dropdown = document.getElementById('notifDropdown');
  const btn = document.getElementById('notifBtn');
  if (dropdown && btn && !dropdown.contains(e.target) && !btn.contains(e.target)) {
    dropdown.classList.remove('active');
  }
});

// Load notifications on page load
document.addEventListener('DOMContentLoaded', loadNotifications);


// ============ METAMASK ACCOUNT CHANGE LISTENER ============

if (window.ethereum) {
  window.ethereum.on('accountsChanged', function (accounts) {
    const stored = localStorage.getItem('userAddress');
    if (stored && accounts[0] !== stored) {
      showToast('MetaMask account changed. Please reconnect.', 'warning');
      disconnectWallet();
      setTimeout(() => window.location.href = '/', 1500);
    }
  });

  window.ethereum.on('chainChanged', function () {
    showToast('Network changed. Reloading...', 'warning');
    setTimeout(() => window.location.reload(), 1000);
  });
}

// ============ THEME TOGGLE ============

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);

  const icon = document.getElementById('themeIcon');
  if (icon) {
    icon.className = newTheme === 'light' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  }
}
