#version 130
// Alternatively, use #version 330 core for more modern features


precision mediump float;

uniform float u_time;
uniform float u_trigger_time;
uniform vec2 u_resolution;
uniform vec2 u_pos;
uniform sampler2D u_texture;

void main() {
    float time_since_trigger = u_time - u_trigger_time;
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    vec2 dir = uv - u_pos;
    dir.x *= u_resolution.x / u_resolution.y;
    float dist = length(dir);

    vec2 totalDistortion = vec2(0.0);
    float totalFlash = 0.0;

    // Durée totale de l'effet
    float duration = 1.0;
    if (time_since_trigger > duration || time_since_trigger < 0.0) {
        gl_FragColor = texture2D(u_texture, uv);
        return;
    }

    // On crée 3 ondes décalées dans le temps
    for (float i = 0.0; i < 5.0; i++) {
        // Chaque onde commence avec un retard (i * 0.15)
        float waveTime = (time_since_trigger - (i * 0.15)) * 1.5; 
        if (waveTime < 0.0 || waveTime > 1.0) continue;
        
        float radius = waveTime * 1.2; // L'onde s'étend
        float thickness = 0.025;
        float force = 0.03 * (1.0 - waveTime); // L'onde faiblit en s'éloignant

        // Masque de l'anneau pour l'onde i
        float mask = pow(1.0 - abs(dist - radius), 15.0);
        mask *= step(dist, radius + thickness);
        mask *= step(radius - thickness, dist);

        // On accumule la déformation
        totalDistortion += normalize(dir) * mask * force;
        // On accumule un petit effet de lumière
        totalFlash += mask * 0.15;
    }

    // On applique la déformation totale sur la texture du jeu
    vec3 sceneColor = texture2D(u_texture, uv - totalDistortion).rgb;
    
    // On ajoute l'éclat blanc des ondes
    sceneColor += totalFlash;

    gl_FragColor = vec4(sceneColor, 1.0);
}