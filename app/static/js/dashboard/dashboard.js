// Main dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tabs
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const mobileNav = document.getElementById('mobile-nav');
  
    function activateTab(tabId) {
      // Hide all tab contents
      tabContents.forEach(content => {
        content.classList.remove('active');
      });
      
      // Remove active class from all tab links
      tabLinks.forEach(link => {
        link.classList.remove('active-nav-link');
      });
      
      // Show the selected tab content
      const tabContent = document.getElementById(`${tabId}-tab`);
      if (tabContent) {
        tabContent.classList.add('active');
      }
      
      // Add active class to the clicked tab link
      const tabLink = document.querySelector(`.${tabId}-tab`);
      if (tabLink) {
        tabLink.classList.add('active-nav-link');
      }
      
      // Update mobile nav
      if (mobileNav) {
        mobileNav.value = tabId;
      }
      
      // Store active tab in local storage
      localStorage.setItem('activeTab', tabId);
    }
  
    // Add click event to tab links
    tabLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        const tabId = this.getAttribute('href').substring(1);
        activateTab(tabId);
      });
    });
  
    // Handle mobile navigation
    if (mobileNav) {
      mobileNav.addEventListener('change', function() {
        activateTab(this.value);
      });
    }
  
    // Initialize dropdowns
    const profileBtn = document.getElementById('profile-btn');
    const profileMenu = document.getElementById('profile-menu');
    const notificationBtn = document.getElementById('notification-btn');
    const notificationMenu = document.getElementById('notification-menu');
  
    if (profileBtn && profileMenu) {
      profileBtn.addEventListener('click', function() {
        profileMenu.classList.toggle('hidden');
        if (notificationMenu) {
          notificationMenu.classList.add('hidden');
        }
      });
    }
  
    if (notificationBtn && notificationMenu) {
      notificationBtn.addEventListener('click', function() {
        notificationMenu.classList.toggle('hidden');
        if (profileMenu) {
          profileMenu.classList.add('hidden');
        }
      });
    }
  
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
      if (profileBtn && profileMenu && !profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.classList.add('hidden');
      }
      
      if (notificationBtn && notificationMenu && !notificationBtn.contains(e.target) && !notificationMenu.contains(e.target)) {
        notificationMenu.classList.add('hidden');
      }
    });
  
    // Initialize toast notifications
    window.showToast = function(title, message, type = 'success') {
      const toast = document.getElementById('toast-notification');
      if (!toast) return;
      
      const toastTitle = document.getElementById('toast-title');
      const toastMessage = document.getElementById('toast-message');
      const toastIcon = document.getElementById('toast-icon');
      
      toastTitle.textContent = title;
      toastMessage.textContent = message;
      
      // Set icon and color based on type
      if (type === 'success') {
        toastIcon.innerHTML = '<i class="fas fa-check"></i>';
        toastIcon.classList.add('bg-green-500');
        toastIcon.classList.remove('bg-red-500', 'bg-blue-500');
      } else if (type === 'error') {
        toastIcon.innerHTML = '<i class="fas fa-exclamation"></i>';
        toastIcon.classList.add('bg-red-500');
        toastIcon.classList.remove('bg-green-500', 'bg-blue-500');
      } else if (type === 'info') {
        toastIcon.innerHTML = '<i class="fas fa-info"></i>';
        toastIcon.classList.add('bg-blue-500');
        toastIcon.classList.remove('bg-green-500', 'bg-red-500');
      }
      
      // Show toast
      toast.classList.remove('hidden');
      setTimeout(() => {
        toast.classList.remove('translate-y-24', 'opacity-0');
      }, 10);
      
      // Hide toast after 5 seconds
      setTimeout(() => {
        toast.classList.add('translate-y-24', 'opacity-0');
        setTimeout(() => {
          toast.classList.add('hidden');
        }, 300);
      }, 5000);
    };
  
    // Initialize toast close button
    const toastClose = document.getElementById('toast-close');
    if (toastClose) {
      toastClose.addEventListener('click', function() {
        const toast = document.getElementById('toast-notification');
        toast.classList.add('translate-y-24', 'opacity-0');
        setTimeout(() => {
          toast.classList.add('hidden');
        }, 300);
      });
    }
  
    // Load notifications
    const loadNotifications = async () => {
      try {
        const response = await fetch('/api/notifications');
        const data = await response.json();
        
        // Update notification badge
        const badge = document.getElementById('notification-badge');
        if (badge) {
          if (data.unread_count > 0) {
            badge.textContent = data.unread_count > 9 ? '9+' : data.unread_count;
            badge.classList.remove('hidden');
          } else {
            badge.classList.add('hidden');
          }
        }
        
        // Update notification list
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
          if (data.notifications.length === 0) {
            notificationList.innerHTML = `
              <div class="px-4 py-3 text-center text-gray-500 text-sm">
                No new notifications
              </div>
            `;
          } else {
            notificationList.innerHTML = '';
            
            data.notifications.slice(0, 5).forEach(notification => {
              const item = document.createElement('div');
              item.className = `px-4 py-3 border-b border-gray-100 ${notification.is_read ? 'bg-white' : 'bg-blue-50'}`;
              
              // Format timestamp
              const date = new Date(notification.created_at);
              const timeAgo = getTimeAgo(date);
              
              item.innerHTML = `
                <div class="flex justify-between items-start">
                  <div>
                    <p class="font-medium text-sm">${notification.title}</p>
                    <p class="text-gray-600 text-sm mt-1">${notification.message}</p>
                  </div>
                  <span class="text-xs text-gray-500">${timeAgo}</span>
                </div>
              `;
              
              // Add click handler to mark as read
              item.addEventListener('click', async () => {
                if (!notification.is_read) {
                  try {
                    await fetch('/api/notifications/mark-read', {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        notification_id: notification.id
                      })
                    });
                    
                    // Update UI
                    item.classList.remove('bg-blue-50');
                    item.classList.add('bg-white');
                    
                    // Update badge count
                    if (badge) {
                      const newCount = parseInt(badge.textContent) - 1;
                      if (newCount <= 0) {
                        badge.classList.add('hidden');
                      } else {
                        badge.textContent = newCount;
                      }
                    }
                  } catch (error) {
                    console.error('Error marking notification as read:', error);
                  }
                }
                
                // Handle notification click based on type
                handleNotificationClick(notification);
              });
              
              notificationList.appendChild(item);
            });
            
            // Add "View All" link if there are more notifications
            if (data.notifications.length > 5) {
              const viewAll = document.createElement('div');
              viewAll.className = 'px-4 py-2 text-center';
              viewAll.innerHTML = `
                <a href="/notifications" class="text-blue-600 text-sm hover:underline">View All Notifications</a>
              `;
              notificationList.appendChild(viewAll);
            }
          }
        }
      } catch (error) {
        console.error('Error loading notifications:', error);
      }
    };
  
    // Handle notification click
    const handleNotificationClick = (notification) => {
      // Close notification menu
      if (notificationMenu) {
        notificationMenu.classList.add('hidden');
      }
      
      // Handle different notification types
      switch (notification.notification_type) {
        case 'booking':
          // Navigate to booking details or show booking modal
          activateTab('bookings');
          break;
          
        case 'payment_proof':
          // Show payment proof modal
          activateTab('bookings');
          break;
          
        case 'package_purchase':
          // Navigate to package approvals tab
          activateTab('packages');
          break;
          
        // Add more notification types as needed
      }
    };
  
    // Helper function to format time ago
    const getTimeAgo = (date) => {
      const seconds = Math.floor((new Date() - date) / 1000);
      
      let interval = Math.floor(seconds / 31536000);
      if (interval >= 1) {
        return interval === 1 ? '1 year ago' : `${interval} years ago`;
      }
      
      interval = Math.floor(seconds / 2592000);
      if (interval >= 1) {
        return interval === 1 ? '1 month ago' : `${interval} months ago`;
      }
      
      interval = Math.floor(seconds / 86400);
      if (interval >= 1) {
        return interval === 1 ? '1 day ago' : `${interval} days ago`;
      }
      
      interval = Math.floor(seconds / 3600);
      if (interval >= 1) {
        return interval === 1 ? '1 hour ago' : `${interval} hours ago`;
      }
      
      interval = Math.floor(seconds / 60);
      if (interval >= 1) {
        return interval === 1 ? '1 minute ago' : `${interval} minutes ago`;
      }
      
      return 'Just now';
    };
  
    // Load notifications on page load
    loadNotifications();
    
    // Periodically check for new notifications (every 60 seconds)
    setInterval(loadNotifications, 60000);
  
    // Load the dashboard data
    loadDashboardData();
    
    // Restore active tab from local storage
    const activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
      activateTab(activeTab);
    }
  });
  
  // Load dashboard data
  async function loadDashboardData() {
    try {
      const response = await fetch('/api/coach/stats');
      const data = await response.json();
      
      // Update dashboard stats
      updateDashboardStats(data);
      
      // Create dashboard earnings chart
      if (document.getElementById('earnings-chart')) {
        createDashboardEarningsChart(data.monthly_earnings);
      }
      
      // Update upcoming bookings list
      const upcomingBookings = await fetch('/api/coach/bookings/upcoming');
      const bookingsData = await upcomingBookings.json();
      
      updateUpcomingBookingsList(bookingsData.slice(0, 3));
      
      // Load session logs for dashboard
      const sessionLogs = await fetch('/api/coach/session-logs');
      const logsData = await sessionLogs.json();
      
      updateRecentLogsList(logsData.slice(0, 3));
      
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      window.showToast('Error', 'Failed to load dashboard data', 'error');
    }
  }
  
  // Update dashboard stats
  function updateDashboardStats(data) {
    // Update completed sessions
    const completedSessions = document.getElementById('completed-sessions');
    if (completedSessions) {
      completedSessions.textContent = data.completed_sessions;
    }
    
    // Update upcoming sessions
    const upcomingSessions = document.getElementById('upcoming-sessions');
    if (upcomingSessions) {
      upcomingSessions.textContent = data.upcoming_sessions;
    }
    
    // Update total earnings
    const totalEarnings = document.getElementById('total-earnings');
    if (totalEarnings) {
      totalEarnings.textContent = '$' + data.total_earnings.toFixed(2);
    }
    
    // Update rating
    const averageRating = document.getElementById('average-rating');
    if (averageRating) {
      averageRating.textContent = data.average_rating.toFixed(1);
    }
    
    const ratingCount = document.getElementById('rating-count');
    if (ratingCount) {
      ratingCount.textContent = `${data.rating_count} reviews`;
    }
    
    // Update rating stars
    const starsContainer = document.getElementById('rating-stars');
    if (starsContainer) {
      starsContainer.innerHTML = '';
      
      const fullStars = Math.floor(data.average_rating);
      const hasHalfStar = data.average_rating % 1 >= 0.5;
      
      for (let i = 1; i <= 5; i++) {
        const star = document.createElement('i');
        
        if (i <= fullStars) {
          star.className = 'fas fa-star';
        } else if (i === fullStars + 1 && hasHalfStar) {
          star.className = 'fas fa-star-half-alt';
        } else {
          star.className = 'far fa-star';
        }
        
        starsContainer.appendChild(star);
      }
    }
  }
  
  // Create dashboard earnings chart
  function createDashboardEarningsChart(monthlyEarnings) {
    const ctx = document.getElementById('earnings-chart');
    if (!ctx) return;
    
    // Clear any existing chart
    if (window.earningsChart) {
      window.earningsChart.destroy();
    }
    
    // Extract labels and data
    const labels = [];
    const data = [];
    
    // Sort months chronologically
    const sortedMonths = Object.keys(monthlyEarnings || {}).sort((a, b) => {
      const dateA = new Date(a);
      const dateB = new Date(b);
      return dateA - dateB;
    });
    
    // Take the last 6 months
    const recentMonths = sortedMonths.slice(-6);
    
    recentMonths.forEach(month => {
      // Format month as MMM
      const date = new Date(month);
      const formattedMonth = date.toLocaleDateString('en-US', { month: 'short' });
      
      labels.push(formattedMonth);
      data.push(monthlyEarnings[month]);
    });
    
    // Create chart
    window.earningsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Earnings',
          data: data,
          backgroundColor: 'rgba(101, 116, 205, 0.7)',
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '$' + value;
              }
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context) {
                return 'Earnings: $' + context.raw.toFixed(2);
              }
            }
          },
          legend: {
            display: false
          }
        }
      }
    });
  }
  
  // Update upcoming bookings list on dashboard
  function updateUpcomingBookingsList(bookings) {
    const container = document.getElementById('upcoming-bookings-list');
    if (!container) return;
    
    if (bookings.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No upcoming bookings</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    bookings.forEach(booking => {
      const bookingItem = document.createElement('div');
      bookingItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2';
      
      // Format date and time
      const bookingDate = new Date(booking.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      const startTime = new Date(`2000-01-01T${booking.start_time}`).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      
      bookingItem.innerHTML = `
        <div>
          <h4 class="font-medium">${booking.student.first_name} ${booking.student.last_name}</h4>
          <p class="text-gray-500 text-sm">${bookingDate} at ${startTime}</p>
        </div>
        <div class="text-right">
          <p class="font-medium">$${booking.price.toFixed(2)}</p>
          <p class="text-gray-500 text-sm">${booking.court.name}</p>
        </div>
      `;
      
      container.appendChild(bookingItem);
    });
  }
  
  // Update recent logs list on dashboard
  function updateRecentLogsList(logs) {
    const container = document.getElementById('recent-logs-list');
    if (!container) return;
    
    if (logs.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No recent session logs</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    logs.forEach(log => {
      const logItem = document.createElement('div');
      logItem.className = 'p-3 bg-gray-50 rounded-lg mb-2';
      
      // Format date
      const logDate = new Date(log.booking.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      
      logItem.innerHTML = `
        <div class="flex justify-between mb-1">
          <h4 class="font-medium">${log.title}</h4>
          <span class="text-sm text-gray-500">${logDate}</span>
        </div>
        <p class="text-gray-600 text-sm line-clamp-2">${log.notes || 'No notes added'}</p>
      `;
      
      container.appendChild(logItem);
    });
  }