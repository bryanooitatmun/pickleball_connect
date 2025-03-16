// Earnings Management
// This file contains functions for displaying and analyzing earnings data

// Initialize the earnings tab
function initEarningsTab() {
    loadEarningsData();
    setupEarningsEventListeners();
  }
  
  // Load earnings data
  async function loadEarningsData() {
    try {
      let endpoint = '/api/coach/earnings';
      let queryParams = '';
      
      // If academy manager and a coach is selected
      if (isAcademyManager()) {
        const coachFilter = document.getElementById('earnings-coach-filter');
        if (coachFilter && coachFilter.value) {
          if (coachFilter.value === 'academy') {
            endpoint = '/api/academy/earnings';
          } else {
            queryParams = `?coach_id=${coachFilter.value}`;
          }
        } else {
          endpoint = '/api/academy/earnings';
        }
      }
      
      const earningsData = await fetchAPI(`${endpoint}${queryParams}`);
      displayEarningsData(earningsData);
      
      // If academy manager, populate coach filter
      if (isAcademyManager()) {
        populateCoachFilter(document.getElementById('earnings-coach-filter'));
      }
    } catch (error) {
      console.error('Error loading earnings data:', error);
      showToast('Error', 'Failed to load earnings data.', 'error');
    }
  }
  
  // Display earnings data
  function displayEarningsData(earningsData) {
    // Update earnings summary
    document.getElementById('total-earnings-value').textContent = formatCurrency(earningsData.total);
    document.getElementById('monthly-average').textContent = formatCurrency(earningsData.monthly_average);
    document.getElementById('this-month-earnings').textContent = formatCurrency(earningsData.this_month);
    
    // Calculate month-over-month change
    const lastMonth = earningsData.last_month || 0;
    let percentageChange = 0;
    
    if (lastMonth > 0) {
      percentageChange = ((earningsData.this_month - lastMonth) / lastMonth) * 100;
    }
    
    const comparisonElem = document.getElementById('this-month-comparison');
    
    if (percentageChange > 0) {
      comparisonElem.textContent = `+${percentageChange.toFixed(1)}% vs. last month`;
      comparisonElem.className = 'text-sm text-green-600';
    } else if (percentageChange < 0) {
      comparisonElem.textContent = `${percentageChange.toFixed(1)}% vs. last month`;
      comparisonElem.className = 'text-sm text-red-600';
    } else {
      comparisonElem.textContent = `0% vs. last month`;
      comparisonElem.className = 'text-sm text-gray-600';
    }
    
    // Create charts
    createEarningsChart(earningsData.monthly);
    createEarningsByCourtChart(earningsData.by_court);
    
    // Update earnings breakdown
    updateEarningsBreakdown(earningsData.breakdown);
  }
  
  // Create earnings chart
  function createEarningsChart(monthlyData) {
    const ctx = document.getElementById('earnings-detailed-chart').getContext('2d');
    
    // Clear any existing chart
    if (window.earningsDetailedChart) {
      window.earningsDetailedChart.destroy();
    }
    
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
    window.earningsDetailedChart = new Chart(ctx, {
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
                return 'Earnings: $' + formatCurrency(context.raw);
              }
            }
          }
        }
      }
    });
  }
  
  // Create earnings by court chart
  function createEarningsByCourtChart(courtData) {
    const ctx = document.getElementById('earnings-by-court-chart').getContext('2d');
    
    // Clear any existing chart
    if (window.earningsByCourtChart) {
      window.earningsByCourtChart.destroy();
    }
    
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
    window.earningsByCourtChart = new Chart(ctx, {
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
                return `${context.label}: $${formatCurrency(value)} (${percentage}%)`;
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
        <span class="font-medium">$${formatCurrency(amount)}</span>
      `;
      
      listContainer.appendChild(listItem);
      index++;
    });
}

// Update earnings breakdown
function updateEarningsBreakdown(breakdownData) {
  const tbody = document.getElementById('earnings-breakdown-body');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  const types = Object.keys(breakdownData || {});
  
  if (!breakdownData || types.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="px-4 py-6 text-center text-gray-500">No earnings data available</td>
      </tr>
    `;
    return;
  }
  
  // Calculate totals
  let totalSessions = 0;
  let totalEarnings = 0;
  
  types.forEach(type => {
    totalSessions += breakdownData[type].sessions || 0;
    totalEarnings += breakdownData[type].amount || 0;
  });
  
  // Populate table rows
  types.forEach(type => {
    const data = breakdownData[type];
    const row = document.createElement('tr');
    
    const percentage = totalEarnings > 0 ? ((data.amount / totalEarnings) * 100).toFixed(1) : 0;
    
    row.innerHTML = `
      <td class="px-4 py-3">${formatBreakdownType(type)}</td>
      <td class="px-4 py-3">${data.sessions}</td>
      <td class="px-4 py-3">$${formatCurrency(data.amount)}</td>
      <td class="px-4 py-3">${percentage}%</td>
    `;
    
    tbody.appendChild(row);
  });
  
  // Update totals
  const totalSessionsElement = document.getElementById('earnings-breakdown-total-sessions');
  const totalAmountElement = document.getElementById('earnings-breakdown-total-amount');
  
  if (totalSessionsElement) totalSessionsElement.textContent = totalSessions;
  if (totalAmountElement) totalAmountElement.textContent = '$' + formatCurrency(totalEarnings);
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

// Setup earnings event listeners
function setupEarningsEventListeners() {
  // Time period selection
  document.getElementById('earnings-time-period')?.addEventListener('change', async function() {
    const months = parseInt(this.value);
    
    try {
      let endpoint = '/api/coach/earnings/' + months;
      let queryParams = '';
      
      // If academy manager and a coach is selected
      if (isAcademyManager()) {
        const coachFilter = document.getElementById('earnings-coach-filter');
        if (coachFilter && coachFilter.value) {
          if (coachFilter.value === 'academy') {
            endpoint = '/api/academy/earnings/' + months;
          } else {
            queryParams = `?coach_id=${coachFilter.value}`;
          }
        } else {
          endpoint = '/api/academy/earnings/' + months;
        }
      }
      
      const periodData = await fetchAPI(`${endpoint}${queryParams}`);
      
      // Update earnings chart
      createEarningsChart(periodData.monthly);
      
    } catch (error) {
      console.error('Error updating earnings chart:', error);
      showToast('Error', 'Failed to update earnings chart.', 'error');
    }
  });
  
  // Breakdown period selection
  document.getElementById('earnings-breakdown-period')?.addEventListener('change', async function() {
    const period = this.value;
    
    try {
      let endpoint = '/api/coach/earnings/breakdown/' + period;
      let queryParams = '';
      
      // If academy manager and a coach is selected
      if (isAcademyManager()) {
        const coachFilter = document.getElementById('earnings-coach-filter');
        if (coachFilter && coachFilter.value) {
          if (coachFilter.value === 'academy') {
            endpoint = '/api/academy/earnings/breakdown/' + period;
          } else {
            queryParams = `?coach_id=${coachFilter.value}`;
          }
        } else {
          endpoint = '/api/academy/earnings/breakdown/' + period;
        }
      }
      
      const breakdownData = await fetchAPI(`${endpoint}${queryParams}`);
      
      // Update earnings breakdown
      updateEarningsBreakdown(breakdownData.breakdown);
      
    } catch (error) {
      console.error('Error updating earnings breakdown:', error);
      showToast('Error', 'Failed to update earnings breakdown.', 'error');
    }
  });
  
  // Coach filter (for academy manager)
  if (isAcademyManager()) {
    document.getElementById('earnings-coach-filter')?.addEventListener('change', function() {
      loadEarningsData();
    });
  }
}