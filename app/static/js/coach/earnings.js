// app/static/js/coach/earnings.js
// Load earnings data
async function loadEarningsData() {
    try {
      const earningsData = await getEarnings();
      
      // Update earnings summary
      if (document.getElementById('total-earnings-value')) {
        document.getElementById('total-earnings-value').textContent = formatCurrency(earningsData.total);
      }
      
      if (document.getElementById('monthly-average')) {
        document.getElementById('monthly-average').textContent = formatCurrency(earningsData.monthly_average);
      }
      
      if (document.getElementById('this-month-earnings')) {
        document.getElementById('this-month-earnings').textContent = formatCurrency(earningsData.this_month);
      }
      
      // Calculate month-over-month change
      const lastMonth = earningsData.last_month || 0;
      let percentageChange = 0;
      
      if (lastMonth > 0) {
        percentageChange = ((earningsData.this_month - lastMonth) / lastMonth) * 100;
      }
      
      const comparisonElem = document.getElementById('this-month-comparison');
      if (comparisonElem) {
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
      }
      
      // Create charts
      createEarningsChart(earningsData.monthly);
      createEarningsByCourtChart(earningsData.by_court);
      
      // Update earnings breakdown
      updateEarningsBreakdown(earningsData.breakdown);
      
    } catch (error) {
      console.error('Error loading earnings data:', error);
      showToast('Error', 'Failed to load earnings data.', 'error');
    }
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
        <td class="px-4 py-3">${formatCurrency(data.amount)}</td>
        <td class="px-4 py-3">${percentage}%</td>
      `;
      
      tbody.appendChild(row);
    });
    
    // Update totals
    const totalSessionsElement = document.getElementById('earnings-breakdown-total-sessions');
    const totalAmountElement = document.getElementById('earnings-breakdown-total-amount');
    
    if (totalSessionsElement) totalSessionsElement.textContent = totalSessions;
    if (totalAmountElement) totalAmountElement.textContent = formatCurrency(totalEarnings);
  }
  
  // Initialize earnings breakdown period change handler
  function initializeEarningsBreakdownHandler() {
    document.getElementById('earnings-breakdown-period')?.addEventListener('change', async function() {
      const period = this.value;
      
      try {
        const breakdownData = await getEarnings(period);
        updateEarningsBreakdown(breakdownData.breakdown);
      } catch (error) {
        console.error('Error updating earnings breakdown:', error);
        showToast('Error', 'Failed to update earnings breakdown.', 'error');
      }
    });
  }
  
  // Export functions
  export {
    loadEarningsData,
    updateEarningsBreakdown,
    initializeEarningsBreakdownHandler
  };