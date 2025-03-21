/**
 * Dashboard tab-specific JavaScript
 */

// Cache for pending approval items
let pendingPackages = [];
let pendingVenues = [];

// This function is called when the dashboard tab is activated
function initDashboardTab() {
  updateDashboardStats();
  loadPendingPackages();
  loadPendingVenues();
  
  // Setup cancel reason modal
  setupCancelReasonModal();
  setupApprovalModalEventListeners();
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

// Load pending package approvals
async function loadPendingPackages() {
  try {
    // Show loading state
    document.getElementById('pending-packages-loading').classList.remove('hidden');
    document.getElementById('pending-packages-list').classList.add('hidden');
    document.getElementById('no-pending-packages').classList.add('hidden');
    document.getElementById('pending-packages-error').classList.add('hidden');
    
    // Fetch pending packages
    const packages = await fetchAPI('/coach/packages/pending');
    
    // Sort by date (earliest first)
    packages.sort((a, b) => new Date(a.purchase_date) - new Date(b.purchase_date));
    
    // Take max 5 items
    pendingPackages = packages.slice(0, 3);
    
    // Update pending count
    document.getElementById('pending-packages-count').textContent = pendingPackages.length;
    
    // Display pending packages
    displayPendingPackages(pendingPackages);
    
    // Hide loading
    document.getElementById('pending-packages-loading').classList.add('hidden');
    
  } catch (error) {
    console.error('Error loading pending packages:', error);
    document.getElementById('pending-packages-loading').classList.add('hidden');
    document.getElementById('pending-packages-error').classList.remove('hidden');
  }
}

// Load pending venue confirmations
async function loadPendingVenues() {
  try {
    // Show loading state
    document.getElementById('pending-venues-loading').classList.remove('hidden');
    document.getElementById('pending-venues-list').classList.add('hidden');
    document.getElementById('no-pending-venues').classList.add('hidden');
    document.getElementById('pending-venues-error').classList.add('hidden');
    
    // Fetch pending venues
    const venues = await fetchAPI('/coach/bookings/pending-venue');
    
    // Sort by date (earliest first)
    venues.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Take max 5 items
    pendingVenues = venues.slice(0, 3);
    
    // Update pending count
    document.getElementById('pending-venues-count').textContent = pendingVenues.length;
    
    // Display pending venues
    displayPendingVenues(pendingVenues);
    
    // Hide loading
    document.getElementById('pending-venues-loading').classList.add('hidden');
    
  } catch (error) {
    console.error('Error loading pending venues:', error);
    document.getElementById('pending-venues-loading').classList.add('hidden');
    document.getElementById('pending-venues-error').classList.remove('hidden');
  }
}

// Display pending packages in the dashboard
function displayPendingPackages(packages) {
  const container = document.getElementById('pending-packages-list');
  
  if (!packages || packages.length === 0) {
    document.getElementById('no-pending-packages').classList.remove('hidden');
    container.classList.add('hidden');
    return;
  }
  
  // Show container, hide empty message
  container.classList.remove('hidden');
  document.getElementById('no-pending-packages').classList.add('hidden');
  
  // Clear container
  container.innerHTML = '';
  
  // Add items to the container
  packages.forEach(item => {
    const approvalCard = document.createElement('div');
    approvalCard.className = 'bg-gray-50 border border-gray-200 rounded-lg p-4';
    approvalCard.innerHTML = createPackageApprovalCard(item);
    container.appendChild(approvalCard);
  });
  
  // Add event listeners to action buttons
  addPackageApprovalEventListeners();
}

// Display pending venue confirmations in the dashboard
function displayPendingVenues(venues) {
  const container = document.getElementById('pending-venues-list');
  
  if (!venues || venues.length === 0) {
    document.getElementById('no-pending-venues').classList.remove('hidden');
    container.classList.add('hidden');
    return;
  }
  
  // Show container, hide empty message
  container.classList.remove('hidden');
  document.getElementById('no-pending-venues').classList.add('hidden');
  
  // Clear container
  container.innerHTML = '';
  
  // Add items to the container
  venues.forEach(item => {
    const approvalCard = document.createElement('div');
    approvalCard.className = 'bg-gray-50 border border-gray-200 rounded-lg p-4';
    approvalCard.innerHTML = createVenueApprovalCard(item);
    container.appendChild(approvalCard);
  });
  
  // Add event listeners to action buttons
  addVenueApprovalEventListeners();
}

// Create HTML for package approval card
function createPackageApprovalCard(packageData) {
  const purchaseDate = formatDate(packageData.purchase_date);
  
  // Determine if we have payment proof available
  const hasPaymentProof = packageData.payment_proof_url || packageData.payment_proof;
  const paymentProofButton = hasPaymentProof ? 
    `<button class="text-blue-600 hover:text-blue-800 view-package-proof-btn" data-proof="${hasPaymentProof}" data-id="${packageData.id}">
      <i class="fas fa-receipt mr-1"></i> View Payment Proof
    </button>` : 
    `<span class="text-gray-500 text-sm">No payment proof available</span>`;
  
  return `
    <div class="flex justify-between">
      <div>
        <div class="flex items-center">
          <span class="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs mr-2">Package</span>
          <h4 class="font-medium">${packageData.pricing_plan.name}</h4>
        </div>
        <p class="text-gray-500 text-sm mt-1">
          Purchase by ${packageData.student.name} on ${purchaseDate}
        </p>
        <p class="text-gray-600 text-sm mt-1">
          ${packageData.total_sessions} sessions for $${formatCurrency(packageData.total_price)}
        </p>
        <div class="mt-2">
          ${paymentProofButton}
        </div>
      </div>
      <div class="flex flex-col justify-between items-end">
        <span class="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800 mb-2">Pending Approval</span>
        <div class="flex space-x-2 mt-2">
          <button class="bg-green-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-green-700 approve-purchase-btn" data-id="${packageData.id}">
            <i class="fas fa-check-circle mr-1"></i> Approve
          </button>
          <button class="bg-red-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-red-700 cancel-package-btn" data-id="${packageData.id}">
            <i class="fas fa-times-circle mr-1"></i> Decline
          </button>
        </div>
      </div>
    </div>
  `;
}

// Create HTML for venue confirmation card
function createVenueApprovalCard(bookingData) {
  const bookingDate = formatDate(bookingData.date);
  
  // Determine if we have proof buttons available
  const hasCoachPaymentProof = bookingData.payment_proof || bookingData.coaching_payment_proof;
  const hasCourtProof = bookingData.court_booking_proof;
  
  const paymentProofButton = hasCoachPaymentProof ? 
    `<button class="text-blue-600 hover:text-blue-800 view-payment-proof-btn mr-3" data-proof="${hasCoachPaymentProof}" data-id="${bookingData.id}">
      <i class="fas fa-file-invoice-dollar mr-1"></i> Coaching Payment
    </button>` : '';
  
  const courtProofButton = hasCourtProof ? 
    `<button class="text-blue-600 hover:text-blue-800 view-court-proof-btn" data-proof="${hasCourtProof}" data-id="${bookingData.id}">
      <i class="fas fa-map-marker-alt mr-1"></i> Court Booking Proof
    </button>` : '';
  
  // If neither proof is available
  const noProofMessage = !hasCoachPaymentProof && !hasCourtProof ? 
    `<span class="text-gray-500 text-sm">No proofs available</span>` : '';
  
  return `
    <div class="flex justify-between">
      <div>
        <div class="flex items-center">
          <span class="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs mr-2">Booking</span>
          <h4 class="font-medium">${bookingData.student.first_name} ${bookingData.student.last_name}</h4>
        </div>
        <p class="text-gray-500 text-sm mt-1">
          Session on ${bookingDate} at ${formatTime(bookingData.start_time)}
        </p>
        <p class="text-gray-600 text-sm mt-1">
          ${bookingData.court.name} - $${formatCurrency(bookingData.price)}
        </p>
        <div class="mt-2">
          ${paymentProofButton}
          ${courtProofButton}
          ${noProofMessage}
        </div>
      </div>
      <div class="flex flex-col justify-between items-end">
        <span class="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800 mb-2">Venue Confirmation Needed</span>
        <div class="flex space-x-2 mt-2">
          <button class="bg-green-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-green-700 confirm-venue-btn" data-id="${bookingData.id}">
            <i class="fas fa-check-circle mr-1"></i> Confirm Venue
          </button>
          <button class="bg-red-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-red-700 cancel-booking-btn" data-id="${bookingData.id}">
            <i class="fas fa-times-circle mr-1"></i> Cancel
          </button>
        </div>
      </div>
    </div>
  `;
}

// Add event listeners to package approval buttons
function addPackageApprovalEventListeners() {
  // Package approval buttons

  document.querySelectorAll('.approve-purchase-btn').forEach(btn => {
    // Clone and replace to remove all listeners
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
  });

  document.querySelectorAll('.approve-purchase-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const packageId = this.getAttribute('data-id');
      // Reuse the existing function from packages.js
      showApprovePurchaseModal(packageId, IS_ACADEMY_MANAGER);
    });
  });
  
  document.querySelectorAll('.cancel-package-btn').forEach(btn => {
    // Clone and replace to remove all listeners
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
  });
  
  // Package cancel buttons
  document.querySelectorAll('.cancel-package-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const packageId = this.getAttribute('data-id');
      showCancelReasonModal('package', packageId);
    });
  });
  
  // View payment proof buttons
  document.querySelectorAll('.view-package-proof-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const packageId = this.getAttribute('data-id');
      const img = this.getAttribute('data-proof');
      viewPackagePaymentProof('uploads' + img);
    });
  });
}

// Add event listeners to venue approval buttons
function addVenueApprovalEventListeners() {
  // Venue confirmation buttons

  document.querySelectorAll('.confirm-venue-btn').forEach(btn => {
    // Clone and replace to remove all listeners
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
  });

  document.querySelectorAll('.confirm-venue-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const bookingId = this.getAttribute('data-id');
      // Reuse the existing function from bookings.js
      showConfirmVenueModal(bookingId);
    });
  });
  
  document.querySelectorAll('.cancel-booking-btn').forEach(btn => {
    // Clone and replace to remove all listeners
    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
  });

  // Booking cancel buttons
  document.querySelectorAll('.cancel-booking-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault(); // Prevent any default actions
      const bookingId = this.getAttribute('data-id');
      console.log("Cancel button clicked, ID:", bookingId); // Debug
      if (bookingId) {
        showCancelReasonModal('booking', bookingId);
      } else {
        console.error("No data-id found on button:", this);
      }
    });
  });
  
  // View payment proof buttons
  document.querySelectorAll('.view-payment-proof-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const bookingId = this.getAttribute('data-id');
      const img = this.getAttribute('data-proof');
      viewBookingPaymentProof(img);
    });
  });
  
  // View court proof buttons
  document.querySelectorAll('.view-court-proof-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const bookingId = this.getAttribute('data-id');
      const img = this.getAttribute('data-proof');
      viewCourtProof(img);
    });
  });
}

// Setup the cancel reason modal
function setupCancelReasonModal() {
  // Close modal buttons
  document.querySelectorAll('.close-cancel-reason-modal')?.forEach(btn => {
    btn.addEventListener('click', function() {
      document.getElementById('cancel-reason-modal').classList.add('hidden');
    });
  });
  
  // Form submission
  document.getElementById('cancel-reason-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const itemId = document.getElementById('cancel-item-id').value;
    const itemType = document.getElementById('cancel-item-type').value;
    const reason = document.getElementById('cancel-reason').value;
    
    try {
      // Show loading state
      showLoading(this);
      
      if (itemType === 'package') {
        // Call API to reject package with reason
        await fetchAPI('/coach/packages/purchased/reject', {
          method: 'POST',
          body: JSON.stringify({
            purchase_id: itemId,
            reason: reason
          })
        });
      } else if (itemType === 'booking') {
        // Call API to cancel booking with reason
        await fetchAPI('/coach/cancel-session', {
          method: 'POST',
          body: JSON.stringify({
            booking_id: itemId,
            reason: reason
          })
        });
      }
      
      // Hide loading and modal
      hideLoading(this);
      document.getElementById('cancel-reason-modal').classList.add('hidden');
      
      // Show success message
      showToast('Success', `${itemType === 'package' ? 'Package' : 'Booking'} has been cancelled.`, 'success');
      
      // Reset form
      this.reset();
      
      // Reload pending approvals and stats
      await loadPendingPackages();
      await loadPendingVenues();
      updateDashboardStats();
      
      // If bookings.js or packages.js are available, trigger their data reload
      if (typeof loadBookings === 'function') {
        loadBookings();
      }
      if (typeof loadPackagesData === 'function') {
        loadPackagesData();
      }
      
    } catch (error) {
      hideLoading(this);
      console.error(`Error cancelling ${itemType}:`, error);
      showToast('Error', `Failed to cancel ${itemType}. Please try again.`, 'error');
    }
  });
}

// Function to show the cancel reason modal
function showCancelReasonModal(itemType, itemId) {
  console.log("Setting values:", itemType, itemId);
  console.log("Element exists:", !!document.getElementById('cancel-item-id'));

  // Set modal values
  const idElement = document.getElementById('cancel-item-id');
  if (idElement) {
    idElement.value = itemId;
    console.log("Value set to:", idElement.value);
  } else {
    console.error("cancel-item-id element not found!");
  }


  // Set modal values
  //document.getElementById('cancel-item-id').value = itemId;
  document.getElementById('cancel-item-type').value = itemType;
  document.getElementById('cancel-reason').value = '';
  
  // Show modal
  document.getElementById('cancel-reason-modal').classList.remove('hidden');
}

// Function to view package payment proof
async function viewPackagePaymentProof(img) {
  try {
    const proofData = '/static/' + img;

    if (proofData) {
      // Open proof in new tab
      window.open(proofData, '_blank');
    } else {
      showToast('Info', 'No payment proof available for this package.', 'info');
    }
  } catch (error) {
    console.error('Error fetching package payment proof:', error);
    showToast('Error', 'Failed to load payment proof.', 'error');
  }
}

// Function to view booking payment proof
async function viewBookingPaymentProof(img) {
  try {
    const proofData = '/static/' + img;
    
    if (proofData) {
      // Open proof in new tab
      window.open(proofData, '_blank');
    } else {
      showToast('Info', 'No payment proof available for this booking.', 'info');
    }
  } catch (error) {
    console.error('Error fetching booking payment proof:', error);
    showToast('Error', 'Failed to load payment proof.', 'error');
  }
}

// Function to view court booking proof
async function viewCourtProof(img) {
  try {
    const proofData = '/static/' + img;
    
    if (proofData) {
      // Open proof in new tab
      window.open(proofData, '_blank');
    } else {
      showToast('Info', 'No court booking proof available.', 'info');
    }
  } catch (error) {
    console.error('Error fetching court booking proof:', error);
    showToast('Error', 'Failed to load court booking proof.', 'error');
  }
}

// Add a listener to refresh the pending approvals after package/venue actions
document.addEventListener('approvalActionCompleted', function() {
  // Reload pending approvals
  loadPendingPackages();
  loadPendingVenues();
});

// Custom event when an approval is completed in packages.js or bookings.js
function triggerApprovalCompleted() {
  document.dispatchEvent(new CustomEvent('approvalActionCompleted'));
}
