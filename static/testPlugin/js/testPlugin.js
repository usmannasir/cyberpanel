/**
 * Test Plugin JavaScript
 * Handles all client-side functionality for the test plugin
 */

class TestPlugin {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeComponents();
    }

    bindEvents() {
        // Toggle switch functionality
        const toggleSwitch = document.getElementById('plugin-toggle');
        if (toggleSwitch) {
            toggleSwitch.addEventListener('change', (e) => this.handleToggle(e));
        }

        // Test button functionality
        const testButton = document.getElementById('test-button');
        if (testButton) {
            testButton.addEventListener('click', (e) => this.handleTestClick(e));
        }

        // Settings form
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => this.handleSettingsSubmit(e));
        }

        // Log filter
        const actionFilter = document.getElementById('action-filter');
        if (actionFilter) {
            actionFilter.addEventListener('change', (e) => this.handleLogFilter(e));
        }
    }

    initializeComponents() {
        // Initialize any components that need setup
        this.initializeTooltips();
        this.initializeAnimations();
    }

    async handleToggle(event) {
        const toggleSwitch = event.target;
        const testButton = document.getElementById('test-button');
        
        try {
            const response = await fetch('/testPlugin/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.status === 1) {
                if (testButton) {
                    testButton.disabled = !data.enabled;
                }
                this.showNotification('success', 'Plugin Toggle', data.message);
                
                // Update status indicator if exists
                this.updateStatusIndicator(data.enabled);
                
                // Reload page after a short delay to update UI
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                this.showNotification('error', 'Error', data.error_message);
                // Revert toggle state
                toggleSwitch.checked = !toggleSwitch.checked;
            }
        } catch (error) {
            this.showNotification('error', 'Error', 'Failed to toggle plugin');
            // Revert toggle state
            toggleSwitch.checked = !toggleSwitch.checked;
        }
    }

    async handleTestClick(event) {
        const testButton = event.target;
        
        if (testButton.disabled) return;

        // Add loading state
        testButton.classList.add('loading');
        testButton.disabled = true;
        const originalContent = testButton.innerHTML;
        testButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';

        try {
            const response = await fetch('/testPlugin/test/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.status === 1) {
                // Update test count
                const testCountElement = document.getElementById('test-count');
                if (testCountElement) {
                    testCountElement.textContent = data.test_count;
                }

                // Show popup message
                this.showPopup(
                    data.popup_message.type,
                    data.popup_message.title,
                    data.popup_message.message
                );

                // Add success animation
                testButton.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                setTimeout(() => {
                    testButton.style.background = '';
                }, 2000);
            } else {
                this.showNotification('error', 'Error', data.error_message);
            }
        } catch (error) {
            this.showNotification('error', 'Error', 'Failed to execute test');
        } finally {
            // Remove loading state
            testButton.classList.remove('loading');
            testButton.disabled = false;
            testButton.innerHTML = originalContent;
        }
    }

    async handleSettingsSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const data = {
            custom_message: formData.get('custom_message')
        };

        try {
            const response = await fetch('/testPlugin/update-settings/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.status === 1) {
                this.showNotification('success', 'Settings Updated', result.message);
            } else {
                this.showNotification('error', 'Error', result.error_message);
            }
        } catch (error) {
            this.showNotification('error', 'Error', 'Failed to update settings');
        }
    }

    handleLogFilter(event) {
        const selectedAction = event.target.value;
        const logRows = document.querySelectorAll('.log-row');

        logRows.forEach(row => {
            if (selectedAction === '' || row.dataset.action === selectedAction) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    showPopup(type, title, message) {
        const popupContainer = document.getElementById('popup-container') || this.createPopupContainer();
        const popup = document.createElement('div');
        popup.className = `popup-message ${type}`;
        
        popup.innerHTML = `
            <button class="popup-close" onclick="this.parentElement.remove()">&times;</button>
            <div class="popup-title">${title}</div>
            <div class="popup-content">${message}</div>
            <div class="popup-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        popupContainer.appendChild(popup);
        
        // Show popup with animation
        setTimeout(() => popup.classList.add('show'), 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            popup.classList.remove('show');
            setTimeout(() => popup.remove(), 300);
        }, 5000);
    }

    showNotification(type, title, message) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-content">${message}</div>
        `;
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    createPopupContainer() {
        const container = document.createElement('div');
        container.id = 'popup-container';
        container.className = 'popup-container';
        document.body.appendChild(container);
        return container;
    }

    updateStatusIndicator(enabled) {
        const statusElements = document.querySelectorAll('.status-indicator');
        statusElements.forEach(element => {
            element.className = `status-indicator ${enabled ? 'enabled' : 'disabled'}`;
            element.innerHTML = enabled ? 
                '<i class="fas fa-check-circle"></i> Enabled' : 
                '<i class="fas fa-times-circle"></i> Disabled';
        });
    }

    initializeTooltips() {
        // Add tooltips to buttons and controls
        const elements = document.querySelectorAll('[data-tooltip]');
        elements.forEach(element => {
            element.addEventListener('mouseenter', (e) => this.showTooltip(e));
            element.addEventListener('mouseleave', (e) => this.hideTooltip(e));
        });
    }

    showTooltip(event) {
        const element = event.target;
        const tooltipText = element.dataset.tooltip;
        
        if (!tooltipText) return;

        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = tooltipText;
        tooltip.style.cssText = `
            position: absolute;
            background: #333;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10000;
            pointer-events: none;
            white-space: nowrap;
        `;

        document.body.appendChild(tooltip);

        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';

        element._tooltip = tooltip;
    }

    hideTooltip(event) {
        const element = event.target;
        if (element._tooltip) {
            element._tooltip.remove();
            delete element._tooltip;
        }
    }

    initializeAnimations() {
        // Add entrance animations to cards
        const cards = document.querySelectorAll('.plugin-card, .stat-card, .log-item');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
}

// Initialize the plugin when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new TestPlugin();
});

// Export for potential external use
window.TestPlugin = TestPlugin;
