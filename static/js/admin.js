/**
 * SpendWise - Admin Dashboard Logic
 * System metrics, user management, and login activity visualization
 */

function formatCurrency(amount) {
  const num = Number(amount) || 0;
  return '₹' + num.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(title, message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconClass = type === 'success' ? 'fa-circle-check' :
                    type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info';

  toast.innerHTML = `
    <div class="toast-icon"><i class="fa-solid ${iconClass}"></i></div>
    <div class="toast-content">
      <div class="toast-title">${escapeHtml(title)}</div>
      <div class="toast-message">${escapeHtml(message)}</div>
    </div>
    <button class="toast-close" aria-label="Close notification">&times;</button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => toast.remove());

  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

let adminLoginsChart = null;
let allUsersData = [];

document.addEventListener('DOMContentLoaded', () => {
  loadAdminStats();
  loadAdminUsers();
  setupUserSearch();
});

async function loadAdminStats() {
  try {
    const res = await fetch('/api/admin/stats');
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/admin/login';
      return;
    }
    const data = await res.json();
    if (!data.success) return;

    // Stat Cards
    document.getElementById('adminTotalUsers').textContent = data.total_users || 0;
    document.getElementById('adminTotalLogins').textContent = data.total_logins || 0;
    document.getElementById('adminTotalTransactions').textContent = data.total_transactions || 0;
    document.getElementById('adminTotalMoney').textContent = formatCurrency(data.total_money_tracked || 0);

    // Render 7-day logins line chart
    renderLoginsLineChart(data.logins_7_days || []);

    // Render Recent Activity Feed
    renderActivityFeed(data.recent_activity || []);

  } catch (err) {
    console.error('Failed to load admin stats:', err);
    showToast('Error', 'Failed to retrieve administrative metrics', 'error');
  }
}

function renderLoginsLineChart(loginsData) {
  const ctx = document.getElementById('adminLoginsLineChart');
  if (!ctx) return;

  const labels = loginsData.map(d => d.date);
  const counts = loginsData.map(d => d.count);

  if (adminLoginsChart) {
    adminLoginsChart.destroy();
  }

  adminLoginsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length > 0 ? labels : ['No recent logins'],
      datasets: [{
        label: 'Logins',
        data: counts.length > 0 ? counts : [0],
        borderColor: '#7c3aed',
        backgroundColor: 'rgba(124, 58, 237, 0.08)',
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#7c3aed',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Logins: ${ctx.raw}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: "'Plus Jakarta Sans', sans-serif" } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            precision: 0,
            font: { family: "'Plus Jakarta Sans', sans-serif" }
          }
        }
      }
    }
  });
}

function renderActivityFeed(feedItems) {
  const container = document.getElementById('adminActivityFeed');
  if (!container) return;
  container.innerHTML = '';

  if (!feedItems || feedItems.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--gray-400); padding: 2rem 0;">
        No recent activity recorded
      </div>
    `;
    return;
  }

  feedItems.forEach(item => {
    const div = document.createElement('div');
    div.className = 'activity-item';

    const isLogin = item.type === 'login';
    const iconClass = isLogin ? 'fa-key' : 'fa-receipt';
    const iconColor = isLogin ? 'var(--purple-600)' : 'var(--blue-600)';

    div.innerHTML = `
      <div class="activity-icon" style="color: ${iconColor};">
        <i class="fa-solid ${iconClass}"></i>
      </div>
      <div class="activity-details">
        <div><strong>${escapeHtml(item.user_name)}</strong> ${escapeHtml(item.description)}</div>
        <div class="activity-time">${escapeHtml(item.timestamp)}</div>
      </div>
    `;
    container.appendChild(div);
  });
}

async function loadAdminUsers() {
  try {
    const res = await fetch('/api/admin/users');
    const data = await res.json();
    if (data.success) {
      allUsersData = data.users || [];
      renderUsersTable(allUsersData);
    }
  } catch (err) {
    console.error('Failed to load users:', err);
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById('adminUsersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!users || users.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; color: var(--gray-400); padding: 2rem;">
          No matching user accounts found
        </td>
      </tr>
    `;
    return;
  }

  users.forEach(u => {
    const tr = document.createElement('tr');
    const isActive = (u.status || 'active') === 'active';
    const isAdmin = u.role === 'admin';

    tr.innerHTML = `
      <td style="color: var(--gray-400); font-weight: 600;">#${u.id}</td>
      <td>
        <div style="font-weight: 600; color: var(--gray-900);">${escapeHtml(u.name)}</div>
      </td>
      <td style="color: var(--gray-600);">${escapeHtml(u.email)}</td>
      <td>
        <span class="badge ${isAdmin ? 'admin-badge' : 'badge-purple'}">
          ${escapeHtml(u.role)}
        </span>
      </td>
      <td style="color: var(--gray-500);">${escapeHtml(u.created_at || 'N/A')}</td>
      <td style="text-align: center; font-weight: 600;">${u.login_count || 0}</td>
      <td style="color: var(--gray-500);">${escapeHtml(u.last_login || 'Never')}</td>
      <td style="text-align: center; font-weight: 600;">${u.transaction_count || 0}</td>
      <td style="text-align: center;">
        <span class="badge ${isActive ? 'badge-income' : 'badge-expense'}">
          ${isActive ? 'Active' : 'Disabled'}
        </span>
      </td>
      <td style="text-align: center;">
        ${isAdmin ? '<span style="color: var(--gray-400); font-size: 0.75rem;">Protected</span>' : `
          <button type="button" class="btn btn-sm ${isActive ? 'btn-outline' : 'btn-success'} toggle-status-btn" data-id="${u.id}" data-active="${isActive}">
            ${isActive ? 'Disable' : 'Enable'}
          </button>
        `}
      </td>
    `;

    const toggleBtn = tr.querySelector('.toggle-status-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => toggleUserStatus(u.id, isActive));
    }

    tbody.appendChild(tr);
  });
}

async function toggleUserStatus(userId, currentlyActive) {
  const newStatus = currentlyActive ? 'disabled' : 'active';
  const actionText = currentlyActive ? 'Disable' : 'Enable';

  if (!confirm(`Are you sure you want to ${actionText.toLowerCase()} this user account?`)) return;

  try {
    const res = await fetch(`/api/admin/users/${userId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Status Updated', `User account set to ${newStatus}`, 'success');
      loadAdminUsers();
      loadAdminStats();
    } else {
      showToast('Error', data.message || 'Could not update user status', 'error');
    }
  } catch (err) {
    showToast('Error', 'Network error updating user', 'error');
  }
}

function setupUserSearch() {
  const searchInput = document.getElementById('adminUserSearchInput');
  if (!searchInput) return;

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    if (!query) {
      renderUsersTable(allUsersData);
      return;
    }

    const filtered = allUsersData.filter(u =>
      (u.name && u.name.toLowerCase().includes(query)) ||
      (u.email && u.email.toLowerCase().includes(query))
    );
    renderUsersTable(filtered);
  });
}
