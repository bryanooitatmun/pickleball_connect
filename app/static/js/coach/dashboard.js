// app/static/js/coach/dashboard.js
// Import utility modules
import { formatDate, formatTime, formatCurrency, showLoading, hideLoading, showToast } from './utils.js';

// Import API functions
import * as api from './api.js';

// Import feature modules
import { populateProfileForm, initializeProfileImageHandling, initializeShowcaseImages } from './profile.js';
import { loadCourts, populateCourtFilters } from './courts.js';
import { setupBookingTabs, loadBookings, filterBookings, displayBookings, updateUpcomingBookingsList } from './bookings.js';
import { calculateAvailabilitySlots, initBulkAvailability, loadAvailability, displayAvailability, filterAvailability, loadAndDisplayTemplates } from './availability.js';
import { loadSessionLogs, displaySessionLogs, updateRecentLogsList, openSessionLogModal, filterSessionLogs } from './session_logs.js';
import { loadPricingPlans, initializePricingFormHandlers } from './pricing.js';
import { loadEarningsData, updateEarningsBreakdown, initializeEarningsBreakdownHandler } from './earnings.js';
import { createDashboardEarningsChart, createEarningsChart, createEarningsByCourtChart } from './charts.js';
import { initCalendarView, loadCalendarView, generateBookingsCalendarView } from './calendar.js';
import { initFAQAccordions, setupSupportForm } from './help.js';
import { setupForms } from './forms.js';
import { updateDashboardStats, setupDashboardStatsHandlers } from './stats.js';
import { setupModals } from './modals.js';

// Store original data for filtering
let originalBookingsData = {
  upcoming: [],
  completed: [],
  cancelled: []
};
let originalAvailabilityData = [];
let originalSessionLogsData = [];

// Global flag
const IS_COACH = true;

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
  // Initialize tabs
  initializeTabs();
  
  // Initialize dropdowns
  initializeDropdowns();
  
  // Initialize profile image handling
  initializeProfileImageHandling();
  
  // Initialize showcase images
  initializeShowcaseImages();
  
  // Initialize pricing form handlers
  initializePricingFormHandlers();
  
  // Initialize FAQ accordions
  initFAQAccordions();
  
  // Set current date as minimum for availability date input
  const today = new Date().toISOString().split('T')[0];
  if (document.getElementById('availability-date')) {
    document.getElementById('availability-date').min = today;
  }
  
  // Setup form submit event listeners
  setupForms();
  
  // Setup modal event listeners
  setupModals();

  // Setup booking tabs
  setupBookingTabs();

  // Initialize bulk availability functionality
  initBulkAvailability();
  
  // Initialize earnings breakdown handlers
  initializeEarningsBreakdownHandler();
  
  // Initialize dashboard stats handlers
  setupDashboardStatsHandlers();
  
  // Setup support form
  setupSupportForm();
  
  // Load templates
  loadAndDisplayTemplates();

  // Initialize calendar view
  initCalendarView();
  
  // Add event listener to make calendar tab active if clicked
  document.querySelector('.calendar-tab')?.addEventListener('click', function() {
    loadCalendarView();
  });
  
  // Load initial data
  loadDashboardData();
});

// Initialize tabs
function initializeTabs() {
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
    document.getElementById(`${tabId}-tab`).classList.add('active');
    
    // Add active class to the clicked tab link
    document.querySelector(`.${tabId}-tab`).classList.add('active-nav-link');
    
    // Update mobile nav
    if (mobileNav) {
      mobileNav.value = tabId;
    }
  }

  tabLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      const tabId = this.getAttribute('href').substring(1);
      activateTab(tabId);
    });
  });

  if (mobileNav) {
    mobileNav.addEventListener('change', function() {
      activateTab(this.value);
    });
  }
}

// Initialize dropdowns
function initializeDropdowns() {
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
}

// Load dashboard data
async function loadDashboardData() {
  try {
    const coachProfile = await api.getCoachProfile();
    
    // Update profile display
    if (document.getElementById('coach-name')) {
      document.getElementById('coach-name').textContent = coachProfile.user.first_name;
    }
    
    if (document.getElementById('profile-name')) {
      document.getElementById('profile-name').textContent = `${coachProfile.user.first_name} ${coachProfile.user.last_name}`;
    }
    
    if (document.getElementById('profile-initial')) {
      document.getElementById('profile-initial').textContent = coachProfile.user.first_name.charAt(0);
    }
    
    // Set profile picture if exists
    if (coachProfile.user.profile_picture) {
      const profileInitial = document.getElementById('profile-initial');
      if (profileInitial) {
        profileInitial.innerHTML = `<img src="/static/${coachProfile.user.profile_picture}" alt="Profile" class="h-8 w-8 rounded-full object-cover">`;
      }
    }

    // Populate profile form
    populateProfileForm(coachProfile);
    
    // Load courts
    loadCourts();
    
    // Load bookings
    loadBookings();
    
    // Load session logs
    loadSessionLogs();
    
    // Load availability
    loadAvailability();
    
    // Load pricing plans
    loadPricingPlans();
    
    // Load earnings data
    loadEarningsData();
    
    // Update dashboard stats
    updateDashboardStats();

    // Load calendar view
    const currentDate = new Date();
    if (document.getElementById('bookings-calendar')) {
      generateBookingsCalendarView(currentDate.getMonth(), currentDate.getFullYear(), await api.getBookings('all'));
    }
    
  } catch (error) {
    console.error('Error loading dashboard data:', error);
    showToast('Error', 'Failed to load dashboard data. Please refresh the page.', 'error');
  }
}

// Make functions globally available
window.formatDate = formatDate;
window.formatTime = formatTime;
window.formatCurrency = formatCurrency;
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.openSessionLogModal = openSessionLogModal;
window.loadCourts = loadCourts;
window.loadBookings = loadBookings;
window.loadAvailability = loadAvailability;
window.filterAvailability = filterAvailability;
window.filterBookings = filterBookings;
window.filterSessionLogs = filterSessionLogs;
window.loadEarningsData = loadEarningsData;
window.loadSessionLogs = loadSessionLogs;
window.loadPricingPlans = loadPricingPlans;
window.calculateAvailabilitySlots = calculateAvailabilitySlots;
window.loadCalendarView = loadCalendarView;
window.updateDashboardStats = updateDashboardStats;