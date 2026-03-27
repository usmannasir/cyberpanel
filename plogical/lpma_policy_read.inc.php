<?php
/**
 * Load Limited phpMyAdmin UI policy (strict mode + blocked preference tabs).
 * Primary: pluginState (writable by cyberpanel). Fallbacks for older installs.
 */
function lpma_read_limited_policy(): array
{
    $defaultBlocked = [
        'manage' => true,
        'two_factor' => true,
        'features' => true,
        'sql' => true,
        'navigation' => true,
        'main_panel' => true,
        'export' => true,
        'import' => true,
    ];
    $policy = [
        'strict_mode' => true,
        'blocked_tabs' => $defaultBlocked,
    ];
    $paths = [
        '/usr/local/CyberCP/pluginState/limited_phpmyadmin_policy.json',
        '/var/lib/cyberpanel-panelstate/limited_phpmyadmin_policy.json',
        '/etc/cyberpanel/limited_phpmyadmin_policy.json',
    ];
    foreach ($paths as $policyPath) {
        if (! @is_readable($policyPath)) {
            continue;
        }
        $raw = @file_get_contents($policyPath);
        if ($raw === false) {
            continue;
        }
        $decoded = @json_decode($raw, true);
        if (! is_array($decoded)) {
            continue;
        }
        $policy['strict_mode'] = isset($decoded['strict_mode']) ? (bool) $decoded['strict_mode'] : true;
        if (isset($decoded['blocked_tabs']) && is_array($decoded['blocked_tabs'])) {
            foreach ($defaultBlocked as $k => $_v) {
                $policy['blocked_tabs'][$k] = isset($decoded['blocked_tabs'][$k])
                    ? (bool) $decoded['blocked_tabs'][$k]
                    : true;
            }
        }
        break;
    }

    return $policy;
}

/**
 * True if a cpma_* request to this application route must be turned away (Settings prefs + main menu targets).
 * Does not block table browse at route "/sql" (that is Browse, not the SQL runner).
 */
function lpma_cpma_route_blocked(string $requestedRoute, array $policy): bool
{
    if ($requestedRoute === '') {
        return false;
    }
    $bt = $policy['blocked_tabs'] ?? [];
    $blocked = static function (string $k) use ($bt): bool {
        return (($bt[$k] ?? true) === true);
    };

    if (strpos($requestedRoute, '/preferences') === 0) {
        $routeToTab = [
            '/preferences/manage' => 'manage',
            '/preferences/two-factor' => 'two_factor',
            '/preferences/features' => 'features',
            '/preferences/sql' => 'sql',
            '/preferences/navigation' => 'navigation',
            '/preferences/main-panel' => 'main_panel',
            '/preferences/export' => 'export',
            '/preferences/import' => 'import',
        ];
        if (isset($routeToTab[$requestedRoute])) {
            return $blocked($routeToTab[$requestedRoute]);
        }

        return (($policy['strict_mode'] ?? true) === true);
    }

    if ($blocked('sql')) {
        if (preg_match('#^/(server|database|table)/sql$#', $requestedRoute) === 1) {
            return true;
        }
        if ($requestedRoute === '/database/multi-table-query' || $requestedRoute === '/database/qbe') {
            return true;
        }
    }

    if ($blocked('export') && preg_match('#^/(server|database|table)/export$#', $requestedRoute) === 1) {
        return true;
    }

    if ($blocked('import') && preg_match('#^/(server|database|table)/import$#', $requestedRoute) === 1) {
        return true;
    }

    if ($blocked('main_panel')) {
        if (
            $requestedRoute === '/server/databases'
            || $requestedRoute === '/server/variables'
            || $requestedRoute === '/server/collations'
        ) {
            return true;
        }
        if (strpos($requestedRoute, '/server/status') === 0) {
            return true;
        }
    }

    if ($blocked('features')) {
        if (
            $requestedRoute === '/server/engines'
            || $requestedRoute === '/server/plugins'
            || $requestedRoute === '/server/binlog'
        ) {
            return true;
        }
        if (
            $requestedRoute === '/database/designer'
            || $requestedRoute === '/database/central-columns'
            || $requestedRoute === '/database/tracking'
            || $requestedRoute === '/table/tracking'
        ) {
            return true;
        }
    }

    return false;
}
