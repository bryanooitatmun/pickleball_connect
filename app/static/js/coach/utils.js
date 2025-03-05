// app/static/js/coach/utils.js
// Helper functions
function formatDate(dateString) {
    const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
  }
  
  function formatTime(timeString) {
    return new Date(`2000-01-01T${timeString}`).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  }
  
  function formatCurrency(amount) {
    return `$${Number(amount).toFixed(2)}`;
  }
  
  function showLoading(element) {
    element.classList.add('loading');
  }
  
  function hideLoading(element) {
    element.classList.remove('loading');
  }
  
  function showToast(title, message, type = 'success') {
    const toast = document.getElementById('toast-notification');
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
  }
  
  // Time utilities
  function timeStringToMinutes(timeString) {
    const [hours, minutes] = timeString.split(':').map(part => parseInt(part));
    return hours * 60 + minutes;
  }
  
  function minutesToTimeString(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  }
  
  function parseDisplayDateToISO(displayDate) {
    // Handle various date formats
    const date = new Date(displayDate);
    if (isNaN(date.getTime())) {
      console.error('Invalid date:', displayDate);
      return null;
    }
    return date.toISOString().split('T')[0];
  }
  
  // Rating stars display
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
  
  // Format breakdown type
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
        return type;
    }
  }