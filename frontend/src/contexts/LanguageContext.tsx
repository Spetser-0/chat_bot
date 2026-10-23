import { createContext, useState, useEffect, type ReactNode } from 'react';

export type Language = 'ar' | 'en';

export interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const translations: Record<Language, Record<string, string>> = {
  ar: {
    'settings.title': 'الإعدادات',
    'settings.desc': 'إدارة ملفك الشخصي وتفضيلاتك',
    'settings.profile': 'الملف الشخصي',
    'settings.name': 'الاسم',
    'settings.email': 'البريد الإلكتروني',
    'settings.appearance': 'المظهر',
    'settings.language': 'اللغة',
    'settings.credits': 'الرصيد',
    'settings.creditsUnit': 'نقطة',
    'settings.lowCredits': 'رصيد منخفض',
    'settings.creditsNote': 'سيتم تفعيل الرصيد اليومي المجاني في التحديث القادم.',
    'settings.account': 'الحساب',
    'settings.logout': 'تسجيل الخروج',
    'settings.backHome': 'العودة إلى الرئيسية',
    'settings.darkMode': 'الوضع الليلي',
    'settings.lightMode': 'الوضع النهاري',
    'language.arabic': 'العربية',
    'language.english': 'English',
    'nav.newThread': 'محادثة جديدة',
    'nav.discover': 'استكشاف',
    'nav.spaces': 'المساحات',
    'nav.library': 'المكتبة',
    'nav.workspace': 'مساحة العمل',
    'nav.threads': 'المحادثات',
    'nav.noThreads': 'لا توجد محادثات نشطة',
    'nav.recent': 'الأحدث',
    'nav.settings': 'الإعدادات',
    'nav.accountSettings': 'إعدادات الحساب',
    'nav.signOut': 'تسجيل الخروج',
    'nav.signIn': 'تسجيل الدخول',
    'nav.freePlan': 'الخطة المجانية',
  },
  en: {
    'settings.title': 'Settings',
    'settings.desc': 'Manage your profile and preferences',
    'settings.profile': 'Profile',
    'settings.name': 'Name',
    'settings.email': 'Email',
    'settings.appearance': 'Appearance',
    'settings.language': 'Language',
    'settings.credits': 'Credits',
    'settings.creditsUnit': 'credits',
    'settings.lowCredits': 'Low credits',
    'settings.creditsNote': 'Free daily credits will be enabled in the upcoming update.',
    'settings.account': 'Account',
    'settings.logout': 'Sign Out',
    'settings.backHome': 'Back to Home',
    'settings.darkMode': 'Dark Mode',
    'settings.lightMode': 'Light Mode',
    'language.arabic': 'العربية',
    'language.english': 'English',
    'nav.newThread': 'New Thread',
    'nav.discover': 'Discover',
    'nav.spaces': 'Spaces',
    'nav.library': 'Library',
    'nav.workspace': 'Workspace',
    'nav.threads': 'Threads',
    'nav.noThreads': 'No active threads',
    'nav.recent': 'Recent',
    'nav.settings': 'Settings',
    'nav.accountSettings': 'Account Settings',
    'nav.signOut': 'Sign Out',
    'nav.signIn': 'Sign In',
    'nav.freePlan': 'Free Plan',
  },
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    try {
      const stored = localStorage.getItem('spetser.language');
      return stored === 'ar' || stored === 'en' ? stored : 'ar';
    } catch {
      return 'ar';
    }
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem('spetser.language', lang);
    } catch {
      /* ignore */
    }

    // Update HTML attributes
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  };

  const t = (key: string): string => {
    return translations[language]?.[key] || translations['ar']?.[key] || key;
  };

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export { LanguageContext };
