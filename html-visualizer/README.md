# HTML Butterchurn Visualizer

A separate browser-based MP3/audio visualizer that renders MilkDrop/projectM-like
output to an HTML canvas through Butterchurn.

## Features

- Local audio file picker for MP3 and other browser-supported audio formats.
- Explicit start button to satisfy browser autoplay and Web Audio policies.
- Butterchurn WebGL canvas renderer using bundled Butterchurn presets.
- Previous, next, random, and direct preset selection controls.
- Vite development and production build flow.

## Install

```bash
npm install
```

## Development

```bash
npm run dev
```

Open the Vite URL, choose a local MP3/audio file, then click **Start visualizer**.

## Build

```bash
npm run build
```

Vite bundles Butterchurn, `butterchurn-presets`, and this app's source into the
production output. The runtime path uses a user-selected local audio file and the
bundled preset object; it does not fetch audio or presets from a CDN.

## Licensing notes

This tool depends on Butterchurn and Butterchurn presets. Butterchurn is MIT
licensed; keep dependency license notices intact when redistributing a built
copy. Community MilkDrop preset authorship can be unclear, so prefer vetted or
self-authored presets for products that require strict provenance.
