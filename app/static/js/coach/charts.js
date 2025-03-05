// app/static/js/coach/charts.js
// Create dashboard earnings chart
function createDashboardEarningsChart(monthlyEarnings) {
    const ctx = document.getElementById('earnings-chart')?.getContext('2d');
    
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
  }
  
  // Create earnings chart
  function createEarningsChart(monthlyData) {
    const ctx = document.getElementById('earnings-detailed-chart')?.getContext('2d');
    
    if (!ctx) return;
    
    // Extract labels and data
    const labels = [];
    const data = [];
    
    // Sort months chronologically
    const sortedMonths = Object.keys(monthlyData).sort((a, b) => {
      const dateA = new Date(a);
      const dateB = new Date(b);
      return dateA - dateB;
    });
    
    sortedMonths.forEach(month => {
      // Format month as MMM YYYY
      const date = new Date(month);
      const formattedMonth = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      
      labels.push(formattedMonth);
      data.push(monthlyData[month]);
    });
    
    // Create chart
    const earningsChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Earnings',
          data: data,
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 2,
          tension: 0.1,
          fill: true
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
                return 'Earnings: ' + formatCurrency(context.raw);
              }
            }
          }
        }
      }
    });
    
    // Update chart when time period changes
    document.getElementById('earnings-time-period')?.addEventListener('change', async function() {
      const months = parseInt(this.value);
      
      try {
        const periodData = await getEarnings(months);
        
        // Update chart
        earningsChart.data.labels = [];
        earningsChart.data.datasets[0].data = [];
        
        // Sort months chronologically
        const sortedPeriodMonths = Object.keys(periodData.monthly).sort((a, b) => {
          const dateA = new Date(a);
          const dateB = new Date(b);
          return dateA - dateB;
        });
        
        sortedPeriodMonths.forEach(month => {
          // Format month as MMM YYYY
          const date = new Date(month);
          const formattedMonth = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
          
          earningsChart.data.labels.push(formattedMonth);
          earningsChart.data.datasets[0].data.push(periodData.monthly[month]);
        });
        
        earningsChart.update();
        
      } catch (error) {
        console.error('Error updating earnings chart:', error);
        showToast('Error', 'Failed to update earnings chart.', 'error');
      }
    });
  }
  
  // Create earnings by court chart
  function createEarningsByCourtChart(courtData) {
    const ctx = document.getElementById('earnings-by-court-chart')?.getContext('2d');
    
    if (!ctx) return;
    
    // Extract labels and data
    const labels = [];
    const data = [];
    const backgroundColor = [
      'rgba(75, 192, 192, 0.7)',
      'rgba(54, 162, 235, 0.7)',
      'rgba(153, 102, 255, 0.7)',
      'rgba(255, 159, 64, 0.7)',
      'rgba(255, 99, 132, 0.7)',
      'rgba(255, 205, 86, 0.7)'
    ];
    
    Object.keys(courtData).forEach((courtName, index) => {
      labels.push(courtName);
      data.push(courtData[courtName]);
    });
    
    // Create chart
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColor,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context) {
                const value = context.raw;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${context.label}: ${formatCurrency(value)} (${percentage}%)`;
              }
            }
          },
          legend: {
            position: 'right'
          }
        }
      }
    });
    
    // Populate earnings by court list
    const listContainer = document.getElementById('earnings-by-court-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    let index = 0;
    Object.entries(courtData)
      .sort((a, b) => b[1] - a[1]) // Sort by earnings in descending order
      .forEach(([courtName, amount]) => {
        const listItem = document.createElement('div');
        listItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
        
        listItem.innerHTML = `
          <div class="flex items-center">
            <div class="h-3 w-3 rounded-full mr-2" style="background-color: ${backgroundColor[index % backgroundColor.length]}"></div>
            <span>${courtName}</span>
          </div>
          <span class="font-medium">${formatCurrency(amount)}</span>
        `;
        
        listContainer.appendChild(listItem);
        index++;
      });
  }
  
  // Export functions
  export {
    createDashboardEarningsChart,
    createEarningsChart,
    createEarningsByCourtChart
  };