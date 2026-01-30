# CyberPanel 2.5.5-dev Custom CSS Guide

A comprehensive guide for creating custom CSS that fully works with the new design system of CyberPanel 2.5.5-dev.

## Table of Contents

1. [Overview](#overview)
2. [Design System Architecture](#design-system-architecture)
3. [CSS Variables Reference](#css-variables-reference)
4. [Component Structure](#component-structure)
5. [Customization Examples](#customization-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Techniques](#advanced-techniques)

## Overview

CyberPanel 2.5.5-dev features a modern, CSS-variable-based design system that supports both light and dark themes. The system is built with:

- **CSS Custom Properties (Variables)** for consistent theming
- **Modern CSS Grid and Flexbox** layouts
- **Responsive design** principles
- **Dark mode support** with automatic theme switching
- **Component-based architecture** for easy customization

## Design System Architecture

### Core Structure

The design system is built around CSS custom properties defined in `:root` and `[data-theme="dark"]` selectors:

```css
:root {
    /* Light Theme Variables */
    --bg-primary: #f0f0ff;
    --bg-secondary: white;
    --text-primary: #2f3640;
    --accent-color: #5856d6;
    /* ... more variables */
}

[data-theme="dark"] {
    /* Dark Theme Variables */
    --bg-primary: #0f0f23;
    --bg-secondary: #1a1a3e;
    --text-primary: #e4e4e7;
    --accent-color: #7c7ff3;
    /* ... more variables */
}
```

### Key Components

1. **Header** (`#header`) - Top navigation bar
2. **Sidebar** (`#sidebar`) - Left navigation panel
3. **Main Content** (`#main-content`) - Page content area
4. **Cards** (`.content-card`) - Content containers
5. **Buttons** (`.btn`) - Interactive elements
6. **Forms** (`.form-*`) - Input elements

## CSS Variables Reference

### Color Variables

#### Background Colors
```css
--bg-primary          /* Main background color */
--bg-secondary        /* Card/container background */
--bg-sidebar          /* Sidebar background */
--bg-sidebar-item     /* Sidebar menu item background */
--bg-hover            /* Hover state background */
```

#### Text Colors
```css
--text-primary        /* Main text color */
--text-secondary      /* Secondary text color */
--text-heading        /* Heading text color */
```

#### Accent Colors
```css
--accent-color        /* Primary accent color */
--accent-hover        /* Accent hover state */
--danger-color        /* Error/danger color */
--success-color       /* Success color */
```

#### Border & Shadow
```css
--border-color        /* Default border color */
--shadow-color        /* Default shadow color */
```

### Special Variables

#### Gradients
```css
--warning-bg          /* Warning banner gradient */
--ai-banner-bg        /* AI scanner banner gradient */
```

#### Status Colors
```css
--success-bg          /* Success background */
--success-border      /* Success border */
--danger-bg           /* Danger background */
--danger-border       /* Danger border */
--warning-bg          /* Warning background */
--info-bg             /* Info background */
```

## Component Structure

### Header Component

```css
#header {
    background: var(--bg-secondary);
    height: 80px;
    display: flex;
    align-items: center;
    padding: 0 30px;
    box-shadow: 0 2px 12px var(--shadow-color);
    position: fixed;
    top: 0;
    left: 260px;
    right: 0;
    z-index: 1000;
}
```

**Customization Example:**
```css
/* Change header height and add custom styling */
#header {
    height: 100px;
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    border-bottom: 3px solid var(--accent-color);
}

#header .logo-text .brand {
    font-size: 32px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Sidebar Component

```css
#sidebar {
    width: 260px;
    background: var(--bg-sidebar);
    height: 100vh;
    position: fixed;
    left: 0;
    top: 0;
    overflow-y: auto;
    z-index: 1001;
}
```

**Customization Example:**
```css
/* Make sidebar wider with custom styling */
#sidebar {
    width: 300px;
    background: linear-gradient(180deg, var(--bg-sidebar), var(--bg-secondary));
    border-right: 2px solid var(--accent-color);
}

#sidebar .menu-item {
    margin: 4px 20px;
    border-radius: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

#sidebar .menu-item:hover {
    transform: translateX(5px);
    box-shadow: 0 4px 12px var(--shadow-color);
}
```

### Content Cards

```css
.content-card {
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 2px 8px var(--shadow-color);
    border: 1px solid var(--border-color);
    margin-bottom: 25px;
}
```

**Customization Example:**
```css
/* Add glassmorphism effect to cards */
.content-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

[data-theme="dark"] .content-card {
    background: rgba(26, 26, 62, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
}
```

## Customization Examples

### 1. Complete Theme Override

```css
/* Custom Purple Theme */
:root {
    --bg-primary: #f8f4ff;
    --bg-secondary: #ffffff;
    --bg-sidebar: #f3f0ff;
    --bg-hover: #e8e0ff;
    --text-primary: #2d1b69;
    --text-secondary: #6b46c1;
    --accent-color: #8b5cf6;
    --accent-hover: #7c3aed;
    --border-color: #e0d7ff;
    --shadow-color: rgba(139, 92, 246, 0.1);
}

[data-theme="dark"] {
    --bg-primary: #1a0b2e;
    --bg-secondary: #2d1b69;
    --bg-sidebar: #1e0a3e;
    --bg-hover: #3d2a7a;
    --text-primary: #f3f0ff;
    --text-secondary: #c4b5fd;
    --accent-color: #a78bfa;
    --accent-hover: #8b5cf6;
    --border-color: #4c1d95;
    --shadow-color: rgba(139, 92, 246, 0.3);
}
```

### 2. Custom Button Styles

```css
/* Custom button variants */
.btn-custom {
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    border: none;
    border-radius: 20px;
    padding: 12px 24px;
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
    transition: all 0.3s ease;
}

.btn-custom:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}

.btn-custom:active {
    transform: translateY(0);
}
```

### 3. Custom Sidebar Menu Items

```css
/* Animated sidebar menu items */
#sidebar .menu-item {
    position: relative;
    overflow: hidden;
}

#sidebar .menu-item::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}

#sidebar .menu-item:hover::before {
    left: 100%;
}

#sidebar .menu-item .icon-wrapper {
    position: relative;
    z-index: 1;
}
```

### 4. Custom Form Styling

```css
/* Modern form inputs */
.form-control {
    border: 2px solid var(--border-color);
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    transition: all 0.3s ease;
    background: var(--bg-secondary);
}

.form-control:focus {
    border-color: var(--accent-color);
    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1);
    transform: translateY(-1px);
}

.form-control::placeholder {
    color: var(--text-secondary);
    opacity: 0.7;
}
```

### 5. Custom Notifications

```css
/* Custom notification banners */
.notification-banner {
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    border-radius: 16px;
    padding: 20px;
    margin: 20px;
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
    position: relative;
    overflow: hidden;
}

.notification-banner::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
    animation: rainbow 3s linear infinite;
}

@keyframes rainbow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
```

## Best Practices

### 1. Use CSS Variables

Always use CSS variables instead of hardcoded values:

```css
/* ✅ Good */
.custom-element {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

/* ❌ Bad */
.custom-element {
    background: white;
    color: #2f3640;
    border: 1px solid #e8e9ff;
}
```

### 2. Support Both Themes

Always provide both light and dark theme support:

```css
.custom-element {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

/* Dark theme specific adjustments */
[data-theme="dark"] .custom-element {
    /* Additional dark theme styling if needed */
}
```

### 3. Use Semantic Class Names

```css
/* ✅ Good */
.primary-button { }
.content-container { }
.navigation-item { }

/* ❌ Bad */
.red-button { }
.big-box { }
.item1 { }
```

### 4. Maintain Responsive Design

```css
.custom-element {
    padding: 20px;
    font-size: 16px;
}

@media (max-width: 768px) {
    .custom-element {
        padding: 15px;
        font-size: 14px;
    }
}
```

### 5. Use Modern CSS Features

```css
.custom-element {
    /* Use CSS Grid for layouts */
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    
    /* Use Flexbox for alignment */
    align-items: center;
    justify-content: space-between;
    
    /* Use CSS custom properties for calculations */
    --element-height: 60px;
    height: var(--element-height);
    
    /* Use modern selectors */
    &:hover { }
    &:focus-within { }
}
```

## Troubleshooting

### Common Issues

#### 1. Custom CSS Not Applying

**Problem:** Custom CSS doesn't appear to be working.

**Solution:**
- Check CSS specificity - use more specific selectors
- Ensure CSS is placed after the base styles
- Use `!important` sparingly and only when necessary

```css
/* Increase specificity */
#main-content .content-card .custom-element {
    background: var(--bg-secondary);
}
```

#### 2. Dark Mode Not Working

**Problem:** Custom styles don't adapt to dark mode.

**Solution:**
- Always use CSS variables
- Test both light and dark themes
- Provide dark mode specific overrides when needed

```css
.custom-element {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

[data-theme="dark"] .custom-element {
    /* Dark mode specific adjustments */
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
```

#### 3. Responsive Issues

**Problem:** Custom styles break on mobile devices.

**Solution:**
- Use relative units (rem, em, %)
- Test on different screen sizes
- Use CSS Grid and Flexbox for responsive layouts

```css
.custom-element {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}

@media (max-width: 768px) {
    .custom-element {
        padding: 0.5rem;
    }
}
```

## Advanced Techniques

### 1. CSS Animations

```css
/* Smooth page transitions */
.page-transition {
    animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Hover animations */
.interactive-element {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.interactive-element:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 25px var(--shadow-color);
}
```

### 2. CSS Grid Layouts

```css
/* Advanced grid layouts */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    padding: 20px;
}

.dashboard-card {
    grid-column: span 1;
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px var(--shadow-color);
}

.dashboard-card.featured {
    grid-column: span 2;
}

@media (max-width: 768px) {
    .dashboard-card.featured {
        grid-column: span 1;
    }
}
```

### 3. CSS Custom Properties with JavaScript

```css
/* Dynamic theming with CSS variables */
:root {
    --custom-accent: #5856d6;
    --custom-accent-hover: #4644c0;
}

.custom-theme {
    --accent-color: var(--custom-accent);
    --accent-hover: var(--custom-accent-hover);
}
```

### 4. Advanced Selectors

```css
/* Complex selectors for specific styling */
#sidebar .menu-item:not(.active):hover {
    background: var(--bg-hover);
    transform: translateX(5px);
}

.content-card > *:first-child {
    margin-top: 0;
}

.content-card > *:last-child {
    margin-bottom: 0;
}

/* Attribute selectors */
[data-status="success"] {
    border-left: 4px solid var(--success-color);
}

[data-status="error"] {
    border-left: 4px solid var(--danger-color);
}
```

### 5. CSS Functions and Calculations

```css
/* Using CSS functions */
.responsive-text {
    font-size: clamp(14px, 2.5vw, 18px);
    line-height: calc(1.5em + 0.5vw);
}

.dynamic-spacing {
    padding: calc(1rem + 2vw);
    margin: calc(0.5rem + 1vw);
}

/* CSS custom properties with calculations */
:root {
    --base-size: 16px;
    --scale-factor: 1.2;
    --large-size: calc(var(--base-size) * var(--scale-factor));
}
```

## Implementation Guide

### Step 1: Access the Design Page

1. Log into CyberPanel
2. Navigate to **Design** in the sidebar
3. Scroll down to the **Custom CSS** section

### Step 2: Add Your Custom CSS

1. Paste your custom CSS into the textarea
2. Click **Save Changes**
3. Refresh the page to see your changes

### Step 3: Test Your Changes

1. Test in both light and dark modes
2. Test on different screen sizes
3. Verify all interactive elements work correctly

### Step 4: Iterate and Refine

1. Make adjustments as needed
2. Test thoroughly before finalizing
3. Document your customizations

## Example: Complete Custom Theme

Here's a complete example of a custom theme that you can use as a starting point:

```css
/* Custom CyberPanel Theme - Ocean Blue */

/* Light Theme */
:root {
    --bg-primary: #f0f9ff;
    --bg-secondary: #ffffff;
    --bg-sidebar: #e0f2fe;
    --bg-sidebar-item: #ffffff;
    --bg-hover: #bae6fd;
    --text-primary: #0c4a6e;
    --text-secondary: #0369a1;
    --text-heading: #0c4a6e;
    --border-color: #bae6fd;
    --shadow-color: rgba(6, 105, 161, 0.1);
    --accent-color: #0284c7;
    --accent-hover: #0369a1;
    --danger-color: #dc2626;
    --success-color: #059669;
    --warning-bg: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    --ai-banner-bg: linear-gradient(135deg, #0284c7 0%, #0369a1 50%, #0c4a6e 100%);
}

/* Dark Theme */
[data-theme="dark"] {
    --bg-primary: #0c4a6e;
    --bg-secondary: #075985;
    --bg-sidebar: #0c4a6e;
    --bg-sidebar-item: #075985;
    --bg-hover: #0369a1;
    --text-primary: #e0f2fe;
    --text-secondary: #bae6fd;
    --text-heading: #f0f9ff;
    --border-color: #0369a1;
    --shadow-color: rgba(0, 0, 0, 0.3);
    --accent-color: #38bdf8;
    --accent-hover: #0ea5e9;
    --danger-color: #f87171;
    --success-color: #34d399;
    --warning-bg: linear-gradient(135deg, #78350f 0%, #92400e 100%);
    --ai-banner-bg: linear-gradient(135deg, #0c4a6e 0%, #075985 50%, #0369a1 100%);
}

/* Custom Header Styling */
#header {
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    box-shadow: 0 4px 20px var(--shadow-color);
}

#header .logo-text .brand {
    color: white;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Custom Sidebar Styling */
#sidebar {
    background: linear-gradient(180deg, var(--bg-sidebar), var(--bg-secondary));
    border-right: 3px solid var(--accent-color);
}

#sidebar .menu-item {
    border-radius: 12px;
    margin: 4px 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

#sidebar .menu-item:hover {
    transform: translateX(8px);
    box-shadow: 0 4px 15px var(--shadow-color);
}

#sidebar .menu-item.active {
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
}

/* Custom Content Cards */
.content-card {
    background: var(--bg-secondary);
    border-radius: 16px;
    box-shadow: 0 4px 20px var(--shadow-color);
    border: 1px solid var(--border-color);
    position: relative;
    overflow: hidden;
}

.content-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent-color), var(--accent-hover));
}

/* Custom Buttons */
.btn {
    border-radius: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary {
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(2, 132, 199, 0.4);
}

/* Custom Form Elements */
.form-control {
    border: 2px solid var(--border-color);
    border-radius: 12px;
    transition: all 0.3s ease;
}

.form-control:focus {
    border-color: var(--accent-color);
    box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.1);
    transform: translateY(-1px);
}

/* Custom Animations */
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.content-card {
    animation: slideIn 0.5s ease-out;
}

/* Responsive Design */
@media (max-width: 768px) {
    #sidebar {
        width: 100%;
        height: auto;
        position: relative;
    }
    
    #header {
        left: 0;
    }
    
    .content-card {
        margin: 10px;
        padding: 20px;
    }
}
```

This guide provides everything you need to create beautiful, functional custom CSS for CyberPanel 2.5.5+. Remember to always test your changes thoroughly and use the CSS variables for consistency across themes.
