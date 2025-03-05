// app/static/js/coach/api.js
const API_BASE_URL = '/api';

// API call functions
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
    const data = await response.json();
    
    // If response is not ok, throw an error with the actual error message from the server
    if (!response.ok) {
      // Use the error message from the response if available
      throw new Error(data.error || response.statusText);
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  } 
}

// Coach Profile
async function getCoachProfile() {
  return fetchAPI('/coach/profile');
}

async function updateCoachProfile(profileData) {
  return fetchAPI('/coach/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData)
  });
}

async function changePassword(passwordData) {
  return fetchAPI('/coach/change-password', {
    method: 'POST',
    body: JSON.stringify(passwordData)
  });
}

// Courts
async function getCourts() {
  return fetchAPI('/courts');
}

async function getCoachCourts() {
  return fetchAPI('/coach/courts');
}

async function addCoachCourt(courtId) {
  return fetchAPI('/coach/courts/add', {
    method: 'POST',
    body: JSON.stringify({ court_id: courtId })
  });
}

async function removeCoachCourt(courtId) {
  return fetchAPI('/coach/courts/remove', {
    method: 'POST',
    body: JSON.stringify({ court_id: courtId })
  });
}

// Availability
async function getAvailability() {
  return fetchAPI('/coach/availability');
}

async function addAvailability(availabilityData) {
  return fetchAPI('/coach/availability/add', {
    method: 'POST',
    body: JSON.stringify(availabilityData)
  });
}

async function deleteAvailability(availabilityId) {
  return fetchAPI('/coach/availability/delete', {
    method: 'POST',
    body: JSON.stringify({ availability_id: availabilityId })
  });
}

async function addBulkAvailability(bulkData) {
  return fetchAPI('/coach/availability/add-bulk', {
    method: 'POST',
    body: JSON.stringify(bulkData)
  });
}

// Bookings
async function getBookings(status = 'upcoming') {
  return fetchAPI(`/coach/bookings/${status}`);
}

async function completeSession(bookingId) {
  return fetchAPI('/coach/complete-session', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

async function cancelSession(bookingId) {
  return fetchAPI('/coach/cancel-session', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

async function confirmVenueBooking(bookingId) {
  return fetchAPI('/coach/confirm-venue', {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId })
  });
}

async function deferBooking(deferData) {
  return fetchAPI('/coach/defer-booking', {
    method: 'POST',
    body: JSON.stringify(deferData)
  });
}

// Session Logs
async function getSessionLogs() {
  return fetchAPI('/coach/session-logs');
}

async function getSessionLog(logId) {
  return fetchAPI(`/coach/session-logs/${logId}`);
}

async function updateSessionLog(logData) {
  return fetchAPI('/coach/session-logs/update', {
    method: 'POST',
    body: JSON.stringify(logData)
  });
}

// Pricing Plans
async function getPricingPlans() {
  return fetchAPI('/coach/pricing-plans');
}

async function addPricingPlan(planData) {
  return fetchAPI('/coach/pricing-plans/add', {
    method: 'POST',
    body: JSON.stringify(planData)
  });
}

async function deletePricingPlan(planId) {
  return fetchAPI('/coach/pricing-plans/delete', {
    method: 'POST',
    body: JSON.stringify({ plan_id: planId })
  });
}

// Earnings
async function getEarnings(period = 'all') {
  return fetchAPI(`/coach/earnings/${period}`);
}

// Dashboard Stats
async function getStats(period = '') {
  return fetchAPI(`/coach/stats${period ? '/' + period : ''}`);
}

// Support
async function submitSupportRequest(requestData) {
  return fetchAPI('/support/request', {
    method: 'POST',
    body: JSON.stringify(requestData)
  });
}

// Templates
async function saveAvailabilityTemplate(templateData) {
  return fetchAPI('/coach/availability/templates/save', {
    method: 'POST',
    body: JSON.stringify(templateData)
  });
}

async function loadAvailabilityTemplates() {
  return fetchAPI('/coach/availability/templates');
}

async function applyTemplate(templateId, dateRange) {
  return fetchAPI('/coach/availability/templates/apply', {
    method: 'POST',
    body: JSON.stringify({
      template_id: templateId,
      start_date: dateRange.start,
      end_date: dateRange.end
    })
  });
}