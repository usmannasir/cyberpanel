/**
 * WebAuthn JavaScript integration for CyberPanel
 * Provides passkey registration and authentication functionality
 */

class CyberPanelWebAuthn {
    constructor() {
        this.isSupported = this.checkSupport();
        this.baseUrl = window.location.origin;
        this.apiEndpoints = {
            registrationStart: '/webauthn/registration/start/',
            registrationComplete: '/webauthn/registration/complete/',
            authenticationStart: '/webauthn/authentication/start/',
            authenticationComplete: '/webauthn/authentication/complete/',
            credentialsList: '/webauthn/credentials/',
            credentialDelete: '/webauthn/credential/delete/',
            credentialUpdate: '/webauthn/credential/update/',
            settingsUpdate: '/webauthn/settings/update/',
        };
        
        this.init();
    }
    
    init() {
        if (!this.isSupported) {
            console.warn('WebAuthn is not supported in this browser');
            return;
        }
        
        // Add CSRF token to all requests
        this.csrfToken = this.getCSRFToken();
        
        // Initialize UI elements
        this.initializeUI();
    }
    
    checkSupport() {
        return !!(navigator.credentials && 
                 navigator.credentials.create && 
                 navigator.credentials.get &&
                 window.PublicKeyCredential);
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
    
    initializeUI() {
        // Add WebAuthn buttons to login form
        this.addLoginButtons();
        
        // Add WebAuthn management to user settings
        this.addUserManagementUI();
    }
    
    addLoginButtons() {
        const loginForm = document.querySelector('#loginForm');
        if (!loginForm) return;
        
        // Add WebAuthn login button
        const webauthnButton = document.createElement('button');
        webauthnButton.type = 'button';
        webauthnButton.className = 'btn btn-primary btn-block';
        webauthnButton.innerHTML = '<i class="fas fa-fingerprint"></i> Login with Passkey';
        webauthnButton.onclick = () => this.startPasswordlessLogin();
        
        // Insert after password field
        const passwordField = loginForm.querySelector('input[type="password"]');
        if (passwordField) {
            passwordField.parentNode.insertBefore(webauthnButton, passwordField.parentNode.nextSibling);
        }
    }
    
    addUserManagementUI() {
        // This will be called when user management page loads
        // Implementation depends on the specific UI structure
    }
    
    async startPasswordlessLogin() {
        try {
            const username = document.querySelector('input[name="username"]').value;
            if (!username) {
                this.showError('Please enter your username first');
                return;
            }
            
            this.showLoading('Starting passkey authentication...');
            
            // Get authentication challenge
            const challengeResponse = await this.makeRequest('POST', this.apiEndpoints.authenticationStart, {
                username: username
            });
            
            if (!challengeResponse.success) {
                throw new Error(challengeResponse.error || 'Failed to start authentication');
            }
            
            // Convert challenge to proper format
            const challenge = this.convertChallenge(challengeResponse.challenge);
            
            // Get credential
            const credential = await navigator.credentials.get({
                publicKey: challenge
            });
            
            // Complete authentication
            const authResponse = await this.makeRequest('POST', this.apiEndpoints.authenticationComplete, {
                challenge_id: challengeResponse.challenge_id,
                credential: {
                    id: this.arrayBufferToBase64(credential.rawId),
                    type: credential.type
                },
                client_data_json: this.arrayBufferToBase64(credential.response.clientDataJSON),
                authenticator_data: this.arrayBufferToBase64(credential.response.authenticatorData),
                signature: this.arrayBufferToBase64(credential.response.signature),
                user_handle: credential.response.userHandle ? 
                    this.arrayBufferToBase64(credential.response.userHandle) : null
            });
            
            if (authResponse.success) {
                this.showSuccess('Authentication successful! Redirecting...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                throw new Error(authResponse.error || 'Authentication failed');
            }
            
        } catch (error) {
            console.error('WebAuthn authentication error:', error);
            this.showError(error.message || 'Authentication failed');
        } finally {
            this.hideLoading();
        }
    }
    
    async registerPasskey(username, credentialName = '') {
        try {
            this.showLoading('Starting passkey registration...');
            
            // Get registration challenge
            const challengeResponse = await this.makeRequest('POST', this.apiEndpoints.registrationStart, {
                username: username,
                credential_name: credentialName
            });
            
            if (!challengeResponse.success) {
                throw new Error(challengeResponse.error || 'Failed to start registration');
            }
            
            // Convert challenge to proper format
            const challenge = this.convertChallenge(challengeResponse.challenge);
            
            // Create credential
            const credential = await navigator.credentials.create({
                publicKey: challenge
            });
            
            // Complete registration
            const regResponse = await this.makeRequest('POST', this.apiEndpoints.registrationComplete, {
                challenge_id: challengeResponse.challenge_id,
                credential: {
                    id: this.arrayBufferToBase64(credential.rawId),
                    type: credential.type
                },
                client_data_json: this.arrayBufferToBase64(credential.response.clientDataJSON),
                attestation_object: this.arrayBufferToBase64(credential.response.attestationObject)
            });
            
            if (regResponse.success) {
                this.showSuccess('Passkey registered successfully!');
                return regResponse;
            } else {
                throw new Error(regResponse.error || 'Registration failed');
            }
            
        } catch (error) {
            console.error('WebAuthn registration error:', error);
            this.showError(error.message || 'Registration failed');
            throw error;
        } finally {
            this.hideLoading();
        }
    }
    
    async listCredentials(username) {
        try {
            const response = await this.makeRequest('GET', 
                `${this.apiEndpoints.credentialsList}${username}/`);
            
            if (response.success) {
                return response.credentials;
            } else {
                throw new Error(response.error || 'Failed to list credentials');
            }
        } catch (error) {
            console.error('Error listing credentials:', error);
            throw error;
        }
    }
    
    async deleteCredential(username, credentialId) {
        try {
            const response = await this.makeRequest('POST', this.apiEndpoints.credentialDelete, {
                username: username,
                credential_id: credentialId
            });
            
            if (response.success) {
                this.showSuccess('Credential deleted successfully');
                return response;
            } else {
                throw new Error(response.error || 'Failed to delete credential');
            }
        } catch (error) {
            console.error('Error deleting credential:', error);
            this.showError(error.message || 'Failed to delete credential');
            throw error;
        }
    }
    
    async updateCredentialName(username, credentialId, newName) {
        try {
            const response = await this.makeRequest('POST', this.apiEndpoints.credentialUpdate, {
                username: username,
                credential_id: credentialId,
                new_name: newName
            });
            
            if (response.success) {
                this.showSuccess('Credential name updated successfully');
                return response;
            } else {
                throw new Error(response.error || 'Failed to update credential name');
            }
        } catch (error) {
            console.error('Error updating credential name:', error);
            this.showError(error.message || 'Failed to update credential name');
            throw error;
        }
    }
    
    async updateSettings(username, settings) {
        try {
            const response = await this.makeRequest('POST', this.apiEndpoints.settingsUpdate, {
                username: username,
                ...settings
            });
            
            if (response.success) {
                this.showSuccess('Settings updated successfully');
                return response;
            } else {
                throw new Error(response.error || 'Failed to update settings');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            this.showError(error.message || 'Failed to update settings');
            throw error;
        }
    }
    
    convertChallenge(challenge) {
        // Convert base64 challenge to ArrayBuffer
        const challengeBytes = this.base64ToArrayBuffer(challenge.challenge);
        
        return {
            ...challenge,
            challenge: challengeBytes,
            user: {
                ...challenge.user,
                id: this.base64ToArrayBuffer(challenge.user.id)
            },
            excludeCredentials: challenge.excludeCredentials?.map(cred => ({
                ...cred,
                id: this.base64ToArrayBuffer(cred.id)
            })) || [],
            allowCredentials: challenge.allowCredentials?.map(cred => ({
                ...cred,
                id: this.base64ToArrayBuffer(cred.id)
            })) || []
        };
    }
    
    base64ToArrayBuffer(base64) {
        const binaryString = window.atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }
    
    async makeRequest(method, url, data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        return await response.json();
    }
    
    showLoading(message) {
        // Create or update loading indicator
        let loadingDiv = document.getElementById('webauthn-loading');
        if (!loadingDiv) {
            loadingDiv = document.createElement('div');
            loadingDiv.id = 'webauthn-loading';
            loadingDiv.className = 'alert alert-info';
            loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + message;
            document.body.appendChild(loadingDiv);
        } else {
            loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + message;
            loadingDiv.style.display = 'block';
        }
    }
    
    hideLoading() {
        const loadingDiv = document.getElementById('webauthn-loading');
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
        }
    }
    
    showSuccess(message) {
        this.showAlert('success', message);
    }
    
    showError(message) {
        this.showAlert('danger', message);
    }
    
    showAlert(type, message) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        `;
        
        // Insert at top of page
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Utility method to check if WebAuthn is available
    static isSupported() {
        return !!(navigator.credentials && 
                 navigator.credentials.create && 
                 navigator.credentials.get &&
                 window.PublicKeyCredential);
    }
}

// Initialize WebAuthn when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (CyberPanelWebAuthn.isSupported()) {
        window.cyberPanelWebAuthn = new CyberPanelWebAuthn();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CyberPanelWebAuthn;
}
