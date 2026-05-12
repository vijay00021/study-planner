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
        new Chart(progressCtx, {
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
});