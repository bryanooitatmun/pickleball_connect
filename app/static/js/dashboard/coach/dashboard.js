/**
 * Dashboard tab-specific JavaScript
 */

// This function is called when the dashboard tab is activated
function initDashboardTab() {
  updateDashboardStats();
}

// Update dashboard stats
async function updateDashboardStats() {
  try {
    const stats = await fetchAPI('/coach/stats');
    
    // Update completed sessions
    document.getElementById('completed-sessions').textContent = stats.completed_sessions;
    
    // Update upcoming sessions
    document.getElementById('upcoming-sessions').textContent = stats.upcoming_sessions;
    
    // Update total earnings
    document.getElementById('total-earnings').textContent = '$' + formatCurrency(stats.total_earnings);
    
    // Update rating
    document.getElementById('average-rating').textContent = stats.average_rating.toFixed(1);
    document.getElementById('rating-count').textContent = `${stats.rating_count} reviews`;
    
    // Update rating stars
    const starsContainer = document.getElementById('rating-stars');
    updateRatingStars(stats.average_rating, starsContainer);
    
    // Create dashboard earnings chart
    createDashboardEarningsChart(stats.monthly_earnings);
    
    // Update upcoming bookings
    updateUpcomingBookingsList(stats.upcoming_bookings || []);
    
    // Update recent logs
    updateRecentLogsList(stats.recent_logs || []);
    
    // Update Academy-specific elements if user is an academy manager
    if (IS_ACADEMY_MANAGER) {
      updateAcademyCoachesList(stats.academy_coaches || []);
      updateRecentPackagesList(stats.recent_packages || []);
    }
  } catch (error) {
    console.error('Error updating dashboard stats:', error);
    showToast('Error', 'Failed to update dashboard statistics', 'error');
  }
}

// Create dashboard earnings chart
function createDashboardEarningsChart(monthlyEarnings) {
  const ctx = document.getElementById('earnings-chart').getContext('2d');
  
  if (!ctx) {
    console.error('Canvas context for earnings chart not found');
    return;
  }
  
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
  
  // Add event listener for earnings period change
  document.getElementById('earnings-period').addEventListener('change', async function() {
    const period = this.value;
    
    try {
      const statsData = await fetchAPI(`/coach/stats/${period}`);
      createDashboardEarningsChart(statsData.monthly_earnings);
    } catch (error) {
      console.error('Error updating dashboard earnings chart:', error);
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
  
  // Take just the first 3 bookings
  const displayBookings = bookings.slice(0, 3);
  
  displayBookings.forEach(booking => {
    const bookingItem = document.createElement('div');
    bookingItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
    
    // Format date and time
    const bookingDate = formatDate(booking.date);
    const startTime = formatTime(booking.start_time);
    
    // Create HTML structure
    bookingItem.innerHTML = `
      <div>
        <h4 class="font-medium">${booking.student.first_name} ${booking.student.last_name}</h4>
        <p class="text-gray-500 text-sm">${bookingDate} at ${startTime}</p>
      </div>
      <div class="text-right">
        <p class="font-medium">$${formatCurrency(booking.price)}</p>
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
  
  // Take just the first 3 logs
  const displayLogs = logs.slice(0, 3);
  
  displayLogs.forEach(log => {
    const logItem = document.createElement('div');
    logItem.className = 'p-3 bg-gray-50 rounded-lg';
    
    // Format date
    const logDate = formatDate(log.booking.date);
    
    // Create HTML structure
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

// Update academy coaches list (for academy managers)
function updateAcademyCoachesList(coaches) {
  const container = document.getElementById('academy-coaches-list');
  
  if (!container) return;
  
  if (coaches.length === 0) {
    container.innerHTML = `
      <div class="text-center py-6 text-gray-500">
        <p>No coaches in the academy</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  // Take just the first 4 coaches
  const displayCoaches = coaches.slice(0, 4);
  
  displayCoaches.forEach(coach => {
    const coachItem = document.createElement('div');
    coachItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
    
    // Format profile picture
    let profilePic = '';
    if (coach.profile_picture) {
      profilePic = `<img src="${coach.profile_picture}" alt="Profile" class="h-10 w-10 rounded-full object-cover">`;
    } else {
      profilePic = `<div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold">
                      ${coach.first_name.charAt(0)}
                    </div>`;
    }
    
    // Create HTML structure
    coachItem.innerHTML = `
      <div class="flex items-center">
        <div class="flex-shrink-0">
          ${profilePic}
        </div>
        <div class="ml-3">
          <h4 class="font-medium">${coach.first_name} ${coach.last_name}</h4>
          <p class="text-gray-500 text-sm">${coach.role || 'Coach'}</p>
        </div>
      </div>
      <div class="text-right">
        <p class="font-medium">DUPR ${coach.dupr_rating}</p>
        <p class="text-gray-500 text-sm">${coach.sessions_completed} sessions</p>
      </div>
    `;
    
    container.appendChild(coachItem);
  });
}

// Update recent packages list (for academy managers)
function updateRecentPackagesList(packages) {
  const container = document.getElementById('recent-packages-list');
  
  if (!container) return;
  
  if (packages.length === 0) {
    container.innerHTML = `
      <div class="text-center py-6 text-gray-500">
        <p>No recent package requests</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  // Take just the first 3 packages
  const displayPackages = packages.slice(0, 3);
  
  displayPackages.forEach(pkg => {
    const packageItem = document.createElement('div');
    packageItem.className = 'p-3 bg-gray-50 rounded-lg';
    
    // Format package status
    let statusClass = 'bg-yellow-100 text-yellow-800';
    if (pkg.status === 'approved') {
      statusClass = 'bg-green-100 text-green-800';
    } else if (pkg.status === 'rejected') {
      statusClass = 'bg-red-100 text-red-800';
    }
    
    // Format date
    const purchaseDate = formatDate(pkg.purchase_date);
    
    // Create HTML structure
    packageItem.innerHTML = `
      <div class="flex justify-between mb-1">
        <h4 class="font-medium">${pkg.student.first_name} ${pkg.student.last_name}</h4>
        <span class="text-sm ${statusClass} px-2 py-1 rounded">${pkg.status.charAt(0).toUpperCase() + pkg.status.slice(1)}</span>
      </div>
      <p class="text-gray-600 text-sm">${pkg.package_name || 'Custom Package'} - ${pkg.sessions_count} sessions</p>
      <p class="text-gray-500 text-xs mt-1">Purchased: ${purchaseDate}</p>
    `;
    
    container.appendChild(packageItem);
  });
}