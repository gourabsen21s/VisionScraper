'use client';

import dynamic from 'next/dynamic';
import { ChatInterface } from '@/components';

const ColorBends = dynamic(() => import('@/components/ColorBends'), {
  ssr: false,
  loading: () => <div className="fixed inset-0 bg-black" />
});

export default function Home() {
  return (
    <main className="relative min-h-screen w-full overflow-hidden">
      {/* Animated Background - More vibrant */}
      <div className="fixed inset-0 z-0">
        <ColorBends
          colors={["#ff3366", "#6633ff", "#00ffcc", "#ff6600", "#33ccff"]}
          rotation={25}
          speed={0.25}
          scale={0.9}
          frequency={1.2}
          warpStrength={1.5}
          mouseInfluence={0.6}
          parallax={0.5}
          noise={0.05}
          transparent={false}
        />
      </div>

      {/* Subtle vignette for depth - much lighter */}
      <div className="fixed inset-0 z-10 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.3)_100%)]" />

      {/* Main Content */}
      <div className="relative z-20 flex flex-col h-screen items-center justify-center">
        <ChatInterface />
      </div>
    </main>
  );
}
