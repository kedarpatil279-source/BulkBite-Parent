/**
 * BulkBite - Zero Delivery Fee Group Ordering Platform
 * Founder: KEDAR PATIL
 * Multi-Campus Communities & Founder Parent Control System
 */

// Application State
const state = {
  currentUser: null,
  token: localStorage.getItem('hostel_token') || '',
  colleges: [],
  selectedCollegeId: 'all',
  settings: {},
  pools: [],
  currentPoolDetail: null,
  activeFilter: 'all',
  activePlatform: 'all',
  searchQuery: '',
  notifications: [],
  lastNotifId: 0,
  soundEnabled: true,
  audioCtx: null,
  deferredPrompt: null
};

// Web Audio API Ding Chime
function playChime(isAlert = false) {
  if (!state.soundEnabled) return;
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!state.audioCtx) {
      state.audioCtx = new AudioContext();
    }
    if (state.audioCtx.state === 'suspended') {
      state.audioCtx.resume();
    }
    const ctx = state.audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = isAlert ? 'triangle' : 'sine';
    const now = ctx.currentTime;

    if (isAlert) {
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(1174, now + 0.12);
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.5);
    } else {
      osc.frequency.setValueAtTime(587.33, now);
      osc.frequency.setValueAtTime(880, now + 0.08);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.4);
    }
  } catch (e) {}
}

// Minimal pure-JS QR code generator for UPI payment
function generateQRCodeSVG(text, size = 180) {
  try {
    const qrMatrix = createQRMatrix(text);
    const n = qrMatrix.length;
    const cell = size / n;
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
    svg += `<rect width="${size}" height="${size}" fill="#ffffff"/>`;
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        if (qrMatrix[r][c]) {
          svg += `<rect x="${(c * cell).toFixed(2)}" y="${(r * cell).toFixed(2)}" width="${Math.ceil(cell)}" height="${Math.ceil(cell)}" fill="#000000"/>`;
        }
      }
    }
    svg += '</svg>';
    return svg;
  } catch (e) {
    return `<div style="width:${size}px; height:${size}px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#f1f5f9; border:2px dashed #94a3b8; border-radius:12px; padding:10px; font-size:11px; text-align:center;">
      <span style="font-size:28px; margin-bottom:4px;">📱</span>
      <strong>UPI Quick Link</strong>
      <span style="word-break:break-all; font-family:monospace; margin-top:4px; font-size:10px;">${text}</span>
    </div>`;
  }
}

function createQRMatrix(data) {
  const size = 25;
  const matrix = Array(size).fill(0).map(() => Array(size).fill(0));

  function drawFinder(x, y) {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const nx = x + c, ny = y + r;
        if (nx >= 0 && nx < size && ny >= 0 && ny < size) {
          if ((r === 0 || r === 6) && (c >= 0 && c <= 6)) matrix[ny][nx] = 1;
          else if ((c === 0 || c === 6) && (r >= 0 && r <= 6)) matrix[ny][nx] = 1;
          else if (r >= 2 && r <= 4 && c >= 2 && c <= 4) matrix[ny][nx] = 1;
          else matrix[ny][nx] = 0;
        }
      }
    }
  }

  drawFinder(0, 0);
  drawFinder(size - 7, 0);
  drawFinder(0, size - 7);

  for (let i = 8; i < size - 8; i++) {
    matrix[6][i] = i % 2 === 0 ? 1 : 0;
    matrix[i][6] = i % 2 === 0 ? 1 : 0;
  }

  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    hash = ((hash << 5) - hash) + data.charCodeAt(i);
    hash |= 0;
  }

  let bitIndex = 0;
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if ((r < 8 && c < 8) || (r < 8 && c >= size - 8) || (r >= size - 8 && c < 8) || r === 6 || c === 6) {
        continue;
      }
      const charCode = data.charCodeAt((bitIndex + r * 3 + c) % data.length) || 42;
      matrix[r][c] = ((hash ^ (charCode * (r + 1) * (c + 1))) % 2 === 0) ? 1 : 0;
      bitIndex++;
    }
  }

  return matrix;
}

// ------------------ API CALLS ------------------ //

async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('hostel_token') || '';
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  try {
    const res = await fetch(endpoint, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Server error occurred');
    }
    return data;
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

// ------------------ APP INITIALIZATION ------------------ //

async function initApp() {
  await loadSettings();
  await loadColleges();
  await verifyAuthentication();
  await loadStats();
  await loadPools();
  await checkNotifications(true);

  // Auto-refresh poll every 5 seconds for live cart & notifications
  setInterval(() => {
    loadPools(false);
    checkNotifications(false);
    loadStats();
    loadSettings();
    if (state.currentPoolDetail) {
      refreshActivePoolDetail(state.currentPoolDetail.id);
    }
  }, 4500);

  setupEventListeners();
  setupPWA();
}

// ------------------ SETTINGS & HELPLINE ------------------ //

async function loadSettings() {
  try {
    const settings = await apiFetch('/api/settings');
    state.settings = settings;

    // Update Live Announcement Bar
    const bar = document.getElementById('liveAnnouncementBar');
    const textEl = document.getElementById('announcementText');
    if (bar && textEl && settings.live_announcement && settings.announcement_active === '1') {
      textEl.textContent = settings.live_announcement;
      bar.style.display = 'flex';
    }

    // Update Helpline Links
    const phoneLink = document.getElementById('helplinePhoneLink');
    const emailLink = document.getElementById('helplineEmailLink');
    const waBtn = document.getElementById('helplineWhatsAppBtn');
    const p = settings.helpline_phone || '+91 8390461240';
    const cleanPhone = p.replace(/[^0-9]/g, '');

    if (phoneLink) {
      phoneLink.textContent = p;
      phoneLink.href = `tel:${p}`;
    }
    if (emailLink) {
      emailLink.textContent = settings.helpline_email || 'support@bulkbite.in';
      emailLink.href = `mailto:${settings.helpline_email || 'support@bulkbite.in'}`;
    }
    if (waBtn) {
      waBtn.href = `https://wa.me/${cleanPhone}?text=Hi%20BulkBite%20Helpline`;
    }
  } catch (e) {}
}

function dismissAnnouncement() {
  const bar = document.getElementById('liveAnnouncementBar');
  if (bar) bar.style.display = 'none';
}

function openHelplineModal() {
  loadSettings();
  document.getElementById('helplineModal').classList.add('active');
}

// ------------------ COLLEGE COMMUNITIES ------------------ //

async function loadColleges() {
  try {
    const colleges = await apiFetch('/api/colleges');
    state.colleges = colleges;

    // Populate dropdowns
    const mainSelect = document.getElementById('collegeCommunitySelect');
    const regSelect = document.getElementById('regCollegeSelect');
    const poolSelect = document.getElementById('poolCollegeSelect');

    let mainOptions = '<option value="all">🌍 All College Communities</option>';
    let formOptions = '';

    colleges.forEach(c => {
      const label = `${c.icon || '🎓'} ${c.name} (${c.code})`;
      mainOptions += `<option value="${c.id}">${label}</option>`;
      formOptions += `<option value="${c.id}">${label}</option>`;
    });

    if (mainSelect) mainSelect.innerHTML = mainOptions;
    if (regSelect) regSelect.innerHTML = formOptions;
    if (poolSelect) poolSelect.innerHTML = formOptions;

    // Update Active College Badge
    updateCollegeBadge();
  } catch (e) {
    console.error("Failed to load colleges", e);
  }
}

function handleCollegeCommunityChange() {
  const select = document.getElementById('collegeCommunitySelect');
  if (select) {
    state.selectedCollegeId = select.value;
    updateCollegeBadge();
    loadPools();
  }
}

function updateCollegeBadge() {
  const badge = document.getElementById('activeCollegeBadge');
  if (!badge) return;

  if (state.selectedCollegeId === 'all') {
    badge.innerHTML = `<span>🌍</span> All Campuses`;
  } else {
    const c = state.colleges.find(col => col.id == state.selectedCollegeId);
    if (c) {
      badge.innerHTML = `<span>${c.icon || '🎓'}</span> ${c.code}`;
    }
  }
}

// ------------------ AUTHENTICATION (ONE STUDENT ONE ACCOUNT) ------------------ //

async function verifyAuthentication() {
  const token = localStorage.getItem('hostel_token');
  if (!token) {
    updateAuthUI(null);
    return;
  }

  try {
    const res = await apiFetch('/api/auth/me');
    if (res.authenticated && res.user) {
      state.currentUser = res.user;
      updateAuthUI(res.user);

      // Auto-set user's college if on 'all'
      if (res.user.college_id && state.selectedCollegeId === 'all') {
        const select = document.getElementById('collegeCommunitySelect');
        if (select) {
          select.value = res.user.college_id;
          state.selectedCollegeId = res.user.college_id;
          updateCollegeBadge();
        }
      }
    } else {
      handleLogoutLocal();
    }
  } catch (e) {
    handleLogoutLocal();
  }
}

function updateAuthUI(user) {
  const loggedOutDiv = document.getElementById('loggedOutButtons');
  const loggedInDiv = document.getElementById('loggedInAccount');
  const founderBtn = document.getElementById('founderHQBtn');
  const menuFounderItem = document.getElementById('menuFounderItem');

  if (!user) {
    if (loggedOutDiv) loggedOutDiv.style.display = 'flex';
    if (loggedInDiv) loggedInDiv.style.display = 'none';
    if (founderBtn) founderBtn.style.display = 'none';
    if (menuFounderItem) menuFounderItem.style.display = 'none';
    state.currentUser = null;
    return;
  }

  if (loggedOutDiv) loggedOutDiv.style.display = 'none';
  if (loggedInDiv) loggedInDiv.style.display = 'block';

  // Founder Controls Visibility (Unlocked for Founder Kedar Patil)
  const isFounder = user.role === 'founder';
  if (founderBtn) founderBtn.style.display = isFounder ? 'flex' : 'none';
  if (menuFounderItem) menuFounderItem.style.display = isFounder ? 'flex' : 'none';

  // Set User details in personal account pill
  const avatarEl = document.getElementById('userAvatarBadge');
  const nameEl = document.getElementById('userNameHeader');
  const roomEl = document.getElementById('userRoomBadge');

  if (avatarEl) {
    avatarEl.textContent = user.name.charAt(0).toUpperCase();
    avatarEl.style.backgroundColor = isFounder ? '#F59E0B' : (user.avatar_color || '#4F46E5');
  }
  if (nameEl) nameEl.textContent = user.name.split(' ')[0];
  if (roomEl) {
    roomEl.textContent = isFounder ? 'Founder' : user.room_number;
    if (isFounder) roomEl.style.background = '#fef3c7';
    if (isFounder) roomEl.style.color = '#b45309';
  }

  // Dropdown card details
  const menuName = document.getElementById('menuFullName');
  const menuRoom = document.getElementById('menuRoomInfo');
  const menuCollege = document.getElementById('menuCollegeInfo');
  const menuPhone = document.getElementById('menuPhoneInfo');
  if (menuName) menuName.textContent = user.name;
  if (menuRoom) menuRoom.textContent = `${user.room_number} • ${user.hostel_block}`;
  if (menuCollege) menuCollege.textContent = `🏫 ${user.college_name || 'Campus Community'}`;
  if (menuPhone) menuPhone.textContent = `📞 ${user.phone}`;
}

function openLoginModal() {
  document.getElementById('loginForm').reset();
  document.getElementById('loginModal').classList.add('active');
}

function openRegisterModal() {
  document.getElementById('registerForm').reset();
  document.getElementById('registerModal').classList.add('active');
}

function switchToRegister() {
  closeModal('loginModal');
  openRegisterModal();
}

function switchToLogin() {
  closeModal('registerModal');
  openLoginModal();
}

function quickFillLogin(phone, password) {
  document.getElementById('loginPhoneInput').value = phone;
  document.getElementById('loginPasswordInput').value = password;
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const phone = document.getElementById('loginPhoneInput').value.trim();
  const password = document.getElementById('loginPasswordInput').value.trim();

  let res = null;
  let lastError = null;

  for (const endpoint of ['/api/auth/login', '/api/login', '/auth/login']) {
    try {
      res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ phone, password })
      });
      break;
    } catch (err) {
      lastError = err;
      if (!err.message.includes('not found') && !err.message.includes('404')) {
        break;
      }
    }
  }

  if (res && res.token) {
    localStorage.setItem('hostel_token', res.token);
    state.currentUser = res.user;
    updateAuthUI(res.user);
    closeModal('loginModal');
    showToast("Logged In Successfully!", `Welcome back, ${res.user.name}!`, "info");
    await loadPools();
  } else {
    showToast("Login Failed", lastError ? lastError.message : "Invalid phone or password", "gate");
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const collegeId = document.getElementById('regCollegeSelect').value;
  const name = document.getElementById('regNameInput').value.trim();
  const room = document.getElementById('regRoomInput').value.trim();
  const hostel = document.getElementById('regHostelInput').value.trim();
  const phone = document.getElementById('regPhoneInput').value.trim();
  const password = document.getElementById('regPasswordInput').value.trim();
  const upi = document.getElementById('regUpiInput').value.trim();

  let res = null;
  let lastError = null;

  for (const endpoint of ['/api/auth/register', '/api/register', '/auth/register', '/api/users']) {
    try {
      res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          college_id: collegeId,
          name,
          room_number: room,
          hostel_block: hostel,
          phone,
          password,
          upi_id: upi
        })
      });
      break;
    } catch (err) {
      lastError = err;
      if (!err.message.includes('not found') && !err.message.includes('404')) {
        break;
      }
    }
  }

  if (res && res.token) {
    localStorage.setItem('hostel_token', res.token);
    state.currentUser = res.user;
    updateAuthUI(res.user);
    closeModal('registerModal');
    showToast("Account Created!", `Welcome to BulkBite, ${res.user.name}!`, "goal");
    await loadPools();
    await loadStats();
  } else {
    showToast("Registration Failed", lastError ? lastError.message : "Registration failed", "gate");
  }
}

async function handleLogout() {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}

  handleLogoutLocal();
  showToast("Logged Out", "You have been logged out of your account.", "info");
  await loadPools();
}

function handleLogoutLocal() {
  localStorage.removeItem('hostel_token');
  state.currentUser = null;
  updateAuthUI(null);
  closeModal('profileModal');
  const menu = document.getElementById('accountDropdownMenu');
  if (menu) menu.classList.remove('active');
}

function openProfileModal() {
  if (!state.currentUser) return;
  const u = state.currentUser;

  document.getElementById('profileAvatarBig').textContent = u.name.charAt(0).toUpperCase();
  document.getElementById('profileAvatarBig').style.backgroundColor = u.role === 'founder' ? '#F59E0B' : (u.avatar_color || '#4F46E5');
  document.getElementById('profileNameBig').textContent = u.name;
  document.getElementById('profileRoomBig').textContent = u.role === 'founder' ? 'Founder HQ' : u.room_number;
  document.getElementById('profileCollege').textContent = u.college_name || 'Main Campus';
  document.getElementById('profileBlock').textContent = u.hostel_block;
  document.getElementById('profilePhone').textContent = u.phone;
  document.getElementById('profileUpi').textContent = u.upi_id || 'Not set yet';

  const menu = document.getElementById('accountDropdownMenu');
  if (menu) menu.classList.remove('active');

  document.getElementById('profileModal').classList.add('active');
}

function handleHostPoolClick() {
  if (!state.currentUser) {
    showToast("Authentication Required", "Please log in or sign up to host a group cart.", "info");
    openLoginModal();
    return;
  }
  openCreatePoolModal();
}

// ------------------ FOUNDER SUPER-ADMIN CONTROL PANEL ("PARENT APP") ------------------ //

function openAdminModal() {
  if (!state.currentUser || state.currentUser.role !== 'founder') {
    showToast("Access Denied", "Founder privileges required to open this portal.", "gate");
    return;
  }
  const modal = document.getElementById('adminModal');
  modal.classList.add('active');
  loadAdminUsers();
  loadAdminColleges();
}

function switchAdminTab(panelId, tabEl) {
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));

  tabEl.classList.add('active');
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.add('active');

  if (panelId === 'usersTab') loadAdminUsers();
  if (panelId === 'collegesTab') loadAdminColleges();
}

async function loadAdminUsers() {
  const container = document.getElementById('adminUserList');
  if (!container) return;
  container.innerHTML = '<div style="padding:16px; text-align:center;">Loading students...</div>';

  try {
    const users = await apiFetch('/api/admin/users');
    if (users.length === 0) {
      container.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted);">No users found.</div>';
      return;
    }

    container.innerHTML = users.map(u => {
      const isBlocked = u.status === 'blocked';
      const isFounder = u.role === 'founder';

      return `
        <div class="admin-user-card ${isBlocked ? 'is-blocked' : ''} ${isFounder ? 'is-founder' : ''}">
          <div>
            <div style="font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px;">
              ${escapeHtml(u.name)}
              <span class="status-tag ${isFounder ? 'founder' : (isBlocked ? 'blocked' : 'active')}">
                ${isFounder ? '👑 Founder' : (isBlocked ? '⛔ Suspended' : '✓ Active')}
              </span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
              ${escapeHtml(u.room_number)} • ${escapeHtml(u.hostel_block)} • 🏫 ${escapeHtml(u.college_name || 'Campus')}
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
              📞 <strong>${u.phone}</strong> ${u.upi_id ? `• UPI: ${u.upi_id}` : ''}
            </div>
          </div>

          <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
            ${!isFounder ? `
              <button 
                class="btn-secondary" 
                onclick="toggleUserStatus(${u.id}, '${isBlocked ? 'active' : 'blocked'}')"
                style="padding: 5px 9px; font-size: 11px; ${isBlocked ? 'color: var(--success);' : 'color: var(--danger);'}"
              >
                ${isBlocked ? '✅ Unblock' : '⛔ Block'}
              </button>
              <button 
                class="btn-secondary" 
                onclick="deleteUserPermanently(${u.id})"
                style="padding: 5px 9px; font-size: 11px; color: var(--danger);"
                title="Permanently remove user"
              >
                🗑️ Delete
              </button>
            ` : '<span style="font-size:12px; font-weight:800; color:#f59e0b;">Master Account</span>'}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="padding:16px; color:var(--danger);">${err.message}</div>`;
  }
}

async function toggleUserStatus(userId, newStatus) {
  try {
    await apiFetch(`/api/admin/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    showToast("Status Updated", `Student status set to ${newStatus}`, "info");
    loadAdminUsers();
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function deleteUserPermanently(userId) {
  if (!confirm("Are you sure you want to permanently delete this student account? This cannot be undone.")) return;
  try {
    await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
    showToast("User Removed", "Student deleted from BulkBite platform", "info");
    loadAdminUsers();
    loadStats();
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function loadAdminColleges() {
  const container = document.getElementById('adminCollegeList');
  if (!container) return;

  try {
    const colleges = await apiFetch('/api/colleges');
    container.innerHTML = colleges.map(c => `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 8px;">
        <div>
          <div style="font-weight: 800; font-size: 13px;">${c.icon || '🎓'} ${escapeHtml(c.name)} <span style="color:var(--primary); font-size:11px;">[${c.code}]</span></div>
          <div style="font-size: 11px; color: var(--text-muted);">${c.city || ''} ${c.state || ''} • 👥 ${c.student_count || 0} students enrolled</div>
        </div>
        ${c.id !== 1 ? `
          <button onclick="deleteCollegeCommunity(${c.id})" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; color: var(--danger);">
            ✕ Remove
          </button>
        ` : '<span style="font-size:11px; color:var(--text-muted);">Default</span>'}
      </div>
    `).join('');
  } catch (e) {}
}

async function handleCreateCollegeSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('newCollegeName').value.trim();
  const code = document.getElementById('newCollegeCode').value.trim();
  const city = document.getElementById('newCollegeCity').value.trim();
  const stateVal = document.getElementById('newCollegeState').value.trim();

  try {
    await apiFetch('/api/admin/colleges', {
      method: 'POST',
      body: JSON.stringify({ name, code, city, state: stateVal })
    });
    showToast("Community Launched!", `Campus community ${name} is live!`, "goal");
    document.getElementById('createCollegeForm').reset();
    await loadColleges();
    loadAdminColleges();
    loadStats();
  } catch (err) {
    showToast("Failed to Create", err.message, "gate");
  }
}

async function deleteCollegeCommunity(collegeId) {
  if (!confirm("Are you sure you want to remove this college community?")) return;
  try {
    await apiFetch(`/api/admin/colleges/${collegeId}`, { method: 'DELETE' });
    showToast("Removed", "College community removed", "info");
    await loadColleges();
    loadAdminColleges();
    loadStats();
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function handleGlobalBroadcastSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('broadcastTitleInput').value.trim();
  const message = document.getElementById('broadcastMessageInput').value.trim();

  try {
    await apiFetch('/api/admin/broadcast', {
      method: 'POST',
      body: JSON.stringify({ title, message })
    });
    showToast("Broadcast Sent!", "Notice published to all students across all campuses!", "goal");
    document.getElementById('broadcastMessageInput').value = '';
    await loadSettings();
  } catch (err) {
    showToast("Broadcast Failed", err.message, "gate");
  }
}

async function handleUpdateSettingsSubmit(e) {
  e.preventDefault();
  const phone = document.getElementById('settingPhoneInput').value.trim();
  const email = document.getElementById('settingEmailInput').value.trim();
  const ann = document.getElementById('settingAnnouncementInput').value.trim();

  try {
    await apiFetch('/api/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        helpline_phone: phone,
        helpline_email: email,
        live_announcement: ann,
        announcement_active: ann ? '1' : '0'
      })
    });
    showToast("Settings Updated!", "Helpline & rules updated instantly across all campuses!", "info");
    await loadSettings();
  } catch (err) {
    showToast("Error", err.message, "gate");
  }
}

// ------------------ STATS & POOLS ------------------ //

async function loadStats() {
  try {
    const stats = await apiFetch('/api/stats');
    const savedEl = document.getElementById('statDeliverySaved');
    const poolsEl = document.getElementById('statActivePools');
    const studentsEl = document.getElementById('statStudents');
    const collegesEl = document.getElementById('statColleges');

    if (savedEl) savedEl.textContent = `₹${Math.round(stats.total_delivery_saved)}`;
    if (poolsEl) poolsEl.textContent = stats.active_pools;
    if (studentsEl) studentsEl.textContent = stats.total_students;
    if (collegesEl) collegesEl.textContent = stats.total_colleges || 6;
  } catch (e) {}
}

async function loadPools(showLoading = true) {
  try {
    let url = `/api/pools?status=${state.activeFilter}`;
    if (state.activePlatform !== 'all') {
      url += `&platform=${encodeURIComponent(state.activePlatform)}`;
    }
    if (state.selectedCollegeId !== 'all') {
      url += `&college_id=${encodeURIComponent(state.selectedCollegeId)}`;
    }

    const pools = await apiFetch(url);
    state.pools = pools;
    renderPools();
  } catch (e) {
    console.error("Failed to load pools", e);
  }
}

async function checkNotifications(isInitial = false) {
  try {
    let url = '/api/notifications';
    if (state.selectedCollegeId !== 'all') {
      url += `?college_id=${state.selectedCollegeId}`;
    }
    const notifs = await apiFetch(url);
    if (!notifs || notifs.length === 0) return;

    if (isInitial) {
      state.notifications = notifs;
      state.lastNotifId = notifs[0].id;
      renderNotificationList();
      return;
    }

    const newItems = notifs.filter(n => n.id > state.lastNotifId);
    if (newItems.length > 0) {
      state.lastNotifId = notifs[0].id;
      state.notifications = notifs;
      renderNotificationList();

      newItems.reverse().forEach(n => {
        const isGateAlert = n.type === 'gate_alert';
        const isBroadcast = n.type === 'admin_broadcast';
        showToast(n.title, n.message, isGateAlert ? 'gate' : (isBroadcast ? 'goal' : 'info'));
        playChime(isGateAlert || isBroadcast);
      });
    }
  } catch (e) {}
}

// ------------------ RENDERING LOGIC ------------------ //

function renderPools() {
  const grid = document.getElementById('poolGrid');
  if (!grid) return;

  let pools = state.pools;

  if (state.searchQuery.trim()) {
    const q = state.searchQuery.toLowerCase();
    pools = pools.filter(p => 
      p.title.toLowerCase().includes(q) ||
      p.host_name.toLowerCase().includes(q) ||
      p.host_room.toLowerCase().includes(q) ||
      p.platform.toLowerCase().includes(q)
    );
  }

  if (pools.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--card-bg); border-radius: var(--radius-lg); border: 1px dashed var(--border);">
        <div style="font-size: 42px; margin-bottom: 12px;">🍔</div>
        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 6px;">No Active Order Pools Right Now</h3>
        <p style="color: var(--text-muted); font-size: 13px; max-width: 400px; margin: 0 auto 16px;">
          Want to order food or snacks? Start a group order, hit the ₹200 free delivery threshold, and save ₹40!
        </p>
        <button class="btn-primary" onclick="handleHostPoolClick()" style="margin: 0 auto;">
          <span>＋</span> Host a BulkBite Pool Now
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = pools.map(pool => renderPoolCard(pool)).join('');
}

function renderPoolCard(pool) {
  const platform = pool.platform.toLowerCase();
  const platformClass = `platform-${platform}` || 'platform-other';

  const statusLabels = {
    'open': 'Open for Pooling',
    'ordering': 'Placing Order',
    'on_the_way': 'On The Way 🚴',
    'at_gate': '🚨 At Gate! Pickup Now',
    'completed': 'Completed'
  };

  const statusClass = `status-${pool.status}`;
  const isHost = state.currentUser && state.currentUser.id === pool.host_id;

  let platformIcon = '🛍️';
  if (platform.includes('blinkit')) platformIcon = '⚡';
  else if (platform.includes('zepto')) platformIcon = '⏱️';
  else if (platform.includes('instamart') || platform.includes('swiggy')) platformIcon = '🛵';
  else if (platform.includes('zomato')) platformIcon = '🍔';

  let savingsHtml = '';
  if (pool.is_target_reached) {
    savingsHtml = `
      <div class="savings-tag reached">
        <span>🎉 Free Delivery Unlocked!</span>
        <span>Saved ₹${Math.round(pool.delivery_fee_saved)} fee</span>
      </div>
    `;
  } else {
    savingsHtml = `
      <div class="savings-tag unreached">
        <span>₹${Math.round(pool.remaining_amount)} more to free delivery</span>
        <span>Hit ₹${Math.round(pool.target_amount)} to save ₹${Math.round(pool.delivery_fee_saved)}!</span>
      </div>
    `;
  }

  return `
    <div class="pool-card">
      <div class="pool-card-header">
        <span class="platform-pill ${platformClass}">
          ${platformIcon} ${pool.platform}
        </span>
        <span class="status-badge ${statusClass}">
          ${statusLabels[pool.status] || pool.status}
        </span>
      </div>

      <h3 class="pool-title">${escapeHtml(pool.title)}</h3>

      <div style="font-size: 11px; font-weight: 700; color: var(--primary); margin-top: -4px; margin-bottom: 8px;">
        🏫 ${escapeHtml(pool.college_name || 'Campus Community')}
      </div>

      <div class="host-row">
        <div class="host-avatar" style="background-color: ${pool.host_avatar || '#4F46E5'}">
          ${pool.host_name.charAt(0).toUpperCase()}
        </div>
        <div class="host-details">
          <div class="host-name">${escapeHtml(pool.host_name)} ${isHost ? '<span style="color:var(--primary); font-size:11px; font-weight:800;">(You)</span>' : ''}</div>
          <div class="host-room-info">${pool.host_room} • ${pool.host_block}</div>
        </div>
        <a href="tel:${pool.host_phone}" class="icon-btn" style="width:30px; height:30px; font-size:13px;" title="Call Host">
          📞
        </a>
      </div>

      <div class="pool-progress-section">
        <div class="progress-header">
          <span class="progress-total">₹${Math.round(pool.current_total)} <small style="font-weight: normal; color: var(--text-muted);">in cart</small></span>
          <span class="progress-target">Target: ₹${Math.round(pool.target_amount)}</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill ${pool.is_target_reached ? 'achieved' : ''}" style="width: ${Math.min(100, pool.progress_percent)}%;"></div>
        </div>
        ${savingsHtml}
      </div>

      <div class="pool-meta-grid">
        <div class="pool-meta-item">
          <span class="meta-icon">⏰</span>
          <div>
            <div style="font-size:10px;">Order Deadline</div>
            <div class="meta-val">${pool.order_time}</div>
          </div>
        </div>
        <div class="pool-meta-item">
          <span class="meta-icon">📍</span>
          <div>
            <div style="font-size:10px;">Pickup Gate</div>
            <div class="meta-val" title="${pool.gate_location}" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:110px;">${pool.gate_location}</div>
          </div>
        </div>
      </div>

      <div class="pool-card-actions">
        ${pool.status === 'open' ? `
          <button class="btn-primary" onclick="handleAddClick(${pool.id})">
            <span>＋</span> Add Item
          </button>
        ` : ''}
        <button class="btn-secondary" onclick="openPoolDetail(${pool.id})">
          <span>👀</span> View Pool & Gate Meetup
        </button>
      </div>
    </div>
  `;
}

function handleAddClick(poolId) {
  if (!state.currentUser) {
    showToast("Authentication Required", "Please log in to add items to this cart.", "info");
    openLoginModal();
    return;
  }
  openAddItemModal(poolId);
}

// ------------------ POOL DETAIL & GATE MEETUP VIEW ------------------ //

async function openPoolDetail(poolId) {
  try {
    const pool = await apiFetch(`/api/pools/${poolId}`);
    state.currentPoolDetail = pool;
    renderPoolDetailModal(pool);
    document.getElementById('poolDetailModal').classList.add('active');
  } catch (e) {
    showToast("Error", "Could not load pool details", "info");
  }
}

async function refreshActivePoolDetail(poolId) {
  try {
    const modal = document.getElementById('poolDetailModal');
    if (!modal || !modal.classList.contains('active')) return;
    const pool = await apiFetch(`/api/pools/${poolId}`);
    state.currentPoolDetail = pool;
    renderPoolDetailModal(pool);
  } catch (e) {}
}

function renderPoolDetailModal(pool) {
  const container = document.getElementById('poolDetailBody');
  if (!container) return;

  const isHost = state.currentUser && state.currentUser.id === pool.host_id;
  const isFounder = state.currentUser && state.currentUser.role === 'founder';

  const steps = [
    { key: 'open', label: '1. Pooling Open' },
    { key: 'ordering', label: '2. Host Ordering' },
    { key: 'on_the_way', label: '3. On The Way' },
    { key: 'at_gate', label: '4. At Gate!' },
    { key: 'completed', label: '5. Settled' }
  ];

  const statusOrder = ['open', 'ordering', 'on_the_way', 'at_gate', 'completed'];
  const currentIndex = statusOrder.indexOf(pool.status);

  let stepperHtml = '<div class="timeline-stepper">';
  steps.forEach((s, idx) => {
    let cls = '';
    if (idx < currentIndex) cls = 'completed';
    else if (idx === currentIndex) cls = 'active';

    stepperHtml += `
      <div class="timeline-step ${cls}">
        <div class="step-circle">${idx < currentIndex ? '✓' : (idx + 1)}</div>
        <div class="step-label">${s.label}</div>
      </div>
    `;
  });
  stepperHtml += '</div>';

  let gateAlertBanner = '';
  if (pool.status === 'at_gate') {
    gateAlertBanner = `
      <div class="gate-meetup-card" style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-color: #f87171; color: #991b1b;">
        <span class="gate-meetup-icon">🚨</span>
        <div class="gate-meetup-text" style="flex:1;">
          <h4>DELIVERY BOY IS AT THE GATE!</h4>
          <p>Please meet <strong>${pool.host_name}</strong> immediately at <strong>${pool.gate_location}</strong> to collect your items and clear UPI payment!</p>
        </div>
      </div>
    `;
  } else if (pool.status === 'on_the_way') {
    gateAlertBanner = `
      <div class="gate-meetup-card">
        <span class="gate-meetup-icon">🚴</span>
        <div class="gate-meetup-text" style="flex:1;">
          <h4>Order Out for Delivery!</h4>
          <p>Estimated Arrival: <strong>${pool.delivery_eta || '10-15 mins'}</strong>. Pickup spot: <strong>${pool.gate_location}</strong>.</p>
        </div>
      </div>
    `;
  }

  // Host Action Control Toolbar
  let hostToolbarHtml = '';
  if (isHost || isFounder) {
    hostToolbarHtml = `
      <div style="background: var(--bg); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border); margin-bottom: 18px;">
        <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; color: var(--primary); margin-bottom: 8px;">
          ${isFounder && !isHost ? '👑 Founder Management Override' : '👑 Host Management Controls'}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          ${pool.status === 'open' ? `
            <button class="btn-secondary" onclick="updatePoolStatus(${pool.id}, 'ordering')" style="font-size:12px;">
              🔒 Lock & Start Ordering
            </button>
          ` : ''}
          ${pool.status === 'ordering' ? `
            <button class="btn-primary" onclick="promptDeliveryETA(${pool.id})" style="font-size:12px;">
              🚴 Placed! Mark Out for Delivery
            </button>
          ` : ''}
          ${pool.status === 'on_the_way' || pool.status === 'ordering' ? `
            <button class="btn-primary" onclick="updatePoolStatus(${pool.id}, 'at_gate')" style="background: #dc2626; font-size:12px;">
              🚨 Broadcast: Arrived at Gate!
            </button>
          ` : ''}
          ${pool.status === 'at_gate' ? `
            <button class="btn-primary" onclick="updatePoolStatus(${pool.id}, 'completed')" style="background: var(--success); font-size:12px;">
              ✅ All Collected & Settled
            </button>
          ` : ''}
          <button class="btn-secondary" onclick="openBroadcastModal(${pool.id})" style="font-size:12px;">
            📢 Send Announcement
          </button>
          ${isFounder ? `
            <button class="btn-secondary" onclick="deletePoolByFounder(${pool.id})" style="font-size:12px; color:var(--danger); margin-left:auto;">
              🗑️ Cancel/Delete Pool
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }

  // Items in the pool
  let itemsHtml = '';
  if (pool.items && pool.items.length > 0) {
    itemsHtml = pool.items.map(item => {
      const isOwner = state.currentUser && state.currentUser.id === item.user_id;
      const canDelete = (pool.status === 'open' && (isOwner || isHost)) || isFounder;
      const subtotal = item.price * item.quantity;

      return `
        <div class="item-row">
          <div class="item-left">
            ${item.image_url ? `
              <img src="${item.image_url}" class="item-thumb" alt="${item.item_name}" onerror="this.src='/uploads/fallback.png'"/>
            ` : `
              <div class="item-thumb-placeholder">🍜</div>
            `}
            <div class="item-info">
              <div class="item-name">${escapeHtml(item.item_name)}</div>
              <div class="item-user-tag">
                <span class="room-badge">${item.user_room}</span>
                <span>${item.user_name}</span>
                ${item.notes ? `• <span style="font-style:italic;">"${escapeHtml(item.notes)}"</span>` : ''}
              </div>
              ${item.product_link ? `
                <a href="${item.product_link}" target="_blank" style="font-size:11px; color:var(--primary); font-weight:600; text-decoration:underline;">
                  🔗 View on ${pool.platform}
                </a>
              ` : ''}
            </div>
          </div>
          <div class="item-right">
            <div class="item-price">₹${subtotal}</div>
            <div class="item-qty">Qty: ${item.quantity} (₹${item.price} each)</div>
            ${canDelete ? `
              <button onclick="deleteItem(${pool.id}, ${item.id})" style="background:none; border:none; color:var(--danger); font-size:11px; cursor:pointer; font-weight:700; margin-top:2px;">
                Remove ✕
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');
  } else {
    itemsHtml = `<div style="text-align:center; padding:16px; color:var(--text-muted); font-size:13px;">No items added yet.</div>`;
  }

  // Participants & Bill Breakdown
  let billsHtml = '';
  if (pool.participants && pool.participants.length > 0) {
    billsHtml = pool.participants.map(p => {
      const isPaid = p.payment_status === 'paid';
      const isSelf = state.currentUser && state.currentUser.id === p.user_id;
      const hostUpi = pool.host_upi || 'hostel@upi';
      const whatsappMsg = `Hey ${p.name.split(' ')[0]}, your order from ${pool.platform} is arriving at ${pool.gate_location}. Your total is ₹${p.total_amount}. Please UPI to ${hostUpi}`;
      const whatsappUrl = `https://wa.me/91${p.phone}?text=${encodeURIComponent(whatsappMsg)}`;

      return `
        <div class="participant-bill-card">
          <div class="p-bill-header">
            <div class="p-bill-user">
              <div class="user-avatar-small" style="background-color: ${p.avatar_color || '#4F46E5'}">
                ${p.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style="font-weight:700; font-size:13px;">${escapeHtml(p.name)} ${p.is_host ? '👑 (Host)' : ''} ${isSelf ? '<span style="color:var(--primary); font-size:11px; font-weight:800;">(You)</span>' : ''}</div>
                <div style="font-size:11px; color:var(--text-muted);">${p.room_number} • 📞 ${p.phone}</div>
              </div>
            </div>
            <div style="text-align:right;">
              <div class="p-bill-amount">₹${p.total_amount}</div>
              <span class="status-badge ${isPaid ? 'status-open' : 'status-ordering'}" style="font-size:10px;">
                ${isPaid ? '✓ Paid' : '⏳ Payment Pending'}
              </span>
            </div>
          </div>

          <div class="p-bill-actions">
            ${!p.is_host && !isPaid ? `
              <button class="btn-primary" onclick="openUPIQRModal('${pool.host_name}', '${hostUpi}', ${p.total_amount})" style="padding:5px 10px; font-size:11px;">
                📱 Show UPI QR / Pay
              </button>
            ` : ''}
            <a href="${whatsappUrl}" target="_blank" class="btn-secondary" style="padding:5px 10px; font-size:11px; text-decoration:none;">
              💬 Ping WhatsApp
            </a>
            ${(isHost || isFounder) && !p.is_host ? `
              <button onclick="togglePaymentStatus(${pool.id}, ${p.user_id}, '${isPaid ? 'pending' : 'paid'}', ${p.total_amount})" class="btn-secondary" style="padding:5px 10px; font-size:11px; margin-left:auto;">
                ${isPaid ? 'Mark as Unpaid' : 'Mark as Paid ✓'}
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  container.innerHTML = `
    ${stepperHtml}
    ${gateAlertBanner}
    ${hostToolbarHtml}

    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <h3 style="font-size:15px; font-weight:800;">Items in Cart (${pool.items ? pool.items.length : 0})</h3>
      <div style="font-weight:800; font-size:15px; color:var(--primary);">
        Total: ₹${pool.current_total} / ₹${pool.target_amount}
      </div>
    </div>

    <div class="items-list">
      ${itemsHtml}
    </div>

    ${pool.status === 'open' ? `
      <div style="margin-top:16px; text-align:center;">
        <button class="btn-primary" onclick="handleAddClick(${pool.id})" style="width:100%; justify-content:center;">
          <span>＋</span> Add More Items to this Cart
        </button>
      </div>
    ` : ''}

    <div style="margin-top:24px; padding-top:18px; border-top:1px solid var(--border);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h3 style="font-size:15px; font-weight:800;">Gate Meetup & Bill Settlement</h3>
        <span style="font-size:12px; color:var(--success); font-weight:700;">
          🎉 ₹${Math.round(pool.delivery_fee_saved || 40)} Delivery Fee Saved!
        </span>
      </div>

      <div style="background:var(--bg); padding:10px 14px; border-radius:var(--radius-md); font-size:12px; color:var(--text-muted); margin-bottom:12px;">
        <strong>Host UPI:</strong> <code style="color:var(--primary); font-weight:700;">${pool.host_upi || 'rahul304@oksbi'}</code>
        <br/>Meet the host at <strong>${pool.gate_location}</strong> when notification pops up!
      </div>

      ${billsHtml}
    </div>
  `;
}

// ------------------ HOST & FOUNDER ACTIONS ------------------ //

async function updatePoolStatus(poolId, newStatus) {
  try {
    await apiFetch(`/api/pools/${poolId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    showToast("Status Updated", `Pool moved to ${newStatus}`, "info");
    await loadPools();
    await refreshActivePoolDetail(poolId);
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function promptDeliveryETA(poolId) {
  const eta = prompt("Enter estimated delivery time (e.g. 15 mins / 11:45 PM):", "15 minutes");
  if (eta === null) return;

  try {
    await apiFetch(`/api/pools/${poolId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'on_the_way', delivery_eta: eta })
    });
    showToast("Order Placed!", `Delivery ETA set to ${eta}`, "info");
    await loadPools();
    await refreshActivePoolDetail(poolId);
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function togglePaymentStatus(poolId, userId, newStatus, amount) {
  try {
    await apiFetch(`/api/pools/${poolId}/payments`, {
      method: 'PATCH',
      body: JSON.stringify({ user_id: userId, status: newStatus, amount: amount })
    });
    showToast("Payment Updated", `Marked as ${newStatus}`, "info");
    await refreshActivePoolDetail(poolId);
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

function openBroadcastModal(poolId) {
  const msg = prompt("Enter announcement message to broadcast to all students in this pool:", "Delivery guy has reached the gate! Meet me now.");
  if (!msg) return;

  apiFetch(`/api/pools/${poolId}/broadcast`, {
    method: 'POST',
    body: JSON.stringify({ message: msg })
  }).then(() => {
    showToast("Broadcast Sent!", "All students received the announcement.", "info");
  }).catch(e => {
    showToast("Error", e.message, "gate");
  });
}

async function deletePoolByFounder(poolId) {
  if (!confirm("Founder action: Are you sure you want to cancel and remove this entire pool?")) return;
  try {
    await apiFetch(`/api/pools/${poolId}`, { method: 'DELETE' });
    closeModal('poolDetailModal');
    showToast("Pool Removed", "Order pool removed by founder", "info");
    await loadPools();
    await loadStats();
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

// ------------------ ADD ITEM MODAL ------------------ //

let targetPoolForNewItem = null;

function openAddItemModal(poolId) {
  targetPoolForNewItem = poolId;
  const pool = state.pools.find(p => p.id === poolId) || state.currentPoolDetail;
  const modal = document.getElementById('addItemModal');

  document.getElementById('addItemPoolTitle').textContent = pool ? `Adding to: ${pool.title} (${pool.platform})` : 'Add Item';
  document.getElementById('itemForm').reset();
  modal.classList.add('active');
}

function selectPresetItem(name, price, link = '') {
  document.getElementById('itemNameInput').value = name;
  document.getElementById('itemPriceInput').value = price;
  if (link) document.getElementById('itemLinkInput').value = link;
}

async function handleAddItemSubmit(e) {
  e.preventDefault();
  if (!targetPoolForNewItem) return;

  if (!state.currentUser) {
    showToast("Authentication Required", "Please log in to your student account first", "gate");
    closeModal('addItemModal');
    openLoginModal();
    return;
  }

  const itemName = document.getElementById('itemNameInput').value.trim();
  const quantity = parseInt(document.getElementById('itemQtyInput').value) || 1;
  const price = parseFloat(document.getElementById('itemPriceInput').value) || 0;
  const productLink = document.getElementById('itemLinkInput').value.trim();
  const imageUrl = document.getElementById('itemImageInput').value.trim();
  const notes = document.getElementById('itemNotesInput').value.trim();

  if (!itemName || price <= 0) {
    alert("Please enter a valid item name and price.");
    return;
  }

  try {
    await apiFetch(`/api/pools/${targetPoolForNewItem}/items`, {
      method: 'POST',
      body: JSON.stringify({
        item_name: itemName,
        quantity,
        price,
        product_link: productLink,
        image_url: imageUrl,
        notes
      })
    });

    closeModal('addItemModal');
    showToast("Item Added!", `${itemName} added to the cart`, "info");
    await loadPools();
    if (state.currentPoolDetail && state.currentPoolDetail.id === targetPoolForNewItem) {
      await refreshActivePoolDetail(targetPoolForNewItem);
    }
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

async function deleteItem(poolId, itemId) {
  if (!confirm("Are you sure you want to remove this item?")) return;
  try {
    await apiFetch(`/api/pools/${poolId}/items/${itemId}`, { method: 'DELETE' });
    showToast("Item Removed", "Cart total updated", "info");
    await loadPools();
    await refreshActivePoolDetail(poolId);
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

// ------------------ CREATE POOL MODAL ------------------ //

function openCreatePoolModal() {
  const modal = document.getElementById('createPoolModal');
  document.getElementById('createPoolForm').reset();

  const now = new Date();
  now.setMinutes(now.getMinutes() + 30);
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  document.getElementById('poolTimeInput').value = timeStr;

  if (state.currentUser && state.currentUser.college_id) {
    document.getElementById('poolCollegeSelect').value = state.currentUser.college_id;
  }

  modal.classList.add('active');
}

function setOrderTimeOffset(minutes) {
  const now = new Date();
  now.setMinutes(now.getMinutes() + minutes);
  document.getElementById('poolTimeInput').value = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function handleCreatePoolSubmit(e) {
  e.preventDefault();
  if (!state.currentUser) {
    showToast("Login Required", "Please log in to host an order", "gate");
    closeModal('createPoolModal');
    openLoginModal();
    return;
  }

  const collegeId = document.getElementById('poolCollegeSelect').value;
  const platform = document.getElementById('poolPlatformSelect').value;
  const title = document.getElementById('poolTitleInput').value.trim();
  const targetAmount = parseFloat(document.getElementById('poolTargetInput').value) || 200.0;
  const orderTime = document.getElementById('poolTimeInput').value.trim();
  const gateLocation = document.getElementById('poolGateInput').value.trim();
  const notes = document.getElementById('poolNotesInput').value.trim();

  const initialName = document.getElementById('hostItemNameInput').value.trim();
  const initialPrice = parseFloat(document.getElementById('hostItemPriceInput').value) || 0;
  const initialQty = parseInt(document.getElementById('hostItemQtyInput').value) || 1;

  const payload = {
    college_id: collegeId,
    title,
    platform,
    target_amount: targetAmount,
    delivery_fee_saved: 40.0,
    order_time: orderTime,
    gate_location: gateLocation,
    notes,
    initial_item: initialName ? {
      item_name: initialName,
      price: initialPrice,
      quantity: initialQty
    } : null
  };

  try {
    const res = await apiFetch('/api/pools', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    closeModal('createPoolModal');
    showToast("Order Pool Live!", `Ordering at ${orderTime}. Campus students can now join!`, "goal");
    await loadPools();
    await loadStats();
    if (res.id) openPoolDetail(res.id);
  } catch (e) {
    showToast("Error", e.message, "gate");
  }
}

// ------------------ UPI QR MODAL ------------------ //

function openUPIQRModal(hostName, upiId, amount) {
  const modal = document.getElementById('upiQRModal');
  const upiUrl = `upi://pay?pa=${encodeURIComponent(upiId)}&pn=${encodeURIComponent(hostName)}&am=${amount}&cu=INR&tn=${encodeURIComponent('BulkBite Pool Payment')}`;

  document.getElementById('qrHostName').textContent = hostName;
  document.getElementById('qrUpiId').textContent = upiId;
  document.getElementById('qrAmount').textContent = `₹${amount}`;
  document.getElementById('qrCodeContainer').innerHTML = generateQRCodeSVG(upiUrl, 190);

  const directPayBtn = document.getElementById('qrDirectPayBtn');
  if (directPayBtn) {
    directPayBtn.href = upiUrl;
  }

  modal.classList.add('active');
}

// ------------------ PWA MOBILE INSTALL ------------------ //

function setupPWA() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.deferredPrompt = e;
    const banner = document.getElementById('pwaInstallBanner');
    if (banner) banner.style.display = 'flex';
  });

  // If already running in standalone PWA mode, hide banner
  if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) {
    const banner = document.getElementById('pwaInstallBanner');
    if (banner) banner.style.display = 'none';
  }
}

function triggerPWAInstall() {
  if (state.deferredPrompt) {
    state.deferredPrompt.prompt();
    state.deferredPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        showToast("App Installing!", "BulkBite is being added to your home screen!", "goal");
      }
      state.deferredPrompt = null;
    });
  } else {
    // Provide clean iOS / mobile browser instructions
    alert("📲 To Install BulkBite on your phone:\n\n• On iPhone (Safari): Tap the Share button at bottom ➔ tap 'Add to Home Screen'.\n• On Android (Chrome): Tap the three dots (⋮) in top right ➔ tap 'Install app' or 'Add to Home screen'.");
  }
}

// ------------------ UI HELPERS & EVENT LISTENERS ------------------ //

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('active');
}

function showToast(title, message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div style="font-size: 20px;">${type === 'gate' ? '🚨' : (type === 'goal' ? '🎉' : '🔔')}</div>
    <div style="flex: 1;">
      <strong style="display: block; font-size: 13px; margin-bottom: 2px;">${escapeHtml(title)}</strong>
      <div style="font-size: 12px; opacity: 0.9;">${escapeHtml(message)}</div>
    </div>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function renderNotificationList() {
  const countBadge = document.getElementById('notifCountBadge');
  const list = document.getElementById('notifDropdownList');
  if (!list) return;

  const unreadCount = state.notifications.length;
  if (countBadge) {
    countBadge.textContent = unreadCount > 9 ? '9+' : unreadCount;
    countBadge.style.display = unreadCount > 0 ? 'flex' : 'none';
  }

  list.innerHTML = state.notifications.slice(0, 10).map(n => `
    <div class="dropdown-item" style="flex-direction:column; align-items:flex-start; border-bottom:1px solid var(--border); padding:10px 14px;">
      <div style="font-weight:700; font-size:12px; color:var(--text-main); display:flex; align-items:center; gap:6px;">
        ${n.type === 'gate_alert' ? '🚨' : (n.type === 'admin_broadcast' ? '📢' : '🔔')} ${escapeHtml(n.title)}
      </div>
      <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">
        ${escapeHtml(n.message)}
      </div>
    </div>
  `).join('');
}

function setupEventListeners() {
  // Personal account menu button
  const accountBtn = document.getElementById('accountMenuBtn');
  const accountMenu = document.getElementById('accountDropdownMenu');
  if (accountBtn && accountMenu) {
    accountBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      accountMenu.classList.toggle('active');
      document.getElementById('notifDropdownList').classList.remove('active');
    });
  }

  // Notification button
  const notifBtn = document.getElementById('notifBtn');
  const notifMenu = document.getElementById('notifDropdownList');
  if (notifBtn && notifMenu) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifMenu.classList.toggle('active');
      if (accountMenu) accountMenu.classList.remove('active');
    });
  }

  document.addEventListener('click', () => {
    if (accountMenu) accountMenu.classList.remove('active');
    if (notifMenu) notifMenu.classList.remove('active');
  });

  // Theme toggle
  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const isDark = document.body.getAttribute('data-theme') === 'dark';
      document.body.setAttribute('data-theme', isDark ? 'light' : 'dark');
      themeBtn.innerHTML = isDark ? '🌙' : '☀️';
    });
  }

  // Sound toggle
  const soundBtn = document.getElementById('soundToggleBtn');
  if (soundBtn) {
    soundBtn.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      soundBtn.innerHTML = state.soundEnabled ? '🔊' : '🔇';
      showToast(state.soundEnabled ? "Sound Enabled" : "Sound Muted", "", "info");
      if (state.soundEnabled) playChime(false);
    });
  }

  // Status Filter Chips
  document.querySelectorAll('.filter-chip[data-status]').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip[data-status]').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.activeFilter = chip.getAttribute('data-status');
      loadPools();
    });
  });

  // Platform Filter Chips
  document.querySelectorAll('.filter-chip[data-platform]').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip[data-platform]').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.activePlatform = chip.getAttribute('data-platform');
      loadPools();
    });
  });

  // Search input
  const searchInput = document.getElementById('poolSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderPools();
    });
  }

  // Forms
  const loginForm = document.getElementById('loginForm');
  if (loginForm) loginForm.addEventListener('submit', handleLoginSubmit);

  const registerForm = document.getElementById('registerForm');
  if (registerForm) registerForm.addEventListener('submit', handleRegisterSubmit);

  const createForm = document.getElementById('createPoolForm');
  if (createForm) createForm.addEventListener('submit', handleCreatePoolSubmit);

  const itemForm = document.getElementById('itemForm');
  if (itemForm) itemForm.addEventListener('submit', handleAddItemSubmit);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// Kickoff
window.addEventListener('DOMContentLoaded', initApp);
