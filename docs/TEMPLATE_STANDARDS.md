# Template Standards - A+ Trading App

## Required Template Structure

All new HTML templates MUST follow this pattern:

```html
{% extends "base.html" %}
{% block title %}Page Title - A+ Trading{% endblock %}

{% block content %}
    <!-- Your page content here -->
{% endblock %}

{% block extra_js %}
    <script>
        // Your JavaScript here
    </script>
{% endblock %}
```

## Navigation Integration

- All new features must be added to the main navigation in `templates/base.html`
- Use dropdown menus for grouped features (like Discord admin)
- Never create standalone navigation systems

## Database Query Standards

- Always check actual database schema before writing queries
- Use `information_schema.columns` to verify column existence
- Document any schema assumptions in code comments

## Styling Rules

- Use existing Bootstrap theme from `base.html`
- Never import different Bootstrap versions
- Leverage existing CSS classes and custom styles
- Test in dark theme (default app theme)

## Checklist for New Features

- [ ] Templates extend `base.html`
- [ ] Navigation updated in main menu
- [ ] Database queries match actual schema
- [ ] Consistent styling with existing app
- [ ] Error handling implemented
- [ ] Testing completed in integrated environment