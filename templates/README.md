# Template Registry

*Auto-generated on 2025-05-23 19:41:46*

## Summary

- **Total Templates**: 7
- **With Header Documentation**: 7
- **Missing Header Documentation**: 0

## Template Inventory

| Template | Location | Purpose | Used By | Dependencies |
|----------|----------|---------|---------|--------------|
| Base Layout | `base.html` | Main layout template providing consistent structure, navigation, and styling for... |  | Bootstrap CSS/JS, Bootstrap Icons, custom styles.c... |
| Discord Channel Management | `discord/channels.html` | Admin interface for configuring Discord channel monitoring and announcement sett... |  | base.html, Bootstrap components, JavaScript fetch ... |
| Discord Messages Monitor | `discord/messages.html` | Real-time monitoring dashboard for Discord messages from trading setup channels |  | base.html, Bootstrap modal components, JavaScript ... |
| Ticker Activity Monitor | `discord/tickers.html` | Analytics dashboard showing ticker activity and trading setup trends from Discor... |  | base.html, Chart.js library, Bootstrap components |
| Main Landing Page | `index.html` | Welcome page and main entry point for the A+ Trading Platform |  | base.html, Bootstrap components |
| Modal Dialog Component | `layouts/_modal.html` | Reusable modal dialog for confirmations, forms, and information display |  | base.html, Bootstrap modal JavaScript |
| Data Table Component | `layouts/_table.html` | Reusable responsive table for displaying structured data with sorting and pagina... |  | base.html, Bootstrap table classes |

## Directory Structure

```
templates/
├── base.html              # Main layout template
├── layouts/               # Shared layout components
│   ├── _modal.html        # Modal dialogs
│   ├── _table.html        # Data tables
│   └── _navigation.html   # Navigation components
├── setups/                # Trading setup views
├── trading/               # Trading interface views
└── discord/               # Discord integration views
```

## Template Best Practices

1. **Always extend base.html**: Every template should start with `{% extends "base.html" %}`
2. **Add header documentation**: Include metadata in HTML comment block at the top
3. **Use semantic naming**: Template names should clearly indicate their purpose
4. **Organize by feature**: Place templates in appropriate subdirectories
5. **Document dependencies**: List any templates this one includes or extends
6. **Keep it DRY**: Extract common elements into layout components

## Validation

Run the template validation script to check for issues:

```bash
python scripts/validate_templates.py
```

This will verify:
- All templates extend base.html
- All templates have header documentation
- No duplicate or similar template names
- Proper directory organization
