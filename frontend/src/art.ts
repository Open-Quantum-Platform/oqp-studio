import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { PhysicalCamera, WebGLPathTracer } from "three-gpu-pathtracer";

type Atom = [string, number, number, number];

const ELEMENTS: Record<string, { color: number; covalent: number; display: number }> = {
  H: { color: 0xf2f2f2, covalent: 0.31, display: 0.34 },
  C: { color: 0x343a42, covalent: 0.76, display: 0.48 },
  N: { color: 0x315ed1, covalent: 0.71, display: 0.46 },
  O: { color: 0xe63226, covalent: 0.66, display: 0.45 },
  F: { color: 0x62c96b, covalent: 0.57, display: 0.43 },
  P: { color: 0xe28c28, covalent: 1.07, display: 0.56 },
  S: { color: 0xe5c83c, covalent: 1.05, display: 0.55 },
  Cl: { color: 0x44ad51, covalent: 1.02, display: 0.56 },
  Br: { color: 0x8d3328, covalent: 1.20, display: 0.61 },
  I: { color: 0x7650a8, covalent: 1.39, display: 0.66 },
};

const stage = document.getElementById("stage")!;
const progress = document.getElementById("progress")!;
const empty = document.getElementById("empty")!;
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(stage.clientWidth, stage.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111318);
const camera = new PhysicalCamera(34, stage.clientWidth / stage.clientHeight, 0.05, 500);
camera.position.set(5, 3.5, 7);
camera.fStop = 14;
camera.focusDistance = 8;
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

const tracer = new WebGLPathTracer(renderer);
tracer.renderScale = 0.75;
tracer.bounces = 5;
tracer.tiles.set(2, 2);
tracer.dynamicLowRes = true;
tracer.lowResScale = 0.25;
tracer.multipleImportanceSampling = true;

let molecule: THREE.Group | null = null;
let paused = false;
let lastAtoms: Atom[] = [];
let pixelProbeDone = false;

function element(symbol: string) {
  return ELEMENTS[symbol] ?? { color: 0xb7bec9, covalent: 0.77, display: 0.49 };
}

function cylinderBetween(a: THREE.Vector3, b: THREE.Vector3, material: THREE.Material): THREE.Mesh {
  const delta = new THREE.Vector3().subVectors(b, a);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.105, 0.105, delta.length(), 24), material);
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.normalize());
  return mesh;
}

function disposeObject(object: THREE.Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;
    child.geometry.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => material.dispose());
  });
}

async function setMolecule(atoms: Atom[]): Promise<void> {
  if (!atoms.length) return;
  lastAtoms = atoms;
  pixelProbeDone = false;
  if (molecule) {
    scene.remove(molecule);
    disposeObject(molecule);
  }
  molecule = new THREE.Group();
  const center = new THREE.Vector3();
  atoms.forEach(([, x, y, z]) => center.add(new THREE.Vector3(x, y, z)));
  center.multiplyScalar(1 / atoms.length);
  const points = atoms.map(([, x, y, z]) => new THREE.Vector3(x, y, z).sub(center));

  atoms.forEach(([symbol], index) => {
    const spec = element(symbol);
    const material = new THREE.MeshStandardMaterial({ color: spec.color, roughness: 0.26, metalness: 0.03 });
    const atom = new THREE.Mesh(new THREE.SphereGeometry(spec.display, 40, 24), material);
    atom.position.copy(points[index]);
    molecule!.add(atom);
  });
  const bondMaterial = new THREE.MeshStandardMaterial({ color: 0xaeb5bf, roughness: 0.38, metalness: 0.02 });
  for (let i = 0; i < atoms.length; i += 1) {
    for (let j = i + 1; j < atoms.length; j += 1) {
      const cutoff = 1.18 * (element(atoms[i][0]).covalent + element(atoms[j][0]).covalent);
      const distance = points[i].distanceTo(points[j]);
      if (distance > 0.35 && distance <= cutoff) molecule.add(cylinderBetween(points[i], points[j], bondMaterial.clone()));
    }
  }
  scene.add(molecule);

  const box = new THREE.Box3().setFromObject(molecule);
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  floor.position.y = box.min.y - 1.25;
  const distance = Math.max(4.5, sphere.radius / Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.45)));
  camera.position.set(distance * 0.65, distance * 0.42, distance);
  camera.near = Math.max(0.02, distance / 100);
  camera.far = distance * 20;
  camera.focusDistance = camera.position.length();
  camera.updateProjectionMatrix();
  controls.target.set(0, 0, 0);
  controls.saveState();
  controls.update();
  empty.style.display = "none";
  progress.textContent = "building ray-tracing scene";
  tracer.setScene(scene, camera, {
    onProgress: (fraction) => { progress.textContent = `building scene ${Math.round(fraction * 100)}%`; },
  });
  tracer.reset();
}

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(80, 80),
  new THREE.MeshStandardMaterial({ color: 0x242830, roughness: 0.68, metalness: 0 }),
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -2.2;
scene.add(floor);
const key = new THREE.RectAreaLight(0xffffff, 28, 5, 5);
key.position.set(4, 6, 5);
key.lookAt(0, 0, 0);
scene.add(key);
const fill = new THREE.RectAreaLight(0x8cbfff, 18, 4, 4);
fill.position.set(-5, 2, 3);
fill.lookAt(0, 0, 0);
scene.add(fill);
const rim = new THREE.RectAreaLight(0xffd5aa, 16, 3, 3);
rim.position.set(1, 3, -5);
rim.lookAt(0, 0, 0);
scene.add(rim);

controls.addEventListener("change", () => {
  camera.focusDistance = camera.position.distanceTo(controls.target);
  tracer.updateCamera();
  tracer.reset();
});

document.getElementById("quality")!.addEventListener("change", (event) => {
  const [scale, bounces] = (event.target as HTMLSelectElement).value.split(",").map(Number);
  tracer.renderScale = scale;
  tracer.bounces = bounces;
  tracer.reset();
});
document.getElementById("exposure")!.addEventListener("input", (event) => {
  renderer.toneMappingExposure = +(event.target as HTMLInputElement).value;
  tracer.reset();
});
document.getElementById("dof")!.addEventListener("change", (event) => {
  const strength = +(event.target as HTMLSelectElement).value;
  camera.fStop = strength === 0 ? 1000 : strength === 1 ? 14 : 5.6;
  camera.focusDistance = camera.position.distanceTo(controls.target);
  tracer.updateCamera();
  tracer.reset();
});
document.getElementById("pause")!.addEventListener("click", (event) => {
  paused = !paused;
  (event.target as HTMLButtonElement).textContent = paused ? "Resume" : "Pause";
});
document.getElementById("reset")!.addEventListener("click", () => {
  controls.reset();
  tracer.updateCamera();
  tracer.reset();
});
document.getElementById("save")!.addEventListener("click", () => {
  const link = document.createElement("a");
  link.download = "oqp-art.png";
  link.href = renderer.domElement.toDataURL("image/png");
  link.click();
});

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin || event.data?.type !== "oqp-art-structure") return;
  void setMolecule(event.data.atoms as Atom[]);
});
window.setTimeout(() => {
  if (!lastAtoms.length) {
    void setMolecule([
      ["O", 0.001, 0.398, 0],
      ["H", -0.764, -0.197, 0],
      ["H", 0.763, -0.201, 0],
    ]);
  }
}, 350);
window.addEventListener("resize", () => {
  const width = stage.clientWidth;
  const height = stage.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
  tracer.updateCamera();
  tracer.reset();
});

function animate(): void {
  requestAnimationFrame(animate);
  controls.update();
  if (lastAtoms.length && !paused) tracer.renderSample();
  if (!pixelProbeDone && tracer.samples >= 8) {
    const gl = renderer.getContext();
    const size = 16;
    const pixels = new Uint8Array(size * size * 4);
    gl.readPixels(
      Math.max(0, Math.floor(renderer.domElement.width / 2) - size / 2),
      Math.max(0, Math.floor(renderer.domElement.height / 2) - size / 2),
      size, size, gl.RGBA, gl.UNSIGNED_BYTE, pixels,
    );
    let nonBlank = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 30) nonBlank += 1;
    }
    progress.dataset.canvasPixels = `${nonBlank}/${size * size}`;
    progress.dataset.canvasSize = `${renderer.domElement.width}x${renderer.domElement.height}`;
    pixelProbeDone = true;
  }
  progress.textContent = lastAtoms.length
    ? `${paused ? "paused" : "tracing"} · ${tracer.samples.toFixed(0)} samples · ${tracer.bounces} bounces`
    : "waiting for a structure";
}
animate();
window.parent.postMessage({ type: "oqp-art-ready" }, window.location.origin);
