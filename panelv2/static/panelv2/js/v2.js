/* =========================================================================
   CyberPanel v2 – Alpine.js Components & AJAX Helpers
   ========================================================================= */

/**
 * CSRF token helper – reads from cookie (Django default).
 */
function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith(name + '=')) {
            return c.substring(name.length + 1);
        }
    }
    return '';
}

/**
 * Fetch wrapper for v2 API calls.
 * @param {string} url
 * @param {object} options - { method, body }
 * @returns {Promise<object>} parsed JSON response
 */
async function v2Fetch(url, options = {}) {
    const method = options.method || 'GET';
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
    };
    const config = { method, headers, credentials: 'same-origin' };
    if (options.body && method !== 'GET') {
        config.body = JSON.stringify(options.body);
    }
    const resp = await fetch(url, config);
    if (!resp.ok) {
        return { status: 0, error_message: 'Server error (' + resp.status + ')' };
    }
    return resp.json();
}

/* =========================================================================
   Alpine.js Store – Theme
   ========================================================================= */
document.addEventListener('alpine:init', () => {

    Alpine.store('theme', {
        dark: localStorage.getItem('v2_theme') === 'dark',

        toggle() {
            this.dark = !this.dark;
            localStorage.setItem('v2_theme', this.dark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', this.dark ? 'dark' : '');
        },

        init() {
            if (this.dark) {
                document.documentElement.setAttribute('data-theme', 'dark');
            }
        }
    });

    Alpine.store('sidebar', {
        open: false,
        toggle() { this.open = !this.open; },
        close() { this.open = false; }
    });
});

/* =========================================================================
   Alpine.js Data Components
   ========================================================================= */

/**
 * Site list component with search & pagination.
 * Expects `window.__v2_sites` to be set by the template.
 */
function siteListComponent() {
    return {
        sites: window.__v2_sites || [],
        search: '',
        page: 1,
        perPage: 20,

        get filtered() {
            const q = this.search.toLowerCase();
            if (!q) return this.sites;
            return this.sites.filter(s => s.domain.toLowerCase().includes(q));
        },

        get paged() {
            const start = (this.page - 1) * this.perPage;
            return this.filtered.slice(start, start + this.perPage);
        },

        get totalPages() {
            return Math.max(1, Math.ceil(this.filtered.length / this.perPage));
        },

        goToSite(id) {
            window.location.href = '/v2/sites/' + id + '/';
        }
    };
}

/**
 * Generic CRUD component for feature pages (databases, email, ftp, etc.).
 * @param {string} apiUrl - base API URL, e.g. /v2/api/sites/3/databases
 * @param {string} itemsKey - JSON key for items list, e.g. 'databases'
 */
function crudComponent(apiUrl, itemsKey) {
    return {
        items: [],
        loading: true,
        showForm: false,
        formData: {},
        error: '',
        success: '',

        async init() {
            await this.load();
        },

        async load() {
            this.loading = true;
            this.error = '';
            try {
                const data = await v2Fetch(apiUrl);
                if (data.status === 1) {
                    this.items = data[itemsKey] || [];
                } else {
                    this.error = data.error_message;
                }
            } catch (e) {
                this.error = 'Failed to load data';
            }
            this.loading = false;
        },

        async create(body) {
            this.error = '';
            this.success = '';
            try {
                const data = await v2Fetch(apiUrl, { method: 'POST', body });
                if (data.status === 1) {
                    this.success = 'Created successfully';
                    this.showForm = false;
                    this.formData = {};
                    await this.load();
                } else {
                    this.error = data.error_message;
                }
            } catch (e) {
                this.error = 'Request failed';
            }
        },

        async remove(body) {
            if (!confirm('Are you sure you want to delete this?')) return;
            this.error = '';
            this.success = '';
            try {
                const data = await v2Fetch(apiUrl, { method: 'DELETE', body });
                if (data.status === 1) {
                    this.success = 'Deleted successfully';
                    await this.load();
                } else {
                    this.error = data.error_message;
                }
            } catch (e) {
                this.error = 'Request failed';
            }
        },

        clearMessages() {
            this.error = '';
            this.success = '';
        }
    };
}

/**
 * Log viewer component.
 * @param {string} apiUrl - /v2/api/sites/<id>/logs
 */
function logViewerComponent(apiUrl) {
    return {
        logs: [],
        logType: 'access',
        lines: 100,
        loading: false,
        error: '',

        async load() {
            this.loading = true;
            this.error = '';
            try {
                const data = await v2Fetch(apiUrl + '?type=' + this.logType + '&lines=' + this.lines);
                if (data.status === 1) {
                    this.logs = data.logs || [];
                } else {
                    this.error = data.error_message || 'Failed to load logs';
                }
            } catch (e) {
                this.error = 'Failed to load logs';
            }
            this.loading = false;
        },

        init() {
            this.load();
        }
    };
}

/**
 * Config editor component.
 * @param {string} apiUrl - /v2/api/sites/<id>/config
 */
function configEditorComponent(apiUrl) {
    return {
        content: '',
        configType: 'vhost',
        loading: false,
        error: '',
        success: '',

        async load() {
            this.loading = true;
            this.error = '';
            try {
                const data = await v2Fetch(apiUrl + '?type=' + this.configType);
                if (data.status === 1) {
                    this.content = data.content || '';
                } else {
                    this.error = data.error_message;
                }
            } catch (e) {
                this.error = 'Failed to load config';
            }
            this.loading = false;
        },

        async save() {
            this.error = '';
            this.success = '';
            try {
                const data = await v2Fetch(apiUrl, {
                    method: 'POST',
                    body: { type: this.configType, content: this.content }
                });
                if (data.status === 1) {
                    this.success = 'Saved successfully';
                } else {
                    this.error = data.error_message;
                }
            } catch (e) {
                this.error = 'Request failed';
            }
        },

        init() {
            this.load();
        }
    };
}
