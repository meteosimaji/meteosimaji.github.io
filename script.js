const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.setClearColor(0x050508, 1);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x020205, 0.08);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
const player = new THREE.Object3D();
player.position.set(0, 1.6, 0);
player.add(camera);
scene.add(player);

const ambient = new THREE.AmbientLight(0x3a2f46, 0.35);
scene.add(ambient);

const lantern = new THREE.PointLight(0xff6b6b, 0.9, 35, 2);
lantern.castShadow = true;
lantern.shadow.mapSize.set(512, 512);
player.add(lantern);
lantern.position.set(0, -0.2, 0);

const glow = new THREE.PointLight(0x2f5bff, 0.35, 45, 1.5);
player.add(glow);
glow.position.set(0, -0.2, 0);

const clock = new THREE.Clock();

const random = mulberry32(Date.now());

class InfiniteMaze {
  constructor(cellSize = 10) {
    this.cellSize = cellSize;
    this.cells = new Map();
    this.generated = new Set();
    this.startCell = this.getCell(0, 0);
    this.startCell.generated = true;
    this.generated.add(this.key(0, 0));
  }

  key(x, z) {
    return `${x},${z}`;
  }

  getCell(x, z) {
    const key = this.key(x, z);
    if (!this.cells.has(key)) {
      this.cells.set(key, {
        x,
        z,
        generated: false,
        passages: { north: false, south: false, east: false, west: false },
        visited: false,
      });
    }
    return this.cells.get(key);
  }

  getExistingCell(x, z) {
    return this.cells.get(this.key(x, z));
  }

  neighbors(x, z) {
    return [
      { dir: 'north', x, z: z - 1 },
      { dir: 'south', x, z: z + 1 },
      { dir: 'east', x: x + 1, z },
      { dir: 'west', x: x - 1, z },
    ];
  }

  opposite(dir) {
    switch (dir) {
      case 'north':
        return 'south';
      case 'south':
        return 'north';
      case 'east':
        return 'west';
      case 'west':
        return 'east';
      default:
        return 'north';
    }
  }

  shuffle(array) {
    for (let i = array.length - 1; i > 0; i -= 1) {
      const j = Math.floor(random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  carvePassage(cell, neighbor, dir) {
    if (!cell || !neighbor) return;
    cell.passages[dir] = true;
    neighbor.passages[this.opposite(dir)] = true;
  }

  generateCell(x, z) {
    const key = this.key(x, z);
    if (this.generated.has(key)) {
      return this.getCell(x, z);
    }

    const cell = this.getCell(x, z);
    const neighbors = this.shuffle(this.neighbors(x, z));
    const connected = neighbors
      .map((n) => ({ ...n, cell: this.getExistingCell(n.x, n.z) }))
      .filter((n) => n.cell && n.cell.generated);

    if (connected.length === 0) {
      const chosen = neighbors[0];
      const next = this.generateCell(chosen.x, chosen.z);
      this.carvePassage(cell, next, chosen.dir);
    } else {
      const chosen = connected[Math.floor(random() * connected.length)];
      this.carvePassage(cell, chosen.cell, chosen.dir);
    }

    cell.generated = true;
    this.generated.add(key);

    // extra passages to reduce dead-ends
    neighbors.forEach((n) => {
      const neighborCell = this.getExistingCell(n.x, n.z);
      if (neighborCell && neighborCell.generated) {
        if (!cell.passages[n.dir] && random() < 0.28) {
          this.carvePassage(cell, neighborCell, n.dir);
        }
      } else if (!neighborCell && random() < 0.12) {
        const created = this.generateCell(n.x, n.z);
        this.carvePassage(cell, created, n.dir);
      }
    });

    const openCount = Object.values(cell.passages).filter(Boolean).length;
    if (openCount === 1) {
      const moreOptions = neighbors
        .map((n) => ({ ...n, cell: this.getExistingCell(n.x, n.z) }))
        .filter((n) => n.cell && n.cell.generated && !cell.passages[n.dir]);
      if (moreOptions.length) {
        const chosen = moreOptions[Math.floor(random() * moreOptions.length)];
        this.carvePassage(cell, chosen.cell, chosen.dir);
      }
    }

    return cell;
  }

  ensureArea(cx, cz, radius) {
    for (let x = cx - radius; x <= cx + radius; x += 1) {
      for (let z = cz - radius; z <= cz + radius; z += 1) {
        const dist = Math.abs(x - cx) + Math.abs(z - cz);
        if (dist > radius + 4) continue;
        this.generateCell(x, z);
      }
    }
  }

  worldToCell(x, z) {
    const cs = this.cellSize;
    return { x: Math.round(x / cs), z: Math.round(z / cs) };
  }

  cellCenter(x, z) {
    return new THREE.Vector3(x * this.cellSize, 0, z * this.cellSize);
  }
}

function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function createStoneTexture() {
  const size = 256;
  const brickH = 32;
  const brickW = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#2a2a30';
  ctx.fillRect(0, 0, size, size);

  for (let y = 0; y < size; y += brickH) {
    const offset = (y / brickH) % 2 === 0 ? 0 : brickW / 2;
    for (let x = -brickW; x < size + brickW; x += brickW) {
      const px = x + offset;
      ctx.fillStyle = `hsl(220, 10%, ${24 + Math.random() * 12}%)`;
      ctx.fillRect(px + 4, y + 4, brickW - 8, brickH - 8);
      ctx.strokeStyle = 'rgba(0,0,0,0.3)';
      ctx.lineWidth = 2;
      ctx.strokeRect(px + 4, y + 4, brickW - 8, brickH - 8);
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(1, 1);
  texture.anisotropy = 4;
  return texture;
}

const maze = new InfiniteMaze(12);

const wallTexture = createStoneTexture();
const wallMaterial = new THREE.MeshStandardMaterial({
  map: wallTexture,
  roughness: 0.9,
  metalness: 0.1,
  bumpMap: wallTexture,
  bumpScale: 0.2,
});
const floorMaterial = new THREE.MeshStandardMaterial({
  color: 0x15131b,
  roughness: 1,
  metalness: 0,
});
const ceilingMaterial = new THREE.MeshStandardMaterial({ color: 0x0a0a10, roughness: 1, metalness: 0 });

const floorGeometry = new THREE.PlaneGeometry(maze.cellSize, maze.cellSize);
floorGeometry.rotateX(-Math.PI / 2);
const ceilingGeometry = floorGeometry.clone();
ceilingGeometry.rotateY(Math.PI);
const wallGeometry = new THREE.BoxGeometry(maze.cellSize, 4, 0.8);
const sideWallGeometry = new THREE.BoxGeometry(0.8, 4, maze.cellSize);

class MazeRenderer {
  constructor(maze, scene) {
    this.maze = maze;
    this.scene = scene;
    this.groups = new Map();
  }

  key(x, z) {
    return `${x},${z}`;
  }

  ensureCellMesh(cell) {
    const key = this.key(cell.x, cell.z);
    if (this.groups.has(key)) return;

    const group = new THREE.Group();
    group.position.copy(this.maze.cellCenter(cell.x, cell.z));

    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.receiveShadow = true;
    group.add(floor);

    const ceiling = new THREE.Mesh(ceilingGeometry, ceilingMaterial);
    ceiling.position.y = 4;
    ceiling.receiveShadow = true;
    group.add(ceiling);

    const half = this.maze.cellSize / 2;

    if (!cell.passages.north) {
      const wall = new THREE.Mesh(wallGeometry, wallMaterial);
      wall.position.set(0, 2, -half + 0.4);
      wall.castShadow = true;
      group.add(wall);
    }
    if (!cell.passages.south) {
      const wall = new THREE.Mesh(wallGeometry, wallMaterial);
      wall.position.set(0, 2, half - 0.4);
      wall.castShadow = true;
      group.add(wall);
    }
    if (!cell.passages.east) {
      const wall = new THREE.Mesh(sideWallGeometry, wallMaterial);
      wall.position.set(half - 0.4, 2, 0);
      wall.castShadow = true;
      group.add(wall);
    }
    if (!cell.passages.west) {
      const wall = new THREE.Mesh(sideWallGeometry, wallMaterial);
      wall.position.set(-half + 0.4, 2, 0);
      wall.castShadow = true;
      group.add(wall);
    }

    this.groups.set(key, group);
    this.scene.add(group);
  }

  updateVisible(cx, cz, radius) {
    const needed = new Set();
    for (let x = cx - radius; x <= cx + radius; x += 1) {
      for (let z = cz - radius; z <= cz + radius; z += 1) {
        const key = this.key(x, z);
        needed.add(key);
        const cell = this.maze.getCell(x, z);
        if (cell.generated) {
          this.ensureCellMesh(cell);
        }
      }
    }

    for (const [key, group] of this.groups.entries()) {
      if (!needed.has(key)) {
        this.scene.remove(group);
        this.groups.delete(key);
      }
    }
  }
}

const mazeRenderer = new MazeRenderer(maze, scene);

const minimapCanvas = document.getElementById('minimap');
const minimapCtx = minimapCanvas.getContext('2d');
let minimapRatio = 1;
let minimapSize = minimapCanvas.clientWidth;

function updateMinimapResolution() {
  minimapSize = minimapCanvas.clientWidth;
  minimapRatio = Math.min(window.devicePixelRatio || 1, 2);
  minimapCanvas.width = minimapSize * minimapRatio;
  minimapCanvas.height = minimapSize * minimapRatio;
  minimapCtx.setTransform(1, 0, 0, 1, 0, 0);
  minimapCtx.scale(minimapRatio, minimapRatio);
}

updateMinimapResolution();

function drawMinimap(playerCell, yaw) {
  const size = minimapSize;
  minimapCtx.clearRect(0, 0, size, size);
  minimapCtx.fillStyle = 'rgba(9, 9, 14, 0.9)';
  minimapCtx.fillRect(0, 0, size, size);

  const radius = 10;
  const cellPixel = size / (radius * 2 + 2);
  const offset = size / 2;

  for (let dx = -radius; dx <= radius; dx += 1) {
    for (let dz = -radius; dz <= radius; dz += 1) {
      const x = playerCell.x + dx;
      const z = playerCell.z + dz;
      const cell = maze.getExistingCell(x, z);
      if (!cell || !cell.generated) continue;
      const px = offset + dx * cellPixel;
      const pz = offset + dz * cellPixel;

      minimapCtx.fillStyle = cell.visited ? 'rgba(180, 80, 110, 0.6)' : 'rgba(80, 80, 110, 0.55)';
      minimapCtx.fillRect(px - cellPixel * 0.4, pz - cellPixel * 0.4, cellPixel * 0.8, cellPixel * 0.8);

      minimapCtx.strokeStyle = 'rgba(30, 30, 40, 0.7)';
      minimapCtx.strokeRect(px - cellPixel * 0.4, pz - cellPixel * 0.4, cellPixel * 0.8, cellPixel * 0.8);

      const passages = cell.passages;
      minimapCtx.strokeStyle = 'rgba(200, 120, 150, 0.45)';
      minimapCtx.lineWidth = 2;
      minimapCtx.beginPath();
      if (passages.north) {
        minimapCtx.moveTo(px, pz - cellPixel * 0.4);
        minimapCtx.lineTo(px, pz - cellPixel * 0.9);
      }
      if (passages.south) {
        minimapCtx.moveTo(px, pz + cellPixel * 0.4);
        minimapCtx.lineTo(px, pz + cellPixel * 0.9);
      }
      if (passages.east) {
        minimapCtx.moveTo(px + cellPixel * 0.4, pz);
        minimapCtx.lineTo(px + cellPixel * 0.9, pz);
      }
      if (passages.west) {
        minimapCtx.moveTo(px - cellPixel * 0.4, pz);
        minimapCtx.lineTo(px - cellPixel * 0.9, pz);
      }
      minimapCtx.stroke();
    }
  }

  minimapCtx.save();
  minimapCtx.translate(offset, offset);
  minimapCtx.rotate(-yaw);
  minimapCtx.fillStyle = '#ffb4c7';
  minimapCtx.beginPath();
  minimapCtx.moveTo(0, -8);
  minimapCtx.lineTo(6, 8);
  minimapCtx.lineTo(-6, 8);
  minimapCtx.closePath();
  minimapCtx.fill();
  minimapCtx.restore();
}

const keys = { forward: false, backward: false, left: false, right: false };
let pointerLocked = false;
let yaw = 0;
let pitch = 0;
const pitchLimit = Math.PI / 2 - 0.12;

function requestPointerLock() {
  if (!pointerLocked && !('ontouchstart' in window)) {
    canvas.requestPointerLock();
  }
}

document.addEventListener('pointerlockchange', () => {
  pointerLocked = document.pointerLockElement === canvas;
});

window.addEventListener('click', () => {
  requestPointerLock();
  startAmbience();
});

canvas.addEventListener('pointerdown', () => {
  requestPointerLock();
  startAmbience();
});

const ambience = document.getElementById('ambience');
let ambienceStarted = false;
function startAmbience() {
  if (!ambienceStarted) {
    ambience.volume = 0.4;
    ambience.play().catch(() => {});
    ambienceStarted = true;
  }
}

window.addEventListener('keydown', (event) => {
  startAmbience();
  switch (event.code) {
    case 'KeyW':
    case 'ArrowUp':
      keys.forward = true;
      break;
    case 'KeyS':
    case 'ArrowDown':
      keys.backward = true;
      break;
    case 'KeyA':
    case 'ArrowLeft':
      keys.left = true;
      break;
    case 'KeyD':
    case 'ArrowRight':
      keys.right = true;
      break;
    default:
      break;
  }
});

window.addEventListener('keyup', (event) => {
  switch (event.code) {
    case 'KeyW':
    case 'ArrowUp':
      keys.forward = false;
      break;
    case 'KeyS':
    case 'ArrowDown':
      keys.backward = false;
      break;
    case 'KeyA':
    case 'ArrowLeft':
      keys.left = false;
      break;
    case 'KeyD':
    case 'ArrowRight':
      keys.right = false;
      break;
    default:
      break;
  }
});

canvas.addEventListener('mousemove', (event) => {
  if (!pointerLocked) return;
  yaw -= event.movementX * 0.0025;
  pitch -= event.movementY * 0.002;
  pitch = Math.max(-pitchLimit, Math.min(pitchLimit, pitch));
});

let touchLookId = null;
let lastTouchPos = null;

function onTouchStart(event) {
  event.preventDefault();
  document.body.classList.add('touch');
  startAmbience();
  for (const touch of event.changedTouches) {
    if (touch.target.closest('#joystick')) continue;
    if (touchLookId === null) {
      touchLookId = touch.identifier;
      lastTouchPos = { x: touch.clientX, y: touch.clientY };
    }
  }
}

function onTouchMove(event) {
  if (touchLookId !== null) {
    event.preventDefault();
  }
  for (const touch of event.changedTouches) {
    if (touch.identifier === touchLookId && lastTouchPos) {
      const dx = touch.clientX - lastTouchPos.x;
      const dy = touch.clientY - lastTouchPos.y;
      yaw -= dx * 0.004;
      pitch -= dy * 0.003;
      pitch = Math.max(-pitchLimit, Math.min(pitchLimit, pitch));
      lastTouchPos = { x: touch.clientX, y: touch.clientY };
    }
  }
}

function onTouchEnd(event) {
  for (const touch of event.changedTouches) {
    if (touch.identifier === touchLookId) {
      touchLookId = null;
      lastTouchPos = null;
    }
  }
}

document.addEventListener('touchstart', onTouchStart, { passive: false });
document.addEventListener('touchmove', onTouchMove, { passive: false });
document.addEventListener('touchend', onTouchEnd, { passive: false });

document.addEventListener('contextmenu', (event) => event.preventDefault());

const joystick = document.getElementById('joystick');
const stick = joystick.querySelector('.stick');
let joystickTouchId = null;
let joystickVector = new THREE.Vector2();

function handleJoystickStart(event) {
  startAmbience();
  for (const touch of event.changedTouches) {
    if (touch.target.closest('#joystick')) {
      event.preventDefault();
      joystickTouchId = touch.identifier;
      updateJoystick(touch.clientX, touch.clientY);
    }
  }
}

function handleJoystickMove(event) {
  for (const touch of event.changedTouches) {
    if (touch.identifier === joystickTouchId) {
      event.preventDefault();
      updateJoystick(touch.clientX, touch.clientY);
    }
  }
}

function handleJoystickEnd(event) {
  for (const touch of event.changedTouches) {
    if (touch.identifier === joystickTouchId) {
      event.preventDefault();
      joystickTouchId = null;
      joystickVector.set(0, 0);
      stick.style.transform = `translate3d(0px,0px,0)`;
    }
  }
}

function updateJoystick(clientX, clientY) {
  const rect = joystick.getBoundingClientRect();
  const x = clientX - (rect.left + rect.width / 2);
  const y = clientY - (rect.top + rect.height / 2);
  const max = rect.width / 2;
  const distance = Math.min(Math.hypot(x, y), max);
  const angle = Math.atan2(y, x);
  const nx = (distance / max) * Math.cos(angle);
  const ny = (distance / max) * Math.sin(angle);
  joystickVector.set(nx, ny);
  stick.style.transform = `translate3d(${nx * max * 0.6}px, ${ny * max * 0.6}px, 0)`;
}

document.addEventListener('touchstart', handleJoystickStart, { passive: false });
document.addEventListener('touchmove', handleJoystickMove, { passive: false });
document.addEventListener('touchend', handleJoystickEnd, { passive: false });
document.addEventListener('touchcancel', handleJoystickEnd, { passive: false });

document.addEventListener('visibilitychange', () => {
  if (document.hidden && ambienceStarted) {
    ambience.pause();
  } else if (!document.hidden && ambienceStarted) {
    ambience.play().catch(() => {});
  }
});

function updatePlayerOrientation() {
  player.rotation.set(0, yaw, 0);
  camera.rotation.set(pitch, 0, 0);
}

const velocity = new THREE.Vector3();
const direction = new THREE.Vector3();
const tmp = new THREE.Vector3();
const wanderWave = new THREE.Vector2(random() * Math.PI * 2, random() * Math.PI * 2);

function getMovementInput() {
  direction.set(0, 0, 0);
  if (keys.forward) direction.z -= 1;
  if (keys.backward) direction.z += 1;
  if (keys.left) direction.x -= 1;
  if (keys.right) direction.x += 1;
  if (joystickVector.lengthSq() > 0) {
    direction.x += joystickVector.x;
    direction.z += joystickVector.y;
  }
  if (direction.lengthSq() > 0) direction.normalize();
  return direction;
}

function resolveCollision(current, attempted) {
  const cs = maze.cellSize;
  const newPosition = attempted.clone();
  const cellX = Math.round(current.x / cs);
  const cellZ = Math.round(current.z / cs);
  maze.ensureArea(cellX, cellZ, 2);
  const cell = maze.getCell(cellX, cellZ);
  const center = maze.cellCenter(cellX, cellZ);
  const local = newPosition.clone().sub(center);
  const half = cs / 2 - 1.1;

  const clampAxis = (positiveDir, negativeDir, value) => {
    if (!cell.passages[positiveDir] && value > half) {
      value = half;
    }
    if (!cell.passages[negativeDir] && value < -half) {
      value = -half;
    }
    return value;
  };

  local.x = clampAxis('east', 'west', local.x);
  local.z = clampAxis('south', 'north', local.z);

  newPosition.copy(center.add(local));
  return newPosition;
}

function update(delta) {
  updatePlayerOrientation();
  const moveInput = getMovementInput();
  const speed = 3.2;

  const moveVector = moveInput.clone();
  const quaternion = new THREE.Quaternion();
  quaternion.setFromEuler(new THREE.Euler(0, yaw, 0));
  moveVector.applyQuaternion(quaternion);

  velocity.x = THREE.MathUtils.damp(velocity.x, moveVector.x * speed, 8, delta);
  velocity.z = THREE.MathUtils.damp(velocity.z, moveVector.z * speed, 8, delta);

  tmp.copy(player.position);
  tmp.x += velocity.x * delta;
  tmp.z += velocity.z * delta;

  const resolved = resolveCollision(player.position, tmp);
  player.position.copy(resolved);

  const cellCoords = maze.worldToCell(player.position.x, player.position.z);
  maze.ensureArea(cellCoords.x, cellCoords.z, 14);
  mazeRenderer.updateVisible(cellCoords.x, cellCoords.z, 12);

  const cell = maze.getCell(cellCoords.x, cellCoords.z);
  cell.visited = true;

  drawMinimap(cellCoords, yaw);

  // Subtle head bob & light flicker
  wanderWave.x += delta * 0.5;
  wanderWave.y += delta * 0.7;
  const bob = Math.sin(wanderWave.x * 2) * 0.03 * moveInput.length();
  camera.position.y = 1.6 + bob;
  lantern.intensity = 0.75 + Math.sin(wanderWave.y * 3 + random() * 0.2) * 0.2;
  glow.intensity = 0.25 + Math.sin(wanderWave.y * 1.3) * 0.1;
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.05);
  update(delta);
  renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  updateMinimapResolution();
});

maze.ensureArea(0, 0, 8);
mazeRenderer.updateVisible(0, 0, 8);
updatePlayerOrientation();
drawMinimap({ x: 0, z: 0 }, yaw);

// atmospheric volumetric motes
const particles = new THREE.Group();
scene.add(particles);
const particleGeometry = new THREE.SphereGeometry(0.05, 6, 6);
const particleMaterial = new THREE.MeshBasicMaterial({ color: 0xff7896, transparent: true, opacity: 0.25 });
for (let i = 0; i < 120; i += 1) {
  const mesh = new THREE.Mesh(particleGeometry, particleMaterial.clone());
  resetParticle(mesh, true);
  particles.add(mesh);
}

function resetParticle(mesh, initial = false) {
  const radius = 25;
  mesh.position.set((random() - 0.5) * radius, 0.5 + random() * 3.2, (random() - 0.5) * radius);
  mesh.material.opacity = 0.1 + random() * 0.2;
  if (!initial) {
    mesh.position.add(player.position);
  }
}

function animateParticles(delta) {
  particles.children.forEach((mesh) => {
    mesh.position.y += Math.sin(clock.elapsedTime * 0.5 + mesh.id) * 0.01;
    mesh.position.x += Math.sin(clock.elapsedTime * 0.3 + mesh.id) * 0.004;
    mesh.position.z += Math.cos(clock.elapsedTime * 0.25 + mesh.id) * 0.004;
    const distance = mesh.position.distanceToSquared(player.position);
    if (distance > 40 * 40) {
      resetParticle(mesh);
    }
  });
}

const originalUpdate = update;
function updateWithParticles(delta) {
  originalUpdate(delta);
  animateParticles(delta);
}
update = updateWithParticles;
