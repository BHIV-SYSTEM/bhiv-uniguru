import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  en: {
    translation: {
      helper: 'Helper',
      enableHelperUI: 'Enable helper UI',
      disableHelperUI: 'Disable helper UI',
      about: 'About',
      login: 'Login',
      signup: 'Sign Up',
      logout: 'Logout',
      gurus: 'Gurus',
      chats: 'Chats',
      createGuru: 'Create Guru',
      newChat: 'New Chat',
      creating: 'Creating...',
      startNewChat: 'Start New Chat',
      navigation: 'Navigation',
      account: 'Account',
      language: 'Language',
      learnMoreAbout: 'Learn more about UniGuru',
      accessYourAccount: 'Access your account',
      createNewAccount: 'Create new account',
      signOutOfYourAccount: 'Sign out of your account',
      selectGuruFirst: 'Select a guru first'
    }
  },
  hi: {
    translation: {
      helper: 'सहायक',
      enableHelperUI: 'सहायक UI सक्षम करें',
      disableHelperUI: 'सहायक UI अक्षम क���ें',
      about: 'परिचय',
      login: 'लॉगिन',
      signup: 'साइन अप',
      logout: 'लॉगआउट',
      gurus: 'गुरु',
      chats: 'चैट्स',
      createGuru: 'गुरु बनाएं',
      newChat: 'नई चैट',
      creating: 'बना रहा है...',
      startNewChat: 'नई चैट शुरू करें',
      navigation: 'नेविगेशन',
      account: 'खाता',
      language: 'भाषा',
      learnMoreAbout: 'UniGuru के बारे में अधिक जानें',
      accessYourAccount: 'अपने खाते तक पहुंचें',
      createNewAccount: 'नया खाता बनाएं',
      signOutOfYourAccount: 'अपने खाते से साइन आउट करें',
      selectGuruFirst: 'पहले एक गुरु चुनें'
    }
  },
  mr: {
    translation: {
      helper: 'मदतनीस',
      enableHelperUI: 'मदतनीस UI सक्षम करा',
      disableHelperUI: 'मदतनीस UI अक्षम करा',
      about: 'विषयी',
      login: 'लॉगिन',
      signup: 'साइन अप',
      logout: 'लॉगआउट',
      gurus: 'गुरू',
      chats: 'चॅट्स',
      createGuru: 'गुरू तयार करा',
      newChat: 'नवीन चॅट',
      creating: 'तयार करत आहे...',
      startNewChat: 'नवीन चॅट सुरू करा',
      navigation: 'नेव्हिगेशन',
      account: 'खाते',
      language: 'भाषा',
      learnMoreAbout: 'UniGuru बद्दल अधिक जाणून घ्या',
      accessYourAccount: 'तुमच्या खात्यात प्रवेश करा',
      createNewAccount: 'नवीन खाते तयार करा',
      signOutOfYourAccount: 'तुमच्या खात्यातून साइन आउट करा',
      selectGuruFirst: 'प्रथम एक गुरू निवडा'
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'hi', 'mr'],
    detection: {
      order: ['localStorage', 'querystring', 'navigator', 'htmlTag'],
      caches: ['localStorage']
    },
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
