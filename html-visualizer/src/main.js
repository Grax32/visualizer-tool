import butterchurn from 'butterchurn';
import butterchurnPresets from 'butterchurn-presets';
import './styles.css';

const fileInput = document.querySelector('#file-input');
const startButton = document.querySelector('#start-button');
const prevButton = document.querySelector('#prev-button');
const nextButton = document.querySelector('#next-button');
const randomButton = document.querySelector('#random-button');
const presetSelect = document.querySelector('#preset-select');
const transitionInput = document.querySelector('#transition-input');
const transitionOutput = document.querySelector('#transition-output');
const statusPill = document.querySelector('#status');
const audio = document.querySelector('#audio');
const canvas = document.querySelector('#visualizer-canvas');

const AudioContextClass = window.AudioContext || window.webkitAudioContext;

let audioContext;
let sourceNode;
let visualizer;
let animationFrameId;
let currentObjectUrl;
let presets = {};
let presetNames = [];
let presetIndex = 0;
let started = false;

function setStatus(message) {
  statusPill.textContent = message;
}

function setPresetControlsEnabled(enabled) {
  prevButton.disabled = !enabled;
  nextButton.disabled = !enabled;
  randomButton.disabled = !enabled;
  presetSelect.disabled = !enabled;
}

function getTransitionDuration() {
  return Number.parseFloat(transitionInput.value) || 0;
}

function resizeVisualizer() {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);

  canvas.width = Math.floor(width * (window.devicePixelRatio || 1));
  canvas.height = Math.floor(height * (window.devicePixelRatio || 1));
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  if (visualizer) {
    visualizer.setRendererSize(width, height);
  }
}

function populatePresetSelect() {
  presetSelect.replaceChildren();

  presetNames.forEach((name, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = name;
    presetSelect.append(option);
  });
}

function loadPreset(index, blendTime = getTransitionDuration()) {
  if (!visualizer || presetNames.length === 0) {
    return;
  }

  presetIndex = (index + presetNames.length) % presetNames.length;
  const presetName = presetNames[presetIndex];

  visualizer.loadPreset(presets[presetName], blendTime);
  presetSelect.value = String(presetIndex);
  setStatus(presetName);
}

function startRenderLoop() {
  if (animationFrameId) {
    return;
  }

  const renderFrame = () => {
    visualizer.render();
    animationFrameId = window.requestAnimationFrame(renderFrame);
  };

  animationFrameId = window.requestAnimationFrame(renderFrame);
}

function loadPresetBundle() {
  presets = butterchurnPresets.getPresets();
  presetNames = Object.keys(presets).sort((a, b) => a.localeCompare(b));

  if (presetNames.length === 0) {
    throw new Error('No Butterchurn presets were bundled.');
  }

  populatePresetSelect();
}

async function startVisualizer() {
  if (!AudioContextClass) {
    throw new Error('This browser does not support the Web Audio API.');
  }

  if (!audio.src) {
    throw new Error('Choose a local MP3 or audio file first.');
  }

  if (!started) {
    audioContext = new AudioContextClass();
    await audioContext.resume();

    sourceNode = audioContext.createMediaElementSource(audio);

    visualizer = butterchurn.createVisualizer(audioContext, canvas, {
      width: window.innerWidth,
      height: window.innerHeight,
      pixelRatio: window.devicePixelRatio || 1,
      textureRatio: 1,
    });

    visualizer.connectAudio(sourceNode);
    sourceNode.connect(audioContext.destination);

    loadPresetBundle();
    resizeVisualizer();
    loadPreset(presetIndex, 0);
    setPresetControlsEnabled(true);
    started = true;
    startButton.textContent = 'Resume visualizer';
  } else if (audioContext.state === 'suspended') {
    await audioContext.resume();
  }

  await audio.play();
  startRenderLoop();
}

fileInput.addEventListener('change', () => {
  const [file] = fileInput.files;

  if (!file) {
    return;
  }

  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
  }

  currentObjectUrl = URL.createObjectURL(file);
  audio.src = currentObjectUrl;
  audio.load();
  setStatus(file.name);
});

startButton.addEventListener('click', async () => {
  try {
    startButton.disabled = true;
    await startVisualizer();
  } catch (error) {
    window.alert(error.message);
    setStatus('Needs audio');
  } finally {
    startButton.disabled = false;
  }
});

prevButton.addEventListener('click', () => {
  loadPreset(presetIndex - 1);
});

nextButton.addEventListener('click', () => {
  loadPreset(presetIndex + 1);
});

randomButton.addEventListener('click', () => {
  if (presetNames.length < 2) {
    loadPreset(0);
    return;
  }

  let nextIndex = presetIndex;
  while (nextIndex === presetIndex) {
    nextIndex = Math.floor(Math.random() * presetNames.length);
  }
  loadPreset(nextIndex);
});

presetSelect.addEventListener('change', () => {
  loadPreset(Number.parseInt(presetSelect.value, 10));
});

transitionInput.addEventListener('input', () => {
  transitionOutput.value = `${getTransitionDuration().toFixed(1)}s`;
});

audio.addEventListener('pause', () => {
  if (audioContext?.state === 'running') {
    setStatus('Paused');
  }
});

audio.addEventListener('play', () => {
  if (presetNames[presetIndex]) {
    setStatus(presetNames[presetIndex]);
  }
});

window.addEventListener('resize', resizeVisualizer);
window.addEventListener('beforeunload', () => {
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
  }
});

resizeVisualizer();
setPresetControlsEnabled(false);
