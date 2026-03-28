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
      
      // --- CALCULS DU PERLIN NOISE CORRECTS ---
      // 1. On normalise d'abord les coords écran (0.0 -> 1.0)
      vec2 screenSpace = gl_FragCoord.xy / u_resolution.y;
      
      // 2. On applique le facteur de zoom du motif (15x)
      vec2 scaledUv = screenSpace * 15.0;
      
      // 3. On ajoute le déplacement de la caméra APRÈS le zoom
      // Comme ça, quand la cam bouge de 1, le motif bouge de 'scale' unités
      // On multiplie par 0.05 pour compenser le zoom 15x et avoir un mouvement lent
      vec2 parallax = u_camera * 0.05; 
      
      vec2 uv = scaledUv + parallax;
      
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
      vec3 ring = vec3(0.6863, 0.0, 0.0);
      
      // --- LISSAGE DU RENDU (ANTI-JITTER) ---
      // Au lieu de couper net avec des IF, on utilise une onde sinusoïdale basée sur le perlin
      // Cela crée des bandes douces et stables qui ne clignotent pas
      
      // On transforme le bruit [-1, 1] en un motif périodique [0, 1]
      float pattern = 0.5 + 0.5 * sin(perlin * 20.0); 
      
      // On seuille doucement pour garder l'esprit "bandes" mais sans aliasing
      // smoothstep(0.4, 0.6, pattern) permet d'avoir une transition floue sur quelques pixels
      float mask = smoothstep(0.45, 0.55, pattern);
      
      vec3 color = mix(bg, ring, mask);
      
      gl_FragColor = vec4(color, 1.0);
  }
}