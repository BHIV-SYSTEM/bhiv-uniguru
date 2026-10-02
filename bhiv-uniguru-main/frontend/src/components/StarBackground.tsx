"use client";

import React, { useState, useRef, Suspense } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";
import * as random from "maath/random/dist/maath-random.esm";

const StarBackground: React.FC = () => {
  const ref = useRef<THREE.Points>(null);
  const [sphere] = useState<Float32Array>(() =>
    random.inSphere(new Float32Array(5000 * 3), { radius: 1.9 })
  );

  useFrame((_state, delta) => {
    if (ref.current) {
      ref.current.rotation.x -= delta / 10;
      ref.current.rotation.y -= delta / 25;
    }
  });

  return (
    <group rotation={[0, 0, Math.PI / 4]}>
      <Points
        ref={ref}
        positions={sphere}
        stride={3}
        frustumCulled
      >
        <PointMaterial
          transparent
          color="#ffffff"
          size={0.0029}
          sizeAttenuation
          depthWrite={false}
        />
      </Points>
    </group>
  );
};

const StarsCanvas: React.FC = () => (
  <Canvas
    camera={{ position: [0, 0, 1] }}
    style={{
      background: "#1B0725",
      position: "absolute",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      zIndex: 0
    }}
  >
    <Suspense fallback={null}>
      <StarBackground />
    </Suspense>
  </Canvas>
);

export default StarsCanvas;
