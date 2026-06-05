/**
 * Discord Login Button Injector
 * Injects Discord login button into CyberPanel login page
 */

(function() {
    'use strict';
    
    // Check if we're on the login page
    if (window.location.pathname !== '/' && !window.location.pathname.includes('login')) {
        return;
    }
    
    // Check if Discord auth is enabled
    function checkDiscordEnabled() {
        return fetch('/plugins/discordAuth/check/', {
            method: 'GET',
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            return { enabled: false };
        })
        .catch(() => {
            return { enabled: false };
        });
    }
    
    // Inject Discord login button
    function injectDiscordButton() {
        checkDiscordEnabled().then(data => {
            if (!data.enabled) {
                return; // Discord auth not enabled
            }
            
            // Wait for login form to be ready
            const checkForm = setInterval(function() {
                const loginForm = document.getElementById('loginForm');
                const submitButton = document.querySelector('#loginForm button[type="submit"]');
                
                if (loginForm && submitButton) {
                    clearInterval(checkForm);
                    
                    // Create Discord button container
                    const discordContainer = document.createElement('div');
                    discordContainer.className = 'discord-login-container';
                    discordContainer.style.cssText = 'text-align: center; margin: 20px 0;';
                    
                    // Create divider
                    const divider = document.createElement('div');
                    divider.className = 'discord-login-divider';
                    divider.textContent = 'OR';
                    
                    // Create Discord button
                    const discordButton = document.createElement('a');
                    discordButton.href = '/plugins/discordAuth/login/';
                    discordButton.className = 'discord-login-btn';
                    discordButton.innerHTML = '<i class="fab fa-discord"></i> Login with Discord';
                    
                    // Insert after submit button
                    submitButton.parentNode.insertBefore(divider, submitButton.nextSibling);
                    submitButton.parentNode.insertBefore(discordContainer, divider.nextSibling);
                    discordContainer.appendChild(discordButton);
                    
                    // Load CSS if not already loaded
                    if (!document.getElementById('discord-auth-css')) {
                        const link = document.createElement('link');
                        link.id = 'discord-auth-css';
                        link.rel = 'stylesheet';
                        link.href = '/static/discordAuth/css/discord-auth.css';
                        document.head.appendChild(link);
                    }
                }
            }, 100);
            
            // Timeout after 5 seconds
            setTimeout(function() {
                clearInterval(checkForm);
            }, 5000);
        });
    }
    
    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectDiscordButton);
    } else {
        injectDiscordButton();
    }
})();
