document.addEventListener('DOMContentLoaded', function() {
    // Redirect to home on manual page reload
    const navEntries = window.performance.getEntriesByType('navigation');
    if (navEntries.length > 0 && navEntries[0].type === 'reload') {
        const path = window.location.pathname;
        if (path !== '/' && path !== '/login' && path !== '/signup') {
            window.location.href = '/';
        }
    }

    // Modal Logic
    const modals = document.querySelectorAll('.modal');
    const openBtns = document.querySelectorAll('[data-modal-target]');
    const closeBtns = document.querySelectorAll('.close-btn');

    openBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = document.querySelector(btn.dataset.modalTarget);
            if (target) target.classList.add('active');
        });
    });

    closeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (modal) modal.classList.remove('active');
        });
    });

    window.addEventListener('click', (e) => {
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Dropdown Logic
    const userToggle = document.getElementById('userDropdownToggle');
    const userMenu = document.getElementById('userMenu');
    const notifToggle = document.getElementById('notificationToggle');
    const notifMenu = document.getElementById('notificationMenu');

    if (userToggle && userMenu) {
        userToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            userMenu.classList.toggle('active');
            if (notifMenu) notifMenu.classList.remove('active');
        });
    }

    if (notifToggle && notifMenu) {
        notifToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            notifMenu.classList.toggle('active');
            if (userMenu) userMenu.classList.remove('active');
        });
    }

    window.addEventListener('click', (e) => {
        if (userMenu && !userMenu.contains(e.target) && !userToggle.contains(e.target)) {
            userMenu.classList.remove('active');
        }
        if (notifMenu && !notifMenu.contains(e.target) && !notifToggle.contains(e.target)) {
            notifMenu.classList.remove('active');
        }
    });

    // Image Zoom Logic
    const profilePics = document.querySelectorAll('.zoomable-profile-pic');
    const zoomModal = document.getElementById('imageZoomModal');
    const zoomedImg = document.getElementById('zoomedImage');

    if (profilePics.length > 0 && zoomModal && zoomedImg) {
        profilePics.forEach(pic => {
            pic.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent dropdown toggle
                zoomedImg.src = pic.src;
                zoomModal.classList.add('active');
            });
        });
    }

    // Chart.js Initialization
    const progressCtx = document.getElementById('progressChart');
    if (progressCtx) {
        window.progressChartInstance = new Chart(progressCtx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Pending'],
                datasets: [{
                    data: [window.completedTasks || 0, window.pendingTasks || 0],
                    backgroundColor: ['#10b981', '#f59e0b'],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    const activityCtx = document.getElementById('activityChart');
    if (activityCtx) {
        new Chart(activityCtx, {
            type: 'line',
            data: {
                labels: window.chartLabels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Study Hours',
                    data: window.chartData || [2, 3.5, 4, 2, 5, 1, 3], // fallback mock data
                    borderColor: '#7c3aed',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(124, 58, 237, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, display: false },
                    x: { grid: { display: false } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    // --- Global Timer Logic ---
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }

    // This runs every second on every page
    setInterval(() => {
        let isRunning = localStorage.getItem('timerRunning') === 'true';
        if (isRunning) {
            let endTime = parseInt(localStorage.getItem('timerEndTime'));
            if (!endTime) return;
            
            let now = Date.now();
            let timeLeft = Math.round((endTime - now) / 1000);
            
            if (timeLeft <= 0) {
                // Timer just finished!
                localStorage.setItem('timerRunning', 'false');
                localStorage.setItem('timerTimeLeft', '0');
                
                let mode = localStorage.getItem('timerMode') || 'focus';
                
                // Play global audio chime
                const audio = new Audio("https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3");
                audio.play().catch(e => console.log("Audio playback blocked by browser:", e));
                
                // Trigger Native Push Notification
                if ("Notification" in window && Notification.permission === "granted") {
                    let msg = mode === 'focus' ? "Great focus session! Don't forget to log it on the Timer page." : "Break is over! Ready to focus again?";
                    new Notification("Time's Up!", {
                        body: msg,
                        icon: "/static/uploads/dummy.jpg" // Note: replace with your real icon path
                    });
                }
                
                // Dispatch event for UI updates if on the timer page
                window.dispatchEvent(new Event('globalTimerFinished'));
            } else {
                localStorage.setItem('timerTimeLeft', timeLeft.toString());
                // Dispatch event for UI updates if on the timer page
                window.dispatchEvent(new Event('globalTimerTick'));
            }
        }
    }, 1000);

    // --- Password Visibility Toggle Logic ---
    const toggleBtns = document.querySelectorAll('.password-toggle-btn');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const container = this.closest('.password-container');
            if (container) {
                const input = container.querySelector('input');
                const icon = this.querySelector('i');
                if (input && icon) {
                    if (input.type === 'password') {
                        input.type = 'text';
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    } else {
                        input.type = 'password';
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                }
            }
        });
    });

    // --- Custom Delete Confirmation Modal Logic ---
    const deleteBtns = document.querySelectorAll('.delete-confirm');
    const deleteModal = document.getElementById('deleteConfirmModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    if (deleteBtns.length > 0 && deleteModal && confirmDeleteBtn) {
        deleteBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const deleteUrl = this.getAttribute('data-delete-url') || this.getAttribute('href');
                if (deleteUrl && deleteUrl !== '#' && !deleteUrl.startsWith('javascript:')) {
                    confirmDeleteBtn.setAttribute('href', deleteUrl);
                    deleteModal.classList.add('active');
                }
            });
        });
    }

    // --- Guest Interception Logic ---
    if (window.isGuest) {
        const loginModal = document.getElementById('loginRequiredModal');
        
        function openLoginModal() {
            if (loginModal) loginModal.classList.add('active');
        }

        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                loginModal.classList.remove('active');
            }
        });

        // 1. Intercept sidebar navigation links (except Dashboard)
        const sidebarLinks = document.querySelectorAll('.sidebar-nav a.nav-item');
        sidebarLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && !href.endsWith('/') && !href.includes('/dashboard')) {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    openLoginModal();
                });
            }
        });

        // 2. Intercept add buttons
        const addButtons = document.querySelectorAll('[data-modal-target="#addSubjectModal"], [data-modal-target="#addTaskModal"]');
        addButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                openLoginModal();
            });
        });

        // 3. Intercept task and subject action links (checkboxes, edits, deletions)
        document.body.addEventListener('click', function(e) {
            const target = e.target.closest('a');
            if (target) {
                const href = target.getAttribute('href');
                if (href && (href.includes('complete-task') || href.includes('delete-task') || href.includes('edit-task') || href.includes('delete-subject') || href.includes('edit-subject') || href.includes('add-subject') || href.includes('add-task'))) {
                    e.preventDefault();
                    e.stopPropagation();
                    openLoginModal();
                }
            }
        });
    }

    // --- Past Dates Restriction ---
    function getLocalDateString(dateObj) {
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    const todayLocalStr = getLocalDateString(new Date());
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.min = todayLocalStr;
    });

    const datetimeInputs = document.querySelectorAll('input[type="datetime-local"]');
    datetimeInputs.forEach(input => {
        input.min = todayLocalStr + "T00:00";
    });

    // --- Dynamic Progress Overview Calculations ---
    function updateProgressOverview() {
        const selectEl = document.getElementById('progressPeriodSelect');
        if (!selectEl) return;
        const period = selectEl.value;

        const today = new Date();
        const todayStr = getLocalDateString(today);

        // Find Monday and Sunday of the current week (local time)
        const dayOfWeek = today.getDay();
        const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        const monday = new Date(today);
        monday.setDate(today.getDate() + diffToMonday);
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);

        const mondayStr = getLocalDateString(monday);
        const sundayStr = getLocalDateString(sunday);

        let filteredTasks = [];
        if (period === 'today') {
            filteredTasks = (window.dashboardTasks || []).filter(t => {
                if (!t.scheduled_time) return false;
                return t.scheduled_time.split('T')[0] === todayStr;
            });
        } else { // week
            filteredTasks = (window.dashboardTasks || []).filter(t => {
                if (!t.scheduled_time) return false;
                const d = t.scheduled_time.split('T')[0];
                return d >= mondayStr && d <= sundayStr;
            });
        }

        const totalTasks = filteredTasks.length;
        const completedTasks = filteredTasks.filter(t => t.status === 'Completed').length;

        // Find subjects active in this period (has at least one task in filteredTasks)
        const activeSubjectIds = new Set(filteredTasks.map(t => t.subject_id).filter(id => id !== null));
        const totalSubjects = activeSubjectIds.size;
        let completedSubjects = 0;

        activeSubjectIds.forEach(subId => {
            // A subject is completed if all its tasks (overall) are completed
            const subjectTasks = (window.dashboardTasks || []).filter(t => t.subject_id === subId);
            if (subjectTasks.length > 0 && subjectTasks.every(t => t.status === 'Completed')) {
                completedSubjects++;
            }
        });

        const totalItems = totalTasks + totalSubjects;
        const completedItems = completedTasks + completedSubjects;
        const percent = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

        // Update UI Text
        const percentText = document.getElementById('progressPercentText');
        const periodLabel = document.getElementById('progressPeriodLabel');
        const feedbackText = document.getElementById('progressFeedbackText');

        if (percentText) {
            percentText.textContent = percent + '%';
        }
        if (periodLabel) {
            periodLabel.textContent = period === 'today' ? "Today's Progress" : "This Week's Progress";
        }
        if (feedbackText) {
            if (percent === 100) {
                feedbackText.textContent = 'All done! Fantastic work!';
            } else if (percent >= 70) {
                feedbackText.textContent = 'Almost there! Keep it up!';
            } else if (percent >= 40) {
                feedbackText.textContent = 'Steady progress! You got this!';
            } else if (percent > 0) {
                feedbackText.textContent = 'Off to a good start!';
            } else {
                feedbackText.textContent = 'No progress logged yet.';
            }
        }

        // Update Progress Doughnut Chart
        if (window.progressChartInstance) {
            const pendingItems = totalItems - completedItems;
            window.progressChartInstance.data.datasets[0].data = [completedItems, pendingItems];
            window.progressChartInstance.update();
        }
    }

    // Set listener and run initial progress update
    const periodSelect = document.getElementById('progressPeriodSelect');
    if (periodSelect) {
        periodSelect.addEventListener('change', updateProgressOverview);
    }
    updateProgressOverview();
});