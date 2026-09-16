import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import './BubblyButton.css';

interface BubblyButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger';
  style?: React.CSSProperties;
}

const BubblyButton: React.FC<BubblyButtonProps> = ({
  children,
  onClick,
  className = '',
  disabled = false,
  type = 'button',
  variant = 'primary',
  style
}) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  // const bubblesRef = useRef<HTMLDivElement[]>([]);
  const isAnimating = useRef(false);

  useEffect(() => {
    const button = buttonRef.current;
    if (!button) return;

    const handleMouseEnter = () => {
      if (!disabled) {
        gsap.to(button, {
          scale: 1.05,
          duration: 0.3,
          ease: "power2.out"
        });
      }
    };

    const handleMouseLeave = () => {
      if (!disabled) {
        gsap.to(button, {
          scale: 1,
          duration: 0.3,
          ease: "power2.out"
        });
      }
    };

    button.addEventListener('mouseenter', handleMouseEnter);
    button.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      button.removeEventListener('mouseenter', handleMouseEnter);
      button.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [disabled]);

  const createBubble = (x: number, y: number, delay: number = 0) => {
    if (!buttonRef.current) return;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Much smaller bubbles - like tiny stars
    const size = Math.random() * 4 + 2; // 2-6px instead of 10-30px
    const colors = getVariantColors();
    const color = colors[Math.floor(Math.random() * colors.length)];

    bubble.style.cssText = `
      position: absolute;
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      border-radius: 50%;
      pointer-events: none;
      z-index: 1000;
      left: ${x - size/2}px;
      top: ${y - size/2}px;
      opacity: 0;
      box-shadow: 0 0 ${size * 2}px ${color}40;
    `;

    buttonRef.current.appendChild(bubble);

    // GSAP animation with stagger and easing - more subtle like stars
    gsap.timeline({ delay })
      .to(bubble, {
        opacity: 0.8,
        scale: 1,
        duration: 0.1,
        ease: "power2.out"
      })
      .to(bubble, {
        y: -40 - Math.random() * 30,
        x: (Math.random() - 0.5) * 50,
        opacity: 0,
        scale: 0.5,
        duration: 1.2,
        ease: "power2.out",
        onComplete: () => {
          if (bubble.parentNode) {
            bubble.parentNode.removeChild(bubble);
          }
        }
      }, 0.05);
  };

  const animateButton = (_e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || isAnimating.current) return;

    isAnimating.current = true;
    const rect = buttonRef.current!.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    // Button press animation
    gsap.timeline()
      .to(buttonRef.current, {
        scale: 0.95,
        duration: 0.1,
        ease: "power2.out"
      })
      .to(buttonRef.current, {
        scale: 1,
        duration: 0.2,
        ease: "elastic.out(1, 0.5)"
      });

    // Create multiple small bubbles with staggered timing - like tiny stars
    const bubbleCount = 20; // More bubbles but much smaller
    for (let i = 0; i < bubbleCount; i++) {
      const angle = (i / bubbleCount) * Math.PI * 2;
      const radius = 10 + Math.random() * 25; // Closer to button center
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      const delay = i * 0.02; // Faster stagger for more sparkle effect

      setTimeout(() => createBubble(x, y, delay), i * 15);
    }

    // Add some random scattered bubbles for extra sparkle
    const extraBubbles = 8;
    for (let i = 0; i < extraBubbles; i++) {
      const x = centerX + (Math.random() - 0.5) * 60;
      const y = centerY + (Math.random() - 0.5) * 40;
      const delay = Math.random() * 0.3;

      setTimeout(() => createBubble(x, y, delay), (bubbleCount + i) * 10);
    }

    // Reset animation flag
    setTimeout(() => {
      isAnimating.current = false;
    }, 800);

    // Call original onClick
    if (onClick) {
      onClick();
    }
  };

  const getVariantClass = () => {
    switch (variant) {
      case 'primary':
        return 'bubbly-button-primary';
      case 'secondary':
        return 'bubbly-button-secondary';
      case 'success':
        return 'bubbly-button-success';
      case 'warning':
        return 'bubbly-button-warning';
      case 'danger':
        return 'bubbly-button-danger';
      default:
        return 'bubbly-button-primary';
    }
  };

  const getVariantColors = () => {
    switch (variant) {
      case 'primary':
        return ['#4a8bc7', '#7a6bc4', '#9560b8', '#7a73b8', '#5fa0a8', '#47b399'];
      case 'secondary':
        return ['#d4a01c', '#cc7f08', '#b56b05', '#8f4f07'];
      case 'success':
        return ['#0b8a5a', '#046647', '#03523d', '#044532'];
      case 'warning':
        return ['#cc5a0f', '#b8460a', '#9c3409', '#7a280a'];
      case 'danger':
        return ['#c73030', '#a61b1b', '#8f1414', '#731212'];
      default:
        return ['#4a8bc7', '#7a6bc4', '#9560b8', '#7a73b8', '#5fa0a8', '#47b399'];
    }
  };

  return (
    <button
      ref={buttonRef}
      type={type}
      onClick={animateButton}
      disabled={disabled}
      style={{ ...style, position: 'relative', overflow: 'visible' }}
      className={`bubbly-button ${getVariantClass()} ${className}`}
    >
      {children}
    </button>
  );
};

export default BubblyButton;
