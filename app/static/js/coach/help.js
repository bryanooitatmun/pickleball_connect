// app/static/js/coach/help.js
// Initialize FAQ accordions
function initFAQAccordions() {
    const faqToggles = document.querySelectorAll('.faq-toggle');
    
    faqToggles.forEach(toggle => {
      toggle.addEventListener('click', function() {
        const content = this.nextElementSibling;
        const icon = this.querySelector('i');
        
        content.classList.toggle('hidden');
        icon.content.classList.toggle('hidden');
        icon.classList.toggle('rotate-180');
      });
    });
  }
  
  // Setup support form
  function setupSupportForm() {
    const supportForm = document.getElementById('support-form');
    
    if (!supportForm) return;
    
    supportForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const requestData = {
        subject: formData.get('subject'),
        message: formData.get('message')
      };
      
      try {
        showLoading(this);
        await submitSupportRequest(requestData);
        hideLoading(this);
        showToast('Success', 'Your support request has been submitted.', 'success');
        this.reset();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to submit support request. Please try again.', 'error');
      }
    });
  }
  
  // Export functions
  export {
    initFAQAccordions,
    setupSupportForm
  };