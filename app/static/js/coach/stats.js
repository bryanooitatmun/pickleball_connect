// app/static/js/coach/stats.js
// Update dashboard stats
async function updateDashboardStats() {
    try {
      const stats = await getStats();
      
      // Update completed sessions
      if (document.getElementById('completed-sessions')) {
        document.getElementById('completed-sessions').textContent = stats.completed_sessions;
      }
      
      // Update upcoming sessions
      if (document.getElementById('upcoming-sessions')) {
        document.getElementById('upcoming-sessions').textContent = stats.upcoming_sessions;
      }
      
      // Update total earnings
      if (document.getElementById('total-earnings')) {
        document.getElementById('total-earnings').textContent = formatCurrency(stats.total_earnings);
      }
      
      // Update rating
      if (document.getElementById('average-rating')) {
        document.getElementById('average-rating').textContent = stats.average_rating.toFixed(1);
      }
      
      if (document.getElementById('rating-count')) {
        document.getElementById('rating-count').textContent = `${stats.rating_count} reviews`;
      }
      
      // Update rating stars
      const starsContainer = document.getElementById('rating-stars');
      if (starsContainer) {
        starsContainer.innerHTML = '';
        
        const fullStars = Math.floor(stats.average_rating);
        const hasHalfStar = stats.average_rating % 1 >= 0.5;
        
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
      
      // Create dashboard earnings chart
      createDashboardEarningsChart(stats.monthly_earnings);
      
    } catch (error) {
      console.error('Error updating dashboard stats:', error);
    }
  }
  
  // Add event listener for earnings period change
  function setupDashboardStatsHandlers() {
    const earningsPeriodSelect = document.getElementById('earnings-period');
    if (earningsPeriodSelect) {
      earningsPeriodSelect.addEventListener('change', async function() {
        const period = this.value;
        
        try {
          const statsData = await getStats(period);
          createDashboardEarningsChart(statsData.monthly_earnings);
        } catch (error) {
          console.error('Error updating dashboard earnings chart:', error);
          showToast('Error', 'Failed to update earnings chart.', 'error');
        }
      });
    }
  }
  
  // Export functions
  export {
    updateDashboardStats,
    setupDashboardStatsHandlers
  };