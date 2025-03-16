/**
 * Common utility functions for the dashboard
 */

// API configuration
const API_BASE_URL = '/api';
const IS_COACH = document.getElementById('user-is-coach')?.value === 'true';
const IS_ACADEMY_MANAGER = document.getElementById('user-is-academy-manager')?.value === 'true';

/**
 * Helper Functions
 */

// Format date string to a more readable format
function formatDate(dateString) {
  const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
  return new Date(dateString).toLocaleDateString('en-US', options);
}

// Format time string to a more readable format
function formatTime(timeString) {
  return new Date(`2000-01-01T${timeString}`).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// Format currency value
function formatCurrency(amount) {
  return Number(parseFloat(amount)).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// Show loading state on an element
function showLoading(element) {
  element.classList.add('loading');
  if (element.tagName === 'BUTTON') {
    element.disabled = true;
  }
}

// Hide loading state from an element
function hideLoading(element) {
  element.classList.remove('loading');
  if (element.tagName === 'BUTTON') {
    element.disabled = false;
  }
}

// Show a toast notification
function showToast(title, message, type = 'success') {
  const toast = document.getElementById('toast-notification');
  const toastTitle = document.getElementById('toast-title');
  const toastMessage = document.getElementById('toast-message');
  const toastIcon = document.getElementById('toast-icon');
  
  if (!toast || !toastTitle || !toastMessage || !toastIcon) {
    console.error('Toast notification elements not found');
    return;
  }
  
  toastTitle.textContent = title;
  toastMessage.textContent = message;
  
  // Set icon and color based on type
  if (type === 'success') {
    toastIcon.innerHTML = '<i class="fas fa-check"></i>';
    toastIcon.className = 'h-6 w-6 flex-shrink-0 flex items-center justify-center rounded-full text-white bg-green-500';
  } else if (type === 'error') {
    toastIcon.innerHTML = '<i class="fas fa-exclamation"></i>';
    toastIcon.className = 'h-6 w-6 flex-shrink-0 flex items-center justify-center rounded-full text-white bg-red-500';
  } else if (type === 'info') {
    toastIcon.innerHTML = '<i class="fas fa-info"></i>';
    toastIcon.className = 'h-6 w-6 flex-shrink-0 flex items-center justify-center rounded-full text-white bg-blue-500';
  } else if (type === 'warning') {
    toastIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
    toastIcon.className = 'h-6 w-6 flex-shrink-0 flex items-center justify-center rounded-full text-white bg-yellow-500';
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
}

// Convert time in HH:MM format to minutes since midnight
function timeStringToMinutes(timeString) {
  if (!timeString) return 0;
  const [hours, minutes] = timeString.split(':').map(part => parseInt(part) || 0);
  return hours * 60 + minutes;
}

// Convert minutes since midnight to HH:MM format
function minutesToTimeString(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

// Format a breakdown type for display
function formatBreakdownType(type) {
  switch (type) {
    case 'regular':
      return 'Regular Sessions';
    case 'first_time':
      return 'First-Time Discount';
    case 'package':
      return 'Package Deals';
    case 'seasonal':
      return 'Seasonal Offers';
    case 'custom':
      return 'Custom Discounts';
    default:
      return type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ');
  }
}

// Update rating stars display
function updateRatingStars(rating, container) {
  container.innerHTML = '';
  
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating % 1 >= 0.5;
  
  for (let i = 1; i <= 5; i++) {
    const star = document.createElement('i');
    
    if (i <= fullStars) {
      star.className = 'fas fa-star';
    } else if (i === fullStars + 1 && hasHalfStar) {
      star.className = 'fas fa-star-half-alt';
    } else {
      star.className = 'far fa-star';
    }
    
    container.appendChild(star);
  }
}

/**
 * API Functions
 */

// Generic fetch API function
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    // Get the response data whether it succeeded or failed
    const data = await response.json().catch(() => ({}));
    
    // If response is not ok, throw an error with the actual error message from the server
    if (!response.ok) {
      throw new Error(data.error || data.message || response.statusText || 'An error occurred');
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// Load user profile
async function loadUserProfile() {
  if (IS_COACH) {
    return await fetchAPI('/coach/profile');
  } else if (IS_ACADEMY_MANAGER) {
    return await fetchAPI('/academy/profile');
  }
  return null;
}

// Get coach profile
async function getCoachProfile() {
  return fetchAPI('/coach/profile');
}

// Update coach profile
async function updateCoachProfile(profileData) {
  return fetchAPI('/coach/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData)
  });
}

// Change password
async function changePassword(passwordData) {
  return fetchAPI('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(passwordData)
  });
}

// Get courts
async function getCourts() {
  return fetchAPI('/courts');
}

// Get coach courts
async function getCoachCourts() {
  return fetchAPI('/coach/courts');
}

// Add coach court
async function addCoachCourt(courtData) {
  return fetchAPI('/coach/courts/add', {
    method: 'POST',
    body: JSON.stringify(courtData)
  });
}

// Remove coach court
async function removeCoachCourt(courtId) {
  return fetchAPI('/coach/courts/remove', {
    method: 'POST',
    body: JSON.stringify({ court_id: courtId })
  });
}

// Update court booking instructions
async function updateCourtBookingInstructions(courtId, instructions) {
  return fetchAPI('/coach/courts/update-instructions', {
    method: 'POST',
    body: JSON.stringify({
      court_id: courtId,
      booking_instructions: instructions
    })
  });
}

// Get availability
async function getAvailability() {
  return fetchAPI('/coach/availability');
}

// Add availability
async function addAvailability(availabilityData) {
  return fetchAPI('/coach/availability/add', {
    method: 'POST',
    body: JSON.stringify(availabilityData)
  });
}

// Delete availability
async function deleteAvailability(availabilityId) {
  return fetchAPI('/coach/availability/delete', {
    method: 'POST',
    body: JSON.stringify({ availability_id: availabilityId })
  });
}

// Get bookings
async function getBookings(status = 'upcoming') {
  return fetchAPI(`/coach/bookings/${status}`);
}

// Complete session
async function completeSession(bookingId) {
  return fetchAPI('/coach/complete-session', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

// Cancel session
async function cancelSession(bookingId) {
  return fetchAPI('/coach/cancel-session', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

// Confirm venue booking
async function confirmVenueBooking(bookingId) {
  return fetchAPI('/coach/confirm-venue', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

// Upload court booking proof
async function uploadCourtBookingProof(bookingId, proofFile) {
  const formData = new FormData();
  formData.append('booking_id', bookingId);
  formData.append('court_proof', proofFile);
  
  return fetch(`${API_BASE_URL}/coach/upload-court-proof`, {
    method: 'POST',
    body: formData
  }).then(response => {
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.error || data.message || response.statusText);
      });
    }
    return response.json();
  });
}

// Reschedule booking
async function rescheduleBooking(rescheduleData) {
  return fetchAPI('/coach/defer-booking', {
    method: 'POST',
    body: JSON.stringify(rescheduleData)
  });
}

// Get session logs
async function getSessionLogs() {
  return fetchAPI('/coach/session-logs');
}

// Get specific session log
async function getSessionLog(logId) {
  return fetchAPI(`/coach/session-logs/${logId}`);
}

// Update session log
async function updateSessionLog(logData) {
  return fetchAPI('/coach/session-logs/update', {
    method: 'POST',
    body: JSON.stringify(logData)
  });
}

// Get pricing plans
async function getPricingPlans() {
  return fetchAPI('/coach/pricing-plans');
}

// Add pricing plan
async function addPricingPlan(planData) {
  return fetchAPI('/coach/pricing-plans/add', {
    method: 'POST',
    body: JSON.stringify(planData)
  });
}

// Delete pricing plan
async function deletePricingPlan(planId) {
  return fetchAPI('/coach/pricing-plans/delete', {
    method: 'POST',
    body: JSON.stringify({ plan_id: planId })
  });
}

// Get earnings data
async function getEarnings(period = 'all') {
  return fetchAPI(`/coach/earnings/${period}`);
}

// // Get coach packages
// async function getCoachPackages() {
//   return fetchAPI('/coach/packages');
// }

// // Approve coach package
// async function approveCoachPackage(packageId) {
//   return fetchAPI('/coach/packages/approve', {
//     method: 'POST',
//     body: JSON.stringify({ package_id: packageId })
//   });
// }

// // Reject coach package
// async function rejectCoachPackage(packageId, reason) {
//   return fetchAPI('/coach/packages/reject', {
//     method: 'POST',
//     body: JSON.stringify({
//       package_id: packageId,
//       rejection_reason: reason
//     })
//   });
// }

// Get academy packages
async function getAcademyPackages() {
  return fetchAPI('/academy/packages');
}

// Approve academy package
async function approveAcademyPackage(packageId) {
  return fetchAPI('/academy/packages/approve', {
    method: 'POST',
    body: JSON.stringify({ package_id: packageId })
  });
}

// Reject academy package
async function rejectAcademyPackage(packageId, reason) {
  return fetchAPI('/academy/packages/reject', {
    method: 'POST',
    body: JSON.stringify({
      package_id: packageId,
      rejection_reason: reason
    })
  });
}

// Get academy details
async function getAcademyDetails(academyId) {
  return fetchAPI(`/academy/${academyId}`);
}

// Update academy details
async function updateAcademyDetails(academyData) {
  return fetchAPI('/academy/update', {
    method: 'POST',
    body: JSON.stringify(academyData)
  });
}

// Add coach to academy
async function addCoachToAcademy(academyId, coachData) {
  return fetchAPI(`/academy/${academyId}/add-coach`, {
    method: 'POST',
    body: JSON.stringify(coachData)
  });
}

// Remove coach from academy
async function removeCoachFromAcademy(academyId, coachId) {
  return fetchAPI(`/academy/${academyId}/remove-coach`, {
    method: 'POST',
    body: JSON.stringify({ coach_id: coachId })
  });
}

// Update coach role in academy
async function updateCoachRole(academyId, coachId, roleData) {
  return fetchAPI(`/academy/${academyId}/update-coach-role`, {
    method: 'POST',
    body: JSON.stringify({
      coach_id: coachId,
      ...roleData
    })
  });
}

// Initialize shared dashboard components
function initDashboardComponents() {
  // Initialize toast notification close button
  const toastCloseBtn = document.getElementById('toast-close');
  if (toastCloseBtn) {
    toastCloseBtn.addEventListener('click', function() {
      const toast = document.getElementById('toast-notification');
      if (toast) {
        toast.classList.add('translate-y-24', 'opacity-0');
        setTimeout(() => {
          toast.classList.add('hidden');
        }, 300);
      }
    });
  }
}

// Update notifications
function updateNotifications(notifications) {
  const notificationList = document.getElementById('notification-list');
  const notificationBadge = document.getElementById('notification-badge');
  
  if (!notificationList || !notificationBadge) return;
  
  if (!notifications || notifications.length === 0) {
    notificationList.innerHTML = `
      <div class="px-4 py-3 text-center text-gray-500 text-sm">
        No new notifications
      </div>
    `;
    notificationBadge.classList.add('hidden');
    return;
  }
  
  notificationList.innerHTML = '';
  notificationBadge.textContent = notifications.length;
  notificationBadge.classList.remove('hidden');
  
  notifications.forEach(notification => {
    const item = document.createElement('div');
    item.className = 'px-4 py-3 border-b border-gray-100 hover:bg-gray-50';
    
    let icon = '';
    switch (notification.type) {
      case 'booking':
        icon = '<i class="fas fa-calendar-check text-blue-500 mr-2"></i>';
        break;
      case 'payment':
        icon = '<i class="fas fa-dollar-sign text-green-500 mr-2"></i>';
        break;
      case 'system':
        icon = '<i class="fas fa-bell text-purple-500 mr-2"></i>';
        break;
      default:
        icon = '<i class="fas fa-circle text-gray-500 mr-2"></i>';
    }
    
    const timeAgo = getTimeAgo(new Date(notification.created_at));
    
    item.innerHTML = `
      <div class="flex items-start">
        <div class="flex-shrink-0 mt-1">${icon}</div>
        <div class="ml-2 flex-1">
          <p class="text-sm font-medium">${notification.title}</p>
          <p class="text-xs text-gray-500 mt-1">${notification.message}</p>
          <p class="text-xs text-gray-400 mt-1">${timeAgo}</p>
        </div>
      </div>
    `;
    
    notificationList.appendChild(item);
  });
}

// Calculate time ago
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  
  let interval = Math.floor(seconds / 31536000);
  if (interval > 1) return interval + ' years ago';
  if (interval === 1) return '1 year ago';
  
  interval = Math.floor(seconds / 2592000);
  if (interval > 1) return interval + ' months ago';
  if (interval === 1) return '1 month ago';
  
  interval = Math.floor(seconds / 86400);
  if (interval > 1) return interval + ' days ago';
  if (interval === 1) return '1 day ago';
  
  interval = Math.floor(seconds / 3600);
  if (interval > 1) return interval + ' hours ago';
  if (interval === 1) return '1 hour ago';
  
  interval = Math.floor(seconds / 60);
  if (interval > 1) return interval + ' minutes ago';
  if (interval === 1) return '1 minute ago';
  
  return 'just now';
}

// Submit support request
async function submitSupportRequest(requestData) {
  return fetchAPI('/support/request', {
    method: 'POST',
    body: JSON.stringify(requestData)
  });
}