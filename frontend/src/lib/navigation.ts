/**
 * Centralized navigation items to ensure consistency across:
 * - StitchSidebar (desktop)
 * - StitchMobileDrawer (mobile)
 * - Any other navigation components
 */

export interface NavItem {
  path: string;
  icon: string;
  labelKey: string; // i18n key
}

export const mainNavItems: NavItem[] = [
  { path: '/', icon: 'search', labelKey: 'nav.newThread' },
  { path: '/history', icon: 'folder_open', labelKey: 'nav.library' },
];

export const bottomNavItems: NavItem[] = [
  { path: '/settings', icon: 'settings', labelKey: 'nav.settings' },
];
