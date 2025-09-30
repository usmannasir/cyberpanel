/**
 * CyberPanel WebAuthn/Passkey Authentication Module
 * Handles passwordless authentication using WebAuthn API
 */

(function() {
    'use strict';

    // Check if WebAuthn is supported
    const isSupported = function() {
        return !!(navigator.credentials && navigator.credentials.create && navigator.credentials.get);
    };

    // Initialize the module
    const init = function() {
        if (!isSupported()) {
            console.log('WebAuthn is not supported in this browser');
            return false;
        }

        console.log('WebAuthn support detected');
        return true;
    };

    // Start passwordless login flow
    const startPasswordlessLogin = function() {
        console.log('Passwordless login not yet implemented');
        // TODO: Implement WebAuthn authentication flow
        alert('Passkey authentication will be available in a future update');
    };

    // Export functions to global scope
    window.cyberPanelWebAuthn = {
        isSupported: isSupported,
        init: init,
        startPasswordlessLogin: startPasswordlessLogin
    };

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();