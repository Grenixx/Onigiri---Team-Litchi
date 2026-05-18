precision mediump float;

uniform float u_time;
uniform vec2 u_resolution;

vec2 randomGradient(vec2 p) {
  p += 0.02;
  float x = dot(p, vec2(123.4, 234.5));
  float y = dot(p, vec2(234.5, 345.6));
  vec2 gradient = vec2(x, y);
  gradient = sin(gradient);
  gradient *= 43758.5453;

  gradient = sin(gradient + u_time);
  return gradient;
}


vec2 quintic(vec2 p) {
  return p * p * p * (10.0 + p * (-15.0 + p * 6.0));
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  uv = gl_FragCoord.xy / u_resolution.y;
  
  vec3 color = vec3(0.0);
  uv *= 15.0;
  vec2 gridId = floor(uv);
  vec2 gridUv = fract(uv);

  vec2 bl = gridId + vec2(0.0, 0.0);
  vec2 br = gridId + vec2(1.0, 0.0);
  vec2 tl = gridId + vec2(0.0, 1.0);
  vec2 tr = gridId + vec2(1.0, 1.0);

  vec2 gradBl = randomGradient(bl);
  vec2 gradBr = randomGradient(br);
  vec2 gradTl = randomGradient(tl);
  vec2 gradTr = randomGradient(tr);

  vec2 distFromPixelToBl = gridUv - vec2(0.0, 0.0);
  vec2 distFromPixelToBr = gridUv - vec2(1.0, 0.0);
  vec2 distFromPixelToTl = gridUv - vec2(0.0, 1.0);
  vec2 distFromPixelToTr = gridUv - vec2(1.0, 1.0);

  float dotBl = dot(gradBl, distFromPixelToBl);
  float dotBr = dot(gradBr, distFromPixelToBr);
  float dotTl = dot(gradTl, distFromPixelToTl);
  float dotTr = dot(gradTr, distFromPixelToTr);

  gridUv = quintic(gridUv);

  float b = mix(dotBl, dotBr, gridUv.x);
  float t = mix(dotTl, dotTr, gridUv.x);
  float perlin = mix(b, t, gridUv.y);

  // Remap perlin from [-1.0, 1.0] to [0.0, 1.0]
  float remappedPerlin = perlin;

  // Define colors based on remappedPerlin ranges
  if (remappedPerlin < 0.) {
    color = vec3(0.0);  // Dark Blue
  } else if (remappedPerlin < 0.1) {
    color = vec3(0.0, 0.15, 0.29);  // Light Blue
  } else if (remappedPerlin < 0.2) {
    color = vec3(0.0, 0.21, 0.41);  // Cyan
  } else if (remappedPerlin < 0.3) {
    color = vec3(0.0, 0.68, 0.59);  // Light Green
  } else if (remappedPerlin < 0.4){
    color = vec3(0.0, 0.45, 0.53);  // White
  }

  gl_FragColor = vec4(color, 1.0);
}
