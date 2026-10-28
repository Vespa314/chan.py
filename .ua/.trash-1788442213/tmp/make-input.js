const fs = require('fs');

const graphPath = 'e:/CodingWork/01csh/chan.py/.ua/intermediate/assembled-graph.json';
const layersPath = 'e:/CodingWork/01csh/chan.py/.ua/intermediate/layers.json';
const outputPath = 'e:/CodingWork/01csh/chan.py/.ua/tmp/ua-tour-input.json';

const graph = JSON.parse(fs.readFileSync(graphPath, 'utf8'));
const layers = JSON.parse(fs.readFileSync(layersPath, 'utf8'));

const input = {
  nodes: graph.nodes,
  edges: graph.edges,
  layers: layers
};

fs.writeFileSync(outputPath, JSON.stringify(input, null, 2));
console.log(`Written ${input.nodes.length} nodes, ${input.edges.length} edges, ${input.layers.length} layers to ${outputPath}`);