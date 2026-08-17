import * as THREE from "three";

/** Limestone path through a stylized Ifrane courtyard: student → TA → professor. */
export const HELP_PATH = new THREE.CatmullRomCurve3(
  [
    new THREE.Vector3(3.2, 0.05, 7.6),
    new THREE.Vector3(4.5, 0.05, 3.4),
    new THREE.Vector3(3.55, 0.05, -0.7),
    new THREE.Vector3(2.15, 0.08, -4.8),
    new THREE.Vector3(1.35, 0.38, -9.15),
  ],
  false,
  "catmullrom",
  0.4,
);

export const FIGURES = {
  student: new THREE.Vector3(3.2, 0, 7.6),
  ta: new THREE.Vector3(3.55, 0, -0.7),
  professor: new THREE.Vector3(1.35, 0.32, -9.15),
};

const KEYFRAMES = [
  {
    t: 0,
    pos: [-1.6, 6.8, 14.2],
    look: [3.0, 1.15, 4.2],
    mobilePos: [3.4, 7.4, 14.5],
    mobileLook: [3.0, 1.0, 2.0],
  },
  {
    t: 0.14,
    pos: [0.15, 2.65, 11.4],
    look: [3.2, 1.2, 7.55],
    mobilePos: [3.2, 3.4, 12.2],
    mobileLook: [3.2, 1.15, 7.2],
  },
  {
    t: 0.36,
    pos: [0.45, 2.85, 5.1],
    look: [4.2, 1.15, 2.2],
    mobilePos: [4.6, 3.6, 6.4],
    mobileLook: [3.8, 1.1, 1.4],
  },
  {
    t: 0.52,
    pos: [0.25, 2.8, 2.95],
    look: [3.55, 1.25, -0.7],
    mobilePos: [3.55, 3.5, 3.4],
    mobileLook: [3.55, 1.2, -0.7],
  },
  {
    t: 0.72,
    pos: [-0.55, 3.35, -3.0],
    look: [1.9, 1.45, -7.4],
    mobilePos: [2.4, 4.1, -2.2],
    mobileLook: [1.6, 1.4, -8.2],
  },
  {
    t: 0.86,
    pos: [-0.35, 3.15, -5.35],
    look: [1.35, 1.55, -9.15],
    mobilePos: [1.35, 3.7, -5.0],
    mobileLook: [1.35, 1.5, -9.15],
  },
  {
    t: 1,
    pos: [1.4, 8.4, 6.2],
    look: [2.6, 1.1, -1.5],
    mobilePos: [3.2, 9.2, 8.0],
    mobileLook: [2.6, 1.0, -2.0],
  },
];

function smoothstep(edge0, edge1, x) {
  const t = THREE.MathUtils.clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

const _pos = new THREE.Vector3();
const _look = new THREE.Vector3();

export function cameraForProgress(progress, mobile) {
  const p = THREE.MathUtils.clamp(progress, 0, 1);
  let i = 0;
  while (i < KEYFRAMES.length - 2 && p > KEYFRAMES[i + 1].t) i += 1;
  const a = KEYFRAMES[i];
  const b = KEYFRAMES[i + 1];
  const u = smoothstep(a.t, b.t, p);
  const ap = mobile ? a.mobilePos : a.pos;
  const bp = mobile ? b.mobilePos : b.pos;
  const al = mobile ? a.mobileLook : a.look;
  const bl = mobile ? b.mobileLook : b.look;
  _pos.set(
    ap[0] + (bp[0] - ap[0]) * u,
    ap[1] + (bp[1] - ap[1]) * u,
    ap[2] + (bp[2] - ap[2]) * u,
  );
  _look.set(
    al[0] + (bl[0] - al[0]) * u,
    al[1] + (bl[1] - al[1]) * u,
    al[2] + (bl[2] - al[2]) * u,
  );
  return { position: _pos, look: _look };
}

export function chapterFromProgress(progress) {
  if (progress < 0.18) return "hero";
  if (progress < 0.42) return "student";
  if (progress < 0.66) return "ta";
  if (progress < 0.88) return "professor";
  return "join";
}
