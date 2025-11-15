# Django Tutor Platform - UI Components

This directory contains the enhanced UI components for the Django Tutor Platform, built with the new responsive design system using SCSS, Alpine.js, and HTMX.

## Design System

The components are built on a modern design system with:

- **CUBE CSS Methodology**: Composition, Utility, Block, Exception approach to styling
- **Mobile-First Responsive Design**: Progressive enhancement for larger screens
- **CSS Custom Properties**: Consistent theming with light/dark mode support
- **Accessibility First**: Proper ARIA labels, keyboard navigation, and screen reader support
- **Modern Interactions**: Smooth transitions, micro-interactions, and loading states

## Component Structure

```
ui_components/
├── templates/
│   └── ui_components/
│       ├── base.html              # Base template with theme support
│       ├── navigation.html         # Responsive navigation component
│       ├── card.html              # Modern card variants
│       ├── form.html              # Enhanced form components
│       ├── table.html             # Interactive data tables
│       ├── modal.html             # Enhanced modal system
│       ├── alert.html             # Alert and notification system
│       ├── pagination.html        # Advanced pagination
│       ├── search_bar.html        # Smart search with autocomplete
│       ├── notification_dropdown.html # Real-time notifications
│       ├── dashboard.html         # Dashboard widgets
│       └── component_test.html    # Component test suite
├── static/
│   └── ui_components/
│       └── scss/
│           ├── _variables.scss      # Design system variables
│           ├── _mixins.scss        # Reusable mixins
│           ├── _base.scss          # Base styles
│           ├── _components.scss    # Component styles
│           └── main.scss          # Main SCSS file
└── templatetags/
    └── ui_tags.py              # Custom template tags
```

## Components Overview

### 1. Base Template (`base.html`)

**Features:**
- PWA support with proper meta tags
- Light/dark theme toggle with system preference detection
- Role-based CSS classes (student, tutor, admin)
- Enhanced accessibility with ARIA labels
- Loading overlay and screen reader announcements
- Responsive design with mobile-first approach

**Usage:**
```django
{% extends "ui_components/base.html" %}
```

### 2. Navigation Component (`navigation.html`)

**Features:**
- Responsive navigation with mobile hamburger menu
- Role-based navigation items
- Integrated search functionality with autocomplete
- Real-time notification dropdown
- User profile dropdown with quick actions
- Keyboard navigation support

**Usage:**
```django
{% include "ui_components/navigation.html" with role="tutor" show_search=true %}
```

### 3. Card Component (`card.html`)

**Variants:**
- `basic`: Standard card with title and content
- `interactive`: Card with hover effects and click actions
- `dashboard`: Optimized for dashboard widgets
- `skeleton`: Loading state with animated placeholders

**Features:**
- Hover effects and micro-interactions
- Loading states and skeleton screens
- Support for different content types
- Responsive grid layouts
- Selection indicators and actions

**Usage:**
```django
{% include "ui_components/card.html" with title="Card Title" variant="interactive" %}
```

### 4. Form Component (`form.html`)

**Features:**
- Floating labels with smooth animations
- Multi-step form support with progress indicators
- Enhanced file upload with drag-and-drop
- Real-time validation with error states
- Auto-save functionality for long forms
- Accessible form controls

**Usage:**
```django
{% include "ui_components/form.html" with multi_step=true show_floating_labels=true %}
```

### 5. Table Component (`table.html`)

**Features:**
- Responsive design with mobile view
- Advanced sorting and filtering
- Pagination with customizable page sizes
- Inline editing capabilities
- Bulk actions and selection
- Export functionality
- Search with autocomplete

**Usage:**
```django
{% include "ui_components/table.html" with selectable=true show_filters=true %}
```

### 6. Modal Component (`modal.html`)

**Features:**
- Multiple sizes (sm, md, lg, xl, fullscreen)
- Modal stacking support
- Enhanced animations and transitions
- Loading and error states
- Full accessibility support
- Action loading states

**Usage:**
```django
{% include "ui_components/modal.html" with modal_id="example" size="modal-lg" %}
```

### 7. Alert Component (`alert.html`)

**Features:**
- Multiple variants (info, success, warning, danger)
- Auto-dismiss with progress indicators
- Toast notifications for real-time updates
- Notification history panel
- Contextual actions

**Usage:**
```django
{% include "ui_components/alert.html" with level="success" dismissible=true %}
```

### 8. Pagination Component (`pagination.html`)

**Features:**
- Smart page number display with ellipsis
- Page size selector
- Jump to page functionality
- Loading states for AJAX pagination
- Keyboard navigation
- Responsive design

**Usage:**
```django
{% include "ui_components/pagination.html" with show_info=true show_jump=true %}
```

### 9. Search Bar Component (`search_bar.html`)

**Features:**
- Real-time search suggestions
- Advanced filtering options
- Recent search history
- Keyboard navigation
- Loading states
- Responsive design

**Usage:**
```django
{% include "ui_components/search_bar.html" with show_filters=true show_suggestions=true %}
```

### 10. Notification Dropdown (`notification_dropdown.html`)

**Features:**
- Real-time notification updates
- Notification filtering and grouping
- Mark all as read functionality
- Notification history
- WebSocket support for live updates
- Responsive design

**Usage:**
```django
{% include "ui_components/notification_dropdown.html" with show_filters=true %}
```

### 11. Dashboard Component (`dashboard.html`)

**Features:**
- Customizable widget layout
- Drag-and-drop widget arrangement
- Statistics cards with trend indicators
- Date range selector
- Export functionality
- Edit mode for layout customization

**Usage:**
```django
{% include "ui_components/dashboard.html" with editable=true show_stats_overview=true %}
```

## Design System Variables

### Colors
```scss
--color-primary: 13, 110, 253;      // Blue
--color-secondary: 108, 117, 125;    // Gray
--color-success: 25, 135, 84;        // Green
--color-warning: 255, 193, 7;         // Yellow
--color-danger: 220, 53, 69;         // Red
--color-info: 13, 202, 240;          // Light Blue
```

### Spacing
```scss
--space-1: 0.25rem;   // 4px
--space-2: 0.5rem;    // 8px
--space-3: 1rem;       // 16px
--space-4: 1.5rem;     // 24px
--space-5: 3rem;       // 48px
```

### Typography
```scss
--font-size-xs: 0.75rem;   // 12px
--font-size-sm: 0.875rem;  // 14px
--font-size-base: 1rem;     // 16px
--font-size-lg: 1.125rem;  // 18px
--font-size-xl: 1.25rem;    // 20px
--font-size-2xl: 1.5rem;   // 24px
```

## JavaScript Framework Integration

### Alpine.js
All components use Alpine.js for reactive state management and interactions:
- Component state management
- Event handling
- Conditional rendering
- Transitions and animations

### HTMX
Dynamic content loading with HTMX:
- AJAX form submissions
- Dynamic content updates
- History management
- Loading indicators

## Accessibility Features

- **ARIA Labels**: Proper labels and descriptions for screen readers
- **Keyboard Navigation**: Full keyboard support for all interactive elements
- **Focus Management**: Logical focus flow and visible focus indicators
- **Color Contrast**: WCAG AA compliant color combinations
- **Screen Reader Announcements**: Dynamic content changes announced
- **Reduced Motion**: Respects prefers-reduced-motion setting

## Responsive Design

- **Mobile-First**: Base styles for mobile, enhanced for larger screens
- **Breakpoints**: 576px (sm), 768px (md), 992px (lg), 1200px (xl)
- **Touch-Friendly**: Appropriate touch targets and gestures
- **Adaptive Layouts**: Components adapt to available space

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Graceful Degradation**: Fallbacks for older browsers
- **Progressive Enhancement**: Core functionality works everywhere

## Testing

A comprehensive test suite is available in `component_test.html`:
- Visual testing of all components
- Interaction testing
- Accessibility testing
- Responsive design testing

## Usage Guidelines

1. **Include Components**: Use Django's `{% include %}` tag
2. **Pass Context**: Use `with` parameter to customize component behavior
3. **Extend Components**: Use Django template blocks for customization
4. **Handle Events**: Listen for Alpine.js events for component interactions
5. **Style Customization**: Override CSS variables for theming

## Best Practices

1. **Consistent Usage**: Use components consistently across the application
2. **Accessibility First**: Test with screen readers and keyboard
3. **Performance**: Lazy load components when possible
4. **Error Handling**: Provide meaningful error states
5. **Documentation**: Document custom component usage

## Future Enhancements

- **Component Library**: Build standalone component library
- **Design Tokens**: Expand design system with more tokens
- **Animation Library**: Create reusable animation components
- **Testing Framework**: Implement automated component testing
- **Documentation Site**: Build comprehensive documentation site

## Contributing

When contributing to UI components:

1. Follow the existing code structure
2. Ensure accessibility compliance
3. Test on multiple devices and browsers
4. Document new features
5. Update the test suite

## Support

For questions or issues with UI components:
- Check the component documentation
- Review the test suite for examples
- Test in different browsers
- Verify accessibility compliance