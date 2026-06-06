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
            authenticationOptions: '/webauthn/authentication/options/',
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
        const existingBtn = document.getElementById('webauthn-login-btn');
        if (existingBtn && !existingBtn.dataset.bound) {
            existingBtn.dataset.bound = '1';
            existingBtn.onclick = () => this.startPasskeyFirstLogin();
        }
    }
    
    addUserManagementUI() {
        // This will be called when user management page loads
        // Implementation depends on the specific UI structure
    }
    
    arrayBufferToBase64url(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
        return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    }

    base64urlToArrayBuffer(str) {
        let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
        const pad = (4 - (base64.length % 4)) % 4;
        for (let i = 0; i < pad; i++) base64 += '=';
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        return bytes.buffer;
    }

    async startPasskeyFirstLogin() {
        try {
            this.showLoading('Signing in with passkey...');
            const optsUrl = this.apiEndpoints.authenticationOptions + '?return=' + encodeURIComponent(window.location.pathname || '/');
            const optsResponse = await fetch(optsUrl, { method: 'GET', credentials: 'same-origin' });
            const optsData = await optsResponse.json();
            if (!optsData.publicKey) {
                throw new Error(optsData.error || 'Failed to get options');
            }
            const publicKey = optsData.publicKey;
            publicKey.challenge = this.base64urlToArrayBuffer(publicKey.challenge);
            if (publicKey.allowCredentials && publicKey.allowCredentials.length) {
                publicKey.allowCredentials = publicKey.allowCredentials.map(function(c) {
                    return {
                        type: c.type || 'public-key',
                        id: typeof c.id === 'string' ? this.base64urlToArrayBuffer(c.id) : c.id,
                        transports: c.transports
                    };
                }.bind(this));
            }
            const credential = await navigator.credentials.get({ publicKey });
            if (!credential) throw new Error('No credential');
            const credentialJson = {
                id: credential.id,
                rawId: this.arrayBufferToBase64url(credential.rawId),
                type: credential.type,
                response: {
                    clientDataJSON: this.arrayBufferToBase64url(credential.response.clientDataJSON),
                    authenticatorData: this.arrayBufferToBase64url(credential.response.authenticatorData),
                    signature: this.arrayBufferToBase64url(credential.response.signature),
                    userHandle: credential.response.userHandle ? this.arrayBufferToBase64url(credential.response.userHandle) : null
                }
            };
            const authResponse = await this.makeRequest('POST', this.apiEndpoints.authenticationComplete, {
                credential: credentialJson
            });
            if (authResponse.success && authResponse.redirect) {
                window.location.href = authResponse.redirect;
                return;
            }
            throw new Error(authResponse.error || 'Verification failed');
        } catch (error) {
            if (error.name === 'NotAllowedError' || (error.message && (error.message.indexOf('cancel') !== -1 || error.message.indexOf('timed out') !== -1))) {
                this.hideLoading();
                return;
            }
            console.error('WebAuthn passkey-first error:', error);
            this.showError(error.message || 'Passkey sign-in failed');
        } finally {
            this.hideLoading();
        }
    }

    async startPasswordlessLogin() {
        try {
            const username = document.querySelector('input[name="username"]').value;
            if (!username) {
                this.showError('Please enter your username first');
                return;
            }
            this.showLoading('Starting passkey authentication...');
            const challengeResponse = await this.makeRequest('POST', this.apiEndpoints.authenticationStart, { username: username });
            if (!challengeResponse.success) {
                throw new Error(challengeResponse.error || 'Failed to start authentication');
            }
            const challenge = this.convertChallenge(challengeResponse.challenge);
            const credential = await navigator.credentials.get({ publicKey: challenge });
            const authResponse = await this.makeRequest('POST', this.apiEndpoints.authenticationComplete, {
                challenge_id: challengeResponse.challenge_id,
                credential: {
                    id: this.arrayBufferToBase64(credential.rawId),
                    type: credential.type
                },
                client_data_json: this.arrayBufferToBase64(credential.response.clientDataJSON),
                authenticator_data: this.arrayBufferToBase64(credential.response.authenticatorData),
                signature: this.arrayBufferToBase64(credential.response.signature),
                user_handle: credential.response.userHandle ? this.arrayBufferToBase64(credential.response.userHandle) : null
            });
            if (authResponse.success) {
                this.showSuccess('Authentication successful! Redirecting...');
                setTimeout(() => { window.location.href = authResponse.redirect || '/'; }, 1000);
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
    
    async registerPasskey(username, credentialName = '', options = {}) {
        const silent = options && options.silent === true;
        try {
            if (!silent) this.showLoading('Starting passkey registration...');
            
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
                if (!silent) this.showSuccess('Passkey registered successfully!');
                return regResponse;
            } else {
                throw new Error(regResponse.error || 'Registration failed');
            }
            
        } catch (error) {
            console.error('WebAuthn registration error:', error);
            if (!silent) this.showError(error.message || 'Registration failed');
            throw error;
        } finally {
            if (!silent) this.hideLoading();
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
        const ch = challenge.challenge;
        const challengeBytes = (typeof ch === 'string' && (ch.indexOf('-') !== -1 || ch.indexOf('_') !== -1))
            ? this.base64urlToArrayBuffer(ch) : this.base64ToArrayBuffer(ch);
        const userId = challenge.user && challenge.user.id;
        const userIdBuf = !userId ? undefined : (typeof userId === 'string' && (userId.indexOf('-') !== -1 || userId.indexOf('_') !== -1)
            ? this.base64urlToArrayBuffer(userId) : this.base64ToArrayBuffer(userId));
        return {
            ...challenge,
            challenge: challengeBytes,
            user: challenge.user ? { ...challenge.user, id: userIdBuf } : undefined,
            excludeCredentials: challenge.excludeCredentials?.map(cred => ({
                ...cred,
                id: typeof cred.id === 'string' && (cred.id.indexOf('-') !== -1 || cred.id.indexOf('_') !== -1)
                    ? this.base64urlToArrayBuffer(cred.id) : this.base64ToArrayBuffer(cred.id)
            })) || [],
            allowCredentials: challenge.allowCredentials?.map(cred => ({
                ...cred,
                id: typeof cred.id === 'string' && (cred.id.indexOf('-') !== -1 || cred.id.indexOf('_') !== -1)
                    ? this.base64urlToArrayBuffer(cred.id) : this.base64ToArrayBuffer(cred.id)
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

// Initialize WebAuthn - run now if DOM ready, else on DOMContentLoaded (script often loads after DOM is ready)
function initCyberPanelWebAuthn() {
    if (CyberPanelWebAuthn.isSupported()) {
        window.cyberPanelWebAuthn = new CyberPanelWebAuthn();
    }
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCyberPanelWebAuthn);
} else {
    initCyberPanelWebAuthn();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CyberPanelWebAuthn;
}
