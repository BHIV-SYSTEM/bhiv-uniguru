import React from 'react';
import BubblyButton from './BubblyButton';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faHeart, faDownload, faTrash, faExclamationTriangle, faCheck } from '@fortawesome/free-solid-svg-icons';

const BubblyButtonDemo: React.FC = () => {
  return (
    <div className="relative">
      {/* Demo Container */}
      <div className="relative z-10 max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-white text-center mb-8">
          Bubbly Button Showcase
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          
          {/* Primary Variant */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Primary</h3>
            <div className="space-y-4">
              <BubblyButton variant="primary">
                Click Me!
              </BubblyButton>
              <BubblyButton variant="primary" className="w-full">
                Full Width
              </BubblyButton>
              <BubblyButton variant="primary">
                <FontAwesomeIcon icon={faHeart} className="mr-2" />
                With Icon
              </BubblyButton>
            </div>
          </div>

          {/* Secondary Variant */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Secondary</h3>
            <div className="space-y-4">
              <BubblyButton variant="secondary">
                Sign Up
              </BubblyButton>
              <BubblyButton variant="secondary" className="w-full">
                Get Started
              </BubblyButton>
              <BubblyButton variant="secondary">
                <FontAwesomeIcon icon={faDownload} className="mr-2" />
                Download
              </BubblyButton>
            </div>
          </div>

          {/* Success Variant */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Success</h3>
            <div className="space-y-4">
              <BubblyButton variant="success">
                Save Changes
              </BubblyButton>
              <BubblyButton variant="success" className="w-full">
                Complete
              </BubblyButton>
              <BubblyButton variant="success">
                <FontAwesomeIcon icon={faCheck} className="mr-2" />
                Confirm
              </BubblyButton>
            </div>
          </div>

          {/* Warning Variant */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Warning</h3>
            <div className="space-y-4">
              <BubblyButton variant="warning">
                Proceed
              </BubblyButton>
              <BubblyButton variant="warning" className="w-full">
                Update Now
              </BubblyButton>
              <BubblyButton variant="warning">
                <FontAwesomeIcon icon={faExclamationTriangle} className="mr-2" />
                Warning
              </BubblyButton>
            </div>
          </div>

          {/* Danger Variant */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Danger</h3>
            <div className="space-y-4">
              <BubblyButton variant="danger">
                Delete
              </BubblyButton>
              <BubblyButton variant="danger" className="w-full">
                Remove All
              </BubblyButton>
              <BubblyButton variant="danger">
                <FontAwesomeIcon icon={faTrash} className="mr-2" />
                Delete Forever
              </BubblyButton>
            </div>
          </div>

          {/* Disabled States */}
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-xl font-semibold text-white mb-4">Disabled</h3>
            <div className="space-y-4">
              <BubblyButton variant="primary" disabled>
                Disabled Primary
              </BubblyButton>
              <BubblyButton variant="secondary" disabled>
                Disabled Secondary
              </BubblyButton>
              <BubblyButton variant="success" disabled>
                Disabled Success
              </BubblyButton>
            </div>
          </div>

        </div>

        <div className="mt-12 text-center">
          <p className="text-gray-400 text-lg mb-4">
            ✨ Click any button to see tiny star-like bubbles sparkle!
          </p>
          <p className="text-gray-500 text-sm mb-2">
            🌟 Features: Subtle hover effects, tiny star bubbles (2-6px), and smooth GSAP animations
          </p>
          <p className="text-gray-500 text-sm">
            Inspired by the CodePen: https://codepen.io/nourabusoud/pen/ypZzMM
          </p>
        </div>
      </div>
    </div>
  );
};

export default BubblyButtonDemo;
