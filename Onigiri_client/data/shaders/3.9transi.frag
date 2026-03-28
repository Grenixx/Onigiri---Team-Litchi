#version 130
precision mediump float;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_camera;
uniform float u_progress; // CONTROLÉ PAR GAME.PY (0.0 fermé -> 1.0 ouvert)
uniform sampler2D u_texture; // L'IMAGE DU JEU

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
  vec2 screenUv = gl_FragCoord.xy / u_resolution.xy; 

  // --- TRANSITION CIRCULAIRE DU JEU ---
  vec2 center = vec2(0.5, 0.5);
  vec2 dir = screenUv - center;
  dir.x *= u_resolution.x / u_resolution.y;
  float dist = length(dir);

  // Le rayon est piloté par u_progress (envoyé par le Python)
  // * 1.5 pour s'assurer que ça ouvre tout l'écran à la fin
  float radius = u_progress * 1.5; 

  // Si on est DANS le cercle, on affiche le JEU
  if (dist < radius) {
      gl_FragColor = texture2D(u_texture, screenUv);
  } 
  else {
      // SINON, on affiche ton effet Perlin stylé (Background)
      
      // --- CALCULS DU PERLIN NOISE (Ton code original) ---
      // On ajoute un facteur de parallaxe (ex: 0.5 * u_camera)
      // Si tu veux que le fond bouge MOINS vite que le joueur (effet loin) : 0.2 ou 0.5
      // Si tu veux que le fond bouge PLUS vite : 1.5 ou 2.0
      vec2 parallaxOffset = u_camera * 0.5; 
      vec2 uv = (gl_FragCoord.xy + parallaxOffset) / u_resolution.y;
      
      uv *= 15.0; // Échelle du bruit
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

      // --- COULEURS ---
      vec3 bg = vec3(0.0, 0.0, 0.0);
      vec3 ring = vec3(0.0392, 0.0392, 0.0392);
      
      vec3 color;
      if (perlin < 0.0 || (perlin > 0.1 && perlin < 0.2) || (perlin > 0.3 && perlin < 0.4) || (perlin > 0.6 && perlin < 0.8)) {
        color = bg;
      } else {
        color = ring;
      }
      
      gl_FragColor = vec4(color, 1.0);
  }
}