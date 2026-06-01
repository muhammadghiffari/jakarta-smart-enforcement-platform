import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

// ── Road grid ────────────────────────────────────────────
function RoadGrid() {
  const roads = useMemo(
    () => [
      { pos: [0, -0.02, 0]    as [number,number,number], rot: -0.18, scale: [8,   0.04, 1] as [number,number,number] },
      { pos: [0.2, -0.05, -1] as [number,number,number], rot:  0.4,  scale: [7.2, 0.032,1] as [number,number,number] },
      { pos: [-0.3,-0.05, 1]  as [number,number,number], rot:  1.1,  scale: [5.5, 0.028,1] as [number,number,number] },
      { pos: [0,  -0.03, 0.3] as [number,number,number], rot: -0.6,  scale: [6,   0.025,1] as [number,number,number] },
    ],
    [],
  );

  return (
    <group rotation={[-Math.PI / 2.4, 0, 0]}>
      {roads.map((r, i) => (
        <mesh key={i} position={r.pos} rotation={[0, 0, r.rot]} scale={r.scale}>
          <boxGeometry args={[1, 1, 1]} />
          <meshBasicMaterial color="#1a2030" transparent opacity={0.85} />
        </mesh>
      ))}
    </group>
  );
}

// ── Floating particle network ─────────────────────────────
function ParticleField({ count = 160 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);

  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 9;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 5;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 9;
      // Teal to cyan gradient
      const t = Math.random();
      col[i * 3]     = 0;
      col[i * 3 + 1] = 0.6 + t * 0.4;
      col[i * 3 + 2] = 0.8 + t * 0.2;
    }
    return [pos, col];
  }, [count]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.y = clock.elapsedTime * 0.04;
    ref.current.rotation.x = Math.sin(clock.elapsedTime * 0.025) * 0.08;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color"    args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.028}
        vertexColors
        transparent
        opacity={0.7}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// ── Camera node (pulsing beacon) ──────────────────────────
function CameraNode({ position, phase }: { position: [number,number,number]; phase: number }) {
  const meshRef  = useRef<THREE.Mesh>(null);
  const ringRef  = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const pulse = 1 + Math.sin(t * 2.8 + phase) * 0.18;
    if (meshRef.current)  meshRef.current.scale.setScalar(pulse);
    if (ringRef.current)  (ringRef.current.material as THREE.MeshBasicMaterial).opacity = 0.25 + Math.sin(t * 1.4 + phase) * 0.15;
    if (ring2Ref.current) ring2Ref.current.scale.setScalar(1 + Math.sin(t * 0.8 + phase) * 0.3);
  });

  return (
    <group position={position}>
      {/* Core sphere */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshBasicMaterial color="#00d4ff" />
      </mesh>
      {/* Inner ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.15, 0.18, 32]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
      {/* Outer breathing ring */}
      <mesh ref={ring2Ref} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.25, 0.27, 32]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.1} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ── Scan beam ─────────────────────────────────────────────
function ScanBeam() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!meshRef.current) return;
    const t = clock.elapsedTime;
    meshRef.current.position.y = -0.5 + Math.sin(t * 0.6) * 1.4;
    (meshRef.current.material as THREE.MeshBasicMaterial).opacity =
      0.06 + Math.abs(Math.sin(t * 0.6)) * 0.12;
  });

  return (
    <mesh ref={meshRef} rotation={[0, 0, 0]}>
      <planeGeometry args={[12, 0.08]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.1} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ── Connection lines between nodes ────────────────────────
function ConnectionLines({ nodes }: { nodes: [number,number,number][] }) {
  const geom = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    // Connect pairs
    const pairs = [
      [0,1],[1,2],[2,3],[3,4],[4,0],[0,2],[1,3],[2,4],
    ];
    for (const [a, b] of pairs) {
      if (nodes[a] && nodes[b]) {
        pts.push(new THREE.Vector3(...nodes[a]));
        pts.push(new THREE.Vector3(...nodes[b]));
      }
    }
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    return g;
  }, [nodes]);

  const matRef = useRef<THREE.LineBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (matRef.current) {
      matRef.current.opacity = 0.08 + Math.sin(clock.elapsedTime * 0.5) * 0.06;
    }
  });

  return (
    <lineSegments geometry={geom}>
      <lineBasicMaterial ref={matRef} color="#00d4ff" transparent opacity={0.1} />
    </lineSegments>
  );
}

// ── Detection quad (hovering evidence plane) ──────────────
function DetectionPlane() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.position.y = 0.55 + Math.sin(clock.elapsedTime * 1.2) * 0.06;
    ref.current.rotation.z = Math.sin(clock.elapsedTime * 0.3) * 0.04;
    (ref.current.material as THREE.MeshBasicMaterial).opacity =
      0.16 + Math.sin(clock.elapsedTime * 0.9) * 0.06;
  });

  return (
    <mesh ref={ref} position={[0.8, 0.55, -0.3]} rotation={[0.15, -0.4, 0]}>
      <planeGeometry args={[1.0, 0.52]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.18} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ── Ground plane ──────────────────────────────────────────
function GroundPlane() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
      <planeGeometry args={[18, 18]} />
      <meshBasicMaterial color="#060c18" transparent opacity={0.6} />
    </mesh>
  );
}

// ── Main scene export ─────────────────────────────────────
const NODES: [number,number,number][] = [
  [-2.2, 0.1, -1.4],
  [-0.9, 0.12,  0.9],
  [ 0.8, 0.12, -0.4],
  [ 1.9, 0.12,  1.2],
  [ 0.2, 0.12,  1.8],
];

export default function SignalScene() {
  return (
    <Canvas
      camera={{ position: [0, 3.2, 5.0], fov: 44 }}
      dpr={[1, 1.8]}
      gl={{ antialias: true, alpha: false }}
    >
      {/* Sky */}
      <color attach="background" args={['#01060f']} />
      <fog attach="fog" args={['#01060f', 5, 12]} />

      {/* Lights */}
      <ambientLight intensity={0.4} />
      <pointLight position={[0, 4, 0]} intensity={1.2} color="#00d4ff" distance={12} />
      <pointLight position={[3, 2, -3]} intensity={0.6} color="#0044aa" distance={8} />

      {/* Background stars */}
      <Stars radius={40} depth={20} count={600} factor={1.8} saturation={0.3} fade speed={0.6} />

      {/* Scene elements */}
      <GroundPlane />
      <RoadGrid />
      <ParticleField count={180} />
      <ConnectionLines nodes={NODES} />
      {NODES.map((pos, i) => (
        <CameraNode key={i} position={pos} phase={(i * Math.PI * 2) / NODES.length} />
      ))}
      <ScanBeam />
      <DetectionPlane />

      {/* Auto-rotating orbit controls */}
      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate
        autoRotateSpeed={0.6}
        maxPolarAngle={Math.PI / 2.2}
        minPolarAngle={Math.PI / 4}
        dampingFactor={0.08}
        enableDamping
      />
    </Canvas>
  );
}
