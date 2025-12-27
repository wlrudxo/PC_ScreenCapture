/**
 * Theme store - localStorage 기반 다크/라이트 테마 관리
 */
import { writable } from 'svelte/store';

const STORAGE_KEY = 'activity-tracker-theme';

function createThemeStore() {
  // 초기값: localStorage에서 로드, 없으면 'dark' (기본값)
  const getInitialTheme = () => {
    if (typeof window === 'undefined') return 'dark';
    return localStorage.getItem(STORAGE_KEY) || 'dark';
  };

  const { subscribe, set, update } = writable(getInitialTheme());

  return {
    subscribe,

    /**
     * 테마 설정
     * @param {'light' | 'dark'} newTheme
     */
    set: (newTheme) => {
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, newTheme);
        applyTheme(newTheme);
      }
      set(newTheme);
    },

    /**
     * 테마 토글
     */
    toggle: () => {
      update(current => {
        const newTheme = current === 'dark' ? 'light' : 'dark';
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, newTheme);
          applyTheme(newTheme);
        }
        return newTheme;
      });
    },

    /**
     * 초기화 (앱 시작 시 호출)
     */
    init: () => {
      if (typeof window === 'undefined') return;
      const savedTheme = localStorage.getItem(STORAGE_KEY) || 'dark';
      applyTheme(savedTheme);
      set(savedTheme);
    }
  };
}

/**
 * HTML에 테마 클래스 적용
 */
function applyTheme(theme) {
  if (typeof document === 'undefined') return;

  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export const theme = createThemeStore();
