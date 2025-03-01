// app/static/js/auth.js
document.addEventListener('DOMContentLoaded', function() {
    // Login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const rememberMe = document.getElementById('remember-me').checked;
        const errorDiv = document.getElementById('login-error');
        
        // Clear previous errors
        errorDiv.textContent = '';
        errorDiv.classList.add('hidden');
        
        // Disable submit button to prevent double submission
        const submitButton = document.getElementById('login-submit');
        submitButton.disabled = true;
        submitButton.textContent = 'Logging in...';
        
        // Send login request to backend
        fetch('/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: email,
            password: password,
            remember_me: rememberMe
          }),
        })
        .then(response => {
          if (!response.ok) {
            return response.json().then(data => {
              throw new Error(data.error || 'Invalid email or password');
            });
          }
          return response.json();
        })
        .then(data => {
          // Successful login
          if (data.redirect) {
            window.location.href = data.redirect;
          } else {
            // Reload the current page if no specific redirect
            window.location.reload();
          }
        })
        .catch(error => {
          // Show error message
          errorDiv.textContent = error.message;
          errorDiv.classList.remove('hidden');
          
          // Re-enable submit button
          submitButton.disabled = false;
          submitButton.textContent = 'Login';
        });
      });
    }
    
    // Registration form steps navigation
    const continueToPasswordBtn = document.getElementById('continue-to-password');
    const backToStep1Btn = document.getElementById('back-to-step-1');
    const registerStep1 = document.getElementById('register-step-1');
    const registerStep2 = document.getElementById('register-step-2');

    const coachFields = document.getElementById('coach-fields');
    
    if (continueToPasswordBtn && registerStep1 && registerStep2) {
      continueToPasswordBtn.addEventListener('click', function() {
        // Validate step 1 fields
        const form = document.getElementById('registration-form');
        const requiredFields = registerStep1.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
          if (!field.checkValidity()) {
            isValid = false;
            field.reportValidity();
          }
        });
        
        // Validate email match
        const email = document.getElementById('register-email').value;
        const confirmEmail = document.getElementById('register-confirm-email').value;
        
        if (email !== confirmEmail) {
          isValid = false;
          document.getElementById('register-error').textContent = 'Email addresses do not match';
          document.getElementById('register-error').classList.remove('hidden');
          return;
        }
        
        if (isValid) {
          // Hide step 1, show step 2
          registerStep1.classList.add('hidden');
          registerStep2.classList.remove('hidden');
        }
      });
      
      if (backToStep1Btn) {
        backToStep1Btn.addEventListener('click', function() {
          // Hide step 2, show step 1
          registerStep2.classList.add('hidden');
          registerStep1.classList.remove('hidden');
        });
      }
    }
    
    
  // Registration form submission
  const registrationForm = document.getElementById('registration-form');
  if (registrationForm) {
    registrationForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      // Password validation
      const password = document.getElementById('register-password').value;
      const confirmPassword = document.getElementById('register-confirm-password').value;
      const passwordMatchError = document.getElementById('password-match-error');
      const errorDiv = document.getElementById('register-error');
      
      // Clear previous errors
      errorDiv.textContent = '';
      errorDiv.classList.add('hidden');
      passwordMatchError.classList.add('hidden');
      
      if (password !== confirmPassword) {
        passwordMatchError.classList.remove('hidden');
        return;
      }
      
      // Disable submit button to prevent double submission
      const submitButton = document.getElementById('register-submit');
      submitButton.disabled = true;
      submitButton.textContent = 'Registering...';
      
      // Prepare form data
      const formData = new FormData(registrationForm);
      
      // Convert FormData to JSON
      const data = {};
      formData.forEach((value, key) => {
        // Skip empty values
        if (value !== '') {
          data[key] = value;
        }
      });
      
      // Add coach flag
      data.is_coach = false;
      
      // Determine which API endpoint to use
      const registerUrl = '/auth/register' ;
      
      // Send registration request to backend
      fetch(registerUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      .then(response => {
        if (!response.ok) {
          return response.json().then(data => {
            throw new Error(data.error || 'Registration failed');
          });
        }
        return response.json();
      })
      .then(data => {
        // Successful registration
        if (data.redirect) {
          window.location.href = data.redirect;
        } else {
          // Fallback to login page
          window.location.href = '/login?registered=true';
        }
      })
      .catch(error => {
        // Show error message
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
        
        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.textContent = 'Register';
        
        // Go back to appropriate step based on error
        if (error.message.includes('email') || error.message.includes('field')) {
          registerStep2.classList.add('hidden');
          registerStep1.classList.remove('hidden');
        }
      });
    });
  }
});