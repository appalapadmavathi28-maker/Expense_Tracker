/**
 * SpendWise - Frontend Application Logic
 * Modern, responsive financial dashboard with Chart.js integration
 */

// ==========================================
// 1. GLOBAL CONSTANTS & HELPERS
// ==========================================

const EXPENSE_CATEGORIES = ['Food', 'Shopping', 'Travel', 'Education', 'Bills', 'Health', 'Other'];
const INCOME_CATEGORIES = ['Salary', 'Freelance', 'Business', 'Gift', 'Other'];

const CATEGORY_ICONS = {
  Food: 'fa-utensils',
  Shopping: 'fa-bag-shopping',
  Travel: 'fa-plane',
  Education: 'fa-graduation-cap',
  Bills: 'fa-file-invoice-dollar',
  Health: 'fa-heart-pulse',
  Salary: 'fa-briefcase',
  Freelance: 'fa-laptop-code',
  Business: 'fa-chart-pie',
  Gift: 'fa-gift',
  Other: 'fa-asterisk'
};

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * Currency Formatter (Single point of change for currency symbol)
 */
function formatCurrency(amount) {
  const num = Number(amount) || 0;
  return '₹' + num.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

/**
 * Escape HTML to prevent Cross-Site Scripting (XSS)
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Toast Notification System
 */
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
  closeBtn.addEventListener('click', () => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    setTimeout(() => toast.remove(), 250);
  });

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(() => toast.remove(), 250);
    }
  }, 4000);
}

// ==========================================
// 2. STATE MANAGEMENT
// ==========================================

const appState = {
  currentUser: null,
  activeView: 'dashboard',
  currentYear: new Date().getFullYear(),
  currentMonth: new Date().getMonth() + 1, // 1-12
  selectedReportYear: new Date().getFullYear(),
  selectedReportMonth: new Date().getMonth() + 1,
  transactions: [],
  filteredTransactions: [],
  categoriesChart: null,
  incomeExpenseChart: null,
  pendingDeleteId: null,
  txSearchDebounceTimer: null
};

// ==========================================
// 3. INITIALIZATION & ROUTING
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
  initDateDisplay();
  setupSidebarNav();
  setupMobileDrawer();
  setupModals();
  setupTransactionForm();
  setupFilters();
  setupReportsControls();
  setupBudgets();
  setupProfileModal();
  loadUserProfile();
  loadDashboardData();
});

function initDateDisplay() {
  const dateEl = document.getElementById('currentDateDisplay');
  if (dateEl) {
    const today = new Date();
    const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
    dateEl.textContent = today.toLocaleDateString('en-US', options);
  }
}

/**
 * Handle view tab switching
 */
function switchView(viewName) {
  appState.activeView = viewName;

  // Update Nav links
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.dataset.view === viewName) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Update Views
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active');
  });

  const activeSec = document.getElementById(`view${capitalize(viewName)}`);
  if (activeSec) {
    activeSec.classList.add('active');
  }

  // Update Page Title
  const titleMap = {
    dashboard: 'Overview',
    transactions: 'Transactions',
    reports: 'Monthly Reports',
    budgets: 'Budgets & Goals'
  };
  const titleEl = document.getElementById('pageTitle');
  if (titleEl) titleEl.textContent = titleMap[viewName] || 'SpendWise';

  // Trigger relevant data load
  if (viewName === 'dashboard') {
    loadDashboardData();
  } else if (viewName === 'transactions') {
    loadTransactions();
  } else if (viewName === 'reports') {
    loadMonthlyReport();
  } else if (viewName === 'budgets') {
    loadBudgets();
  }

  // Close mobile drawer if open
  closeMobileSidebar();
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function setupSidebarNav() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      const view = link.dataset.view;
      if (view) {
        e.preventDefault();
        switchView(view);
      }
    });
  });

  const viewAllBtn = document.getElementById('viewAllTxBtn');
  if (viewAllBtn) {
    viewAllBtn.addEventListener('click', () => switchView('transactions'));
  }
}

function setupMobileDrawer() {
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('appSidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (mobileBtn && sidebar && overlay) {
    mobileBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
      overlay.classList.toggle('mobile-open');
    });

    overlay.addEventListener('click', closeMobileSidebar);
  }
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('appSidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (sidebar) sidebar.classList.remove('mobile-open');
  if (overlay) overlay.classList.remove('mobile-open');
}

// ==========================================
// 4. USER PROFILE & AUTH CHECK
// ==========================================

async function loadUserProfile() {
  try {
    const res = await fetch('/api/me');
    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }
    const data = await res.json();
    if (data.success && data.user) {
      appState.currentUser = data.user;
      const avatarEl = document.getElementById('sidebarAvatar');
      const nameEl = document.getElementById('sidebarUserName');
      const emailEl = document.getElementById('sidebarUserEmail');
      const topAvatar = document.getElementById('topbarAvatar');
      const topName = document.getElementById('topbarUserName');

      if (nameEl) nameEl.textContent = data.user.name;
      if (emailEl) emailEl.textContent = data.user.email;
      if (avatarEl) avatarEl.textContent = data.user.name.charAt(0).toUpperCase();
      if (topAvatar) topAvatar.textContent = data.user.name.charAt(0).toUpperCase();
      if (topName) topName.textContent = data.user.name;

      const profileNameInput = document.getElementById('profileNameInput');
      const profileEmailDisplay = document.getElementById('profileEmailDisplay');
      if (profileNameInput) profileNameInput.value = data.user.name;
      if (profileEmailDisplay) profileEmailDisplay.value = data.user.email;
    }
  } catch (err) {
    console.error('Failed to load user profile', err);
  }
}

function setupProfileModal() {
  const btn = document.getElementById('userProfileBtn');
  const topbarBtn = document.getElementById('topbarProfileBtn');
  const modal = document.getElementById('profileModalBackdrop');
  const closeBtn = document.getElementById('profileModalCloseBtn');
  const cancelBtn = document.getElementById('profileCancelBtn');
  const form = document.getElementById('profileForm');

  if (btn && modal) {
    btn.addEventListener('click', () => modal.classList.add('active'));
  }
  if (topbarBtn && modal) {
    topbarBtn.addEventListener('click', () => modal.classList.add('active'));
  }
  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.remove('active'));

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nameInput = document.getElementById('profileNameInput');
      const curPwdInput = document.getElementById('currentPasswordInput');
      const newPwdInput = document.getElementById('newPasswordInput');
      const nameError = document.getElementById('profileNameError');
      const newPwdError = document.getElementById('newPasswordError');

      nameError.classList.remove('visible');
      newPwdError.classList.remove('visible');

      const name = nameInput.value.trim();
      const current_password = curPwdInput.value;
      const new_password = newPwdInput.value;

      if (name.length < 2) {
        nameError.classList.add('visible');
        return;
      }

      if (new_password) {
        const hasLength = new_password.length >= 8;
        const hasLetter = /[a-zA-Z]/.test(new_password);
        const hasNumber = /[0-9]/.test(new_password);
        if (!hasLength || !hasLetter || !hasNumber) {
          newPwdError.classList.add('visible');
          return;
        }
      }

      try {
        const res = await fetch('/api/change-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, current_password, new_password })
        });
        const data = await res.json();
        if (data.success) {
          showToast('Profile Updated', 'Your profile details have been saved.', 'success');
          modal.classList.remove('active');
          loadUserProfile();
          curPwdInput.value = '';
          newPwdInput.value = '';
        } else {
          showToast('Update Failed', data.message || 'Could not update profile', 'error');
        }
      } catch (err) {
        showToast('Error', 'Network error while updating profile', 'error');
      }
    });
  }
}

// ==========================================
// 5. DASHBOARD VIEW & CHARTS
// ==========================================

async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard-summary');
    if (!res.ok) throw new Error('Failed to fetch summary');
    const data = await res.json();

    if (!data.success) return;

    // Stat Cards
    const totalBalance = (data.total_income || 0) - (data.total_expenses || 0);
    const balanceEl = document.getElementById('cardTotalBalance');
    const incomeEl = document.getElementById('cardTotalIncome');
    const expensesEl = document.getElementById('cardTotalExpenses');
    const savingsRateEl = document.getElementById('cardSavingsRate');

    if (balanceEl) balanceEl.textContent = formatCurrency(totalBalance);
    if (incomeEl) incomeEl.textContent = formatCurrency(data.total_income || 0);
    if (expensesEl) expensesEl.textContent = formatCurrency(data.total_expenses || 0);

    const savingsRate = data.total_income > 0
      ? Math.max(0, Math.round((totalBalance / data.total_income) * 100))
      : 0;
    if (savingsRateEl) savingsRateEl.textContent = `${savingsRate}%`;

    // Render Charts
    renderIncomeExpenseChart(data.monthly_bar_data || []);
    renderCategoryDoughnutChart(data.category_data || {});

    // Render This Month Summary
    renderThisMonthSummary(data.this_month_data || {});

    // Render Recent Transactions
    renderRecentTransactions(data.recent_transactions || []);

  } catch (err) {
    console.error('Error loading dashboard:', err);
    showToast('Dashboard Error', 'Could not load summary data', 'error');
  }
}

/**
 * Render Chart.js Income vs Expense 12 Months Bar Chart
 */
function renderIncomeExpenseChart(monthlyData) {
  const ctx = document.getElementById('incomeExpenseChart');
  if (!ctx) return;

  const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const incomeValues = new Array(12).fill(0);
  const expenseValues = new Array(12).fill(0);

  monthlyData.forEach(item => {
    const idx = (item.month || 1) - 1;
    if (idx >= 0 && idx < 12) {
      incomeValues[idx] = item.income || 0;
      expenseValues[idx] = item.expense || 0;
    }
  });

  if (appState.incomeExpenseChart) {
    appState.incomeExpenseChart.destroy();
  }

  appState.incomeExpenseChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Income',
          data: incomeValues,
          backgroundColor: '#10b981',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.8
        },
        {
          label: 'Expenses',
          data: expenseValues,
          backgroundColor: '#7c3aed',
          borderRadius: 6,
          barPercentage: 0.6,
          categoryPercentage: 0.8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            boxWidth: 14,
            usePointStyle: true,
            pointStyle: 'circle',
            font: { family: "'Plus Jakarta Sans', sans-serif", weight: '600' }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.dataset.label + ': ' + formatCurrency(context.raw);
            }
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
            font: { family: "'Plus Jakarta Sans', sans-serif" },
            callback: function(value) {
              return '₹' + value;
            }
          }
        }
      }
    }
  });
}

/**
 * Render Chart.js Category Doughnut Chart
 */
function renderCategoryDoughnutChart(categoryData) {
  const ctx = document.getElementById('categoryDoughnutChart');
  if (!ctx) return;

  const categories = Object.keys(categoryData);
  const values = Object.values(categoryData);

  const colorPalette = [
    '#7c3aed', '#3b82f6', '#10b981', '#f59e0b',
    '#ec4899', '#8b5cf6', '#06b6d4', '#64748b'
  ];

  if (appState.categoriesChart) {
    appState.categoriesChart.destroy();
  }

  if (categories.length === 0) {
    // Show placeholder if no expenses recorded
    appState.categoriesChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['No Expenses Yet'],
        datasets: [{
          data: [1],
          backgroundColor: ['#e2e8f0'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  appState.categoriesChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categories,
      datasets: [{
        data: values,
        backgroundColor: colorPalette.slice(0, categories.length),
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            pointStyle: 'circle',
            font: { family: "'Plus Jakarta Sans', sans-serif", weight: '500', size: 12 }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const val = context.raw || 0;
              return `${label}: ${formatCurrency(val)}`;
            }
          }
        }
      }
    }
  });
}

/**
 * Render This Month Summary & Progress Bars
 */
function renderThisMonthSummary(thisMonthData) {
  const monthNameEl = document.getElementById('thisMonthName');
  const badgeEl = document.getElementById('thisMonthTotalBadge');
  const container = document.getElementById('monthlyProgressContainer');

  const curMonthIndex = new Date().getMonth();
  if (monthNameEl) monthNameEl.textContent = `${MONTH_NAMES[curMonthIndex]} ${new Date().getFullYear()}`;

  const totalSpent = thisMonthData.total_expense || 0;
  if (badgeEl) badgeEl.textContent = formatCurrency(totalSpent);

  if (!container) return;
  container.innerHTML = '';

  const categories = thisMonthData.categories || {};
  const entries = Object.entries(categories);

  if (entries.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--gray-400); padding: 1.5rem 0;">
        <i class="fa-regular fa-folder-open" style="font-size: 1.8rem; margin-bottom: 0.5rem; display: block;"></i>
        No expenses recorded this month
      </div>
    `;
    return;
  }

  // Sort descending by amount
  entries.sort((a, b) => b[1] - a[1]);

  entries.slice(0, 5).forEach(([cat, amount]) => {
    const pct = totalSpent > 0 ? Math.round((amount / totalSpent) * 100) : 0;
    const item = document.createElement('div');
    item.className = 'progress-item';
    item.innerHTML = `
      <div class="progress-item-header">
        <span><i class="fa-solid ${CATEGORY_ICONS[cat] || 'fa-tag'}" style="color: var(--purple-600); margin-right: 0.4rem;"></i> ${escapeHtml(cat)}</span>
        <span>${formatCurrency(amount)} (${pct}%)</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width: ${pct}%;"></div>
      </div>
    `;
    container.appendChild(item);
  });
}

/**
 * Render Recent Transactions List on Dashboard
 */
function renderRecentTransactions(transactions) {
  const tbody = document.getElementById('recentTransactionsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--gray-400); padding: 2rem;">
          No transactions yet. Click "+ Add Transaction" to begin!
        </td>
      </tr>
    `;
    return;
  }

  transactions.forEach(tx => {
    const isIncome = tx.type === 'income';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <span class="badge ${isIncome ? 'badge-income' : 'badge-expense'}">
          <i class="fa-solid ${isIncome ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
          ${isIncome ? 'Income' : 'Expense'}
        </span>
      </td>
      <td>
        <span style="font-weight: 500;">
          <i class="fa-solid ${CATEGORY_ICONS[tx.category] || 'fa-tag'}" style="color: var(--gray-400); margin-right: 0.35rem;"></i>
          ${escapeHtml(tx.category)}
        </span>
      </td>
      <td>${escapeHtml(tx.description)}</td>
      <td style="color: var(--gray-500);">${escapeHtml(tx.date)}</td>
      <td style="text-align: right;" class="${isIncome ? 'table-amount-income' : 'table-amount-expense'}">
        ${isIncome ? '+' : '-'}${formatCurrency(tx.amount)}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ==========================================
// 6. TRANSACTIONS VIEW (LIST, FILTER, CSV)
// ==========================================

async function loadTransactions() {
  const search = document.getElementById('txSearchInput')?.value.trim() || '';
  const type = document.getElementById('txTypeFilter')?.value || '';
  const category = document.getElementById('txCategoryFilter')?.value || '';
  const startDate = document.getElementById('txStartDateFilter')?.value || '';
  const endDate = document.getElementById('txEndDateFilter')?.value || '';

  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (type) params.append('type', type);
  if (category) params.append('category', category);
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  try {
    const res = await fetch(`/api/transactions?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load transactions');
    const data = await res.json();

    if (data.success) {
      appState.filteredTransactions = data.transactions || [];
      renderTransactionsTable(appState.filteredTransactions);
    }
  } catch (err) {
    console.error('Error fetching transactions:', err);
    showToast('Error', 'Failed to retrieve transactions', 'error');
  }
}

function renderTransactionsTable(transactions) {
  const tbody = document.getElementById('allTransactionsTableBody');
  const emptyState = document.getElementById('txEmptyState');
  const counterText = document.getElementById('txCounterText');

  if (!tbody) return;
  tbody.innerHTML = '';

  if (counterText) {
    counterText.textContent = `Showing ${transactions.length} transaction${transactions.length === 1 ? '' : 's'}`;
  }

  if (!transactions || transactions.length === 0) {
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  if (emptyState) emptyState.style.display = 'none';

  transactions.forEach(tx => {
    const isIncome = tx.type === 'income';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <span class="badge ${isIncome ? 'badge-income' : 'badge-expense'}">
          <i class="fa-solid ${isIncome ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
          ${isIncome ? 'Income' : 'Expense'}
        </span>
      </td>
      <td>
        <span style="font-weight: 500;">
          <i class="fa-solid ${CATEGORY_ICONS[tx.category] || 'fa-tag'}" style="color: var(--gray-400); margin-right: 0.35rem;"></i>
          ${escapeHtml(tx.category)}
        </span>
      </td>
      <td style="font-weight: 500; color: var(--gray-800);">${escapeHtml(tx.description)}</td>
      <td style="color: var(--gray-500);">${escapeHtml(tx.date)}</td>
      <td style="text-align: right;" class="${isIncome ? 'table-amount-income' : 'table-amount-expense'}">
        ${isIncome ? '+' : '-'}${formatCurrency(tx.amount)}
      </td>
      <td style="text-align: center;">
        <div class="action-buttons" style="justify-content: center;">
          <button type="button" class="action-btn edit-btn" title="Edit transaction" data-id="${tx.id}">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button type="button" class="action-btn delete-btn" title="Delete transaction" data-id="${tx.id}">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      </td>
    `;

    // Hook edit & delete
    tr.querySelector('.edit-btn').addEventListener('click', () => openEditTxModal(tx));
    tr.querySelector('.delete-btn').addEventListener('click', () => openDeleteModal(tx.id));

    tbody.appendChild(tr);
  });
}

function setupFilters() {
  const searchInput = document.getElementById('txSearchInput');
  const typeFilter = document.getElementById('txTypeFilter');
  const catFilter = document.getElementById('txCategoryFilter');
  const startInput = document.getElementById('txStartDateFilter');
  const endInput = document.getElementById('txEndDateFilter');
  const resetBtn = document.getElementById('txResetFiltersBtn');
  const exportBtn = document.getElementById('exportCsvBtn');
  const emptyAddBtn = document.getElementById('emptyAddTxBtn');

  // Populate Category Filter dropdown with both Expense and Income categories
  if (catFilter) {
    const allCats = Array.from(new Set([...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES]));
    catFilter.innerHTML = '<option value="">All Categories</option>' +
      allCats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
  }

  // Debounced Search
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(appState.txSearchDebounceTimer);
      appState.txSearchDebounceTimer = setTimeout(() => {
        loadTransactions();
      }, 300);
    });
  }

  // Filter change events
  if (typeFilter) typeFilter.addEventListener('change', loadTransactions);
  if (catFilter) catFilter.addEventListener('change', loadTransactions);
  if (startInput) startInput.addEventListener('change', loadTransactions);
  if (endInput) endInput.addEventListener('change', loadTransactions);

  // Reset Filters
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (typeFilter) typeFilter.value = '';
      if (catFilter) catFilter.value = '';
      if (startInput) startInput.value = '';
      if (endInput) endInput.value = '';
      loadTransactions();
    });
  }

  // Export CSV
  if (exportBtn) {
    exportBtn.addEventListener('click', exportFilteredTransactionsToCSV);
  }

  if (emptyAddBtn) {
    emptyAddBtn.addEventListener('click', () => openAddTxModal());
  }
}

/**
 * CSV Export with Formula Injection Protection
 * Protects against formula injection by prefixing '=', '+', '-', '@', '\t', '\r' with '\''
 */
function exportFilteredTransactionsToCSV() {
  const txs = appState.filteredTransactions;
  if (!txs || txs.length === 0) {
    showToast('Export Notice', 'No transactions to export for current filters', 'info');
    return;
  }

  function sanitizeCsvCell(value) {
    if (value === null || value === undefined) return '""';
    let str = String(value);

    // CSV Formula Injection Check: If starts with =, +, -, @, \t, \r, prepend a single quote '
    if (/^[=+\-@\t\r]/.test(str)) {
      str = "'" + str;
    }

    // Escape quotes
    str = str.replace(/"/g, '""');
    return `"${str}"`;
  }

  const headers = ['ID', 'Type', 'Category', 'Description', 'Amount', 'Date', 'Created At'];
  const rows = [headers.join(',')];

  txs.forEach(tx => {
    const row = [
      sanitizeCsvCell(tx.id),
      sanitizeCsvCell(tx.type),
      sanitizeCsvCell(tx.category),
      sanitizeCsvCell(tx.description),
      sanitizeCsvCell(tx.amount),
      sanitizeCsvCell(tx.date),
      sanitizeCsvCell(tx.created_at || '')
    ];
    rows.push(row.join(','));
  });

  const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(rows.join('\n'));
  const link = document.createElement('a');
  link.setAttribute('href', csvContent);
  link.setAttribute('download', `SpendWise_Transactions_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast('Export Successful', `Exported ${txs.length} transactions as CSV`, 'success');
}

// ==========================================
// 7. TRANSACTION MODAL (ADD / EDIT / DELETE)
// ==========================================

let activeTxType = 'expense';

function setupModals() {
  const addBtn1 = document.getElementById('openAddTxModalBtn');
  const addBtn2 = document.getElementById('openAddTxModalBtn2');
  const modalClose = document.getElementById('txModalCloseBtn');
  const cancelBtn = document.getElementById('txCancelBtn');
  const delCancelBtn = document.getElementById('deleteCancelBtn');
  const delConfirmBtn = document.getElementById('deleteConfirmBtn');

  if (addBtn1) addBtn1.addEventListener('click', () => openAddTxModal());
  if (addBtn2) addBtn2.addEventListener('click', () => openAddTxModal());

  if (modalClose) {
    modalClose.addEventListener('click', () => {
      document.getElementById('txModalBackdrop').classList.remove('active');
    });
  }
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      document.getElementById('txModalBackdrop').classList.remove('active');
    });
  }

  // Type Toggle Buttons inside Modal
  const expenseBtn = document.getElementById('typeExpenseBtn');
  const incomeBtn = document.getElementById('typeIncomeBtn');

  if (expenseBtn && incomeBtn) {
    expenseBtn.addEventListener('click', () => setModalTxType('expense'));
    incomeBtn.addEventListener('click', () => setModalTxType('income'));
  }

  // Delete Modal
  if (delCancelBtn) {
    delCancelBtn.addEventListener('click', () => {
      document.getElementById('deleteModalBackdrop').classList.remove('active');
    });
  }
  if (delConfirmBtn) {
    delConfirmBtn.addEventListener('click', executeDeleteTransaction);
  }
}

function setModalTxType(type) {
  activeTxType = type;
  const expenseBtn = document.getElementById('typeExpenseBtn');
  const incomeBtn = document.getElementById('typeIncomeBtn');
  const catSelect = document.getElementById('txCategorySelect');

  if (type === 'expense') {
    expenseBtn.className = 'type-toggle-btn active expense';
    incomeBtn.className = 'type-toggle-btn income';
    populateModalCategories(EXPENSE_CATEGORIES);
  } else {
    incomeBtn.className = 'type-toggle-btn active income';
    expenseBtn.className = 'type-toggle-btn expense';
    populateModalCategories(INCOME_CATEGORIES);
  }
}

function populateModalCategories(categories, selectedVal = '') {
  const select = document.getElementById('txCategorySelect');
  if (!select) return;
  select.innerHTML = categories.map(cat => `
    <option value="${escapeHtml(cat)}" ${cat === selectedVal ? 'selected' : ''}>${escapeHtml(cat)}</option>
  `).join('');
}

function openAddTxModal() {
  const modal = document.getElementById('txModalBackdrop');
  const title = document.getElementById('txModalTitle');
  const editId = document.getElementById('txEditId');
  const amountInput = document.getElementById('txAmountInput');
  const descInput = document.getElementById('txDescriptionInput');
  const dateInput = document.getElementById('txDateInput');

  clearTxErrors();
  title.textContent = 'Add Transaction';
  editId.value = '';
  amountInput.value = '';
  descInput.value = '';

  // Default to today's date YYYY-MM-DD
  const today = new Date().toISOString().split('T')[0];
  dateInput.value = today;

  setModalTxType('expense');
  modal.classList.add('active');
}

function openEditTxModal(tx) {
  const modal = document.getElementById('txModalBackdrop');
  const title = document.getElementById('txModalTitle');
  const editId = document.getElementById('txEditId');
  const amountInput = document.getElementById('txAmountInput');
  const descInput = document.getElementById('txDescriptionInput');
  const dateInput = document.getElementById('txDateInput');

  clearTxErrors();
  title.textContent = 'Edit Transaction';
  editId.value = tx.id;
  amountInput.value = tx.amount;
  descInput.value = tx.description;
  dateInput.value = tx.date;

  setModalTxType(tx.type);
  populateModalCategories(tx.type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES, tx.category);

  modal.classList.add('active');
}

function clearTxErrors() {
  document.getElementById('txCategoryError').classList.remove('visible');
  document.getElementById('txAmountError').classList.remove('visible');
  document.getElementById('txDescriptionError').classList.remove('visible');
  document.getElementById('txDateError').classList.remove('visible');
}

function setupTransactionForm() {
  const form = document.getElementById('txForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearTxErrors();

    const editId = document.getElementById('txEditId').value;
    const type = activeTxType;
    const category = document.getElementById('txCategorySelect').value;
    const amountVal = parseFloat(document.getElementById('txAmountInput').value);
    const description = document.getElementById('txDescriptionInput').value.trim();
    const date = document.getElementById('txDateInput').value;

    let isValid = true;

    if (!category) {
      document.getElementById('txCategoryError').classList.add('visible');
      isValid = false;
    }
    if (isNaN(amountVal) || amountVal <= 0) {
      document.getElementById('txAmountError').classList.add('visible');
      isValid = false;
    }
    if (!description) {
      document.getElementById('txDescriptionError').classList.add('visible');
      isValid = false;
    }
    if (!date) {
      document.getElementById('txDateError').classList.add('visible');
      isValid = false;
    }

    if (!isValid) return;

    const saveBtn = document.getElementById('txSaveBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

    const payload = { type, category, amount: amountVal, description, date };
    const url = editId ? `/api/transactions/${editId}` : '/api/transactions';
    const method = editId ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showToast('Success', editId ? 'Transaction updated successfully' : 'Transaction added successfully', 'success');
        document.getElementById('txModalBackdrop').classList.remove('active');

        // Refresh currently active view data
        if (appState.activeView === 'dashboard') {
          loadDashboardData();
        } else if (appState.activeView === 'transactions') {
          loadTransactions();
        } else if (appState.activeView === 'reports') {
          loadMonthlyReport();
        }
      } else {
        showToast('Validation Error', data.message || 'Could not save transaction', 'error');
      }
    } catch (err) {
      showToast('Error', 'Network error while saving transaction', 'error');
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Transaction';
    }
  });
}

function openDeleteModal(txId) {
  appState.pendingDeleteId = txId;
  const modal = document.getElementById('deleteModalBackdrop');
  if (modal) modal.classList.add('active');
}

async function executeDeleteTransaction() {
  if (!appState.pendingDeleteId) return;

  const btn = document.getElementById('deleteConfirmBtn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';

  try {
    const res = await fetch(`/api/transactions/${appState.pendingDeleteId}`, {
      method: 'DELETE'
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast('Deleted', 'Transaction has been deleted', 'success');
      document.getElementById('deleteModalBackdrop').classList.remove('active');

      if (appState.activeView === 'transactions') {
        loadTransactions();
      } else {
        loadDashboardData();
      }
    } else {
      showToast('Error', data.message || 'Could not delete transaction', 'error');
    }
  } catch (err) {
    showToast('Error', 'Network error while deleting', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Yes, Delete';
    appState.pendingDeleteId = null;
  }
}

// ==========================================
// 8. MONTHLY REPORTS VIEW
// ==========================================

function setupReportsControls() {
  const yearSelect = document.getElementById('reportYearSelect');
  const monthSelect = document.getElementById('reportMonthSelect');

  if (!yearSelect || !monthSelect) return;

  // Populate Year options: Current year - 3 to Current year + 1
  const currentYear = new Date().getFullYear();
  yearSelect.innerHTML = '';
  for (let y = currentYear - 3; y <= currentYear + 1; y++) {
    const opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y;
    if (y === appState.selectedReportYear) opt.selected = true;
    yearSelect.appendChild(opt);
  }

  // Pre-select current month
  monthSelect.value = String(appState.selectedReportMonth);

  yearSelect.addEventListener('change', () => {
    appState.selectedReportYear = parseInt(yearSelect.value, 10);
    loadMonthlyReport();
  });

  monthSelect.addEventListener('change', () => {
    appState.selectedReportMonth = parseInt(monthSelect.value, 10);
    loadMonthlyReport();
  });
}

async function loadMonthlyReport() {
  const year = appState.selectedReportYear;
  const month = appState.selectedReportMonth;

  try {
    const res = await fetch(`/api/reports/monthly?year=${year}&month=${month}`);
    if (!res.ok) throw new Error('Failed to load monthly report');
    const data = await res.json();

    if (!data.success) return;

    // Update Selected Month Metric Cards
    const curMonth = data.selected_month_data || {};
    const income = curMonth.income || 0;
    const expenses = curMonth.expenses || 0;
    const savings = income - expenses;
    const savingsRate = income > 0 ? Math.max(0, Math.round((savings / income) * 100)) : 0;

    document.getElementById('reportMonthIncome').textContent = formatCurrency(income);
    document.getElementById('reportMonthExpenses').textContent = formatCurrency(expenses);
    document.getElementById('reportMonthSavings').textContent = formatCurrency(savings);
    document.getElementById('reportMonthSavingsRate').textContent = `${savingsRate}%`;

    // Render 12-Month Annual Breakdown Table
    renderTwelveMonthTable(data.twelve_months_data || [], month);

  } catch (err) {
    console.error('Error loading report:', err);
    showToast('Report Error', 'Could not load monthly report', 'error');
  }
}

function renderTwelveMonthTable(twelveMonths, selectedMonthNum) {
  const tbody = document.getElementById('twelveMonthTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  MONTH_NAMES.forEach((mName, idx) => {
    const mNum = idx + 1;
    const rowData = twelveMonths.find(m => m.month === mNum) || { income: 0, expenses: 0 };
    const inc = rowData.income || 0;
    const exp = rowData.expenses || 0;
    const sav = inc - exp;
    const rate = inc > 0 ? Math.max(0, Math.round((sav / inc) * 100)) : 0;

    const isSelected = mNum === selectedMonthNum;

    const tr = document.createElement('tr');
    if (isSelected) {
      tr.className = 'month-table-highlight';
    }

    tr.innerHTML = `
      <td>
        <strong>${mName}</strong>
        ${isSelected ? '<span class="badge badge-purple" style="margin-left: 0.5rem;">Selected</span>' : ''}
      </td>
      <td style="text-align: right; color: var(--green-600); font-weight: 600;">${formatCurrency(inc)}</td>
      <td style="text-align: right; color: var(--red-500); font-weight: 600;">${formatCurrency(exp)}</td>
      <td style="text-align: right; font-weight: 700; color: ${sav >= 0 ? 'var(--purple-700)' : 'var(--red-600)'};">
        ${formatCurrency(sav)}
      </td>
      <td style="text-align: right; font-weight: 600; color: var(--gray-700);">${rate}%</td>
    `;

    tbody.appendChild(tr);
  });
}

// ==========================================
// 9. BUDGETS & GOALS (EXTRA FEATURE)
// ==========================================

function setupBudgets() {
  const openModalBtn = document.getElementById('openAddBudgetModalBtn');
  const modal = document.getElementById('budgetModalBackdrop');
  const closeBtn = document.getElementById('budgetModalCloseBtn');
  const cancelBtn = document.getElementById('budgetCancelBtn');
  const form = document.getElementById('budgetForm');

  if (openModalBtn && modal) {
    openModalBtn.addEventListener('click', () => {
      document.getElementById('budgetLimitInput').value = '';
      document.getElementById('budgetLimitError').classList.remove('visible');
      modal.classList.add('active');
    });
  }

  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.remove('active'));

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const catSelect = document.getElementById('budgetCategorySelect');
      const limitInput = document.getElementById('budgetLimitInput');
      const errorEl = document.getElementById('budgetLimitError');

      const category = catSelect.value;
      const limit = parseFloat(limitInput.value);

      if (isNaN(limit) || limit <= 0) {
        errorEl.classList.add('visible');
        return;
      }
      errorEl.classList.remove('visible');

      try {
        const res = await fetch('/api/budgets', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category, monthly_limit: limit })
        });
        const data = await res.json();
        if (data.success) {
          showToast('Budget Set', `Monthly budget for ${category} saved`, 'success');
          modal.classList.remove('active');
          loadBudgets();
        } else {
          showToast('Error', data.message || 'Failed to save budget', 'error');
        }
      } catch (err) {
        showToast('Error', 'Network error while saving budget', 'error');
      }
    });
  }
}

async function loadBudgets() {
  const container = document.getElementById('budgetCardGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/budgets');
    const data = await res.json();

    if (!data.success) return;
    container.innerHTML = '';

    const budgets = data.budgets || [];
    if (budgets.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1rem;">
          <div class="empty-icon"><i class="fa-solid fa-bullseye"></i></div>
          <h3 class="empty-title">No monthly budgets configured</h3>
          <p class="empty-desc">Set spending limits for categories like Food, Shopping, or Travel to stay on track.</p>
        </div>
      `;
      return;
    }

    budgets.forEach(b => {
      const spent = b.current_month_spent || 0;
      const limit = b.monthly_limit || 1;
      const pct = Math.min(100, Math.round((spent / limit) * 100));

      let statusBadge = '<span class="badge badge-income"><i class="fa-solid fa-check"></i> On Track</span>';
      let barColor = 'var(--green-500)';

      if (spent >= limit) {
        statusBadge = '<span class="badge badge-expense"><i class="fa-solid fa-triangle-exclamation"></i> Exceeded 100%</span>';
        barColor = 'var(--red-500)';
      } else if (pct >= 80) {
        statusBadge = '<span class="badge badge-warning"><i class="fa-solid fa-bell"></i> Caution 80%+</span>';
        barColor = 'var(--amber-500)';
      }

      const card = document.createElement('div');
      card.className = 'budget-card';
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <div style="width: 38px; height: 38px; border-radius: var(--radius-md); background: var(--purple-50); color: var(--purple-600); display: flex; align-items: center; justify-content: center; font-size: 1.1rem;">
              <i class="fa-solid ${CATEGORY_ICONS[b.category] || 'fa-tag'}"></i>
            </div>
            <div>
              <h4 style="font-size: 1rem;">${escapeHtml(b.category)}</h4>
              <span style="font-size: 0.78rem; color: var(--gray-500);">Monthly Target</span>
            </div>
          </div>
          <div>${statusBadge}</div>
        </div>

        <div>
          <div style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 600; margin-bottom: 0.4rem;">
            <span>Spent: ${formatCurrency(spent)}</span>
            <span style="color: var(--gray-500);">Limit: ${formatCurrency(limit)}</span>
          </div>
          <div class="progress-track" style="height: 10px;">
            <div class="progress-fill" style="width: ${pct}%; background-color: ${barColor};"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--gray-500); margin-top: 0.35rem;">
            <span>${pct}% used</span>
            <span>${spent >= limit ? 'Over budget by ' + formatCurrency(spent - limit) : formatCurrency(limit - spent) + ' remaining'}</span>
          </div>
        </div>

        <div style="border-top: 1px solid var(--border-light); padding-top: 0.6rem; display: flex; justify-content: flex-end;">
          <button type="button" class="btn btn-sm btn-outline delete-budget-btn" data-cat="${escapeHtml(b.category)}" style="color: var(--red-500);">
            <i class="fa-solid fa-trash-can"></i> Remove
          </button>
        </div>
      `;

      card.querySelector('.delete-budget-btn').addEventListener('click', async () => {
        if (!confirm(`Remove budget limit for ${b.category}?`)) return;
        try {
          const res = await fetch(`/api/budgets/${encodeURIComponent(b.category)}`, { method: 'DELETE' });
          const resData = await res.json();
          if (resData.success) {
            showToast('Budget Removed', `Budget for ${b.category} removed`, 'info');
            loadBudgets();
          }
        } catch (err) {
          showToast('Error', 'Failed to remove budget', 'error');
        }
      });

      container.appendChild(card);
    });

  } catch (err) {
    console.error('Error loading budgets:', err);
  }
}
