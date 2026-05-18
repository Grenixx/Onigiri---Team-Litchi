precision mediump float;

uniform float u_time;
uniform vec2 u_resolution;
uniform sampler2D u_texture;

// Fonction pour générer des lignes radiales (les "rayons" du cri)
float radialLines(vec2 dir, float count, float speed) {
    float angle = atan(dir.y, dir.x);
    float value = sin(angle * count + u_time * speed);
    return smoothstep(0.5, 0.8, value);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    vec2 screenCenter = vec2(0.5, 0.5);
    vec2 dir = uv - screenCenter;
    float aspect = u_resolution.x / u_resolution.y;
    dir.x *= aspect;
    float dist = length(dir);

    vec2 totalDistortion = vec2(0.0);
    float glow = 0.0;

    // --- ONDES DE CHOC (Distorsion) ---
    for (float i = 0.0; i < 3.0; i++) {
        float waveTime = fract(u_time * 0.4 - (i * 0.25));
        float radius = waveTime * 1.2;
        
        // Masque de l'onde
        float mask = pow(1.0 - abs(dist - radius), 20.0);
        mask *= (1.0 - waveTime); // Atténuation avec le temps
        
        // Déformation vers l'extérieur
        totalDistortion += normalize(dir) * mask * 0.04;
        glow += mask * 0.2;
    }

    // --- LIGNES DE CRI (Effet visuel) ---
    // On ajoute des lignes de choc qui "vibrent"
    float lines = radialLines(dir, 20.0, 30.0);
    lines *= smoothstep(0.0, 0.4, dist); // Ne pas toucher le centre du visage
    lines *= pow(1.0 - dist, 2.0);      // S'estompe vers les bords
    
    // --- APPLICATION FINALE ---
    // On déforme les UV de la texture d'origine
    vec2 distortedUV = uv - totalDistortion;
    
    // On récupère la couleur de la scène déformée
    vec3 scene = texture2D(u_texture, distortedUV).rgb;
    
    // On ajoute le glow blanc et les lignes radiales
    scene += (glow + lines * 0.15);

    gl_FragColor = vec4(scene, 1.0);
}