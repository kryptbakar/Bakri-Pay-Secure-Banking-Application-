/**
 * Main JavaScript file for the Banking System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });

    // PIN field security
    const pinInputs = document.querySelectorAll('input[type="password"][id*="pin"]');
    pinInputs.forEach(function(input) {
        // Add maxlength if not present
        if (!input.hasAttribute('maxlength')) {
            input.setAttribute('maxlength', '6');
        }
        
        // Only allow numeric input
        input.addEventListener('keypress', function(e) {
            if (!/^\d$/.test(e.key)) {
                e.preventDefault();
            }
        });
    });

    // Amount input formatting
    const amountInputs = document.querySelectorAll('input[type="number"][id*="amount"]');
    amountInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value !== '') {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });

    // Mobile number formatting
    const mobileInputs = document.querySelectorAll('input[type="tel"][id*="mobile"]');
    mobileInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            // Ensure it starts with +
            if (this.value !== '' && !this.value.startsWith('+')) {
                this.value = '+' + this.value;
            }
        });
    });

    // Session timeout warning
    let sessionTimeoutWarning;
    let sessionTimeout;
    const warningTime = 25 * 60 * 1000; // 25 minutes
    const timeoutTime = 30 * 60 * 1000; // 30 minutes
    
    function resetSessionTimers() {
        clearTimeout(sessionTimeoutWarning);
        clearTimeout(sessionTimeout);
        
        // Set warning timer
        sessionTimeoutWarning = setTimeout(function() {
            // Show warning modal if it exists
            const warningModal = document.getElementById('sessionWarningModal');
            if (warningModal) {
                const modal = new bootstrap.Modal(warningModal);
                modal.show();
            } else {
                alert('Your session will expire in 5 minutes due to inactivity. Please save your work.');
            }
        }, warningTime);
        
        // Set timeout timer
        sessionTimeout = setTimeout(function() {
            window.location.href = '/auth/logout';
        }, timeoutTime);
    }
    
    // Reset timers on user activity
    document.addEventListener('click', resetSessionTimers);
    document.addEventListener('keypress', resetSessionTimers);
    
    // Initialize timers if user is logged in
    if (document.querySelector('.navbar .dropdown-item[href*="logout"]')) {
        resetSessionTimers();
    }
});

/**
 * Format currency value
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted currency string
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

/**
 * Format date to local string
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date string
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Show loading spinner
 * @param {string} targetId - The ID of the element to show spinner in
 * @param {string} message - Optional loading message
 */
function showSpinner(targetId, message = 'Loading...') {
    const target = document.getElementById(targetId);
    if (target) {
        target.innerHTML = `
            <div class="text-center my-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">${message}</p>
            </div>
        `;
    }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise} - Promise that resolves when text is copied
 */
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text)
        .then(() => {
            // Show success toast if available
            const toast = document.querySelector('.toast.copy-toast');
            if (toast) {
                const bsToast = new bootstrap.Toast(toast);
                toast.querySelector('.toast-body').textContent = 'Copied to clipboard!';
                bsToast.show();
            }
        })
        .catch(err => {
            console.error('Could not copy text: ', err);
        });
}
