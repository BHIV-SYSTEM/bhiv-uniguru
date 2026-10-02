/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{html,js,jsx,ts,tsx}",  // Add file extensions as needed
  ],
  theme: {
    screens: {
      'xs': '475px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
      // Mobile-first breakpoints
      'mobile': {'max': '640px'},
      'tablet': {'min': '641px', 'max': '1024px'},
      'desktop': {'min': '1025px'},
      // Touch device detection
      'touch': {'raw': '(hover: none) and (pointer: coarse)'},
      'no-touch': {'raw': '(hover: hover) and (pointer: fine)'},
    },
    extend: {
      colors: {
        // Glassmorphism card colors (only for the card, not background)
        glass: {
          card: 'rgba(255, 255, 255, 0.13)', // Glass card background
          border: 'rgba(255, 255, 255, 0.1)', // Glass card border
          input: 'rgba(255, 255, 255, 0.07)', // Input background
          sidebar: 'rgba(26, 26, 46, 0.95)', // Sidebar background
          'sidebar-light': 'rgba(255, 255, 255, 0.05)', // Light sidebar elements
          'sidebar-border': 'rgba(255, 255, 255, 0.1)', // Sidebar borders
        },
        // Text colors for glassmorphism
        text: {
          glass: '#ffffff', // White text on glass
          placeholder: '#e5e5e5', // Placeholder text
          button: '#080710', // Dark text on white button
        }
      },
      fontFamily: {
        // Poppins font (matching CodePen)
        'poppins': ['Poppins', 'sans-serif'],
        'inder': ['Inder', 'sans-serif'],
        'inknut': ['Inknut Antiqua', 'serif'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'glass': '10px', // Glass card border radius
      },
      boxShadow: {
        // Glassmorphism shadows (matching CodePen)
        'glass': '0 0 40px rgba(8, 7, 16, 0.6)',
      },
      backdropBlur: {
        'glass': '10px', // Glass backdrop blur
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'float': 'float 6s ease-in-out infinite',
        'gradient': 'gradient-shift 4s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite',
        'gradient-advanced': 'gradient-shift-advanced 3s ease infinite',
        'mega-pulse': 'mega-pulse-glow 2s ease-in-out infinite',
        'sparkle-float': 'sparkle-float 3s ease-in-out infinite',
        'text-glow': 'text-glow 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
      },
    },
  },
  plugins: [],
}

