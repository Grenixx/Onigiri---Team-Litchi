precision mediump float;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_camera;

vec2 randomGradient(vec2 p) {
  p += 0.02;
  float x = dot(p, vec2(123.4, 234.5));
  float y = dot(p, vec2(234.5, 345.6));
  vec2 gradient = vec2(x, y);
  gradient = sin(gradient);
  gradient *= 43758.5453;
  gradient = sin(gradient + u_time * 0.15);
  return gradient;
}

vec2 quintic(vec2 p) {
  return p * p * p * (10.0 + p * (-15.0 + p * 6.0));
}

void main() {
  // --- CALCULS DU PERLIN NOISE ---
  vec2 uv = (gl_FragCoord.xy + u_camera) / u_resolution.y;
  uv *= 15.0;
  vec2 gridId = floor(uv);
  vec2 gridUv = fract(uv);

  vec2 bl = gridId + vec2(0.0, 0.0);
  vec2 br = gridId + vec2(1.0, 0.0);
  vec2 tl = gridId + vec2(0.0, 1.0);
  vec2 tr = gridId + vec2(1.0, 1.0);

  float dotBl = dot(randomGradient(bl), gridUv - vec2(0.0, 0.0));
  float dotBr = dot(randomGradient(br), gridUv - vec2(1.0, 0.0));
  float dotTl = dot(randomGradient(tl), gridUv - vec2(0.0, 1.0));
  float dotTr = dot(randomGradient(tr), gridUv - vec2(1.0, 1.0));

  vec2 smoothUv = quintic(gridUv);
  float perlin = mix(mix(dotBl, dotBr, smoothUv.x), mix(dotTl, dotTr, smoothUv.x), smoothUv.y);

  // --- TRANSITION CIRCULAIRE DOUCE ---
  vec2 screenUv = gl_FragCoord.xy / u_resolution.xy; 
  //vec2 uv_center = screenUv - 0.5;
  vec2 uv_center = screenUv -0.5;

  uv_center.x *= u_resolution.x / u_resolution. y;
  float dist = length(uv_center);

  // Paramètres de la transition
  float radius =  u_time * 0.5;
  float softness = 0.2; // Plus cette valeur est petite, plus le bord est net (mais anti-aliasé)
  // smoothstep crée un dégradé progressif au bord du cercle
  float transition = smoothstep(radius - softness, radius + softness, dist);

  // --- COULEURS ---
  // Thème A (Extérieur : Bleu/Blanc)
  vec3 bgA = vec3(0.2353, 0.8471, 1.0);
  vec3 ringA = vec3(0.7961, 0.9373, 0.9725);

  // Thème B (Intérieur : Noir/Rouge)
  vec3 bgB = vec3(0.0, 0.0, 0.0);
  vec3 ringB = vec3(0.6863, 0.0, 0.0);

  // On mélange les thèmes en fonction de la transition
  vec3 currentBg = mix(bgB, bgA, transition);
  vec3 currentRing = mix(ringB, ringA, transition);

  // --- DESSIN DES ANNEAUX ---
  vec3 color;
  // Astuce : au lieu de plein de IF, on utilise fract ou step pour les anneaux
  if (perlin < 0.0 || (perlin > 0.1 && perlin < 0.2) || (perlin > 0.3 && perlin < 0.4) || (perlin > 0.6 && perlin < 0.8)) {
    color = currentBg;
  } else {
    color = currentRing;
  }

  gl_FragColor = vec4(color, 1.0);
}