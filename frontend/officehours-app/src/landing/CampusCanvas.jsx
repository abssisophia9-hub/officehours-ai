import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { FIGURES, HELP_PATH, cameraForProgress } from "./helpPath.js";

const LOOK = new THREE.Vector3();
const POINT = new THREE.Vector3();
const TANGENT = new THREE.Vector3();

function GableHall({ position, w = 2.4, d = 1.8, h = 1.7, yaw = 0, wall = "#efe3cc" }) {
  return (
    <group position={position} rotation={[0, yaw, 0]}>
      <mesh position={[0, h / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[w, h, d]} />
        <meshStandardMaterial color={wall} roughness={0.82} />
      </mesh>
      <mesh position={[0, h + 0.58, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
        <coneGeometry args={[Math.max(w, d) * 0.74, 1.16, 4]} />
        <meshStandardMaterial color="#c2573a" roughness={0.7} />
      </mesh>
    </group>
  );
}

function Cedar({ position, scale = 1 }) {
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 0.35, 0]} castShadow>
        <cylinderGeometry args={[0.08, 0.11, 0.7, 6]} />
        <meshStandardMaterial color="#5c3d28" roughness={0.9} />
      </mesh>
      <mesh position={[0, 1.15, 0]} castShadow>
        <coneGeometry args={[0.72, 1.5, 7]} />
        <meshStandardMaterial color="#1f4a34" roughness={0.75} />
      </mesh>
      <mesh position={[0, 1.85, 0]} castShadow>
        <coneGeometry args={[0.48, 1.05, 7]} />
        <meshStandardMaterial color="#2a6a48" roughness={0.75} />
      </mesh>
    </group>
  );
}

function Lamp({ position }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.7, 0]} castShadow>
        <cylinderGeometry args={[0.045, 0.055, 1.4, 8]} />
        <meshStandardMaterial color="#3d4a40" metalness={0.35} roughness={0.45} />
      </mesh>
      <mesh position={[0, 1.48, 0]}>
        <sphereGeometry args={[0.11, 10, 10]} />
        <meshStandardMaterial
          color="#fff4d2"
          emissive="#ffe7a3"
          emissiveIntensity={1.4}
        />
      </mesh>
      <pointLight position={[0, 1.48, 0]} color="#ffe7a3" intensity={0.55} distance={4.5} />
    </group>
  );
}

function Plaza({ position, radius = 1.55, color = "#e7dcc6" }) {
  return (
    <mesh position={position} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <circleGeometry args={[radius, 28]} />
      <meshStandardMaterial color={color} roughness={0.9} />
    </mesh>
  );
}

function Person({ position, kind, progressRef, glowFrom = [0, 1, 1, 1] }) {
  const group = useRef();
  const halo = useRef();
  const badge = useRef();
  const palette =
    kind === "student"
      ? { body: "#c45c48", pants: "#3d4a40", accent: "#efe3cc" }
      : kind === "ta"
        ? { body: "#1f8a5b", pants: "#24352c", accent: "#f4efe6" }
        : { body: "#146345", pants: "#1b2f26", accent: "#f0e4ce" };

  useFrame(({ clock }) => {
    if (!group.current) return;
    const bob = Math.sin(clock.elapsedTime * 1.6 + position[0]) * 0.025;
    group.current.position.y = position[1] + bob;
    group.current.rotation.y = Math.sin(clock.elapsedTime * 0.5 + position[2]) * 0.08;
    const p = progressRef?.current ?? 0;
    const hl =
      THREE.MathUtils.smoothstep(p, glowFrom[0], glowFrom[1]) *
      (1 - THREE.MathUtils.smoothstep(p, glowFrom[2], glowFrom[3]));
    if (halo.current) halo.current.material.opacity = 0.12 + hl * 0.22;
    if (badge.current) badge.current.material.emissiveIntensity = 0.55 + hl * 1.1;
  });

  return (
    <group ref={group} position={position}>
      <mesh position={[-0.12, 0.28, 0.02]} castShadow>
        <capsuleGeometry args={[0.07, 0.38, 4, 8]} />
        <meshStandardMaterial color={palette.pants} roughness={0.7} />
      </mesh>
      <mesh position={[0.12, 0.28, 0.02]} castShadow>
        <capsuleGeometry args={[0.07, 0.38, 4, 8]} />
        <meshStandardMaterial color={palette.pants} roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.92, 0]} castShadow>
        <capsuleGeometry args={[0.22, 0.42, 4, 10]} />
        <meshStandardMaterial color={palette.body} roughness={0.55} />
      </mesh>
      <mesh position={[0, 1.42, 0.02]} castShadow>
        <sphereGeometry args={[0.18, 16, 16]} />
        <meshStandardMaterial color="#e2b089" roughness={0.55} />
      </mesh>
      {kind === "student" ? (
        <mesh position={[0, 1.02, -0.22]} castShadow>
          <boxGeometry args={[0.28, 0.32, 0.12]} />
          <meshStandardMaterial color="#3a332c" roughness={0.7} />
        </mesh>
      ) : null}
      {kind === "ta" ? (
        <mesh ref={badge} position={[0.02, 1.08, 0.22]} castShadow>
          <boxGeometry args={[0.16, 0.12, 0.03]} />
          <meshStandardMaterial color="#d4f58a" emissive="#b6e85c" emissiveIntensity={0.6} />
        </mesh>
      ) : null}
      {kind === "professor" ? (
        <mesh position={[0.28, 0.95, 0.12]} rotation={[0.15, -0.4, 0.2]} castShadow>
          <boxGeometry args={[0.18, 0.24, 0.05]} />
          <meshStandardMaterial color="#f4efe6" roughness={0.5} />
        </mesh>
      ) : null}
      <mesh ref={halo} position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.42, 16]} />
        <meshBasicMaterial color="#1f8a5b" transparent opacity={0.12} />
      </mesh>
    </group>
  );
}

function AskCards({ origin }) {
  const ref = useRef();
  const cards = useMemo(
    () => [
      { x: -0.85, z: 0.55, y: 0.95, rot: 0.4, color: "#fff8e8" },
      { x: 0.95, z: 0.2, y: 1.25, rot: -0.35, color: "#e8f6ef" },
      { x: -0.15, z: 1.05, y: 1.55, rot: 0.15, color: "#dff3ff" },
    ],
    [],
  );
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.children.forEach((child, i) => {
      child.position.y = cards[i].y + Math.sin(clock.elapsedTime * 1.2 + i) * 0.08;
      child.rotation.z = cards[i].rot + Math.sin(clock.elapsedTime * 0.6 + i) * 0.05;
    });
  });
  return (
    <group ref={ref} position={origin}>
      {cards.map((card) => (
        <mesh key={`${card.x}-${card.z}`} position={[card.x, card.y, card.z]} castShadow>
          <boxGeometry args={[0.55, 0.38, 0.03]} />
          <meshStandardMaterial color={card.color} roughness={0.45} />
        </mesh>
      ))}
    </group>
  );
}

function QueueCards({ origin }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.children.forEach((child, i) => {
      const t = (clock.elapsedTime * 0.18 + i * 0.2) % 1;
      child.position.set(-0.9 + t * 1.6, 0.85 + i * 0.08, 0.55 - t * 0.9);
    });
  });
  return (
    <group ref={ref} position={origin}>
      {Array.from({ length: 5 }, (_, i) => (
        <mesh key={i} castShadow>
          <boxGeometry args={[0.42, 0.28, 0.025]} />
          <meshStandardMaterial
            color={i % 2 ? "#fff3d1" : "#d9f5e8"}
            transparent
            opacity={0.92}
          />
        </mesh>
      ))}
    </group>
  );
}

function ClusterConstellation({ origin }) {
  const points = useMemo(
    () => [
      new THREE.Vector3(-0.7, 1.35, 0.2),
      new THREE.Vector3(0.15, 1.7, -0.15),
      new THREE.Vector3(0.75, 1.25, 0.35),
      new THREE.Vector3(0.05, 0.95, 0.55),
      new THREE.Vector3(-0.35, 1.15, -0.45),
    ],
    [],
  );
  const line = useMemo(() => {
    const verts = [];
    const links = [
      [0, 1],
      [1, 2],
      [1, 3],
      [0, 4],
      [4, 1],
    ];
    links.forEach(([a, b]) => {
      verts.push(points[a].x, points[a].y, points[a].z, points[b].x, points[b].y, points[b].z);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    return geo;
  }, [points]);
  const orbs = useRef();
  useFrame(({ clock }) => {
    if (!orbs.current) return;
    orbs.current.rotation.y = Math.sin(clock.elapsedTime * 0.25) * 0.15;
  });
  return (
    <group position={origin}>
      <lineSegments geometry={line}>
        <lineBasicMaterial color="#9be07a" transparent opacity={0.7} />
      </lineSegments>
      <group ref={orbs}>
        {points.map((p, i) => (
          <mesh key={i} position={p}>
            <sphereGeometry args={[0.09 + (i === 1 ? 0.04 : 0), 12, 12]} />
            <meshStandardMaterial
              color="#d4f58a"
              emissive="#8fd15c"
              emissiveIntensity={0.9}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}

function HelpPath() {
  return (
    <group>
      <mesh receiveShadow>
        <tubeGeometry args={[HELP_PATH, 96, 0.2, 10, false]} />
        <meshStandardMaterial color="#efe6d4" roughness={0.88} />
      </mesh>
      <mesh>
        <tubeGeometry args={[HELP_PATH, 96, 0.28, 8, false]} />
        <meshBasicMaterial color="#c6f07a" transparent opacity={0.18} />
      </mesh>
    </group>
  );
}

function PathBeacon({ progressRef }) {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = THREE.MathUtils.clamp(progressRef.current * 0.92 + 0.04, 0.02, 0.98);
    HELP_PATH.getPointAt(t, POINT);
    HELP_PATH.getTangentAt(t, TANGENT);
    ref.current.position.copy(POINT);
    ref.current.position.y += 0.32 + Math.sin(clock.elapsedTime * 3) * 0.04;
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.13, 16, 16]} />
      <meshStandardMaterial
        color="#eaffb0"
        emissive="#b8f06c"
        emissiveIntensity={2.2}
      />
    </mesh>
  );
}

function FlowOrbs() {
  const refs = useRef([]);
  useFrame(({ clock }) => {
    refs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const t = (clock.elapsedTime * 0.07 + i * 0.22) % 1;
      HELP_PATH.getPointAt(t, POINT);
      mesh.position.copy(POINT);
      mesh.position.y += 0.22;
    });
  });
  return (
    <group>
      {Array.from({ length: 4 }, (_, i) => (
        <mesh
          key={i}
          ref={(node) => {
            refs.current[i] = node;
          }}
        >
          <sphereGeometry args={[0.055, 10, 10]} />
          <meshStandardMaterial
            color="#fff8d6"
            emissive="#ffe08a"
            emissiveIntensity={1.1}
          />
        </mesh>
      ))}
    </group>
  );
}

function Fireflies() {
  const ref = useRef();
  const positions = useMemo(() => {
    const arr = new Float32Array(90);
    for (let i = 0; i < 30; i += 1) {
      arr[i * 3] = (Math.random() - 0.35) * 16;
      arr[i * 3 + 1] = 0.4 + Math.random() * 4.5;
      arr[i * 3 + 2] = (Math.random() - 0.45) * 18;
    }
    return arr;
  }, []);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.y = clock.elapsedTime * 0.02;
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#d4f58a" size={0.07} transparent opacity={0.55} />
    </points>
  );
}

function CameraRig({ progressRef, reducedMotion }) {
  const { camera, size } = useThree();
  const look = useRef(new THREE.Vector3(3, 1.2, 4));
  useFrame((_, delta) => {
    const mobile = size.width < 840;
    const p = reducedMotion ? 0.14 : progressRef.current;
    const target = cameraForProgress(p, mobile);
    const k = 1 - Math.exp(-delta * 3.2);
    camera.position.lerp(target.position, k);
    look.current.lerp(target.look, k);
    LOOK.copy(look.current);
    camera.lookAt(LOOK);
  });
  return null;
}

function CampusWorld({ progressRef, reducedMotion }) {
  return (
    <>
      <color attach="background" args={["#e8f0e6"]} />
      <fog attach="fog" args={["#e8f0e6", 16, 38]} />
      <hemisphereLight args={["#f7f1e3", "#6d8a74", 0.72]} />
      <directionalLight
        position={[-7, 12, 6]}
        intensity={1.55}
        color="#fff3d6"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-camera-near={1}
        shadow-camera-far={40}
        shadow-camera-left={-14}
        shadow-camera-right={14}
        shadow-camera-top={14}
        shadow-camera-bottom={-14}
      />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[1.5, 0, -1]} receiveShadow>
        <circleGeometry args={[22, 48]} />
        <meshStandardMaterial color="#c5d9c4" roughness={0.95} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[2.4, 0.01, 1]} receiveShadow>
        <circleGeometry args={[11, 40]} />
        <meshStandardMaterial color="#b7cdae" roughness={0.96} />
      </mesh>

      <GableHall position={[-3.4, 0, 6.4]} w={2.8} d={2.1} h={1.9} yaw={0.35} />
      <GableHall position={[-5.2, 0, 1.2]} w={2.2} d={3.2} h={2.2} yaw={-0.4} wall="#f6ead6" />
      <GableHall position={[8.1, 0, 4.6]} w={2.4} d={1.7} h={1.6} yaw={-0.55} />
      <GableHall position={[7.4, 0, -2.8]} w={3.1} d={2.0} h={2.0} yaw={0.7} />
      <GableHall position={[-3.8, 0, -6.6]} w={2.6} d={2.4} h={1.8} yaw={0.2} />
      <GableHall position={[5.6, 0.32, -10.4]} w={2.9} d={2.2} h={1.7} yaw={-0.25} />

      <Cedar position={[-1.6, 0, 9.2]} scale={1.15} />
      <Cedar position={[-2.4, 0, 8.1]} scale={0.85} />
      <Cedar position={[6.4, 0, 8.8]} scale={1.05} />
      <Cedar position={[7.2, 0, 1.1]} scale={0.9} />
      <Cedar position={[-1.1, 0, -2.4]} scale={1.2} />
      <Cedar position={[6.8, 0, -6.2]} scale={1.1} />
      <Cedar position={[-2.6, 0, -9.4]} scale={0.95} />
      <Cedar position={[3.8, 0.32, -11.6]} scale={0.8} />

      <Lamp position={[2.15, 0, 6.35]} />
      <Lamp position={[5.15, 0, 2.55]} />
      <Lamp position={[2.35, 0, -1.55]} />
      <Lamp position={[0.35, 0.32, -8.2]} />

      <Plaza position={[3.2, 0.02, 7.6]} />
      <Plaza position={[3.55, 0.02, -0.7]} radius={1.35} color="#eadfc8" />
      <Plaza position={[1.35, 0.34, -9.15]} radius={1.45} color="#e4d7bc" />

      <HelpPath />
      <PathBeacon progressRef={progressRef} />
      {reducedMotion ? null : <FlowOrbs />}
      <Fireflies />

      <Person
        position={[FIGURES.student.x, FIGURES.student.y, FIGURES.student.z]}
        kind="student"
        progressRef={progressRef}
        glowFrom={[0.08, 0.16, 0.34, 0.44]}
      />
      <AskCards origin={[FIGURES.student.x, 0, FIGURES.student.z]} />

      <Person
        position={[FIGURES.ta.x, FIGURES.ta.y, FIGURES.ta.z]}
        kind="ta"
        progressRef={progressRef}
        glowFrom={[0.4, 0.5, 0.62, 0.72]}
      />
      <QueueCards origin={[FIGURES.ta.x, 0, FIGURES.ta.z]} />

      <Person
        position={[FIGURES.professor.x, FIGURES.professor.y, FIGURES.professor.z]}
        kind="professor"
        progressRef={progressRef}
        glowFrom={[0.68, 0.8, 1.2, 1.3]}
      />
      <ClusterConstellation origin={[FIGURES.professor.x, FIGURES.professor.y, FIGURES.professor.z]} />

      <CameraRig progressRef={progressRef} reducedMotion={reducedMotion} />
    </>
  );
}

export default function CampusCanvas({ progressRef, reducedMotion }) {
  return (
    <Canvas
      className="oh-land-canvas"
      shadows
      dpr={[1, 1.6]}
      style={{ position: "fixed", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
        toneMapping: THREE.ACESFilmicToneMapping,
      }}
      camera={{ fov: 42, near: 0.1, far: 70, position: [-1.6, 6.8, 14.2] }}
      aria-hidden="true"
    >
      <CampusWorld progressRef={progressRef} reducedMotion={reducedMotion} />
    </Canvas>
  );
}
